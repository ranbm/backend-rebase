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
logger = logging.getLogger('rbm_awesome_logger')  # Get the same logger from app.py
EMAIL_REGEX = re.compile(r"^(?!.*\.\.)[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

@users_api.route('/<email>', methods=['GET'])
def get_user(email):
    try:
        user = get_user_by_email(email, include_deleted=False)
        
        if user:
            user_id, email, full_name, joined_at = user
            log_user_retrieval_event(LogEvent.USER_RETRIEVED, email, user_id)
            return jsonify({
                "email": email,
                "full_name": full_name,
                "joined_at": joined_at.isoformat() + "Z"  # ISO-8601 format with UTC indicator
            })
        else:
            log_user_retrieval_event(LogEvent.USER_NOT_FOUND, email)
            return jsonify({"error": "User not found"}), 404
            
    except Exception as e:
        log_error_event(LogEvent.DB_ERROR, str(e))
        return jsonify({"error": "internal server error"}), 500


@users_api.route('/<email>', methods=['DELETE'])
def delete_user(email):
    try:
        # Get the user_id if the user exists and is active (for logging)
        user_id = get_active_user_id(email)
        
        # Perform the soft delete using the exact SQL statement required
        deleted_since = datetime.datetime.utcnow()
        result, rows_affected = execute_update(
            "UPDATE users SET deleted_since = %s WHERE email = %s AND deleted_since IS NULL", 
            (deleted_since, email)
        )
        
        if rows_affected > 0:
            # User was successfully soft-deleted
            log_user_deletion_event(LogEvent.USER_SOFT_DELETED, email, user_id)
        else:
            # User doesn't exist or is already inactive
            log_user_deletion_event(LogEvent.USER_NOT_FOUND_OR_INACTIVE, email)
        
        # Return empty response as requested
        return "", 204
        
    except Exception as e:
        log_error_event(LogEvent.DB_ERROR, str(e))
        return jsonify({"error": "internal server error"}), 500


@users_api.route('/', methods=['POST'])
def create_or_update_user():
    data = request.get_json()

    if not data or 'email' not in data or 'full_name' not in data:
        return jsonify({"error": "email and full_name are required"}), 400

    email = data['email'].strip()
    full_name = data['full_name'].strip()

    if not EMAIL_REGEX.match(email):
        return jsonify({"error": "Invalid email format"}), 400
    if not full_name or len(full_name) > 200:
        return jsonify({"error": "Invalid full_name"}), 400

    user_id = generate_snowflake_id()
    joined_at = datetime.datetime.utcnow()

    try:
        upsert_query = """
            INSERT INTO users (id, full_name, email, joined_at)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (email) DO UPDATE
            SET
                full_name = EXCLUDED.full_name,
                joined_at = EXCLUDED.joined_at,
                deleted_since = NULL
            WHERE
                users.full_name IS DISTINCT FROM EXCLUDED.full_name OR
                users.deleted_since IS NOT NULL
            RETURNING id, email, deleted_since
        """
        
        result, rows_affected = execute_update(upsert_query, (user_id, full_name, email, joined_at))

        if result:
            user_id, email_returned, deleted_since = result

            # Use the semantic helper function
            event = LogEvent.USER_REACTIVATED if deleted_since else LogEvent.USER_CREATED
            log_user_event(event, user_id, email_returned)
            return "", 201

        else:
            # Use the semantic helper function
            log_user_event(LogEvent.USER_ALREADY_ACTIVE, user_id, email)
            return "", 200

    except Exception as e:
        # Use the semantic helper function  
        log_error_event(LogEvent.DB_ERROR, str(e))
        return jsonify({"error": "internal server error"}), 500


def generate_snowflake_id():
    timestamp = int(time.time() * 1000)
    rand = random.randint(1000, 9999)
    return f"{timestamp}{rand}"