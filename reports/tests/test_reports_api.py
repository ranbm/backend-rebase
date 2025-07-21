import pytest
from datetime import datetime as dt
from unittest.mock import patch


def test_get_report_basic_functionality(client, mock_execute_query_all):
    mock_data = [
        (dt(2024, 1, 15, 10, 0, 0), 5),
        (dt(2024, 1, 15, 11, 0, 0), 3),
        (dt(2024, 1, 15, 12, 0, 0), 8),
    ]
    mock_execute_query_all.return_value = mock_data
    
    response = client.get('/reports/test-page')
    
    assert response.status_code == 200
    assert response.mimetype == 'text/plain'
    
    content = response.get_data(as_text=True)
    assert '| Hour            | Views |' in content
    assert '| 10:00-11:00     | 5     |' in content
    assert '| 11:00-12:00     | 3     |' in content
    assert '| 12:00-13:00     | 8     |' in content


def test_get_report_with_now_parameter(client, mock_execute_query_all):
    mock_execute_query_all.return_value = [
        (dt(2024, 1, 15, 10, 0, 0), 5),
        (dt(2024, 1, 15, 11, 0, 0), 3),
    ]
    
    now_param = "2024-01-15T14:30:00"
    response = client.get(f'/reports/test-page?now={now_param}')
    
    assert response.status_code == 200
    mock_execute_query_all.assert_called_once()
    
    args, kwargs = mock_execute_query_all.call_args
    query, params = args
    page_id, start_time, end_time = params
    
    assert page_id == 'test-page'
    assert start_time == dt(2024, 1, 14, 14, 0, 0)
    assert end_time == dt(2024, 1, 15, 13, 0, 0)


def test_get_report_with_order_asc(client, mock_execute_query_all):
    mock_execute_query_all.return_value = [
        (dt(2024, 1, 15, 10, 0, 0), 5),
        (dt(2024, 1, 15, 11, 0, 0), 3),
    ]
    
    response = client.get('/reports/test-page?order=asc')
    
    assert response.status_code == 200
    
    args, kwargs = mock_execute_query_all.call_args
    query, params = args
    assert 'ORDER BY hour_start ASC' in query


def test_get_report_with_order_desc(client, mock_execute_query_all):
    mock_execute_query_all.return_value = [
        (dt(2024, 1, 15, 11, 0, 0), 3),
        (dt(2024, 1, 15, 10, 0, 0), 5),
    ]
    
    response = client.get('/reports/test-page?order=desc')
    
    assert response.status_code == 200
    
    args, kwargs = mock_execute_query_all.call_args
    query, params = args
    assert 'ORDER BY hour_start DESC' in query


def test_get_report_with_take_parameter(client, mock_execute_query_all):
    mock_execute_query_all.return_value = [
        (dt(2024, 1, 15, 10, 0, 0), 5),
        (dt(2024, 1, 15, 11, 0, 0), 3),
        (dt(2024, 1, 15, 12, 0, 0), 8),
        (dt(2024, 1, 15, 13, 0, 0), 2),
    ]
    
    response = client.get('/reports/test-page?take=2')
    
    assert response.status_code == 200
    content = response.get_data(as_text=True)
    
    assert '| 10:00-11:00     | 5     |' in content
    assert '| 11:00-12:00     | 3     |' in content
    assert '| 12:00-13:00     | 8     |' not in content
    assert '| 13:00-14:00     | 2     |' not in content


def test_get_report_with_all_parameters(client, mock_execute_query_all):
    mock_execute_query_all.return_value = [
        (dt(2024, 1, 15, 11, 0, 0), 3),
        (dt(2024, 1, 15, 10, 0, 0), 5),
    ]
    
    response = client.get('/reports/test-page?now=2024-01-15T14:30:00&order=desc&take=1')
    
    assert response.status_code == 200
    content = response.get_data(as_text=True)
    
    assert '| 11:00-12:00     | 3     |' in content
    assert '| 10:00-11:00     | 5     |' not in content


def test_get_report_empty_data(client, mock_execute_query_all):
    mock_execute_query_all.return_value = []
    
    response = client.get('/reports/nonexistent-page')
    
    assert response.status_code == 200
    content = response.get_data(as_text=True)
    
    assert '| Hour            | Views |' in content
    assert '|-----------------|-------|' in content


def test_get_report_with_highlighting(client, mock_execute_query_all):
    with patch('api.v0.reports_routes.dt') as mock_dt:
        mock_dt.utcnow.return_value = dt(2024, 1, 15, 14, 0, 0)
        mock_dt.strptime.side_effect = dt.strptime
        
        mock_execute_query_all.return_value = [
            (dt(2024, 1, 15, 10, 0, 0), 5),
            (dt(2024, 1, 15, 14, 0, 0), 3),
        ]
        
        response = client.get('/reports/test-page')
        
        assert response.status_code == 200
        content = response.get_data(as_text=True)
        
        assert '| 10:00-11:00     | 5     |' in content
        assert '| 14:00-15:00 [*] | 3     |' in content


def test_get_report_invalid_now_parameter(client, mock_execute_query_all):
    response = client.get('/reports/test-page?now=invalid-datetime')
    assert response.status_code == 400


def test_get_report_edge_case_midnight_hour(client, mock_execute_query_all):
    mock_execute_query_all.return_value = [
        (dt(2024, 1, 15, 23, 0, 0), 5),
        (dt(2024, 1, 16, 0, 0, 0), 3),
    ]
    
    response = client.get('/reports/test-page')
    
    assert response.status_code == 200
    content = response.get_data(as_text=True)
    
    assert '| 23:00-0:00  [*] | 5     |' in content
    assert '| 0:00 -1:00      | 3     |' in content


def test_get_report_case_insensitive_order(client, mock_execute_query_all):
    mock_execute_query_all.return_value = [
        (dt(2024, 1, 15, 10, 0, 0), 5),
    ]
    
    response = client.get('/reports/test-page?order=DESC')
    assert response.status_code == 200
    
    args, kwargs = mock_execute_query_all.call_args
    query, params = args
    assert 'ORDER BY hour_start DESC' in query


def test_get_report_invalid_take_parameter(client, mock_execute_query_all):
    mock_execute_query_all.return_value = [
        (dt(2024, 1, 15, 10, 0, 0), 5),
    ]
    
    response = client.get('/reports/test-page?take=invalid')
    
    assert response.status_code == 200
    content = response.get_data(as_text=True)
    assert '| 10:00-11:00     | 5     |' in content


def test_build_ascii_table_basic(client):
    from reports.api.v0.reports_routes import build_ascii_table
    
    data = [
        {"h": 10, "v": 5},
        {"h": 11, "v": 3},
    ]
    
    result = build_ascii_table(data)
    
    expected_lines = [
        "| Hour            | Views |",
        "|-----------------|-------|",
        "| 10:00-11:00     | 5     |",
        "| 11:00-12:00     | 3     |",
        "|-----------------|-------|"
    ]
    
    assert result == "\n".join(expected_lines)


def test_build_ascii_table_with_highlights(client):
    from reports.api.v0.reports_routes import build_ascii_table
    
    data = [
        {"h": 10, "v": 5},
        {"h": 11, "v": 3},
    ]
    highlight_hours = {11}
    
    result = build_ascii_table(data, highlight_hours)
    
    assert "| 11:00-12:00 [*] | 3     |" in result
    assert "| 10:00-11:00     | 5     |" in result


def test_build_ascii_table_empty():
    from reports.api.v0.reports_routes import build_ascii_table
    
    data = []
    result = build_ascii_table(data)
    
    expected_lines = [
        "| Hour            | Views |",
        "|-----------------|-------|",
        "|-----------------|-------|"
    ]
    
    assert result == "\n".join(expected_lines)


def test_build_ascii_table_midnight_wraparound():
    from reports.api.v0.reports_routes import build_ascii_table
    
    data = [
        {"h": 23, "v": 5},
        {"h": 0, "v": 3},
    ]
    
    result = build_ascii_table(data)
    
    assert "| 23:00-0:00      | 5     |" in result
    assert "| 0:00 -1:00      | 3     |" in result


@pytest.mark.integration
def test_get_report_with_real_database(client, insert_sample_data):
    sample_data = insert_sample_data
    page_id = sample_data["page_id"]
    
    now_param = "2024-01-15T14:30:00"
    response = client.get(f'/reports/{page_id}?now={now_param}')
    
    assert response.status_code == 200
    content = response.get_data(as_text=True)

    assert '| Hour            | Views |' in content
    assert '|-----------------|-------|' in content
    
    assert 'Views' in content


@pytest.mark.integration
def test_get_report_nonexistent_page_real_db(client):
    response = client.get('/reports/definitely-nonexistent-page')
    
    assert response.status_code == 200
    content = response.get_data(as_text=True)
    
    assert '| Hour            | Views |' in content
    assert '|-----------------|-------|' in content


@pytest.mark.integration
def test_get_report_database_error_handling(client):
    with patch('api.v0.reports_routes.execute_query_all') as mock_execute:
        mock_execute.side_effect = Exception("Database connection failed")
        
        response = client.get('/reports/test-page')
        
        assert response.status_code == 500


