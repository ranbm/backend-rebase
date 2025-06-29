import os
import asyncpg
from typing import Optional, List, Tuple

async def get_connection():
    return await asyncpg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "app_db"),
        user=os.getenv("DB_USER", "app_user"),
        password=os.getenv("DB_PASSWORD", "secret")
    )

async def execute_query_single(query: str, params: tuple = ()) -> Optional[tuple]:
    conn = await get_connection()
    try:
        result = await conn.fetchrow(query, *params)
        return tuple(result) if result else None
    finally:
        await conn.close()


async def execute_query_all(query: str, params: tuple = ()) -> List[tuple]:
    conn = await get_connection()
    try:
        results = await conn.fetch(query, *params)
        return [tuple(row) for row in results]
    finally:
        await conn.close()


async def execute_update(query: str, params: tuple = ()) -> Tuple[Optional[tuple], int]:
    conn = await get_connection()
    try:
        async with conn.transaction():
            if "RETURNING" in query.upper():
                result = await conn.fetchrow(query, *params)
                rows_affected = 1 if result else 0
                return (tuple(result) if result else None, rows_affected)
            else:
                status = await conn.execute(query, *params)
                rows_affected = int(status.split()[-1]) if status else 0
                return None, rows_affected
    finally:
        await conn.close()


async def get_user_by_email(email: str, include_deleted: bool = False) -> Optional[tuple]:
    where_clause = "WHERE email = $1"
    if not include_deleted:
        where_clause += " AND deleted_since IS NULL"
    
    query = f"SELECT id, email, full_name, joined_at FROM users {where_clause}"
    return await execute_query_single(query, (email,))


async def get_active_user_id(email: str) -> Optional[str]:
    result = await execute_query_single(
        "SELECT id FROM users WHERE email = $1 AND deleted_since IS NULL", 
        (email,)
    )
    return result[0] if result else None