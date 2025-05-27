import os
import re
import json
from typing import Dict, Iterator

from flask import Flask, request, abort, jsonify, Response

app = Flask(__name__)

MAX_LENGTH = 10 * 1024 * 1024 #10MB
MAX_DISK_QUOTA = 1024 * 1024 * 1024 #1GB
MAX_HEADER_LENGTH = 50
MAX_HEADER_COUNT = 20
MAX_ID_LENGTH = 200
MAX_BLOBS_IN_FOLDER = 10000
DATA_DIR = "temp_folder"
CHUNK_SIZE = 10000
ID_PATTERN = re.compile(r"^[a-z0-9._-]+$")

def _load_metadata(blob_path: str) -> Dict[str, str]:
    meta_path = f"{blob_path}.meta"
    if os.path.isfile(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as m:
                return json.load(m)
        except Exception:
            pass
    return {}



def _error(err_message, status_code=400):
    response = jsonify({"error": err_message})
    response.status_code = status_code
    return response

def _check_folder_size(request_size: int):
    total_size = request_size
    for dirpath, dirnames, filenames in os.walk(DATA_DIR):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size <= MAX_DISK_QUOTA

def _check_blobs_count_in_folder():
    count = 0
    for dirpath, dirnames, filenames in os.walk(DATA_DIR):
        count += len(filenames)
    return count <= MAX_BLOBS_IN_FOLDER


@app.route('/blobs/<blob_id>', methods=['POST'])
def upload_blob(blob_id):
    headers = request.headers
    if len(blob_id) > MAX_ID_LENGTH:
        return _error(f"ID exceeds MAX_ID_LENGTH: {MAX_ID_LENGTH}")
    if not ID_PATTERN.fullmatch(blob_id):
        return _error("ID can only contain alphanumeric characters, underscores, and hyphens")
    content_length = headers.get('content-length')
    if not content_length:
        return _error("Missing content-length header")
    if content_length and int(content_length) > MAX_LENGTH:
        return _error(f"Content length exceeds MAX_LENGTH: {MAX_LENGTH} bytes")
    if len(headers)> MAX_HEADER_COUNT:
        return _error(f"Too many headers, maximum allowed is {MAX_HEADER_COUNT}")
    for header, val in headers.items():
        if len(val) > MAX_HEADER_LENGTH:
            return _error(f"Header '{header}' exceeds MAX_HEADER_LENGTH: {MAX_HEADER_LENGTH} characters")
    if not _check_folder_size(int(content_length)):
        return _error(f"Folder size exceeds MAX_DISK_QUOTA: {MAX_DISK_QUOTA} bytes")
    if not _check_blobs_count_in_folder():
        return _error(f"Too many blobs in folder, maximum allowed is {MAX_BLOBS_IN_FOLDER}")
    tmp_path = os.path.join(DATA_DIR, f"{blob_id}.tmp")
    final_path = os.path.join(DATA_DIR, blob_id)

    bytes_written = 0
    try:
        with open(tmp_path, "wb") as dst:
            while True:
                # Read at most the remaining allowed size this iteration.
                to_read = min(CHUNK_SIZE, MAX_LENGTH - bytes_written)
                chunk = request.stream.read(to_read)
                if not chunk:
                    break
                dst.write(chunk)
                bytes_written += len(chunk)
                if bytes_written > MAX_LENGTH:
                    # Abruptly abort if client lied about Content‑Length.
                    raise ValueError("payload exceeds max_length during upload")
    except ValueError as ve:
        try:
            os.remove(tmp_path)
        finally:
            return _error(str(ve), status=413)
    except Exception:
        try:
            os.remove(tmp_path)
        finally:
            abort(500)

    os.replace(tmp_path, final_path)
    metadata = {}
    content_type = request.headers.get("Content-Type")
    if content_type:
        metadata["content-type"] = content_type
    for header, value in request.headers.items():
        if header.lower().startswith("x-rebase-"):
            metadata[header] = value

    if metadata:
        meta_path = f"{final_path}.meta"
        with open(meta_path, "w", encoding="utf-8") as meta_f:
            json.dump(metadata, meta_f, indent=2)

    return ("", 201)

@app.route("/blobs/<string:blob_id>", methods=["GET"])
def download_blob(blob_id: str):
    # ID validation
    if len(blob_id) > MAX_ID_LENGTH:
        return _error("id exceeds max_id_length (200)")
    if not ID_PATTERN.fullmatch(blob_id):
        return _error("id may contain only lowercase a–z and digits 0–9")

    blob_path = os.path.join(DATA_DIR, blob_id)
    if not os.path.isfile(blob_path):
        return _error("blob not found", status=404)

    metadata = _load_metadata(blob_path)
    ctype = metadata.get("content-type")
    if not ctype:
        ctype = "application/octet-stream"

    def _file_iterator(path: str) -> Iterator[bytes]:
        with open(path, "rb") as f:
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                yield chunk

    file_size = os.path.getsize(blob_path)
    resp = Response(_file_iterator(blob_path), mimetype=ctype)
    resp.headers["Content-Length"] = str(file_size)
    resp.headers["Content-Disposition"] = f"inline; filename={blob_id}"

    # Attach stored X-Rebase-* headers
    for header, value in metadata.items():
        if header.lower().startswith("x-rebase-"):
            resp.headers[header] = value

    return resp

if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    app.run(host="0.0.0.0", port=50000)
