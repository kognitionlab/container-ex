import threading
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional

from app.models.container import ContainerStatus, ExecutionResult
from app.services.container_backend import ContainerBackend

logger = logging.getLogger(__name__)

class ContainerManager:
    def __init__(self, backend: ContainerBackend):
        self.executions: Dict[str, ExecutionResult] = {}
        self.lock = threading.Lock()
        self.backend = backend
    
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
        """Get container status from backend"""
        return self.backend.get_container_status(container_id) 