SELECT current_database();

CREATE TABLE IF NOT EXISTS users (
    id VARCHAR PRIMARY KEY NOT NULL UNIQUE,
    full_name VARCHAR(200) NOT NULL,
    email VARCHAR(200) NOT NULL UNIQUE,
    joined_at TIMESTAMP NOT NULL,
    deleted_since TIMESTAMP
);

CREATE TABLE IF NOT EXISTS page_hourly_views (
    page_id TEXT NOT NULL,
    hour_start TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    view_count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (page_id, hour_start)
);