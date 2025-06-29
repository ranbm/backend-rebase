from users.logger.log_types import LogEvent
import json
import logging

logger = logging.getLogger('rbm_awesome_logger')


def log_user_event(event: LogEvent, user_id: str):
    logger.info(json.dumps({
        "event": event,
        "user_id": user_id
    }))


def log_error_event(event: LogEvent, error: str):
    logger.error(json.dumps({
        "event": event,
        "error": error
    }))


def log_user_retrieval_event(event: LogEvent, user_id: str = None):
    log_data = {
        "event": event
    }
    if user_id:
        log_data["user_id"] = user_id
    
    logger.info(json.dumps(log_data))


def log_user_deletion_event(event: LogEvent, user_id: str = None):
    log_data = {
        "event": event
    }
    if user_id:
        log_data["user_id"] = user_id
    
    logger.info(json.dumps(log_data))