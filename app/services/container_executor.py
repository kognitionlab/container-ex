import time
import logging
from datetime import datetime

from app.models.container import ContainerStatus
from app.services.container_manager import ContainerManager

logger = logging.getLogger(__name__)

class ContainerExecutor:
    def __init__(self, manager: ContainerManager):
        self.manager = manager

    def run_container_test(self, execution_id: str):
        """Run container and execute test command in background"""
        execution = self.manager.get_execution(execution_id)
        if not execution:
            return
        
        try:
            # Update status to starting
            self.manager.update_execution(execution_id, status=ContainerStatus.STARTING)
            
            # Parse docker command to extract container name if provided
            docker_args = execution.docker_command.split()
            container_name = self._extract_container_name(docker_args, execution_id)
            
            # Add detach flag if not present
            if '-d' not in docker_args and '--detach' not in docker_args:
                docker_args.append('-d')
            
            # Run the container
            logger.info(f"Starting container with command: {' '.join(docker_args)}")
            returncode, stdout, stderr = self.manager.backend.run_container(' '.join(docker_args))
            
            if returncode != 0:
                self._handle_container_start_failure(execution_id, stderr)
                return
            
            container_id = stdout.strip()
            self.manager.update_execution(
                execution_id,
                container_id=container_id,
                container_name=container_name,
                status=ContainerStatus.RUNNING
            )
            
            # Wait for container to be ready
            time.sleep(2)
            
            # Check if container is still running
            container_status = self.manager.get_container_status(container_id)
            if container_status not in ['running', 'up']:
                self._handle_container_failure(execution_id, container_id, container_status)
                return
            
            # Run test command inside container
            self._execute_test_command(execution_id, container_id, execution.test_command)
            
        except Exception as e:
            self._handle_execution_error(execution_id, e)

    def _extract_container_name(self, docker_args: list, execution_id: str) -> str:
        """Extract or generate container name from docker arguments"""
        if '--name' in docker_args:
            name_index = docker_args.index('--name')
            if name_index + 1 < len(docker_args):
                return docker_args[name_index + 1]
        return f"test-container-{execution_id[:8]}"

    def _handle_container_start_failure(self, execution_id: str, error_message: str):
        """Handle container start failure"""
        self.manager.update_execution(
            execution_id,
            status=ContainerStatus.FAILED,
            error_message=f"Failed to start container: {error_message}",
            end_time=datetime.now()
        )

    def _handle_container_failure(self, execution_id: str, container_id: str, container_status: str):
        """Handle container failure after start"""
        returncode, stdout, stderr = self.manager.backend.get_container_logs(container_id)
        self.manager.update_execution(
            execution_id,
            status=ContainerStatus.FAILED,
            error_message=f"Container exited with status: {container_status}. Logs: {stdout}",
            end_time=datetime.now()
        )

    def _execute_test_command(self, execution_id: str, container_id: str, test_command: str):
        """Execute test command in container"""
        self.manager.update_execution(execution_id, status=ContainerStatus.TESTING)
        
        returncode, stdout, stderr = self.manager.backend.exec_command(container_id, test_command)
        
        self.manager.update_execution(
            execution_id,
            status=ContainerStatus.COMPLETED if returncode == 0 else ContainerStatus.FAILED,
            test_output=stdout,
            error_message=stderr if stderr else None,
            exit_code=returncode,
            end_time=datetime.now()
        )

    def _handle_execution_error(self, execution_id: str, error: Exception):
        """Handle general execution error"""
        logger.error(f"Error in container test execution: {error}")
        self.manager.update_execution(
            execution_id,
            status=ContainerStatus.FAILED,
            error_message=str(error),
            end_time=datetime.now()
        ) 