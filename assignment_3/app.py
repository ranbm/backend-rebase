import logging
import logging.config
from assignment_3.api.v0.file_management_routes import file_management
from assignment_3.config import LOGGING


def make_app():
    from flask import Flask

    app = Flask(__name__)

    # Set up application configuration
    app.config['MAX_LENGTH'] = 10 * 1024 * 1024  # 10 MB
    app.config['MAX_ID_LENGTH'] = 64
    app.config['MAX_HEADER_LENGTH'] = 256
    app.config['MAX_HEADER_COUNT'] = 100
    app.config['MAX_DISK_QUOTA'] = 100 * 1024 * 1024  # 100 MB
    app.config['MAX_BLOBS_IN_FOLDER'] = 1000
    app.config['DATA_DIR'] = 'data'

    logging.config.dictConfig(LOGGING)
    logger_extra_fields = {
        'app_name': 'rbm_awesome_app',
    }
    logger = logging.getLogger('rbm_awesome_logger')
    logger.info('rbm awesome logger is set up', extra=logger_extra_fields)

    file_management.logger = logger
    app.register_blueprint(file_management, url_prefix='/api/v0')

    return app

if __name__ == "__main__":
    app = make_app()
    app.run(host="0.0.0.0", port=50001)