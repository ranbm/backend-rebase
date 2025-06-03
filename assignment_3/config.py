import os
import logging.config

LOGZIO_API_KEY = os.getenv("logzIO_api_key")
if not LOGZIO_API_KEY:
    raise RuntimeError("Missing environment variable: LOGZIO_API_KEY")

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'logzioFormat': {
            'format': '{"additional_field": "value"}',
            'validate': False
        }
    },
    'handlers': {
        'logzio': {
            'class': 'logzio.handler.LogzioHandler',
            'level': 'INFO',
            'formatter': 'logzioFormat',
            'token': LOGZIO_API_KEY,
            'logzio_type': 'rbm-logs',
            'logs_drain_timeout': 5,
            'url': 'https://listener-eu.logz.io:8071',
            'retries_no': 4,
            'retry_timeout': 2,
        }
    },
    'loggers': {
        '': {
            'level': 'DEBUG',
            'handlers': ['logzio'],
            'propagate': True
        }
    }
}


