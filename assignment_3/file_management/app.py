import os
import logging
import logging.config
import requests
import time
import threading
from flask import Flask

from assignment_3.config import LOGGING
from file_management.api.v0.file_management_routes import file_server, init_usage

def auto_register_with_load_balancer(logger, port):
    """Try to register this node with the load balancer if MASTER_NODE_ADDRESS is set"""
    master_address = os.getenv('MASTER_NODE_ADDRESS')
    if not master_address:
        logger.info('MASTER_NODE_ADDRESS not set, skipping auto-registration')
        return
    
    logger.info(f'Auto-registration enabled, master address: {master_address}')
    
    container_name = os.getenv('HOSTNAME', 'localhost')  # Docker sets HOSTNAME to container name
    
    registration_payload = {
        "destination": {
            "host": container_name,
            "port": port
        },
        "name": f"auto-{container_name}"
    }
    
    registration_url = f"http://{master_address}/api/v0/internal/nodes"
    
    start_time = time.time()
    timeout = 30
    
    while time.time() - start_time < timeout:
        try:
            logger.info(f'Attempting to register with load balancer at {registration_url}')
            response = requests.post(
                registration_url,
                json=registration_payload,
                timeout=5
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f'Successfully registered with load balancer, node ID: {result.get("id")}')
                return
            elif response.status_code == 403:
                logger.warning('Registration rejected: registration period is over')
                return
            else:
                logger.error(f'Registration failed with status {response.status_code}: {response.text}')
                
        except requests.exceptions.RequestException as e:
            logger.error(f'Failed to connect to load balancer: {str(e)}')
        
        # Wait 2 seconds before retrying
        time.sleep(2)
    
    logger.error(f'Failed to register with load balancer after {timeout} seconds')

def make_app():
    app = Flask(__name__)

    app.config['MAX_LENGTH'] = 10 * 1024 * 1024       # 10 MB per blob
    app.config['MAX_ID_LENGTH'] = 200                 # Max ID length
    app.config['MAX_HEADER_LENGTH'] = 50              # Max header name/value length
    app.config['MAX_HEADER_COUNT'] = 20               # Max number of stored headers
    app.config['MAX_DISK_QUOTA'] = 1 * 1024 * 1024 * 1024  # 1 GB total
    app.config['DATA_DIR'] = 'data'                   # Storage root

    logging.config.dictConfig(LOGGING)
    logger = logging.getLogger('file_management')
    logger.info('File management service starting up')

    logger.info(f'Max blob size: {app.config["MAX_LENGTH"] / (1024*1024):.1f} MB')
    logger.info(f'Max disk quota: {app.config["MAX_DISK_QUOTA"] / (1024*1024*1024):.1f} GB')
    logger.info(f'Data directory: {app.config["DATA_DIR"]}')

    file_server.logger = logger
    app.register_blueprint(file_server, url_prefix='/api/v0')

    logger.info('Initializing storage usage tracking...')
    init_usage(app.config['DATA_DIR'])
    logger.info('File management service initialized successfully')

    return app, logger


if __name__ == '__main__':
    app, logger = make_app()
    port = int(os.environ.get("PORT", 50001))
    app.logger = logger
    app.logger.info(f'Starting file management service on port {port}')
    
    if os.getenv('MASTER_NODE_ADDRESS'):
        registration_thread = threading.Thread(
            target=auto_register_with_load_balancer,
            args=(logger, port),
            daemon=True
        )
        registration_thread.start()
    
    app.run(host='0.0.0.0', port=port)