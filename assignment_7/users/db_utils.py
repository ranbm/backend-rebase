import os
import psycopg2
from typing import Optional, Any, List, Tuple

def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),  # use explicit host
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "app_db"),
        user=os.getenv("DB_USER", "app_user"),
        password=os.getenv("DB_PASSWORD", "secret")
    )

def execute_query_single(query: str, params: tuple = ()) -> Optional[tuple]:
    """Execute a query and return a single row, or None if no results"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(query, params)
        result = cur.fetchone()
        return result
    finally:
        cur.close()
        conn.close()


def execute_query_all(query: str, params: tuple = ()) -> List[tuple]:
    """Execute a query and return all rows"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(query, params)
        results = cur.fetchall()
        return results
    finally:
        cur.close()
        conn.close()


def execute_update(query: str, params: tuple = ()) -> Tuple[Optional[tuple], int]:
    """Execute an UPDATE/INSERT/DELETE query and return (result, rows_affected)"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(query, params)
        rows_affected = cur.rowcount
        # For INSERT...RETURNING queries
        result = cur.fetchone() if "RETURNING" in query.upper() else None
        conn.commit()
        return result, rows_affected
    finally:
        cur.close()
        conn.close()


def get_user_by_email(email: str, include_deleted: bool = False) -> Optional[tuple]:
    """Get user by email. By default excludes deleted users."""
    where_clause = "WHERE email = %s"
    if not include_deleted:
        where_clause += " AND deleted_since IS NULL"
    
    query = f"SELECT id, email, full_name, joined_at FROM users {where_clause}"
    return execute_query_single(query, (email,))


def get_active_user_id(email: str) -> Optional[str]:
    """Get user_id for an active user by email"""
    result = execute_query_single(
        "SELECT id FROM users WHERE email = %s AND deleted_since IS NULL", 
        (email,)
    )
    return result[0] if result else None 