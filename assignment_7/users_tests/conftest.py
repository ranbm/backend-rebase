import pytest
import os
from unittest.mock import patch, MagicMock

os.environ.setdefault('logzIO_api_key', 'test-api-key-for-pytest')

from users.app import make_app
from users.db_utils import get_connection


@pytest.fixture
def app():
    app = make_app()
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def mock_db():
    with patch('users.db_utils.get_connection') as mock_conn:
        yield mock_conn


@pytest.fixture(autouse=True) 
def mock_logger():
    with patch('users.logger.logger.logger') as mock_logger:
        mock_logger.info = MagicMock()
        mock_logger.error = MagicMock()
        yield mock_logger


@pytest.fixture(autouse=True)
def setup_test_db():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE email LIKE '%@test.com'")
        conn.commit()
        cur.close()
        conn.close()
        yield
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE email LIKE '%@test.com'")
        conn.commit()
        cur.close()
        conn.close()
    except Exception:
        yield


@pytest.fixture
def sample_user_data():
    return {
        "email": "test@test.com",
        "full_name": "Test User"
    }


@pytest.fixture
def invalid_user_data():
    return [
        {"email": "invalid-email", "full_name": "Test User"},
        {"email": "", "full_name": "Test User"},
        {"email": "test@test.com", "full_name": ""},
        {"email": "test@test.com"},
        {"full_name": "Test User"},
        {}
    ] 