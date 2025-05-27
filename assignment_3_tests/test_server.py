from __future__ import annotations

import importlib
import os
import random
import string
import sys
import threading
import time
from pathlib import Path

import pytest
from werkzeug.test import EnvironBuilder

RAND = random.SystemRandom()
ALPHANUM = string.ascii_lowercase + string.digits + "._-"


def random_id(n: int = 16) -> str:
    return "".join(RAND.choice(ALPHANUM) for _ in range(n))


def random_bytes(size: int) -> bytes:
    return os.urandom(size)


@pytest.fixture()
def client(tmp_path):
    data_dir = tmp_path / "temp_folder"
    data_dir.mkdir()

    server = importlib.import_module("assignment_2.server")
    importlib.reload(server)
    server.DATA_DIR = str(data_dir)
    os.makedirs(server.DATA_DIR, exist_ok=True)

    server.app.logger.setLevel("INFO")  # enable application logging in tests
    server.app.config.update(TESTING=True)
    with server.app.test_client() as c:
        yield c, server


def test_post_get_roundtrip(client):
    c, srv = client
    blob_id = random_id()
    payload = random_bytes(2048)

    r = c.post(
        f"/blobs/{blob_id}",
        data=payload,
        headers={
            "Content-Length": str(len(payload)),
            "Content-Type": "application/octet-stream",
            "X-Rebase-Tag": "pytest",
        },
    )
    assert r.status_code == 201

    r = c.get(f"/blobs/{blob_id}")
    assert r.status_code == 200
    assert r.data == payload
    assert r.headers["X-Rebase-Tag"] == "pytest"



def test_payload_too_large(client):
    c, srv = client
    too_big = random_bytes(srv.MAX_LENGTH + 1)
    r = c.post(f"/blobs/{random_id()}", data=too_big, headers={"Content-Length": str(len(too_big))})
    assert r.status_code == 400


def test_header_length_limit(client):
    c, srv = client
    long_val = "x" * (srv.MAX_HEADER_LENGTH + 1)
    r = c.post(
        f"/blobs/{random_id()}",
        data=b"abc",
        headers={"Content-Length": "3", "X-Long": long_val},
    )
    assert r.status_code == 400


def test_header_count_limit(client):
    c, srv = client
    headers = {"Content-Length": "0"}
    for i in range(srv.MAX_HEADER_COUNT + 1):
        headers[f"X-H-{i}"] = "v"
    r = c.post(f"/blobs/{random_id()}", data=b"", headers=headers)
    assert r.status_code == 400


@pytest.mark.parametrize("num_blobs, blob_size", [(12000, 256)])
def test_folder_capacity_rotation(client, num_blobs: int, blob_size: int):
    """Upload > MAX_BLOBS_IN_FOLDER small blobs and ensure no 400 is raised.
    Also verify that total file count equals what we pushed (sanity) and that
    at least two sub‑folders were used (capacity rotation).
    """
    c, srv = client
    successes = 0
    for _ in range(num_blobs):
        blob_id = random_id(20)
        r = c.post(
            f"/blobs/{blob_id}",
            data=random_bytes(blob_size),
            headers={"Content-Length": str(blob_size)},
        )
        assert r.status_code == 201
        successes += 1

    files = [p for p in Path(srv.DATA_DIR).rglob("*") if p.is_file() and not p.name.endswith(".meta")]
    assert len(files) == successes

    parent_dirs = {f.parent for f in files}
    assert len(parent_dirs) >= successes // srv.MAX_BLOBS_IN_FOLDER  # used ≥ expected buckets


def test_disk_quota_enforced(client):
    """Keep uploading until quota – 1 MiB, then try a blob that is *2 MiB* larger
    than the remaining space.  This overshoot guarantees failure even after the
    server creates the extra `.meta` file.
    """
    c, srv = client

    size_each = 1 * 1024 * 1024  # 1 MiB
    while True:
        used = sum(p.stat().st_size for p in Path(srv.DATA_DIR).rglob("*") if p.is_file())
        remaining = srv.MAX_DISK_QUOTA - used
        if remaining <= size_each:
            break
        r = c.post(
            f"/blobs/{random_id()}",
            data=random_bytes(size_each),
            headers={"Content-Length": str(size_each)},
        )
        assert r.status_code == 201

    overshoot = remaining + 2 * size_each
    r = c.post(
        f"/blobs/{random_id()}",
        data=random_bytes(overshoot),
        headers={"Content-Length": str(overshoot)},
    )
    assert r.status_code == 400



def test_interrupted_upload_cleanup(client):
    c, srv = client

    blob_id = random_id()
    partial = random_bytes(64 * 1024)  # 64 KiB

    builder = EnvironBuilder(
        path=f"/blobs/{blob_id}",
        method="POST",
        headers={"Content-Length": str(srv.MAX_LENGTH)},  # lie: bigger than sent
        environ_overrides={"wsgi.input_terminated": True},
    )
    env = builder.get_environ()
    env["wsgi.input"] = IteratorStream([partial])  # custom iterable stream

    resp = c.open(env)
    # Server should detect mismatch and 400/413, not 500
    assert resp.status_code in {400, 413}

    # After the request, no blob nor tmp exists
    target = Path(srv.DATA_DIR) / blob_id
    assert not target.exists()
    assert not target.with_suffix(".tmp").exists()


class IteratorStream:
    def __init__(self, iterable):
        self._it = iter(iterable)

    def read(self, n=-1):
        try:
            return next(self._it)
        except StopIteration:
            return b""


USAGE = """\npython -m assignment_2_tests.test_server load <base_url> <num_files> <bytes_each>\n"""


def _cli_load(base_url: str, n: int, size: int):
    import requests
    start = time.time()

    def worker(idx):
        bid = random_id(20)
        r = requests.post(
            f"{base_url.rstrip('/')}/blobs/{bid}",
            data=random_bytes(size),
            headers={"Content-Length": str(size)},
        )
        if idx % 50 == 0:
            print(f"{idx:6d}/{n} -> {r.status_code}")

    threads = []
    for i in range(1, n + 1):
        t = threading.Thread(target=worker, args=(i,), daemon=True)
        threads.append(t)
        t.start()
    for t in threads:
        t.join()

    print(f"Uploaded {n} files of {size} bytes in {time.time() - start:.1f}s")


if __name__ == "__main__":
    if len(sys.argv) == 5 and sys.argv[1] == "load":
        _cli_load(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]))
    else:
        print(USAGE)
