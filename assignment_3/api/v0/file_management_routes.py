import os
import re
import json
import shutil
import hashlib
import mimetypes
from flask import Blueprint, request, abort, Response, current_app

file_server = Blueprint('file_server', __name__)
total_used = 0

CHUNK_SIZE = 8 * 1024  # 8 KB streaming chunks
ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,%d}$" % 200)

def init_usage(data_dir: str):
    global total_used
    usage = 0
    for dp, _, files in os.walk(data_dir):
        for f in files:
            fp = os.path.join(dp, f)
            try:
                usage += os.path.getsize(fp)
            except OSError:
                pass
    total_used = usage
def _get_data_dir():
    return os.path.abspath(current_app.config['DATA_DIR'])


def _compute_blob_dir(blob_id: str) -> str:
    # Bucket path: first 3 hex chars + next 2 of SHA-1(blob_id)
    h = hashlib.sha1(blob_id.encode('utf-8')).hexdigest()
    p1, p2 = h[:3], h[3:5]
    return os.path.join(_get_data_dir(), p1, p2, blob_id)


@file_server.route('/blobs/<blob_id>', methods=['POST'])
def upload_blob(blob_id):
    global total_used
    cfg = current_app.config
    if not ID_PATTERN.fullmatch(blob_id):
        abort(400, 'Invalid blob ID')

    if 'Content-Length' not in request.headers:
        abort(400, 'Missing Content-Length header')
    try:
        total_len = int(request.headers['Content-Length'])
    except ValueError:
        abort(400, 'Invalid Content-Length header')

    stored = {}
    if 'Content-Type' in request.headers:
        stored['Content-Type'] = request.headers['Content-Type']
    for name, val in request.headers.items():
        if name.lower().startswith('x-rebase-'):
            stored[name] = val

    if len(stored) > cfg['MAX_HEADER_COUNT']:
        abort(400, 'Too many stored headers')
    for name, val in stored.items():
        if len(name) > cfg['MAX_HEADER_LENGTH'] or len(val) > cfg['MAX_HEADER_LENGTH']:
            abort(400, f'Header "{name}" exceeds max length')

    header_bytes = sum(len(n) + len(v) for n, v in stored.items())
    if total_len + header_bytes > cfg['MAX_LENGTH']:
        abort(413, 'Payload and headers exceed max length')

    blob_dir = _compute_blob_dir(blob_id)
    data_path = os.path.join(blob_dir, 'data')
    if os.path.isdir(blob_dir) and os.path.isfile(data_path):
        try:
            old_size = os.path.getsize(data_path)
            total_used -= old_size
        except OSError:
            pass
        shutil.rmtree(blob_dir)

    if total_used + total_len > cfg['MAX_DISK_QUOTA']:
        abort(413, 'Disk quota exceeded')
    os.makedirs(blob_dir, exist_ok=True)

    with open(os.path.join(blob_dir, 'metadata.json'), 'w', encoding='utf-8') as mf:
        json.dump(stored, mf, indent=2)

    tmp_path = os.path.join(blob_dir, 'data.tmp')
    remaining = total_len
    try:
        with open(tmp_path, 'wb') as df:
            while remaining:
                chunk = request.stream.read(min(CHUNK_SIZE, remaining))
                if not chunk:
                    break
                df.write(chunk)
                remaining -= len(chunk)
        if remaining:
            raise ValueError('Incomplete upload')
        os.replace(tmp_path, data_path)
        total_used += total_len
    except Exception:
        shutil.rmtree(blob_dir, ignore_errors=True)
        abort(500, 'Error writing blob')

    return '', 201


@file_server.route('/blobs/<blob_id>', methods=['GET'])
def download_blob(blob_id):
    if not ID_PATTERN.fullmatch(blob_id):
        abort(400, 'Invalid blob ID')

    blob_dir = _compute_blob_dir(blob_id)
    data_path = os.path.join(blob_dir, 'data')
    if not os.path.isfile(data_path):
        abort(404, 'Blob not found')

    try:
        with open(os.path.join(blob_dir, 'metadata.json'), 'r', encoding='utf-8') as mf:
            metadata = json.load(mf)
    except Exception:
        metadata = {}

    content_type = metadata.get('Content-Type') or mimetypes.guess_type(blob_id)[0] or 'application/octet-stream'

    def gen():
        with open(data_path, 'rb') as f:
            while True:
                data = f.read(CHUNK_SIZE)
                if not data:
                    break
                yield data

    stat = os.stat(data_path)
    headers = {
        'Content-Type': content_type,
        'Content-Length': str(stat.st_size)
    }
    for name, val in metadata.items():
        if name.lower().startswith('x-rebase-'):
            headers[name] = val

    return Response(gen(), headers=headers)


@file_server.route('/blobs/<blob_id>', methods=['DELETE'])
def delete_blob(blob_id):
    global total_used
    if not ID_PATTERN.fullmatch(blob_id):
        abort(400, 'Invalid blob ID')
    blob_dir = _compute_blob_dir(blob_id)
    data_path = os.path.join(blob_dir, 'data')
    if os.path.isdir(blob_dir) and os.path.isfile(data_path):
        try:
            size = os.path.getsize(data_path)
            total_used -= size
        except OSError:
            pass
        shutil.rmtree(blob_dir)
    return '', 204
