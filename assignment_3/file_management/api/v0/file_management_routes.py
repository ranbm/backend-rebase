import os
import re
import json
import shutil
import hashlib
import mimetypes
import logging
from flask import Blueprint, request, abort, Response, current_app

file_server = Blueprint('file_server', __name__)
total_used = 0

CHUNK_SIZE = 8 * 1024  # 8 KB streaming chunks
ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,%d}$" % 200)

def init_usage(data_dir: str):
    global total_used
    logger = logging.getLogger('file_management')
    usage = 0
    file_count = 0
    
    if not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)
        logger.info(f'Created data directory: {data_dir}')
    
    for dp, _, files in os.walk(data_dir):
        for f in files:
            fp = os.path.join(dp, f)
            try:
                size = os.path.getsize(fp)
                usage += size
                file_count += 1
            except OSError as e:
                logger.warning(f'Could not get size for file {fp}: {e}')
                pass
    
    total_used = usage
    logger.info(f'Storage usage initialized: {usage / (1024*1024):.2f} MB used across {file_count} files')

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
    logger = getattr(file_server, 'logger', logging.getLogger('file_management'))
    logger.info(f'Upload request for blob: {blob_id}')
    
    cfg = current_app.config
    if not ID_PATTERN.fullmatch(blob_id):
        logger.error(f'Upload failed: Invalid blob ID "{blob_id}"')
        abort(400, 'Invalid blob ID')

    if 'Content-Length' not in request.headers:
        logger.error(f'Upload failed for {blob_id}: Missing Content-Length header')
        abort(400, 'Missing Content-Length header')
    try:
        total_len = int(request.headers['Content-Length'])
        logger.info(f'Upload {blob_id}: Content-Length = {total_len} bytes')
    except ValueError:
        logger.error(f'Upload failed for {blob_id}: Invalid Content-Length header')
        abort(400, 'Invalid Content-Length header')

    stored = {}
    if 'Content-Type' in request.headers:
        stored['Content-Type'] = request.headers['Content-Type']
    for name, val in request.headers.items():
        if name.lower().startswith('x-rebase-'):
            stored[name] = val

    logger.info(f'Upload {blob_id}: Storing {len(stored)} headers')

    if len(stored) > cfg['MAX_HEADER_COUNT']:
        logger.error(f'Upload failed for {blob_id}: Too many headers ({len(stored)} > {cfg["MAX_HEADER_COUNT"]})')
        abort(400, 'Too many stored headers')
    for name, val in stored.items():
        if len(name) > cfg['MAX_HEADER_LENGTH'] or len(val) > cfg['MAX_HEADER_LENGTH']:
            logger.error(f'Upload failed for {blob_id}: Header "{name}" exceeds max length')
            abort(400, f'Header "{name}" exceeds max length')

    header_bytes = sum(len(n) + len(v) for n, v in stored.items())
    if total_len + header_bytes > cfg['MAX_LENGTH']:
        logger.error(f'Upload failed for {blob_id}: Payload and headers exceed max length ({total_len + header_bytes} > {cfg["MAX_LENGTH"]})')
        abort(413, 'Payload and headers exceed max length')

    blob_dir = _compute_blob_dir(blob_id)
    data_path = os.path.join(blob_dir, 'data')
    
    # Check if blob already exists
    if os.path.isdir(blob_dir) and os.path.isfile(data_path):
        try:
            old_size = os.path.getsize(data_path)
            total_used -= old_size
            logger.info(f'Upload {blob_id}: Replacing existing blob (old size: {old_size} bytes)')
        except OSError:
            pass
        shutil.rmtree(blob_dir)

    if total_used + total_len > cfg['MAX_DISK_QUOTA']:
        logger.error(f'Upload failed for {blob_id}: Disk quota exceeded ({total_used + total_len} > {cfg["MAX_DISK_QUOTA"]})')
        abort(413, 'Disk quota exceeded')
    
    os.makedirs(blob_dir, exist_ok=True)
    logger.info(f'Upload {blob_id}: Created storage directory {blob_dir}')

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
        logger.info(f'Upload {blob_id}: Successfully stored {total_len} bytes. Total usage: {total_used / (1024*1024):.2f} MB')
    except Exception as e:
        logger.error(f'Upload failed for {blob_id}: Error writing blob - {str(e)}')
        shutil.rmtree(blob_dir, ignore_errors=True)
        abort(500, 'Error writing blob')

    return '', 201


@file_server.route('/blobs/<blob_id>', methods=['GET'])
def download_blob(blob_id):
    logger = getattr(file_server, 'logger', logging.getLogger('file_management'))
    logger.info(f'Download request for blob: {blob_id}')
    
    if not ID_PATTERN.fullmatch(blob_id):
        logger.error(f'Download failed: Invalid blob ID "{blob_id}"')
        abort(400, 'Invalid blob ID')

    blob_dir = _compute_blob_dir(blob_id)
    data_path = os.path.join(blob_dir, 'data')
    if not os.path.isfile(data_path):
        logger.warning(f'Download failed: Blob "{blob_id}" not found')
        abort(404, 'Blob not found')

    try:
        with open(os.path.join(blob_dir, 'metadata.json'), 'r', encoding='utf-8') as mf:
            metadata = json.load(mf)
    except Exception as e:
        logger.warning(f'Download {blob_id}: Could not load metadata - {str(e)}')
        metadata = {}

    content_type = metadata.get('Content-Type') or mimetypes.guess_type(blob_id)[0] or 'application/octet-stream'
    stat = os.stat(data_path)
    
    logger.info(f'Download {blob_id}: Serving {stat.st_size} bytes as {content_type}')

    def gen():
        with open(data_path, 'rb') as f:
            while True:
                data = f.read(CHUNK_SIZE)
                if not data:
                    break
                yield data

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
    logger = getattr(file_server, 'logger', logging.getLogger('file_management'))
    logger.info(f'Delete request for blob: {blob_id}')
    
    if not ID_PATTERN.fullmatch(blob_id):
        logger.error(f'Delete failed: Invalid blob ID "{blob_id}"')
        abort(400, 'Invalid blob ID')
        
    blob_dir = _compute_blob_dir(blob_id)
    data_path = os.path.join(blob_dir, 'data')
    
    if os.path.isdir(blob_dir) and os.path.isfile(data_path):
        try:
            size = os.path.getsize(data_path)
            total_used -= size
            shutil.rmtree(blob_dir)
            logger.info(f'Delete {blob_id}: Successfully deleted {size} bytes. Total usage: {total_used / (1024*1024):.2f} MB')
        except OSError as e:
            logger.error(f'Delete failed for {blob_id}: {str(e)}')
    else:
        logger.warning(f'Delete {blob_id}: Blob not found (no-op)')
        
    return '', 204
