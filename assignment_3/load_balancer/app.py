import os
import logging
import logging.config
from flask import Flask
from assignment_3.config import LOGGING
from load_balancer.load_balancer_routes import loadbalancer_api, lb

def register_default_nodes(logger):
    """Register the default nodes from docker-compose"""
    nodes = [
        {"host": "node1", "port": 50001, "name": "file-server-1"},
        {"host": "node2", "port": 50002, "name": "file-server-2"},
        {"host": "node3", "port": 50003, "name": "file-server-3"}
    ]
    
    for node in nodes:
        try:
            node_id = lb.add_node(node["host"], node["port"], node["name"])
            logger.info(f'Registered node {node["name"]} at {node["host"]}:{node["port"]} with ID: {node_id}')
        except Exception as e:
            logger.error(f'Failed to register node {node["name"]} at {node["host"]}:{node["port"]}: {str(e)}')

def make_app():
    app = Flask(__name__)
    
    logging.config.dictConfig(LOGGING)
    logger = logging.getLogger('load_balancer')
    logger.info('Load balancer starting up')
    
    app.logger = logger
    
    app.register_blueprint(loadbalancer_api, url_prefix='/api/v0')
    
    logger.info('Registering default nodes...')
    register_default_nodes(logger)
    
    registered_nodes = lb.list_nodes()
    logger.info(f'Total registered nodes: {len(registered_nodes)}')
    for node in registered_nodes:
        logger.info(f'Node: {node["name"]} - {node["destination"]["host"]}:{node["destination"]["port"]} (ID: {node["id"]})')
    
    logger.info('Load balancer initialized successfully')
    return app

if __name__ == '__main__':
    app = make_app()
    port = int(os.environ.get("PORT", 40001))
    app.logger.info(f'Starting load balancer on port {port}')
    app.run(host='0.0.0.0', port=port, debug=True)
