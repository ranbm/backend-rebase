from users.logger.log_types import LogEvent
import json
import logging

# Get the same logger configured in app.py with logz.io handler
logger = logging.getLogger('rbm_awesome_logger')


def log_user_event(event: LogEvent, user_id: str, email: str):
    """Log a user-related event"""
    logger.info(json.dumps({
        "event": event,
        "user_id": user_id,
        "email": email
    }))


def log_error_event(event: LogEvent, error: str):
    """Log an error event"""
    logger.error(json.dumps({
        "event": event,
        "error": error
    }))


def log_user_retrieval_event(event: LogEvent, email: str, user_id: str = None):
    """Log a user retrieval event (with optional user_id)"""
    log_data = {
        "event": event,
        "email": email
    }
    if user_id:
        log_data["user_id"] = user_id
    
    logger.info(json.dumps(log_data))


def log_user_deletion_event(event: LogEvent, email: str, user_id: str = None):
    """Log a user deletion event (with optional user_id)"""
    log_data = {
        "event": event,
        "email": email
    }
    if user_id:
        log_data["user_id"] = user_id
    
    logger.info(json.dumps(log_data))