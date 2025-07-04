# Users Microservice

A production-ready users microservice built with Flask and PostgreSQL, featuring structured logging to logz.io.

## Features

- **CRUD Operations**: Create, read, and soft-delete users
- **Snowflake ID Generation**: Unique user identifiers 
- **Soft Delete**: Users are marked as deleted, not permanently removed
- **User Reactivation**: Creating a deleted user reactivates them
- **Structured Logging**: JSON logs sent to logz.io with comprehensive event tracking
- **Email Validation**: Robust email format validation

## Quick Start

### Prerequisites
- Docker and Docker Compose
- logz.io account and API key

### Run the Service

```bash
# Clone and navigate to the project root
cd backend-rebase

# Start the services
docker-compose up -d

# The API will be available at http://localhost:5001
```

### Environment Variables

Required environment variables (set in `docker-compose.yml` in the root directory):

```bash
DB_HOST=db
DB_PORT=5432
DB_NAME=app_db
DB_USER=app_user
DB_PASSWORD=secret
logzIO_api_key=your-logzio-api-key
```

## API Endpoints

### Create/Update User
```http
POST /users/
Content-Type: application/json

{
  "email": "user@example.com",
  "full_name": "John Doe"
}
```

**Responses:**
- `201` - User created
- `200` - User already active (no changes)
- `400` - Invalid input data

### Get User
```http
GET /users/{email}
```

**Response (200):**
```json
{
  "email": "user@example.com",
  "full_name": "John Doe", 
  "joined_at": "2025-06-29T09:00:00.000000Z"
}
```

**Response (404):**
```json
{
  "error": "User not found"
}
```

### Delete User (Soft Delete)
```http
DELETE /users/{email}
```

**Response:** `204` (empty body)

## Database Schema

```sql
CREATE TABLE users (
    id VARCHAR PRIMARY KEY NOT NULL UNIQUE,           -- Snowflake ID
    email VARCHAR(200) NOT NULL UNIQUE,               -- User email
    full_name VARCHAR(200) NOT NULL,                  -- Full name
    joined_at TIMESTAMP NOT NULL,                     -- UTC timestamp
    deleted_since TIMESTAMP                           -- Soft delete timestamp
);
```

## Logging Events


- `user_created` - New user registration
- `user_reactivated` - Deleted user recreated
- `user_already_active` - Attempted to create existing active user
- `user_retrieved` - User data fetched
- `user_not_found` - Attempted to fetch non-existent user
- `user_soft_deleted` - User marked as deleted
- `user_not_found_or_inactive` - Attempted to delete non-existent/inactive user
- `db_error` - Database operation errors

## Development

### Project Structure
```
backend-rebase/
├── docker-compose.yml       # Docker configuration (root level)
├── Dockerfile              # Container definition (root level)
├── init.sql                 # Database initialization (root level)
└── assignment_7/
    ├── users/                    # Main application package
    │   ├── api/v0/              # API routes
    │   ├── logger/              # Logging utilities
    │   ├── db_utils.py          # Database abstraction layer
    │   ├── config.py            # logz.io configuration
    │   └── app.py               # Flask application
    └── users_tests/             # Test suite
```

### Running Tests

```bash
# Run all tests
docker exec -it backend-rebase_web_1 python -m pytest users_tests/ -v

# Run specific test file
docker exec -it backend-rebase_web_1 python -m pytest users_tests/test_users_api.py -v

# Run specific test
docker exec -it backend-rebase_web_1 python -m pytest users_tests/test_users_api.py::test_create_user_success -v
```

### Local Development

```bash
# Build and run (from root directory)
docker-compose down
docker-compose build
docker-compose up -d

# View logs
docker-compose logs web
docker-compose logs db

# Database access
docker exec -it backend-rebase_db_1 psql -U app_user -d app_db

# Check health status
curl http://localhost:5001/health
curl http://localhost:5001/ready
```
