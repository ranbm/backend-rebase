import requests
from functools import wraps

def log_handler(logger, extra_fields=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                extra = extra_fields or {}
                logger.info(f"Calling {func.__name__} with args: {args}, kwargs: {kwargs}", extra=extra)
                response = func(*args, **kwargs)
                logger.info(f"{func.__name__} succeeded with status code {response.status_code}", extra=extra)
                return response
            except requests.exceptions.HTTPError as http_err:
                logger.error(f"HTTP error in {func.__name__}: {http_err}", extra=extra)
                raise
            except requests.exceptions.RequestException as req_err:
                logger.error(f"Request error in {func.__name__}: {req_err}", extra=extra)
                raise
        return wrapper
    return decorator