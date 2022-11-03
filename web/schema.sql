CREATE TABLE IF NOT EXISTS video (
    hash TEXT PRIMARY KEY,
    location geometry NOT NULL,
    direction int NOT NULL,
    start_time TIMESTAMP NOT NULL,
    address TEXT NOT NULL
);
