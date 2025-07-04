SELECT current_database();

CREATE TABLE IF NOT EXISTS users (
    id VARCHAR PRIMARY KEY NOT NULL UNIQUE,
    full_name VARCHAR(200) NOT NULL,
    email VARCHAR(200) NOT NULL UNIQUE,
    joined_at TIMESTAMP NOT NULL,
    deleted_since TIMESTAMP
);
