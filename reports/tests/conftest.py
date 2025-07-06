import pytest
from datetime import datetime as dt, timedelta
from unittest.mock import patch


from reports.app import make_app
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
    with patch('assignment_7.users.db_utils.get_connection') as mock_conn:
        yield mock_conn


@pytest.fixture(autouse=True)
def setup_test_db():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM page_hourly_views WHERE page_id LIKE 'test-%'")
        conn.commit()
        cur.close()
        conn.close()
        yield
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM page_hourly_views WHERE page_id LIKE 'test-%'")
        conn.commit()
        cur.close()
        conn.close()
    except Exception:
        yield


@pytest.fixture
def sample_now():
    return dt(2024, 1, 15, 14, 30, 0)  # 2024-01-15 14:30:00


@pytest.fixture
def sample_page_data():
    return {
        "page_id": "test-page-1",
        "base_hour": dt(2024, 1, 15, 14, 0, 0),  # 2024-01-15 14:00:00
        "view_counts": [5, 3, 8, 2, 1, 0, 4, 6, 9, 7, 2, 1, 3, 5, 8, 2, 6, 4, 1, 7, 3, 9, 5, 2]
    }


@pytest.fixture
def mock_execute_query_all():
    with patch('api.v0.reports_routes.execute_query_all') as mock_execute:
        yield mock_execute


@pytest.fixture
def insert_sample_data(sample_page_data):
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        page_id = sample_page_data["page_id"]
        base_hour = sample_page_data["base_hour"]
        view_counts = sample_page_data["view_counts"]
        
        start_time = base_hour - timedelta(hours=24)
        for i, count in enumerate(view_counts):
            hour_start = start_time + timedelta(hours=i)
            cur.execute(
                "INSERT INTO page_hourly_views (page_id, hour_start, view_count) VALUES (%s, %s, %s)",
                (page_id, hour_start, count)
            )
        
        conn.commit()
        cur.close()
        conn.close()
        yield sample_page_data
        
    except Exception as e:
        print(f"Error inserting sample data: {e}")
        yield sample_page_data


@pytest.fixture
def empty_page_data():
    return {
        "page_id": "test-empty-page",
        "base_hour": dt(2024, 1, 15, 14, 0, 0)
    } 