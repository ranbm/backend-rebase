import pytest
from unittest.mock import patch, MagicMock
from users.db_utils import (
    execute_query_single, 
    execute_query_all, 
    execute_update, 
    get_user_by_email, 
    get_active_user_id
)


@patch('users.db_utils.get_connection')
def test_execute_query_single_success(mock_get_conn):
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_get_conn.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cur
    mock_cur.fetchone.return_value = ('123', 'test@test.com', 'Test User')
    
    result = execute_query_single("SELECT * FROM users WHERE email = %s", ("test@test.com",))
    
    assert result == ('123', 'test@test.com', 'Test User')
    mock_cur.execute.assert_called_once_with("SELECT * FROM users WHERE email = %s", ("test@test.com",))
    mock_cur.close.assert_called_once()
    mock_conn.close.assert_called_once()


@patch('users.db_utils.get_connection')
def test_execute_query_single_no_results(mock_get_conn):
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_get_conn.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cur
    mock_cur.fetchone.return_value = None
    
    result = execute_query_single("SELECT * FROM users WHERE email = %s", ("nonexistent@test.com",))
    
    assert result is None


@patch('users.db_utils.get_connection')
def test_execute_query_all_success(mock_get_conn):
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_get_conn.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cur
    mock_cur.fetchall.return_value = [
        ('123', 'test1@test.com', 'Test User 1'),
        ('456', 'test2@test.com', 'Test User 2')
    ]
    
    result = execute_query_all("SELECT * FROM users")
    
    assert len(result) == 2
    assert result[0] == ('123', 'test1@test.com', 'Test User 1')
    assert result[1] == ('456', 'test2@test.com', 'Test User 2')
    mock_cur.execute.assert_called_once_with("SELECT * FROM users", ())


@patch('users.db_utils.get_connection')
def test_execute_update_with_returning(mock_get_conn):
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_get_conn.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cur
    mock_cur.rowcount = 1
    mock_cur.fetchone.return_value = ('123', 'test@test.com', None)
    
    query = "INSERT INTO users (id, email, full_name) VALUES (%s, %s, %s) RETURNING id, email, deleted_since"
    result, rows_affected = execute_update(query, ('123', 'test@test.com', 'Test User'))
    
    assert result == ('123', 'test@test.com', None)
    assert rows_affected == 1
    mock_conn.commit.assert_called_once()


@patch('users.db_utils.get_connection')
def test_execute_update_without_returning(mock_get_conn):
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_get_conn.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cur
    mock_cur.rowcount = 1
    
    query = "UPDATE users SET deleted_since = %s WHERE email = %s"
    result, rows_affected = execute_update(query, ('2023-01-01', 'test@test.com'))
    
    assert result is None
    assert rows_affected == 1
    mock_cur.fetchone.assert_not_called()


@patch('users.db_utils.execute_query_single')
def test_get_user_by_email_active_user(mock_execute):
    mock_execute.return_value = ('123', 'test@test.com', 'Test User', '2023-01-01T00:00:00')
    
    result = get_user_by_email('test@test.com', include_deleted=False)
    
    assert result == ('123', 'test@test.com', 'Test User', '2023-01-01T00:00:00')
    expected_query = "SELECT id, email, full_name, joined_at FROM users WHERE email = %s AND deleted_since IS NULL"
    mock_execute.assert_called_once_with(expected_query, ('test@test.com',))


@patch('users.db_utils.execute_query_single')
def test_get_user_by_email_include_deleted(mock_execute):
    mock_execute.return_value = ('123', 'test@test.com', 'Test User', '2023-01-01T00:00:00')
    
    result = get_user_by_email('test@test.com', include_deleted=True)
    
    expected_query = "SELECT id, email, full_name, joined_at FROM users WHERE email = %s"
    mock_execute.assert_called_once_with(expected_query, ('test@test.com',))


@patch('users.db_utils.execute_query_single')
def test_get_active_user_id_exists(mock_execute):
    mock_execute.return_value = ('123',)
    
    result = get_active_user_id('test@test.com')
    
    assert result == '123'
    expected_query = "SELECT id FROM users WHERE email = %s AND deleted_since IS NULL"
    mock_execute.assert_called_once_with(expected_query, ('test@test.com',))


@patch('users.db_utils.execute_query_single')
def test_get_active_user_id_not_exists(mock_execute):
    mock_execute.return_value = None
    
    result = get_active_user_id('nonexistent@test.com')
    
    assert result is None


@patch('users.db_utils.get_connection')
def test_connection_cleanup_on_exception(mock_get_conn):
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_get_conn.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cur
    mock_cur.execute.side_effect = Exception("DB Error")
    
    with pytest.raises(Exception):
        execute_query_single("SELECT * FROM users")
    
    mock_cur.close.assert_called_once()
    mock_conn.close.assert_called_once()


@patch('users.db_utils.get_connection')
def test_execute_update_exception_no_commit(mock_get_conn):
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_get_conn.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cur
    mock_cur.execute.side_effect = Exception("DB Error")
    
    with pytest.raises(Exception):
        execute_update("UPDATE users SET deleted_since = %s", ('2023-01-01',))
    
    mock_conn.commit.assert_not_called()
    mock_cur.close.assert_called_once()
    mock_conn.close.assert_called_once() 