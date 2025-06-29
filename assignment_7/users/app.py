import logging
import logging.config

from flask import Flask
from users.api.v0.users_routes import users_api
from users.config import LOGGING
def make_app():
    app = Flask(__name__)

    logging.config.dictConfig(LOGGING)
    logger = logging.getLogger('rbm_awesome_logger')
    logger.info('Logger initialized for rbm_awesome_app')

    app.register_blueprint(users_api, url_prefix='/users')

    return app


if __name__ == '__main__':
    app = make_app()
    app.run(host='0.0.0.0', port=5001)
