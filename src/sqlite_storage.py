import os
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo  # py>=3.9
except Exception:  # pragma: no cover
    ZoneInfo = None


_SESSION_TS_FMT = "%H:%M:%S / %d-%m-%Y"


def _vn_tzinfo():
    if ZoneInfo is not None:
        try:
            return ZoneInfo("Asia/Ho_Chi_Minh")
        except Exception:
            pass
    return timezone(timedelta(hours=7))


def _format_session_timestamp_vn(dt: datetime) -> str:
    """Định dạng giờ Việt Nam: HH:MM:SS / DD-MM-YYYY (ví dụ 21:03:29 / 15-04-2026)."""
    return dt.astimezone(_vn_tzinfo()).strftime(_SESSION_TS_FMT)


def now_session_timestamp_vn() -> str:
    return datetime.now(_vn_tzinfo()).strftime(_SESSION_TS_FMT)


def _parse_to_session_timestamp(value: str | None) -> str | None:
    """Chuyển ISO-8601 sang định dạng giờ Việt Nam; chuỗi hiển thị thì giữ nguyên."""
    if value is None:
        return None
    s = value.strip()
    if not s:
        return None
    if " / " in s and s.count(":") >= 2:
        return s
    try:
        iso = s.replace("Z", "+00:00") if s.endswith("Z") else s
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return _format_session_timestamp_vn(dt)
    except ValueError:
        return s


class SQLiteStorage:
    def __init__(self, db_path="data/face_emotion.db", schema_path="sql/schema.sql"):
        self.db_path = db_path
        self.schema_path = schema_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self.conn.row_factory = sqlite3.Row

    def init_schema(self):
        with open(self.schema_path, "r", encoding="utf-8") as f:
            sql = f.read()
        self.conn.executescript(sql)
        self.conn.commit()
        self._migrate_session_table_if_needed()
        self._migrate_frame_metrics_table_if_needed()
        self._migrate_session_time_to_vn_if_needed()

    def _migrate_session_time_to_vn_if_needed(self):
        """Chuẩn hóa start_time/end_time sang giờ Việt Nam cho DB hiện tại."""
        cols = [r[1] for r in self.conn.execute("PRAGMA table_info(Session)").fetchall()]
        if not cols or "start_time" not in cols:
            return
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS App_meta (
                key   TEXT PRIMARY KEY,
                value TEXT
            )
            """
        )
        migrated = self.conn.execute(
            "SELECT value FROM App_meta WHERE key = ?",
            ("session_time_vn_migrated_v2",),
        ).fetchone()
        if migrated and migrated[0] == "1":
            return
        rows = self.conn.execute("SELECT id, start_time, end_time FROM Session").fetchall()
        updates = []
        for sid, st, et in rows:
            st_new = self._to_vn_for_legacy_session_value(st)
            et_new = self._to_vn_for_legacy_session_value(et)
            if st_new != st or et_new != et:
                updates.append((st_new, et_new, sid))
        if updates:
            self.conn.executemany("UPDATE Session SET start_time = ?, end_time = ? WHERE id = ?", updates)
        self.conn.execute(
            "INSERT OR REPLACE INTO App_meta(key, value) VALUES (?, ?)",
            ("session_time_vn_migrated_v2", "1"),
        )
        self.conn.commit()

    def _to_vn_for_legacy_session_value(self, value: str | None) -> str | None:
        """One-time migration: giá trị ISO hoặc định dạng cũ (được coi là UTC) -> giờ VN."""
        if value is None:
            return None
        s = value.strip()
        if not s:
            return None
        if " / " in s and s.count(":") >= 2:
            try:
                dt_naive = datetime.strptime(s, _SESSION_TS_FMT)
                return _format_session_timestamp_vn(dt_naive.replace(tzinfo=timezone.utc))
            except Exception:
                return s
        return _parse_to_session_timestamp(s)

    def _migrate_session_table_if_needed(self):
        """DB cũ có cột video_path/...: chuyển sang schema mới và chuẩn hóa start_time/end_time."""
        cols = [r[1] for r in self.conn.execute("PRAGMA table_info(Session)").fetchall()]
        if not cols or "video_path" not in cols:
            return
        self.conn.execute("PRAGMA foreign_keys=OFF")
        self.conn.execute("BEGIN")
        try:
            self.conn.execute("DROP TABLE IF EXISTS Session_new")
            self.conn.execute(
                """
                CREATE TABLE Session_new (
                    id                INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_code      TEXT    NOT NULL UNIQUE,
                    mode              TEXT    NOT NULL,
                    start_time        TEXT    NOT NULL,
                    end_time          TEXT,
                    camera_index      INTEGER NOT NULL,
                    width             INTEGER NOT NULL,
                    height            INTEGER NOT NULL,
                    fps               REAL    NOT NULL
                )
                """
            )
            rows = self.conn.execute(
                """
                SELECT id, session_code, mode, start_time, end_time,
                       camera_index, width, height, fps
                FROM Session
                """
            ).fetchall()
            for row in rows:
                sid, code, mode, st, et, ci, w, h, f = row
                self.conn.execute(
                    """
                    INSERT INTO Session_new(
                        id, session_code, mode, start_time, end_time,
                        camera_index, width, height, fps
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        sid,
                        code,
                        mode,
                        _parse_to_session_timestamp(st),
                        _parse_to_session_timestamp(et),
                        ci,
                        w,
                        h,
                        f,
                    ),
                )
            self.conn.execute("DROP TABLE Session")
            self.conn.execute("ALTER TABLE Session_new RENAME TO Session")
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        finally:
            self.conn.execute("PRAGMA foreign_keys=ON")

    def create_session(self, mode: str, camera_index: int, width: int, height: int, fps: float) -> int:
        session_code = "S_" + uuid.uuid4().hex[:10]
        cur = self.conn.execute(
            """
            INSERT INTO Session(
                session_code, mode, start_time, end_time,
                camera_index, width, height, fps
            )
            VALUES (?, ?, ?, NULL, ?, ?, ?, ?)
            """,
            (
                session_code,
                mode,
                now_session_timestamp_vn(),
                camera_index,
                width,
                height,
                float(fps),
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def _migrate_frame_metrics_table_if_needed(self):
        """DB cũ có cột face_confidence: chuyển sang schema mới."""
        cols = [r[1] for r in self.conn.execute("PRAGMA table_info(Frame_metrics)").fetchall()]
        if not cols or "face_confidence" not in cols:
            return
        self.conn.execute("PRAGMA foreign_keys=OFF")
        self.conn.execute("BEGIN")
        try:
            self.conn.execute("DROP TABLE IF EXISTS Frame_metrics_new")
            self.conn.execute(
                """
                CREATE TABLE Frame_metrics_new (
                    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id         INTEGER NOT NULL,
                    frame_index        INTEGER NOT NULL,
                    timestamp_ms       INTEGER NOT NULL,
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
                )
                """
            )
            self.conn.execute(
                """
                INSERT INTO Frame_metrics_new(
                    id, session_id, frame_index, timestamp_ms, face_detected,
                    ear_l, ear_r, mar, brow_ratio, cheek_ratio, head_turn_ratio,
                    emotion_label, emotion_confidence, state_text
                )
                SELECT
                    id, session_id, frame_index, timestamp_ms, face_detected,
                    ear_l, ear_r, mar, brow_ratio, cheek_ratio, head_turn_ratio,
                    emotion_label, emotion_confidence, state_text
                FROM Frame_metrics
                """
            )
            self.conn.execute("DROP TABLE Frame_metrics")
            self.conn.execute("ALTER TABLE Frame_metrics_new RENAME TO Frame_metrics")
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_frame_session_time ON Frame_metrics(session_id, timestamp_ms)"
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_frame_session_emotion ON Frame_metrics(session_id, emotion_label)"
            )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        finally:
            self.conn.execute("PRAGMA foreign_keys=ON")

    def end_session(self, session_id: int):
        self.conn.execute(
            "UPDATE Session SET end_time = ? WHERE id = ?",
            (now_session_timestamp_vn(), session_id)
        )
        self.conn.commit()

    def insert_frame_metrics(
        self,
        session_id: int,
        frame_index: int,
        timestamp_ms: int,
        face_detected: int,
        ear_l: float = None,
        ear_r: float = None,
        mar: float = None,
        brow_ratio: float = None,
        cheek_ratio: float = None,
        head_turn_ratio: float = None,
        emotion_label: str = None,
        emotion_confidence: float = None,
        state_text: str = None,
    ):
        self.conn.execute(
            """
            INSERT INTO Frame_metrics(
                session_id, frame_index, timestamp_ms, face_detected,
                ear_l, ear_r, mar, brow_ratio, cheek_ratio, head_turn_ratio,
                emotion_label, emotion_confidence, state_text
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id, frame_index, timestamp_ms, face_detected,
                ear_l, ear_r, mar, brow_ratio, cheek_ratio, head_turn_ratio,
                emotion_label, emotion_confidence, state_text
            )
        )

    def insert_event(
        self,
        session_id: int,
        event_type: str,
        start_ms: int,
        end_ms: int,
        severity: int = None,
        average_confidence: float = None,
    ):
        duration_ms = max(0, int(end_ms) - int(start_ms))
        self.conn.execute(
            """
            INSERT INTO Event(
                session_id, event_type, start_ms, end_ms, duration_ms, severity, average_confidence
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (session_id, event_type, int(start_ms), int(end_ms), duration_ms, severity, average_confidence)
        )

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()