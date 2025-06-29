import json
from unittest.mock import patch


def test_create_user_success(client, sample_user_data):
    response = client.post('/users/',
                         data=json.dumps(sample_user_data),
                         content_type='application/json')
    
    assert response.status_code == 201
    assert response.data == b''


def test_create_user_validation_errors(client, invalid_user_data):
    for invalid_data in invalid_user_data:
        response = client.post('/users/', 
                             data=json.dumps(invalid_data),
                             content_type='application/json')
        
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert 'error' in response_data


def test_get_existing_user(client, sample_user_data):
    client.post('/users/',
               data=json.dumps(sample_user_data),
               content_type='application/json')
    
    response = client.get(f'/users/{sample_user_data["email"]}')
    
    assert response.status_code == 200
    response_data = json.loads(response.data)
    
    assert response_data['email'] == sample_user_data['email']
    assert response_data['full_name'] == sample_user_data['full_name']
    assert 'joined_at' in response_data
    assert response_data['joined_at'].endswith('Z')  # UTC format


def test_get_nonexistent_user(client):
    response = client.get('/users/nonexistent@test.com')
    
    assert response.status_code == 404
    response_data = json.loads(response.data)
    assert response_data['error'] == 'User not found'


def test_delete_existing_user(client, sample_user_data):
    client.post('/users/',
               data=json.dumps(sample_user_data),
               content_type='application/json')
    
    response = client.delete(f'/users/{sample_user_data["email"]}')
    
    assert response.status_code == 204
    assert response.data == b''
    
    get_response = client.get(f'/users/{sample_user_data["email"]}')
    assert get_response.status_code == 404


def test_delete_nonexistent_user(client):
    response = client.delete('/users/nonexistent@test.com')
    
    assert response.status_code == 204
    assert response.data == b''


def test_delete_already_deleted_user(client, sample_user_data):
    client.post('/users/', 
               data=json.dumps(sample_user_data),
               content_type='application/json')
    
    response1 = client.delete(f'/users/{sample_user_data["email"]}')
    assert response1.status_code == 204
    
    response2 = client.delete(f'/users/{sample_user_data["email"]}')
    assert response2.status_code == 204


def test_user_reactivation(client, sample_user_data):
    email = sample_user_data["email"]
    
    client.post('/users/',
               data=json.dumps(sample_user_data),
               content_type='application/json')
    
    client.delete(f'/users/{email}')
    
    response = client.get(f'/users/{email}')
    assert response.status_code == 404
    
    reactivation_data = {
        "email": email,
        "full_name": "Reactivated User"
    }
    response = client.post('/users/', 
                         data=json.dumps(reactivation_data),
                         content_type='application/json')
    assert response.status_code == 201
    
    response = client.get(f'/users/{email}')
    assert response.status_code == 200
    response_data = json.loads(response.data)
    assert response_data['full_name'] == "Reactivated User"


def test_user_already_active_scenario(client, sample_user_data):
    email = sample_user_data["email"]
    
    response1 = client.post('/users/',
                          data=json.dumps(sample_user_data),
                          content_type='application/json')
    assert response1.status_code == 201
    
    response2 = client.post('/users/',
                          data=json.dumps(sample_user_data),
                          content_type='application/json')
    assert response2.status_code == 200  # Already active
    
    updated_data = {
        "email": email,
        "full_name": "Updated Name"
    }
    response3 = client.post('/users/', 
                          data=json.dumps(updated_data),
                          content_type='application/json')
    assert response3.status_code == 201  # Updated
    
    response = client.get(f'/users/{email}')
    response_data = json.loads(response.data)
    assert response_data['full_name'] == "Updated Name"


@patch('users.api.v0.users_routes.log_user_event')
@patch('users.api.v0.users_routes.log_user_retrieval_event')
@patch('users.api.v0.users_routes.log_user_deletion_event')
def test_logging_calls(mock_delete_log, mock_retrieve_log, mock_user_log, client, sample_user_data):
    email = sample_user_data["email"]
    
    client.post('/users/',
               data=json.dumps(sample_user_data),
               content_type='application/json')
    mock_user_log.assert_called()
    
    client.get(f'/users/{email}')
    mock_retrieve_log.assert_called()
    
    client.delete(f'/users/{email}')
    mock_delete_log.assert_called()


def test_invalid_email_format(client):
    invalid_emails = [
        "not-an-email",
        "@domain.com",
        "user@",
        "user@domain",
        "user space@domain.com",
        "user..double@domain.com"
    ]
    
    for invalid_email in invalid_emails:
        data = {"email": invalid_email, "full_name": "Test User"}
        response = client.post('/users/', 
                             data=json.dumps(data),
                             content_type='application/json')
        assert response.status_code == 400


def test_full_name_validation(client):
    long_name = "A" * 201
    data = {"email": "test@test.com", "full_name": long_name}
    
    response = client.post('/users/', 
                         data=json.dumps(data),
                         content_type='application/json')
    assert response.status_code == 400


def test_malformed_json(client):
    response = client.post('/users/',
                         data='{"invalid": json}',
                         content_type='application/json')
    assert response.status_code == 400
