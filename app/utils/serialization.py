from datetime import datetime
from typing import Any, Dict

from app.models.container import ExecutionResult

def serialize_execution(execution: ExecutionResult) -> Dict[str, Any]:
    """Convert ExecutionResult to JSON-serializable dict"""
    result = {
        'id': execution.id,
        'docker_command': execution.docker_command,
        'test_command': execution.test_command,
        'status': execution.status.value,
        'container_id': execution.container_id,
        'container_name': execution.container_name,
        'test_output': execution.test_output,
        'error_message': execution.error_message,
        'exit_code': execution.exit_code
    }
    
    # Convert datetime objects to ISO format strings
    if execution.start_time:
        result['start_time'] = execution.start_time.isoformat()
    if execution.end_time:
        result['end_time'] = execution.end_time.isoformat()
    
    return result 