import os
import logging
from flask import Flask, render_template
from flask_swagger_ui import get_swaggerui_blueprint

from app.services.container_manager import ContainerManager
from app.services.container_backend import get_backend
from app.api.routes import init_api

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app(backend_type: str = 'docker'):
    app = Flask(__name__)
    app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-this')
    
    # Initialize container manager with selected backend
    backend = get_backend(backend_type)
    container_manager = ContainerManager(backend)
    
    # Register API routes
    api = init_api(container_manager)
    app.register_blueprint(api, url_prefix='/api')
    
    # Configure Swagger UI
    SWAGGER_URL = '/api/docs'
    API_URL = '/static/openapi.yml'
    
    swaggerui_blueprint = get_swaggerui_blueprint(
        SWAGGER_URL,
        API_URL,
        config={
            'app_name': "Container Test Manager API"
        }
    )
    app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)
    
    @app.route('/')
    def index():
        """Main page with container execution form"""
        return render_template('index.html')
    
    @app.route('/history')
    def history():
        """History page showing all executions"""
        return render_template('history.html')
    
    return app 