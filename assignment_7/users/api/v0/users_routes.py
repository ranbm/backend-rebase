import datetime
import logging
import random
import re
import time

from flask import Blueprint, jsonify, request

from users.db_utils import get_user_by_email, get_active_user_id, execute_update
from users.logger.log_types import LogEvent
from users.logger.logger import log_user_event, log_error_event, log_user_retrieval_event, log_user_deletion_event

users_api = Blueprint('users', __name__)
logger = logging.getLogger('rbm_awesome_logger')
EMAIL_REGEX = re.compile(r"^(?!.*\.\.)[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

@users_api.route('/<email>', methods=['GET'])
async def get_user(email):
    try:
        user = await get_user_by_email(email, include_deleted=False)
        if user:
            user_id, email, full_name, joined_at = user
            log_user_retrieval_event(LogEvent.USER_RETRIEVED, user_id)
            return jsonify({
                "email": email,
                "full_name": full_name,
                "joined_at": joined_at.isoformat() + "Z"  # ISO-8601 format with UTC indicator
            })
        else:
            log_user_retrieval_event(LogEvent.USER_NOT_FOUND)
            return jsonify({"error": "User not found"}), 404
            
    except Exception as e:
        log_error_event(LogEvent.DB_ERROR, str(e))
        return jsonify({"error": "internal server error"}), 500


@users_api.route('/<email>', methods=['DELETE'])
async def delete_user(email):
    try:
        user_id = await get_active_user_id(email)
        
        deleted_since = datetime.datetime.utcnow()
        result, rows_affected = await execute_update(
            "UPDATE users SET deleted_since = $1 WHERE email = $2 AND deleted_since IS NULL", 
            (deleted_since, email)
        )
        
        if rows_affected > 0:
            log_user_deletion_event(LogEvent.USER_SOFT_DELETED, user_id)
        else:
            log_user_deletion_event(LogEvent.USER_NOT_FOUND_OR_INACTIVE)
        
        return "", 204
        
    except Exception as e:
        log_error_event(LogEvent.DB_ERROR, str(e))
        return jsonify({"error": "internal server error"}), 500


@users_api.route('/', methods=['POST'])
async def create_or_update_user():
    data = request.get_json()

    if not data:
        return jsonify({"error": "email and full_name are required"}), 400

    email = data.get('email', '').strip()
    full_name = data.get('full_name', '').strip()

    if not email or not full_name:
        return jsonify({"error": "email and full_name are required"}), 400

    if not EMAIL_REGEX.match(email):
        return jsonify({"error": "Invalid email format"}), 400
    if not full_name or len(full_name) > 200:
        return jsonify({"error": "Invalid full_name"}), 400

    user_id = generate_snowflake_id()
    joined_at = datetime.datetime.utcnow()

    try:
        upsert_query = """
            WITH existing_user AS (
                SELECT deleted_since IS NOT NULL as was_deleted
                FROM users 
                WHERE email = $1
            )
            INSERT INTO users (id, full_name, email, joined_at)
            VALUES ($2, $3, $4, $5)
            ON CONFLICT (email) DO UPDATE
            SET
                full_name = EXCLUDED.full_name,
                deleted_since = NULL
            WHERE
                users.full_name IS DISTINCT FROM EXCLUDED.full_name OR
                users.deleted_since IS NOT NULL
            RETURNING 
                id, 
                email,
                (xmax = 0) as is_inserted,
                (xmax != 0) as is_updated,
                (SELECT (xmax != 0 AND was_deleted) FROM existing_user) as was_reactivated
        """
        
        result, rows_affected = await execute_update(upsert_query, (email, user_id, full_name, email, joined_at))

        if result:
            returned_user_id, email_returned, is_inserted, is_updated, was_reactivated = result

            if is_inserted:
                event = LogEvent.USER_CREATED
            elif was_reactivated:
                event = LogEvent.USER_REACTIVATED
            else:
                event = LogEvent.USER_ALREADY_ACTIVE

            log_user_event(event, returned_user_id)
            return "", 201

        else:
            existing_user_id = await get_active_user_id(email)
            log_user_event(LogEvent.USER_ALREADY_ACTIVE, existing_user_id or user_id)
            return "", 200

    except Exception as e:
        log_error_event(LogEvent.DB_ERROR, str(e))
        return jsonify({"error": "internal server error"}), 500


def generate_snowflake_id():
    timestamp = int(time.time() * 1000)
    rand = random.randint(1000, 9999)
    return f"{timestamp}{rand}"