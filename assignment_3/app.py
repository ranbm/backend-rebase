import os
import logging
import logging.config
from flask import Flask
from assignment_3.config import LOGGING
from assignment_3.api.v0.file_management_routes import file_server, init_usage


def make_app():
    # Create Flask app
    app = Flask(__name__)

    # Application configuration
    app.config['MAX_LENGTH'] = 10 * 1024 * 1024       # 10 MB per blob
    app.config['MAX_ID_LENGTH'] = 200                 # Max ID length
    app.config['MAX_HEADER_LENGTH'] = 50              # Max header name/value length
    app.config['MAX_HEADER_COUNT'] = 20               # Max number of stored headers
    app.config['MAX_DISK_QUOTA'] = 1 * 1024 * 1024 * 1024  # 1 GB total
    app.config['DATA_DIR'] = 'data'                   # Storage root

    # Logging setup
    logging.config.dictConfig(LOGGING)
    logger = logging.getLogger('rbm_awesome_logger')
    logger.info('Logger initialized for rbm_awesome_app')

    # Attach the blueprint and logger
    file_server.logger = logger
    app.register_blueprint(file_server, url_prefix='/api/v0')

    init_usage(app.config['DATA_DIR'])

    return app


if __name__ == '__main__':
    app = make_app()
    app.run(host='0.0.0.0', port=50001)