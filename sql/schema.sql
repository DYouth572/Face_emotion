PRAGMA foreign_keys = ON;

-- =========================
-- 1) Session
-- =========================
CREATE TABLE IF NOT EXISTS Session (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    session_code      TEXT    NOT NULL UNIQUE,
    mode              TEXT    NOT NULL,
    start_time        TEXT    NOT NULL,              -- ví dụ: 14:03:29 / 15-04-2026 (VN)
    end_time          TEXT,                          -- null khi session chưa kết thúc
    camera_index      INTEGER NOT NULL,
    width             INTEGER NOT NULL,
    height            INTEGER NOT NULL,
    fps               REAL    NOT NULL
);

-- =========================
-- 2) Frame_metrics
-- =========================
CREATE TABLE IF NOT EXISTS Frame_metrics (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id         INTEGER NOT NULL,
    frame_index        INTEGER NOT NULL,
    timestamp_ms       INTEGER NOT NULL,             -- mốc thời gian theo ms trong session
    face_detected      INTEGER NOT NULL CHECK (face_detected IN (0, 1)),

    ear_l              REAL,
    ear_r              REAL,
    mar                REAL,
    brow_ratio         REAL,
    cheek_ratio        REAL,
    head_turn_ratio    REAL,

    emotion_label      TEXT,
    emotion_confidence REAL,
    state_text         TEXT,

    FOREIGN KEY (session_id) REFERENCES Session(id) ON DELETE CASCADE,
    UNIQUE (session_id, frame_index),
    CHECK (timestamp_ms >= 0),
    CHECK (emotion_confidence IS NULL OR (emotion_confidence >= 0.0 AND emotion_confidence <= 100.0))
);

-- =========================
-- 3) Event
-- =========================
CREATE TABLE IF NOT EXISTS Event (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id   INTEGER NOT NULL,
    event_type   TEXT    NOT NULL,                  -- ví dụ: yawn, sleep, turn_left...
    start_ms     INTEGER NOT NULL,
    end_ms       INTEGER NOT NULL,
    duration_ms  INTEGER NOT NULL,
    severity            INTEGER,                     -- có thể null/ là cột để lưu mức độ nghiêm trọng/độ mạnh của một event (thường thang 1-5 theo schema của bạn)
    average_confidence  REAL,                        -- confidence trung bình của event (0..100)

    FOREIGN KEY (session_id) REFERENCES Session(id) ON DELETE CASCADE,
    CHECK (start_ms >= 0),
    CHECK (end_ms >= start_ms),
    CHECK (duration_ms >= 0),
    CHECK (severity IS NULL OR severity BETWEEN 1 AND 5),
    CHECK (average_confidence IS NULL OR (average_confidence >= 0.0 AND average_confidence <= 100.0))
);

-- =========================
-- Index để query nhanh
-- =========================
CREATE INDEX IF NOT EXISTS idx_frame_session_time
    ON Frame_metrics(session_id, timestamp_ms);

CREATE INDEX IF NOT EXISTS idx_frame_session_emotion
    ON Frame_metrics(session_id, emotion_label);

CREATE INDEX IF NOT EXISTS idx_event_session_type_start
    ON Event(session_id, event_type, start_ms);
