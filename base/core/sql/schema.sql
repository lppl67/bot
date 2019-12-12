CREATE TABLE IF NOT EXISTS currency (
    user_id     BIGINT          PRIMARY KEY,
    tokens      BIGINT          NOT NULL DEFAULT 0 CHECK (tokens >= 0),
    seed        VARCHAR(128)    NOT NULL DEFAULT 'default'
);