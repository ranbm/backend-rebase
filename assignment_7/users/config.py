import os

LOGZIO_API_KEY = os.getenv("logzIO_api_key")

# Check if we're in test mode
IS_TESTING = os.getenv("TESTING", "false").lower() == "true"

if not LOGZIO_API_KEY and not IS_TESTING:
    raise RuntimeError("Missing environment variable: LOGZIO_API_KEY")

TEST_LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '%(levelname)s - %(message)s',
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'simple',
            'stream': 'ext://sys.stdout'
        },
        'null': {
            'class': 'logging.NullHandler',
            'level': 'DEBUG'
        }
    },
    'loggers': {
        'rbm_awesome_logger': {
            'level': 'DEBUG',
            'handlers': ['null'],  # Use null handler to suppress logs during tests
            'propagate': False
        },
        'werkzeug': {
            'level': 'ERROR',
            'handlers': [],
            'propagate': False
        }
    }
}

# Production logging configuration (logz.io)
PRODUCTION_LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'logzioFormat': {
            'format': '%(message)s',
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
        'rbm_awesome_logger': {
            'level': 'DEBUG',
            'handlers': ['logzio'],
            'propagate': False
        },
        'werkzeug': {
            'level': 'ERROR',
            'handlers': [],
            'propagate': False
        }
    }
}

LOGGING = TEST_LOGGING if IS_TESTING else PRODUCTION_LOGGING
