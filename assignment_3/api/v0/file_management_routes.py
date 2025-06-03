import os
import re
import json
import shutil
import time
import hashlib
from typing import Dict, Iterator
from flask import Blueprint, request, abort, jsonify, Response, current_app

file_management = Blueprint('file_management', __name__)

MAX_LENGTH          = 10 * 1024 * 1024      # 10MB per chunk
MAX_DISK_QUOTA      = 1 * 1024 * 1024 * 1024 # 1GB total
MAX_HEADER_LENGTH   = 100
MAX_HEADER_COUNT    = 20
MAX_ID_LENGTH       = 200
MAX_BLOBS_IN_FOLDER = 10000

CHUNK_SIZE = 100_000
# Expect chunk IDs of the form "<8-hex>-<4-digits>"
ID_PATTERN = re.compile(r"^[a-f0-9]{8}-\d{4}$")


def _get_data_dir() -> str:
    base = current_app.config.get("DATA_DIR", "data")
    return os.path.abspath(base)


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


def _check_folder_size(request_size: int) -> bool:
    total_size = request_size
    data_dir = _get_data_dir()
    for dirpath, _, filenames in os.walk(data_dir):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            try:
                total_size += os.path.getsize(fp)
            except OSError:
                continue
    return total_size <= MAX_DISK_QUOTA


def _check_blobs_count_in_folder() -> bool:
    count = 0
    data_dir = _get_data_dir()
    for _, _, filenames in os.walk(data_dir):
        count += len(filenames)
    return count <= MAX_BLOBS_IN_FOLDER


def _sanitize_filename(filename: str) -> str:
    name = filename.lower()
    safe = re.sub(r"[^a-z0-9._-]", "_", name)
    return safe[:MAX_ID_LENGTH]


@file_management.route('/upload/<path:filename>', methods=['POST'])
def upload_and_chunk(filename):
    logger = file_management.logger

    safe_name = _sanitize_filename(filename)
    if not safe_name:
        return _error("Invalid filename provided", status_code=400)

    content_length = request.headers.get("Content-Length")
    if content_length:
        try:
            total_len = int(content_length)
        except ValueError:
            return _error("Invalid Content-Length header", status_code=400)

        if total_len >= MAX_DISK_QUOTA:
            return _error(f"File size must be less than {MAX_DISK_QUOTA} bytes", status_code=413)

        if not _check_folder_size(total_len):
            return _error(f"Folder size exceeds MAX_DISK_QUOTA: {MAX_DISK_QUOTA} bytes", status_code=413)

    if not _check_blobs_count_in_folder():
        return _error(f"Too many blobs in folder (max {MAX_BLOBS_IN_FOLDER})", status_code=413)

    headers = request.headers
    if len(headers) > MAX_HEADER_COUNT:
        logger.error(f"Too many headers: {len(headers)} > {MAX_HEADER_COUNT}", extra={"filename": filename})
        return _error(f"Too many headers, maximum allowed is {MAX_HEADER_COUNT}", status_code=400)

    for header_name, header_val in headers.items():
        if len(header_val) > MAX_HEADER_LENGTH:
            logger.error(
                f"Header '{header_name}' exceeds MAX_HEADER_LENGTH: {MAX_HEADER_LENGTH} chars",
                extra={"filename": filename, "header": header_name, "length": len(header_val)}
            )
            return _error(f"Header '{header_name}' exceeds MAX_HEADER_LENGTH: {MAX_HEADER_LENGTH} characters",
                          status_code=400)
    upload_key = f"{safe_name}:{time.time()}".encode("utf-8")
    upload_id = hashlib.sha256(upload_key).hexdigest()[:8]

    data_dir = _get_data_dir()
    upload_folder = os.path.join(data_dir, upload_id)
    os.makedirs(upload_folder, exist_ok=True)

    created_blob_ids = []
    total_written = 0
    chunk_index = 0

    while True:
        chunk_data = request.stream.read(MAX_LENGTH)
        if not chunk_data:
            break

        blob_id = f"{upload_id}-{chunk_index:04d}"
        if len(blob_id) > MAX_ID_LENGTH:
            blob_id = blob_id[:MAX_ID_LENGTH]

        if not ID_PATTERN.fullmatch(blob_id):
            return _error("Generated blob_id is invalid", status_code=500)

        final_path = os.path.join(upload_folder, blob_id)
        try:
            with open(final_path, "wb") as dst:
                dst.write(chunk_data)
        except Exception:
            abort(500)

        metadata: Dict[str, str] = {}
        content_type = request.headers.get("Content-Type")
        if content_type:
            metadata["content-type"] = content_type
        for hn, hv in request.headers.items():
            if hn.lower().startswith("x-rebase-"):
                metadata[hn] = hv

        if metadata:
            meta_path = f"{final_path}.meta"
            try:
                with open(meta_path, "w", encoding="utf-8") as mf:
                    json.dump(metadata, mf, indent=2)
            except Exception:
                try:
                    os.remove(final_path)
                except OSError:
                    pass
                abort(500)

        created_blob_ids.append(blob_id)
        total_written += len(chunk_data)
        chunk_index += 1

    if not created_blob_ids:
        return _error("No file data received", status_code=400)

    # Write manifest.json so download can reassemble
    manifest = {
        "original_filename": safe_name,
        "chunks": created_blob_ids
    }
    manifest_path = os.path.join(upload_folder, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as mf:
        json.dump(manifest, mf, indent=2)

    return jsonify({
        "upload_id": upload_id,
        "created_blob_ids": created_blob_ids,
        "total_bytes": total_written
    }), 201


@file_management.route('/download/<path:filename>', methods=['GET'])
def download_full(filename):
    logger = file_management.logger

    safe_name = _sanitize_filename(filename)
    if not safe_name:
        return _error("Invalid filename", status_code=400)

    data_dir = _get_data_dir()

    candidates = []
    for sub in os.listdir(data_dir):
        folder = os.path.join(data_dir, sub)
        if not os.path.isdir(folder):
            continue
        manifest_path = os.path.join(folder, "manifest.json")
        if not os.path.isfile(manifest_path):
            continue

        try:
            with open(manifest_path, "r", encoding="utf-8") as mf:
                m = json.load(mf)
        except Exception:
            continue

        if m.get("original_filename") == safe_name:
            mtime = os.path.getmtime(manifest_path)
            candidates.append((mtime, sub, m["chunks"]))

    if not candidates:
        return _error("file not found", status_code=404)

    candidates.sort(reverse=True, key=lambda x: x[0])
    _, chosen_upload_id, chunk_list = candidates[0]
    upload_folder = os.path.join(data_dir, chosen_upload_id)

    def stream_all_chunks() -> Iterator[bytes]:
        for blob_id in chunk_list:
            blob_path = os.path.join(upload_folder, blob_id)
            if not os.path.isfile(blob_path):
                raise FileNotFoundError(blob_id)
            with open(blob_path, "rb") as f:
                while True:
                    data = f.read(CHUNK_SIZE)
                    if not data:
                        break
                    yield data

    total_bytes = 0
    for blob_id in chunk_list:
        blob_path = os.path.join(upload_folder, blob_id)
        total_bytes += os.path.getsize(blob_path)

    headers = {
        "Content-Disposition": f"attachment; filename={safe_name}",
        "Content-Length": str(total_bytes),
        "Content-Type": "application/octet-stream"
    }

    return Response(stream_all_chunks(), headers=headers)

@file_management.route('/delete/<path:filename>', methods=['DELETE'])
def delete_file(filename):
    logger = file_management.logger

    safe_name = _sanitize_filename(filename)
    if not safe_name:
        return _error("Invalid filename", status_code=400)

    data_dir = _get_data_dir()
    deleted_any = False

    for sub in os.listdir(data_dir):
        upload_folder = os.path.join(data_dir, sub)
        if not os.path.isdir(upload_folder):
            continue

        manifest_path = os.path.join(upload_folder, "manifest.json")
        if not os.path.isfile(manifest_path):
            continue

        try:
            with open(manifest_path, "r", encoding="utf-8") as mf:
                m = json.load(mf)
        except Exception:
            continue

        if m.get("original_filename") == safe_name:
            try:
                shutil.rmtree(upload_folder)
                deleted_any = True
            except Exception as e:
                logger.error(f"Failed to delete folder {upload_folder}: {e}")
                return _error("Error deleting files", status_code=500)

    if not deleted_any:
        return _error("file not found", status_code=404)

    return jsonify({"deleted": safe_name}), 200