CREATE TABLE IF NOT EXISTS video_request (
    request_id TEXT PRIMARY KEY,
    request_location GEOMETRY NOT NULL,
    request_radius INT default 10,
    request_start_time TIMESTAMP NOT NULL,
    request_end_time TIMESTAMP NOT NULL,
    request_direction INT NOT NULL,
    reward DECIMAL NOT NULL,
    requestor_address TEXT NOT NULL,
    uploader_address TEXT NULL,
    actual_location GEOMETRY NULL,
    actual_median_direction INT NULL,
    uploaded_at TIMESTAMP NULL,
    actual_start_time TIMESTAMP NULL,
    actual_end_time TIMESTAMP NULL,
    file_hash TEXT NULL
);
