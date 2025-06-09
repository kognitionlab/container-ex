from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

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