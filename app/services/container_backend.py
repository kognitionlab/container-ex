from abc import ABC, abstractmethod
import subprocess
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class ContainerBackend(ABC):
    """Abstract base class for container backends"""
    
    @abstractmethod
    def run_container(self, command: str, timeout: int = 60) -> Tuple[int, str, str]:
        """Run a container command"""
        pass
    
    @abstractmethod
    def exec_command(self, container_id: str, command: str, timeout: int = 300) -> Tuple[int, str, str]:
        """Execute a command inside a container"""
        pass
    
    @abstractmethod
    def get_container_status(self, container_id: str) -> str:
        """Get container status"""
        pass
    
    @abstractmethod
    def stop_container(self, container_id: str) -> Tuple[int, str, str]:
        """Stop a container"""
        pass
    
    @abstractmethod
    def get_container_logs(self, container_id: str) -> Tuple[int, str, str]:
        """Get container logs"""
        pass

class DockerBackend(ContainerBackend):
    """Docker backend implementation"""
    
    def run_container(self, command: str, timeout: int = 60) -> Tuple[int, str, str]:
        """Run a docker container"""
        result = subprocess.run(
            command.split(),
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    
    def exec_command(self, container_id: str, command: str, timeout: int = 300) -> Tuple[int, str, str]:
        """Execute a command inside a docker container"""
        result = subprocess.run(
            ['docker', 'exec', container_id] + command.split(),
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    
    def get_container_status(self, container_id: str) -> str:
        """Get docker container status"""
        try:
            result = subprocess.run(
                ['docker', 'inspect', container_id, '--format', '{{.State.Status}}'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as e:
            logger.error(f"Error getting docker container status: {e}")
        return "unknown"
    
    def stop_container(self, container_id: str) -> Tuple[int, str, str]:
        """Stop a docker container"""
        result = subprocess.run(
            ['docker', 'stop', container_id],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode, result.stdout, result.stderr
    
    def get_container_logs(self, container_id: str) -> Tuple[int, str, str]:
        """Get docker container logs"""
        result = subprocess.run(
            ['docker', 'logs', container_id],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode, result.stdout, result.stderr

class PodmanBackend(ContainerBackend):
    """Podman backend implementation"""
    
    def run_container(self, command: str, timeout: int = 60) -> Tuple[int, str, str]:
        """Run a podman container"""
        # Replace 'docker' with 'podman' in the command
        podman_command = command.replace('docker', 'podman', 1)
        result = subprocess.run(
            podman_command.split(),
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    
    def exec_command(self, container_id: str, command: str, timeout: int = 300) -> Tuple[int, str, str]:
        """Execute a command inside a podman container"""
        result = subprocess.run(
            ['podman', 'exec', container_id] + command.split(),
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    
    def get_container_status(self, container_id: str) -> str:
        """Get podman container status"""
        try:
            result = subprocess.run(
                ['podman', 'inspect', container_id, '--format', '{{.State.Status}}'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as e:
            logger.error(f"Error getting podman container status: {e}")
        return "unknown"
    
    def stop_container(self, container_id: str) -> Tuple[int, str, str]:
        """Stop a podman container"""
        result = subprocess.run(
            ['podman', 'stop', container_id],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode, result.stdout, result.stderr
    
    def get_container_logs(self, container_id: str) -> Tuple[int, str, str]:
        """Get podman container logs"""
        result = subprocess.run(
            ['podman', 'logs', container_id],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode, result.stdout, result.stderr

def get_backend(backend_type: str) -> ContainerBackend:
    """Factory function to get the appropriate backend"""
    if backend_type.lower() == 'podman':
        return PodmanBackend()
    return DockerBackend()  # Default to Docker 