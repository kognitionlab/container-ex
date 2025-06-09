import threading
from flask import Blueprint, jsonify, request

from app.services.container_manager import ContainerManager
from app.services.container_executor import ContainerExecutor
from app.services.container_backend import get_backend
from app.utils.serialization import serialize_execution

api = Blueprint('api', __name__)

def init_api(container_manager: ContainerManager):
    container_executor = ContainerExecutor(container_manager)
    
    @api.route('/execute', methods=['POST'])
    def execute_container():
        """Execute docker command and test"""
        data = request.get_json()
        docker_command = data.get('docker_command', '').strip()
        test_command = data.get('test_command', '').strip()
        backend_type = data.get('backend', 'docker').lower()
        
        if not docker_command or not test_command:
            return jsonify({'error': 'Both docker command and test command are required'}), 400
        
        # Validate docker command starts with 'docker run'
        if not docker_command.startswith('docker run'):
            return jsonify({'error': 'Command must start with "docker run"'}), 400
        
        # Create execution record
        execution_id = container_manager.create_execution(docker_command, test_command)
        
        # Start background thread for execution
        thread = threading.Thread(
            target=container_executor.run_container_test,
            args=(execution_id,)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({'execution_id': execution_id})

    @api.route('/status/<execution_id>')
    def get_status(execution_id):
        """Get execution status"""
        execution = container_manager.get_execution(execution_id)
        if not execution:
            return jsonify({'error': 'Execution not found'}), 404
        return jsonify(serialize_execution(execution))

    @api.route('/executions')
    def get_executions():
        """Get all executions"""
        executions = container_manager.get_all_executions()
        return jsonify([serialize_execution(execution) for execution in executions])

    @api.route('/executions/<execution_id>', methods=['DELETE'])
    def delete_execution(execution_id):
        """Delete execution record"""
        if container_manager.delete_execution(execution_id):
            return '', 204
        return jsonify({'error': 'Execution not found'}), 404

    @api.route('/containers/<container_id>/stop', methods=['POST'])
    def stop_container(container_id):
        """Stop a running container"""
        try:
            returncode, stdout, stderr = container_manager.backend.stop_container(container_id)
            if returncode == 0:
                return jsonify({'message': 'Container stopped successfully'})
            return jsonify({'error': f'Failed to stop container: {stderr}'}), 500
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return api 