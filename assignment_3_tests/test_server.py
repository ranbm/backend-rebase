import pytest
from assignment_3.file_management.app import make_app

@pytest.fixture
def client(tmp_path, monkeypatch):
    app = make_app()
    app.config['DATA_DIR'] = str(tmp_path / "data")
    monkeypatch.setenv('DATA_DIR', app.config['DATA_DIR'])
    client = app.test_client()
    yield client

def test_upload_download_delete(client):
    data = b"abc123"
    rv = client.post(
        "/api/v0/blobs/foo1",
        headers={
            "Content-Length": str(len(data)),
            "Content-Type": "application/octet-stream",
            "X-Rebase-Test": "yes",
        },
        data=data
    )
    assert rv.status_code == 201

    rv = client.get("/api/v0/blobs/foo1")
    assert rv.status_code == 200
    assert rv.data == data
    assert rv.headers["X-Rebase-Test"] == "yes"

    rv = client.delete("/api/v0/blobs/foo1")
    assert rv.status_code == 204

    rv = client.get("/api/v0/blobs/foo1")
    assert rv.status_code == 404

def test_size_limit(client):
    big = b"x" * (client.application.config['MAX_LENGTH'] + 1)
    rv = client.post(
        "/api/v0/blobs/big",
        headers={"Content-Length": str(len(big))},
        data=big
    )
    assert rv.status_code == 413