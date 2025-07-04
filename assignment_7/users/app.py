import atexit
import logging
import logging.config
import signal
import sys
import threading
import time
from contextlib import contextmanager

from flask import Flask, jsonify
from users.api.v0.users_routes import users_api
from users.config import LOGGING
from users.db_utils import get_connection

_app_ready = False
_shutdown_event = threading.Event()


def check_database_connection(max_retries=5, retry_delay=2):
    for attempt in range(max_retries):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            logging.error(f"Database connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
    return False


def setup_graceful_shutdown(app):
    def shutdown_handler(signum, frame):
        logging.info(f"Received signal {signum}, initiating graceful shutdown...")
        _shutdown_event.set()
        
        shutdown_timeout = 30
        logging.info(f"Waiting up to {shutdown_timeout}s for requests to complete...")
        time.sleep(2)
        
        logging.info("Shutdown complete")
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, shutdown_handler)  # Docker stop
    signal.signal(signal.SIGINT, shutdown_handler)   # Ctrl+C
    
    atexit.register(lambda: logging.info("Application cleanup completed"))


@contextmanager
def application_lifecycle():
    global _app_ready
    
    logging.info("=== APPLICATION STARTUP ===")
    
    try:
        logging.info("Checking database connection...")
        if not check_database_connection():
            raise Exception("Database connection failed after retries")
        logging.info("Database connection verified")
        
        _app_ready = True
        logging.info("Application ready to serve requests")
        
        yield
        
    except Exception as e:
        logging.error(f"Startup failed: {e}")
        raise
    finally:
        logging.info("=== APPLICATION SHUTDOWN ===")
        _app_ready = False


def make_app():
    app = Flask(__name__)

    logging.config.dictConfig(LOGGING)
    logger = logging.getLogger('rbm_awesome_logger')
    
    setup_graceful_shutdown(app)
    
    @app.route('/health', methods=['GET'])
    def health_check():
        if not _app_ready:
            return jsonify({
                "status": "starting",
                "message": "Application is initializing"
            }), 503
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            conn.close()
            db_status = "healthy"
        except Exception:
            db_status = "unhealthy"
        
        status_code = 200 if db_status == "healthy" else 503
        return jsonify({
            "status": "ready" if db_status == "healthy" else "degraded",
            "database": db_status,
            "timestamp": time.time()
        }), status_code

    @app.route('/ready', methods=['GET'])
    def readiness_check():
        if _app_ready:
            return jsonify({"status": "ready"}), 200
        else:
            return jsonify({"status": "not ready"}), 503

    app.register_blueprint(users_api, url_prefix='/users')
    
    @app.before_request
    def check_shutdown():
        if _shutdown_event.is_set():
            return jsonify({"error": "Service shutting down"}), 503

    return app


def run_app():
    app = make_app()
    
    with application_lifecycle():
        logger = logging.getLogger('rbm_awesome_logger')
        logger.info('Starting rbm_awesome_app on port 5001')
        
        app.run(
            host='0.0.0.0', 
            port=5001,
            debug=False,
            use_reloader=False
        )


if __name__ == '__main__':
    try:
        run_app()
    except KeyboardInterrupt:
        logging.info("Received keyboard interrupt")
    except Exception as e:
        logging.error(f"Application failed to start: {e}")
        sys.exit(1)
