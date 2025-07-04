from enum import Enum
from typing import Dict


class LogEvent(str, Enum):
    USER_CREATED = "user_created"
    USER_REACTIVATED = "user_reactivated"
    USER_ALREADY_ACTIVE = "user_already_active"
    USER_RETRIEVED = "user_retrieved"
    USER_NOT_FOUND = "user_not_found"
    USER_SOFT_DELETED = "user_soft_deleted"
    USER_NOT_FOUND_OR_INACTIVE = "user_not_found_or_inactive"
    DB_ERROR = "db_error"


class UserLog(Dict):
    event: LogEvent
    user_id: str
    email: str


class ErrorLog(Dict):
    event: LogEvent
    error: str