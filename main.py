#!/usr/bin/env python3
"""
Docker Container Test Manager
A Flask web application for managing docker containers and running test commands.
"""

import os
import subprocess
import threading
import time
import uuid
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from enum import Enum
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-this')

class ContainerStatus(Enum):
    PENDING = "pending"
    STARTING = "starting"
    RUNNING = "running"
    TESTING = "testing"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"

@dataclass
class ExecutionResult:
    id: str
    docker_command: str
    test_command: str
    status: ContainerStatus
    container_id: Optional[str] = None
    container_name: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    test_output: Optional[str] = None
    error_message: Optional[str] = None
    exit_code: Optional[int] = None

class ContainerManager:
    def __init__(self):
        self.executions: Dict[str, ExecutionResult] = {}
        self.lock = threading.Lock()

    def create_execution(self, docker_command: str, test_command: str) -> str:
        """Create a new execution record"""
        execution_id = str(uuid.uuid4())
        execution = ExecutionResult(
            id=execution_id,
            docker_command=docker_command,
            test_command=test_command,
            status=ContainerStatus.PENDING,
            start_time=datetime.now()
        )

        with self.lock:
            self.executions[execution_id] = execution

        return execution_id

    def update_execution(self, execution_id: str, **kwargs):
        """Update execution record"""
        with self.lock:
            if execution_id in self.executions:
                execution = self.executions[execution_id]
                for key, value in kwargs.items():
                    if hasattr(execution, key):
                        setattr(execution, key, value)

    def get_execution(self, execution_id: str) -> Optional[ExecutionResult]:
        """Get execution by ID"""
        with self.lock:
            return self.executions.get(execution_id)

    def get_all_executions(self) -> List[ExecutionResult]:
        """Get all executions"""
        with self.lock:
            return list(self.executions.values())

    def delete_execution(self, execution_id: str) -> bool:
        """Delete execution record"""
        with self.lock:
            if execution_id in self.executions:
                del self.executions[execution_id]
                return True
        return False

    def get_container_status(self, container_id: str) -> str:
        """Get container status from docker"""
        try:
            result = subprocess.run(
                ['docker', 'inspect', container_id, '--format', '{{.State.Status}}'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as e:
            logger.error(f"Error getting container status: {e}")
        return "unknown"

def run_container_test(manager: ContainerManager, execution_id: str):
    """Run container and execute test command in background"""
    execution = manager.get_execution(execution_id)
    if not execution:
        return

    try:
        # Update status to starting
        manager.update_execution(execution_id, status=ContainerStatus.STARTING)

        # Parse docker command to extract container name if provided
        docker_args = execution.docker_command.split()
        container_name = None

        # Look for --name flag
        if '--name' in docker_args:
            name_index = docker_args.index('--name')
            if name_index + 1 < len(docker_args):
                container_name = docker_args[name_index + 1]

        # If no name provided, generate one
        if not container_name:
            container_name = f"test-container-{execution_id[:8]}"
            # Insert --name and container_name before the image name (last argument)
            docker_args.insert(-1, '--name')
            docker_args.insert(-1, container_name)

        # Add detach flag if not present
        if '-d' not in docker_args and '--detach' not in docker_args:
            docker_args.insert(-1, '-d')

        # Run the container
        logger.info(f"Starting container with command: {' '.join(docker_args)}")
        result = subprocess.run(docker_args, capture_output=True, text=True, timeout=60)

        if result.returncode != 0:
            manager.update_execution(
                execution_id,
                status=ContainerStatus.FAILED,
                error_message=f"Failed to start container: {result.stderr}",
                end_time=datetime.now()
            )
            return

        container_id = result.stdout.strip()
        manager.update_execution(
            execution_id,
            container_id=container_id,
            container_name=container_name,
            status=ContainerStatus.RUNNING
        )

        # Wait for container to be ready
        time.sleep(2)

        # Check if container is still running
        container_status = manager.get_container_status(container_id)
        if container_status not in ['running', 'up']:
            # Get container logs for debugging
            log_result = subprocess.run(
                ['docker', 'logs', container_id],
                capture_output=True, text=True, timeout=30
            )
            manager.update_execution(
                execution_id,
                status=ContainerStatus.FAILED,
                error_message=f"Container exited with status: {container_status}. Logs: {log_result.stdout}",
                end_time=datetime.now()
            )
            return

        # Run test command inside container
        manager.update_execution(execution_id, status=ContainerStatus.TESTING)

        test_result = subprocess.run(
            ['docker', 'exec', container_id] + execution.test_command.split(),
            capture_output=True, text=True, timeout=300
        )

        # Update execution with results
        manager.update_execution(
            execution_id,
            status=ContainerStatus.COMPLETED if test_result.returncode == 0 else ContainerStatus.FAILED,
            test_output=test_result.stdout,
            error_message=test_result.stderr if test_result.stderr else None,
            exit_code=test_result.returncode,
            end_time=datetime.now()
        )

    except subprocess.TimeoutExpired:
        manager.update_execution(
            execution_id,
            status=ContainerStatus.FAILED,
            error_message="Command execution timed out",
            end_time=datetime.now()
        )
    except Exception as e:
        logger.error(f"Error in container test execution: {e}")
        manager.update_execution(
            execution_id,
            status=ContainerStatus.FAILED,
            error_message=str(e),
            end_time=datetime.now()
        )

# Global container manager instance
container_manager = ContainerManager()

@app.route('/')
def index():
    """Main page with container execution form"""
    return render_template('index.html')

@app.route('/execute', methods=['POST'])
def execute_container():
    """Execute docker command and test"""
    data = request.get_json()
    docker_command = data.get('docker_command', '').strip()
    test_command = data.get('test_command', '').strip()

    if not docker_command or not test_command:
        return jsonify({'error': 'Both docker command and test command are required'}), 400

    # Validate docker command starts with 'docker run'
    if not docker_command.startswith('docker run'):
        return jsonify({'error': 'Command must start with "docker run"'}), 400

    # Create execution record
    execution_id = container_manager.create_execution(docker_command, test_command)

    # Start background thread for execution
    thread = threading.Thread(
        target=run_container_test,
        args=(container_manager, execution_id)
    )
    thread.daemon = True
    thread.start()

    return jsonify({'execution_id': execution_id})

def serialize_execution(execution: ExecutionResult) -> dict:
    """Convert ExecutionResult to JSON-serializable dict"""
    data = asdict(execution)
    # Convert enum to string
    data['status'] = execution.status.value
    # Convert datetime objects to ISO strings
    if execution.start_time:
        data['start_time'] = execution.start_time.isoformat()
    if execution.end_time:
        data['end_time'] = execution.end_time.isoformat()
    return data

@app.route('/status/<execution_id>')
def get_status(execution_id):
    """Get execution status"""
    execution = container_manager.get_execution(execution_id)
    if not execution:
        return jsonify({'error': 'Execution not found'}), 404

    return jsonify(serialize_execution(execution))

@app.route('/history')
def history():
    """History page showing all executions"""
    return render_template('history.html')

@app.route('/api/executions')
def get_executions():
    """Get all executions as JSON"""
    executions = container_manager.get_all_executions()
    return jsonify([serialize_execution(execution) for execution in executions])

@app.route('/api/executions/<execution_id>', methods=['DELETE'])
def delete_execution(execution_id):
    """Delete an execution and its container"""
    execution = container_manager.get_execution(execution_id)
    if not execution:
        return jsonify({'error': 'Execution not found'}), 404

    # Stop and remove container if it exists
    if execution.container_id:
        try:
            subprocess.run(['docker', 'stop', execution.container_id], timeout=30)
            subprocess.run(['docker', 'rm', execution.container_id], timeout=30)
        except Exception as e:
            logger.error(f"Error cleaning up container: {e}")

    # Delete execution record
    container_manager.delete_execution(execution_id)
    return jsonify({'success': True})

@app.route('/api/containers/<container_id>/stop', methods=['POST'])
def stop_container(container_id):
    """Stop a running container"""
    try:
        result = subprocess.run(['docker', 'stop', container_id], timeout=30)
        if result.returncode == 0:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to stop container'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9595, debug=False)