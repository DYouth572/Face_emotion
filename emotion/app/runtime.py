"""
FastAPI server used by the project start scripts.

This file is the contract layer between the React frontend and the local
camera/emotion pipeline. Keep the REST and WebSocket payloads aligned with
frontend-AI/src/types.
"""

import asyncio
import base64
import csv
import io
import json
import os
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone

import uvicorn
import cv2
import numpy as np
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

APP_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(APP_DIR)
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "src"))

from camera import Camera
from emotieff_emotion import EmotiEffEmotionDetector as EmotionDetector
from au_feature_extractor import AUFeatureExtractor
from au_ml_engine import AU_KEYS, AUMLEngine
from face_detector import FaceDetector
from landmark_extractor import LandmarkExtractor
from preprocessor import Preprocessor
from sqlite_storage import SQLiteStorage


storage = SQLiteStorage(
    db_path=os.path.join(BASE_DIR, "data", "face_emotion.db"),
    schema_path=os.path.join(BASE_DIR, "sql", "schema.sql"),
)
storage.init_schema()

app = FastAPI(title="Face Emotion Monitor API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

EMOTION_LABELS = ["angry", "disgust", "fear", "happy", "neutral", "sad", "surprise"]
VN_TZ = timezone(timedelta(hours=7))


def now_ms() -> int:
    return int(time.time() * 1000)


def make_base(msg_type: str) -> dict:
    return {"type": msg_type, "timestamp": now_ms(), "messageId": str(uuid.uuid4())}


def parse_session_time(value: str | None) -> int | None:
    if not value:
        return None
    for fmt in ("%H:%M:%S / %d-%m-%Y", "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            dt = datetime.strptime(value, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=VN_TZ)
            return int(dt.timestamp() * 1000)
        except ValueError:
            pass
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=VN_TZ)
        return int(dt.timestamp() * 1000)
    except ValueError:
        return None


def paginate(items: list, page: int, page_size: int) -> dict:
    total = len(items)
    start = (page - 1) * page_size
    return {
        "items": items[start : start + page_size],
        "pagination": {
            "page": page,
            "pageSize": page_size,
            "total": total,
            "totalPages": max(1, (total + page_size - 1) // page_size),
        },
    }


def classify_blink_rate(rate: float) -> str:
    if rate < 8:
        return "very_slow"
    if rate < 13:
        return "slow"
    if rate <= 20:
        return "normal"
    if rate <= 30:
        return "fast"
    return "very_fast"


def classify_mouth_state(mar: float) -> str:
    if mar >= 0.6:
        return "wide_open"
    if mar >= 0.4:
        return "open"
    if mar >= 0.25:
        return "slightly_open"
    return "closed"


def classify_brow_level(distance: float) -> str:
    if distance <= 0:
        return "none"
    if distance < 10:
        return "strong"
    if distance < 15:
        return "moderate"
    if distance < 25:
        return "slight"
    return "none"


def calc_focus_level(stress_score: float, blink_rate: float) -> str:
    if stress_score >= 70:
        return "low"
    if blink_rate and (blink_rate < 8 or blink_rate > 30):
        return "medium"
    if stress_score >= 40:
        return "medium"
    return "high"


def row_has_blink(row: dict) -> bool:
    return "blink" in (row.get("state_text") or "").lower()


def count_blink_events(metrics: list[dict]) -> int:
    total = 0
    was_blinking = False
    for row in metrics:
        is_blinking = row_has_blink(row)
        if is_blinking and not was_blinking:
            total += 1
        was_blinking = is_blinking
    return total


def estimate_frame_interval_ms(metrics: list[dict], fallback_fps: float = 15.0) -> int:
    timestamps = [int(row.get("timestamp_ms") or 0) for row in metrics]
    diffs = [cur - prev for prev, cur in zip(timestamps, timestamps[1:]) if cur > prev]
    if diffs:
        return max(1, int(sum(diffs) / len(diffs)))
    fps = fallback_fps if fallback_fps > 0 else 15.0
    return int(1000 / fps)


def build_blink_series(metrics: list[dict]) -> tuple[list[int], list[float]]:
    blink_times = []
    was_blinking = False
    rates = []
    for row in metrics:
        timestamp = int(row.get("timestamp_ms") or 0)
        is_blinking = row_has_blink(row)
        if is_blinking and not was_blinking:
            blink_times.append(timestamp)
        was_blinking = is_blinking
        rates.append(float(sum(1 for item in blink_times if 0 <= timestamp - item <= 60000)))
    return blink_times, rates


def sum_timeline_duration(
    timeline: list[dict],
    interval_ms: int,
    predicate,
) -> int:
    return int(sum(interval_ms for point in timeline if predicate(point)))


def build_emotion(emotion_label: str, raw_scores: dict) -> dict:
    label = emotion_label if emotion_label in EMOTION_LABELS else "neutral"
    scores = []
    dominant_score = 0.0
    for item in EMOTION_LABELS:
        pct = round(float(raw_scores.get(item, 0.0)), 2)
        score = round(pct / 100, 4)
        scores.append({"label": item, "score": score, "percentage": pct})
        if item == label:
            dominant_score = score
    return {
        "dominant": label,
        "dominantScore": dominant_score,
        "scores": scores,
        "processedAt": now_ms(),
    }


def apply_emotion_landmark_adjustments(emotion_label: str, raw_scores: dict, analysis: dict) -> tuple[str, dict]:
    scores = {label: float(raw_scores.get(label, 0.0)) for label in EMOTION_LABELS}
    states = [str(state).lower() for state in analysis.get("States", []) or []]
    state_text = " ".join(states)
    mar = float(analysis.get("MAR", 0.0) or 0.0)
    ear_l = float(analysis.get("EAR_L", 0.0) or 0.0)
    ear_r = float(analysis.get("EAR_R", ear_l) or 0.0)
    ear_avg = (ear_l + ear_r) / 2.0

    mouth_open = "ha mieng to" in state_text or mar >= 0.45
    mouth_wide_open = mar >= 0.6
    eyes_wide = "mat mo to" in state_text
    eyes_closed = "ngu gat" in state_text or "blink" in state_text or (0.0 < ear_avg < 0.18)
    frowning = "nhiu may" in state_text or "frown" in state_text

    surprise_cue = (
        mouth_open
        and not eyes_closed
        and (eyes_wide or mouth_wide_open or scores.get("surprise", 0.0) >= 15.0)
    )
    if surprise_cue:
        boost = 18.0
        if eyes_wide:
            boost += 12.0
        if mouth_wide_open:
            boost += 10.0

        floor = 70.0 if eyes_wide or mouth_wide_open else 55.0
        top_other = max(score for label, score in scores.items() if label != "surprise")
        scores["surprise"] = min(100.0, max(scores.get("surprise", 0.0) + boost, floor, top_other + 5.0))
        if scores.get("neutral", 0.0) >= 95.0:
            scores["neutral"] = min(scores["neutral"], 45.0)

    if frowning and not surprise_cue:
        scores["angry"] = min(100.0, scores.get("angry", 0.0) + 12.0)

    adjusted_label = max(scores, key=scores.get)
    return adjusted_label if adjusted_label in EMOTION_LABELS else emotion_label, scores


def build_features(
    analysis: dict,
    box: dict | None,
    raw_landmarks=None,
    processing_ms: float = 0.0,
) -> dict:
    states = analysis.get("States", []) or []
    ear_l = round(float(analysis.get("EAR_L", 0.0)), 4)
    ear_r = round(float(analysis.get("EAR_R", ear_l)), 4)
    ear_avg = round((ear_l + ear_r) / 2, 4)
    mar = round(float(analysis.get("MAR", 0.0)), 4)
    blink_rate = round(float(analysis.get("blink_rate", 0.0)), 2)
    brow_distance = round(float(analysis.get("BROW_R", 0.0)), 4)
    stress_score = round(float(analysis.get("stress_level", 0.0)) * 100, 2)

    bounding_box = None
    if box:
        bounding_box = {
            "x": int(box["x1"]),
            "y": int(box["y1"]),
            "width": int(box["x2"] - box["x1"]),
            "height": int(box["y2"] - box["y1"]),
            "confidence": round(float(box.get("confidence", 1.0)), 4),
        }

    landmarks = None
    if raw_landmarks:
        landmarks = [
            {"x": float(lm.x), "y": float(lm.y), "z": float(getattr(lm, "z", 0.0))}
            for lm in raw_landmarks
        ]

    return {
        "boundingBox": bounding_box,
        "landmarks": landmarks,
        "blink": {
            "isBlinking": "blink" in states,
            "ear": {"left": ear_l, "right": ear_r, "average": ear_avg},
            "leftEyeState": "closed" if ear_l < 0.21 else "open",
            "rightEyeState": "closed" if ear_r < 0.21 else "open",
            "countInWindow": int(analysis.get("blink_count", 0) or 0),
            "ratePerMinute": blink_rate,
            "rateCategory": classify_blink_rate(blink_rate),
        },
        "brow": {
            "furrowLevel": "strong" if any(s in ["Nhiu may", "NhÃ­u mÃ y", "frown"] for s in states) else "none",
            "innerDistance": brow_distance,
            "isAsymmetric": False,
            "leftHeight": round(float(analysis.get("brow_left_height", 0.0)), 4),
            "rightHeight": round(float(analysis.get("brow_right_height", 0.0)), 4),
        },
        "mouth": {
            "state": classify_mouth_state(mar),
            "mar": {"value": mar, "baseline": 0.15},
            "lipCorner": "smile" if "smile" in states else "frown" if "frown" in states else "none",
            "isTalking": "talk" in states,
            "cornerAngle": round(float(analysis.get("corner_angle", 0.0)), 4),
        },
        "tension": {
            "overallScore": stress_score,
            "foreheadScore": round(float(analysis.get("forehead_score", 0.0)) * 100, 2),
            "jawScore": round(float(analysis.get("jaw_score", 0.0)) * 100, 2),
            "periocularScore": round(float(analysis.get("periocular_score", 0.0)) * 100, 2),
        },
        "headPose": {
            "pitch": round(float(analysis.get("pitch", 0.0)), 2),
            "yaw": round(float(analysis.get("yaw", 0.0)), 2),
            "roll": round(float(analysis.get("roll", 0.0)), 2),
        },
        "extractedAt": now_ms(),
        "processingMs": round(processing_ms, 2),
        "_states": states,
    }


def metric_to_features(row: dict) -> dict:
    ear_l = float(row.get("ear_l") or 0.0)
    ear_r = float(row.get("ear_r") or ear_l)
    mar = float(row.get("mar") or 0.0)
    brow = float(row.get("au4") if row.get("au4") is not None else row.get("brow_ratio") or 0.0)
    au6 = row.get("au6") if row.get("au6") is not None else row.get("cheek_ratio")
    stress = min(100.0, max(0.0, float(au6 or 0.0) * 100))
    states = [s.strip() for s in (row.get("state_text") or "").split(",") if s.strip()]
    return {
        "boundingBox": None,
        "landmarks": None,
        "blink": {
            "isBlinking": "blink" in states,
            "ear": {"left": ear_l, "right": ear_r, "average": round((ear_l + ear_r) / 2, 4)},
            "leftEyeState": "closed" if ear_l < 0.21 else "open",
            "rightEyeState": "closed" if ear_r < 0.21 else "open",
            "countInWindow": 0,
            "ratePerMinute": 0.0,
            "rateCategory": "very_slow",
        },
        "brow": {
            "furrowLevel": classify_brow_level(brow),
            "innerDistance": brow,
            "isAsymmetric": False,
            "leftHeight": 0.0,
            "rightHeight": 0.0,
        },
        "mouth": {
            "state": classify_mouth_state(mar),
            "mar": {"value": mar, "baseline": 0.15},
            "lipCorner": "none",
            "isTalking": False,
            "cornerAngle": 0.0,
        },
        "tension": {
            "overallScore": stress,
            "foreheadScore": 0.0,
            "jawScore": 0.0,
            "periocularScore": 0.0,
        },
        "headPose": {"pitch": 0.0, "yaw": 0.0, "roll": 0.0},
        "extractedAt": int(row.get("timestamp_ms") or 0),
        "processingMs": 0.0,
    }


def metric_to_emotion_snapshot(row: dict) -> dict:
    label = row.get("emotion_label") or "neutral"
    if label not in EMOTION_LABELS:
        label = "neutral"
    confidence = float(row.get("emotion_confidence") or 0.0)
    confidence_pct = confidence * 100 if confidence <= 1.0 else confidence
    return {
        "timestamp": int(row.get("timestamp_ms") or 0),
        "frameIndex": int(row.get("frame_index") or 0),
        "result": build_emotion(label, {label: confidence_pct}),
    }


def fetch_metrics(session_id: int) -> list[dict]:
    rows = storage.conn.execute(
        "SELECT * FROM Frame_metrics WHERE session_id = ? ORDER BY frame_index ASC",
        (session_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def build_report(session_id: int) -> dict:
    session = storage.conn.execute("SELECT * FROM Session WHERE id = ?", (session_id,)).fetchone()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    metrics = fetch_metrics(session_id)
    started_at = parse_session_time(session["start_time"]) or now_ms()
    ended_at = parse_session_time(session["end_time"]) or now_ms()
    duration_ms = max(0, ended_at - started_at)
    features = [metric_to_features(row) for row in metrics]
    emotions = [metric_to_emotion_snapshot(row) for row in metrics]
    total = len(metrics)
    detected = sum(1 for row in metrics if row.get("face_detected"))
    labels = [e["result"]["dominant"] for e in emotions]
    stress_values = [f["tension"]["overallScore"] for f in features]
    ear_values = [f["blink"]["ear"]["average"] for f in features]
    interval_ms = estimate_frame_interval_ms(metrics, float(session["fps"] or 15))
    blink_times, blink_rates = build_blink_series(metrics)
    total_blinks = len(blink_times)
    distribution = {
        label: round(labels.count(label) * 100 / total, 2) if total else 0.0
        for label in EMOTION_LABELS
    }
    dominant = max(distribution, key=distribution.get) if total else "neutral"
    au_averages = {
        key: round(
            sum(float(row.get(key.lower()) or 0.0) for row in metrics) / total,
            4,
        )
        if total
        else 0.0
        for key in AU_KEYS
    }
    active_au_threshold = 0.35
    active_aus = [key for key, value in au_averages.items() if value >= active_au_threshold]
    facs_counts: dict[str, int] = {}
    for row in metrics:
        facs_text = row.get("raw_facs_combination") or row.get("state_text") or "Binh thuong"
        for facs_state in [item.strip() for item in str(facs_text).split(",") if item.strip()]:
            facs_counts[facs_state] = facs_counts.get(facs_state, 0) + 1
    facs_distribution = {
        state: round(count * 100 / total, 2) if total else 0.0
        for state, count in facs_counts.items()
    }
    dominant_facs = max(facs_counts, key=facs_counts.get) if facs_counts else "Binh thuong"

    timeline = []
    for idx, row in enumerate(metrics):
        feature = features[idx]
        emotion = emotions[idx]
        blink_rate = blink_rates[idx] if idx < len(blink_rates) else 0.0
        stress_score = feature["tension"]["overallScore"]
        point_au_scores = {key: float(row.get(key.lower()) or 0.0) for key in AU_KEYS}
        point_facs_text = row.get("raw_facs_combination") or row.get("state_text") or "Binh thuong"
        timeline.append(
            {
                "timestamp": started_at + int(row.get("timestamp_ms") or 0),
                "elapsedSec": round((row.get("timestamp_ms") or 0) / 1000, 2),
                "stressScore": stress_score,
                "blinkRate": blink_rate,
                "earAverage": feature["blink"]["ear"]["average"],
                "emotion": emotion["result"]["dominant"],
                "emotionEngine": "EmotiEff",
                "auScores": point_au_scores,
                "facsStates": [
                    item.strip()
                    for item in str(point_facs_text).split(",")
                    if item.strip()
                ],
                "focusLevel": calc_focus_level(stress_score, blink_rate),
            }
        )

    focus_counts = {
        "high": sum(1 for point in timeline if point["focusLevel"] == "high"),
        "medium": sum(1 for point in timeline if point["focusLevel"] == "medium"),
        "low": sum(1 for point in timeline if point["focusLevel"] == "low"),
    }
    focus_distribution = {
        key: round(value * 100 / total, 2) if total else 0.0
        for key, value in focus_counts.items()
    }
    total_observed_ms = max(duration_ms, total * interval_ms)
    long_no_blink_ms = 0
    if total_observed_ms and blink_times:
        gaps = [blink_times[0], *[cur - prev for prev, cur in zip(blink_times, blink_times[1:])]]
        gaps.append(max(0, int(total_observed_ms) - blink_times[-1]))
        long_no_blink_ms = sum(max(0, gap - 5000) for gap in gaps if gap > 5000)
    elif total_observed_ms:
        long_no_blink_ms = max(0, int(total_observed_ms) - 5000)

    return {
        "reportId": f"report_{session_id}",
        "sessionId": str(session_id),
        "generatedAt": now_ms(),
        "overview": {
            "startedAt": started_at,
            "endedAt": ended_at,
            "durationMs": duration_ms,
            "totalFrames": total,
            "averageFps": round(total / (duration_ms / 1000), 2) if duration_ms else float(session["fps"]),
            "faceDetectedFrames": detected,
            "faceDetectionRate": round(detected / total, 4) if total else 0.0,
        },
        "emotion": {
            "dominant": dominant,
            "distribution": distribution,
            "engine": "EmotiEff",
            "avgConfidence": round(
                sum(
                    (
                        float(row.get("emotion_confidence") or 0.0) * 100
                        if float(row.get("emotion_confidence") or 0.0) <= 1.0
                        else float(row.get("emotion_confidence") or 0.0)
                    )
                    for row in metrics
                )
                / total,
                2,
            )
            if total
            else 0.0,
            "transitionCount": sum(1 for prev, cur in zip(labels, labels[1:]) if prev != cur),
        },
        "auFacs": {
            "engine": "AU/FACS",
            "avgAuScores": au_averages,
            "activeAus": active_aus,
            "dominantFacs": dominant_facs,
            "facsDistribution": facs_distribution,
        },
        "blink": {
            "totalBlinks": total_blinks,
            "avgRatePerMin": round(total_blinks / (duration_ms / 60000), 2) if duration_ms else 0.0,
            "minRatePerMin": round(min(blink_rates), 2) if blink_rates else 0.0,
            "maxRatePerMin": round(max(blink_rates), 2) if blink_rates else 0.0,
            "avgEar": round(sum(ear_values) / total, 4) if total else 0.0,
            "longNoBlinkMs": int(long_no_blink_ms),
        },
        "stress": {
            "avgScore": round(sum(stress_values) / total, 2) if total else 0.0,
            "peakScore": round(max(stress_values), 2) if total else 0.0,
            "minScore": round(min(stress_values), 2) if total else 0.0,
            "highStressMs": sum_timeline_duration(timeline, interval_ms, lambda point: point["stressScore"] >= 70),
            "criticalStressMs": sum_timeline_duration(timeline, interval_ms, lambda point: point["stressScore"] >= 85),
            "avgForeheadScore": 0.0,
            "avgJawScore": 0.0,
            "avgPeriocularScore": 0.0,
        },
        "focus": {
            "distribution": focus_distribution,
            "highFocusMs": sum_timeline_duration(timeline, interval_ms, lambda point: point["focusLevel"] == "high"),
            "lowFocusMs": sum_timeline_duration(timeline, interval_ms, lambda point: point["focusLevel"] == "low"),
        },
        "alerts": {
            "totalCount": 0,
            "byType": {},
            "bySeverity": {"info": 0, "warning": 0, "critical": 0},
        },
        "timeline": timeline,
    }


@app.get("/health")
def health():
    return {
        "success": True,
        "data": {
            "status": "ok",
            "version": "1.1.1-au-facs",
            "services": {
                "camera": True,
                "mediapipe": True,
                "emotieff": True,
                "au_facs": True,
                "database": True,
            },
            "checkedAt": now_ms(),
        },
    }


@app.get("/api/health")
def api_health():
    return health()


@app.get("/api/sessions")
def get_sessions(page: int = Query(default=1, ge=1), pageSize: int = Query(default=10, ge=1, le=100)):
    rows = storage.conn.execute("SELECT * FROM Session ORDER BY id DESC").fetchall()
    items = []
    for row in rows:
        data = dict(row)
        started_at = parse_session_time(data.get("start_time")) or 0
        ended_at = parse_session_time(data.get("end_time")) or started_at
        metrics = storage.conn.execute(
            """
            SELECT emotion_label, cheek_ratio, au6, state_text, raw_facs_combination
            FROM Frame_metrics
            WHERE session_id = ?
            """,
            (data["id"],),
        ).fetchall()
        
        metric_dicts = [dict(m) for m in metrics]
        total_blinks = count_blink_events(metric_dicts)
        stress_sum = 0
        peak_stress = 0.0
        emotions = {}
        facs_counts = {}
        for m in metrics:
            au6_score = m["au6"] if m["au6"] is not None else m["cheek_ratio"]
            stress_score = (au6_score or 0) * 100
            stress_sum += stress_score
            peak_stress = max(peak_stress, stress_score)
            emo = m["emotion_label"] or "neutral"
            emotions[emo] = emotions.get(emo, 0) + 1
            facs_text = m["raw_facs_combination"] or m["state_text"]
            if facs_text:
                facs_counts[facs_text] = facs_counts.get(facs_text, 0) + 1
            if m["state_text"] and "blink" in m["state_text"].lower():
                # ÄÃ¢y lÃ  má»™t cÃ¡ch Æ°á»›c tÃ­nh, thá»±c táº¿ nÃªn Ä‘áº¿m event
                pass

        # Äáº¿m blink chÃ­nh xÃ¡c hÆ¡n tá»« table Event náº¿u cÃ³, hoáº·c dÃ¹ng max blink_count tá»« Frame_metrics
        # NhÆ°ng Frame_metrics cá»§a tÃ´i khÃ´ng lÆ°u blink_count. 
        # TÃ´i sáº½ láº¥y max(blink_count) náº¿u tÃ´i thÃªm nÃ³ vÃ o schema, hoáº·c Ä‘áº¿m chuá»—i "blink" chuyá»ƒn Ä‘á»•i.
        
        # Thá»­ láº¥y tá»« Frame_metrics náº¿u cÃ³ lÆ°u
        count_row = storage.conn.execute(
            "SELECT MAX(frame_index) as frames, COUNT(id) as count FROM Frame_metrics WHERE session_id = ?",
            (data["id"],)
        ).fetchone()
        
        dominant_emo = max(emotions, key=emotions.get) if emotions else "neutral"
        facs_summary = max(facs_counts, key=facs_counts.get) if facs_counts else "Binh thuong"
        avg_stress = stress_sum / len(metrics) if metrics else 0
        
        # TÃ­nh blink rate trung bÃ¬nh Ä‘Æ¡n giáº£n: (sá»‘ frames cÃ³ 'blink' / fps)
        total_frames = len(metrics)
        duration_ms = max(0, ended_at - started_at)
        avg_blink_rate = round(total_blinks / (duration_ms / 60000), 2) if duration_ms else 0.0
        
        items.append(
            {
                "sessionId": str(data["id"]),
                "sessionCode": data.get("session_code"),
                "mode": data.get("mode"),
                "startedAt": started_at,
                "endedAt": ended_at,
                "durationMs": duration_ms,
                "totalFrames": int(total_frames or 0),
                "averageFps": float(data.get("fps") or 0),
                "totalBlinks": total_blinks,
                "avgBlinkRate": avg_blink_rate,
                "avgStressScore": round(avg_stress, 1),
                "peakStressScore": round(peak_stress, 1),
                "dominantEmotion": dominant_emo,
                "facsSummary": facs_summary,
                "totalAlerts": 0,
            }
        )
    return {"success": True, "data": paginate(items, page, pageSize)}


@app.get("/api/sessions/{session_id}")
def get_session_details(session_id: int):
    row = storage.conn.execute("SELECT * FROM Session WHERE id = ?", (session_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    data = dict(row)
    started_at = parse_session_time(data.get("start_time")) or now_ms()
    ended_at = parse_session_time(data.get("end_time"))
    total_frames = storage.conn.execute(
        "SELECT COUNT(*) FROM Frame_metrics WHERE session_id = ?",
        (session_id,),
    ).fetchone()[0]
    return {
        "success": True,
        "data": {
            "sessionId": str(data["id"]),
            "status": "ended" if ended_at else "running",
            "startedAt": started_at,
            "endedAt": ended_at,
            "endReason": None,
            "config": {
                "targetFps": int(data.get("fps") or 15),
                "resolution": "720p",
                "enableBlink": True,
                "enableEmotion": True,
                "enableMuscleTension": True,
                "enableHeadPose": True,
                "stressAlertThreshold": 70,
                "blinkAlertThreshold": 8,
            },
            "totalFrames": int(total_frames or 0),
            "averageFps": float(data.get("fps") or 0),
        },
    }


@app.delete("/api/sessions")
def delete_all_sessions():
    storage.conn.execute("DELETE FROM Frame_metrics")
    storage.conn.execute("DELETE FROM Event")
    storage.conn.execute("DELETE FROM Session")
    storage.commit()
    return {"success": True, "data": {"deleted": True}, "message": "All sessions deleted"}


@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: int):
    storage.conn.execute("DELETE FROM Frame_metrics WHERE session_id = ?", (session_id,))
    storage.conn.execute("DELETE FROM Event WHERE session_id = ?", (session_id,))
    cur = storage.conn.execute("DELETE FROM Session WHERE id = ?", (session_id,))
    storage.commit()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True, "data": {"deleted": True}, "message": "Session deleted"}


@app.get("/api/sessions/{session_id}/metrics")
def get_session_metrics(session_id: int):
    return {"success": True, "data": fetch_metrics(session_id)}


@app.get("/api/sessions/{session_id}/features")
def get_session_features(
    session_id: int,
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=50, ge=1, le=500),
):
    return {
        "success": True,
        "data": paginate([metric_to_features(row) for row in fetch_metrics(session_id)], page, pageSize),
    }


@app.get("/api/sessions/{session_id}/emotions")
def get_session_emotions(
    session_id: int,
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=50, ge=1, le=500),
):
    return {
        "success": True,
        "data": paginate([metric_to_emotion_snapshot(row) for row in fetch_metrics(session_id)], page, pageSize),
    }


@app.get("/api/sessions/{session_id}/emotions/distribution")
def get_session_emotion_distribution(session_id: int):
    rows = storage.conn.execute(
        "SELECT emotion_label, COUNT(*) AS total FROM Frame_metrics WHERE session_id = ? GROUP BY emotion_label",
        (session_id,),
    ).fetchall()
    total = sum(int(row["total"] or 0) for row in rows)
    distribution = {label: 0.0 for label in EMOTION_LABELS}
    for row in rows:
        label = row["emotion_label"] if row["emotion_label"] in EMOTION_LABELS else "neutral"
        distribution[label] = round(int(row["total"] or 0) * 100 / total, 2) if total else 0.0
    return {"success": True, "data": distribution}


@app.get("/api/sessions/{session_id}/report")
def get_session_report(session_id: int):
    return {"success": True, "data": build_report(session_id)}


@app.get("/api/sessions/{session_id}/report/export")
def export_session_report(session_id: int, format: str = Query(default="csv", pattern="^(json|csv|pdf)$")):
    report = build_report(session_id)
    if format == "json":
        content = json.dumps(report, ensure_ascii=False, indent=2)
        return StreamingResponse(
            io.BytesIO(content.encode("utf-8")),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="report_{session_id}.json"'},
        )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["metric", "value"])
    writer.writerow(["sessionId", report["sessionId"]])
    writer.writerow(["startedAt", report["overview"]["startedAt"]])
    writer.writerow(["endedAt", report["overview"]["endedAt"]])
    writer.writerow(["durationMs", report["overview"]["durationMs"]])
    writer.writerow(["totalFrames", report["overview"]["totalFrames"]])
    writer.writerow(["emotionEngine", report["emotion"].get("engine", "EmotiEff")])
    writer.writerow(["dominantEmotion", report["emotion"]["dominant"]])
    writer.writerow(["auFacsEngine", report.get("auFacs", {}).get("engine", "AU/FACS")])
    writer.writerow(["dominantFacs", report.get("auFacs", {}).get("dominantFacs", "Binh thuong")])
    writer.writerow(["activeAus", "; ".join(report.get("auFacs", {}).get("activeAus", []))])
    writer.writerow(["avgStressScore", report["stress"]["avgScore"]])
    writer.writerow([])
    writer.writerow(
        [
            "timestamp",
            "elapsedSec",
            "stressScore",
            "blinkRate",
            "earAverage",
            "emotionEngine",
            "emotion",
            "facsStates",
            *AU_KEYS,
            "focusLevel",
        ]
    )
    for point in report["timeline"]:
        au_scores = point.get("auScores", {})
        writer.writerow(
            [
                point["timestamp"],
                point["elapsedSec"],
                point["stressScore"],
                point["blinkRate"],
                point["earAverage"],
                point.get("emotionEngine", report["emotion"].get("engine", "EmotiEff")),
                point["emotion"],
                "; ".join(point.get("facsStates", [])),
                *[au_scores.get(key, 0.0) for key in AU_KEYS],
                point["focusLevel"],
            ]
        )

    # The frontend historically allowed "pdf" here. Return a downloadable
    # report blob instead of failing, while the UI still uses client-side PDF.
    extension = "pdf" if format == "pdf" else "csv"
    media_type = "application/pdf" if format == "pdf" else "text/csv"
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="report_{session_id}.{extension}"'},
    )


class SessionState:
    def __init__(self):
        self.session_id: str | None = None
        self.db_session_id: int | None = None
        self.config: dict = {}
        self.is_running = False
        self.is_paused = False
        self.frame_index = 0
        self.started_at = 0


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    camera = Camera(camera_index=0, width=640, height=480, fps=30)
    detector = FaceDetector(min_detection_confidence=0.6)
    extractor = LandmarkExtractor()
    prep = Preprocessor()
    emotion_detector = EmotionDetector(analyze_every_n_frames=1)
    au_feature_extractor = AUFeatureExtractor()
    au_ml_engine = AUMLEngine(model_dir="models")
    au_ml_engine.load_pretrained_models()
    session = SessionState()

    async def heartbeat_loop():
        while True:
            await asyncio.sleep(30)
            try:
                await websocket.send_text(
                    json.dumps({**make_base("heartbeat"), "payload": {"serverTime": now_ms()}})
                )
            except Exception:
                break

    heartbeat_task = asyncio.create_task(heartbeat_loop())

    try:
        while True:
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                await handle_inbound(
                    websocket,
                    json.loads(raw),
                    session,
                    camera,
                    detector,
                    extractor,
                    prep,
                    emotion_detector,
                    au_feature_extractor,
                    au_ml_engine,
                )
            except asyncio.TimeoutError:
                continue

    except WebSocketDisconnect:
        print("[WS] Client disconnected")
    except Exception as exc:
        print(f"[WS] Error: {exc}")
        await send_error(websocket, "INTERNAL_ERROR", str(exc), fatal=True)
    finally:
        heartbeat_task.cancel()
        camera.release()
        detector.release()
        extractor.release()
        if session.db_session_id:
            storage.end_session(session.db_session_id)
            storage.commit()
        if session.is_running and session.session_id:
            try:
                await websocket.send_text(
                    json.dumps(
                        {
                            **make_base("session_ended"),
                            "payload": {"sessionId": session.session_id, "endedAt": now_ms(), "reason": "error"},
                        }
                    )
                )
            except Exception:
                pass


def decode_data_url_to_bgr(image_data: str):
    if "," in image_data:
        image_data = image_data.split(",", 1)[1]
    raw = base64.b64decode(image_data)
    arr = np.frombuffer(raw, dtype=np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


async def process_frame(
    websocket: WebSocket,
    frame_bgr,
    session: SessionState,
    detector: FaceDetector,
    extractor: LandmarkExtractor,
    prep: Preprocessor,
    emotion_detector: EmotionDetector,
    au_feature_extractor: AUFeatureExtractor,
    au_ml_engine: AUMLEngine,
):
    if not session.is_running or session.is_paused:
        return
    if frame_bgr is None:
        await send_error(websocket, "INVALID_FRAME", "Frame khong hop le", fatal=False)
        return

    frame_start = time.time()
    session.frame_index += 1
    frame_rgb = prep.prepare_for_mediapipe(prep.bgr_to_rgb(frame_bgr))
    height, width = frame_bgr.shape[:2]
    box = detector.get_primary_face(frame_rgb)
    raw_landmarks = extractor.extract(frame_rgb)

    analysis = {}
    au_scores = {key: 0.0 for key in AU_KEYS}
    facs_states = ["Binh thuong"]

    if raw_landmarks:
        coords = extractor.to_pixel_coords(raw_landmarks, width, height)

        au_features = au_feature_extractor.extract_features(coords)
        if au_features is not None:
            au_scores = au_ml_engine.predict_au_scores(au_features)

        facs_states = []
        if au_scores.get("AU6", 0.0) > 0.45 and au_scores.get("AU12", 0.0) > 0.45:
            facs_states.append("Vui ve: AU6 + AU12")

        if (
            au_scores.get("AU1", 0.0) > 0.45
            and au_scores.get("AU4", 0.0) > 0.40
            and au_scores.get("AU15", 0.0) > 0.35
        ):
            facs_states.append("Buon: AU1 + AU4 + AU15")

        if (
            au_scores.get("AU4", 0.0) > 0.45
            and (
                au_scores.get("AU5", 0.0) > 0.35
                or au_scores.get("AU7", 0.0) > 0.35
                or au_scores.get("AU23", 0.0) > 0.35
            )
        ):
            facs_states.append("Tuc gian: AU4 + AU5/AU7/AU23")

        if (
            au_scores.get("AU1", 0.0) > 0.45
            and au_scores.get("AU2", 0.0) > 0.45
            and au_scores.get("AU5", 0.0) > 0.40
            and au_scores.get("AU26", 0.0) > 0.35
        ):
            facs_states.append("Ngac nhien: AU1 + AU2 + AU5 + AU26")

        if (
            au_scores.get("AU1", 0.0) > 0.35
            and au_scores.get("AU2", 0.0) > 0.35
            and au_scores.get("AU4", 0.0) > 0.35
            and (
                au_scores.get("AU20", 0.0) > 0.35
                or au_scores.get("AU25", 0.0) > 0.35
                or au_scores.get("AU26", 0.0) > 0.35
            )
        ):
            facs_states.append("So hai: AU1 + AU2 + AU4 + AU20/AU25/AU26")

        if au_scores.get("AU9", 0.0) > 0.40 or au_scores.get("AU10", 0.0) > 0.40:
            facs_states.append("Ghe tom: AU9/AU10")

        if not facs_states:
            facs_states.append("Binh thuong")

    features = build_features(
        analysis,
        box,
        raw_landmarks=raw_landmarks,
        processing_ms=(time.time() - frame_start) * 1000,
    )

    emotion_label = "neutral"
    raw_scores = {label: 0.0 for label in EMOTION_LABELS}
    raw_scores["neutral"] = 100.0
    if box and session.config.get("enableEmotion", True):
        face_roi = detector.crop_face(frame_rgb, box, padding=0.45)
        emotion_label, raw_scores = emotion_detector.detect_with_scores(face_roi, session.frame_index)

    emotion = build_emotion(emotion_label, raw_scores)
    elapsed_sec = (now_ms() - session.started_at) / 1000.0
    current_fps = round(session.frame_index / elapsed_sec, 1) if elapsed_sec > 0 else 0.0
    await websocket.send_text(
        json.dumps(
            {
                **make_base("frame_result"),
                "payload": {
                    "features": features,
                    "emotion": emotion,
                    "au_scores": {key: float(au_scores.get(key, 0.0)) for key in AU_KEYS},
                    "facs_states": facs_states,
                    "frameIndex": session.frame_index,
                    "currentFps": current_fps,
                },
            }
        )
    )

    if session.db_session_id:
        try:
            storage.insert_frame_metrics(
                session_id=session.db_session_id,
                frame_index=session.frame_index,
                timestamp_ms=now_ms() - session.started_at,
                face_detected=1 if box else 0,
                ear_l=features["blink"]["ear"]["left"],
                ear_r=features["blink"]["ear"]["right"],
                mar=features["mouth"]["mar"]["value"],
                brow_ratio=au_scores.get("AU4", 0.0),
                cheek_ratio=au_scores.get("AU6", 0.0),
                head_turn_ratio=analysis.get("head_turn_ratio", 0.0),
                emotion_label=emotion_label,
                emotion_confidence=raw_scores.get(emotion_label, 0.0),
                state_text=", ".join(facs_states),
                au_scores=au_scores,
                raw_facs_combination=", ".join(facs_states),
            )
            if session.frame_index % 30 == 0:
                storage.commit()
        except Exception as exc:
            print(f"[DB] Error: {exc}")

    await check_and_send_alerts(websocket, features, session)


async def handle_inbound(
    websocket: WebSocket,
    msg: dict,
    session: SessionState,
    camera: Camera,
    detector: FaceDetector,
    extractor: LandmarkExtractor,
    prep: Preprocessor,
    emotion_detector: EmotionDetector,
    au_feature_extractor: AUFeatureExtractor,
    au_ml_engine: AUMLEngine,
):
    msg_type = msg.get("type", "")
    payload = msg.get("payload", {})

    if msg_type == "start_session":
        config = payload.get("config", {})
        session.session_id = str(uuid.uuid4())
        session.config = config
        session.is_running = True
        session.is_paused = False
        session.frame_index = 0
        session.started_at = now_ms()

        res_map = {"480p": (640, 480), "720p": (1280, 720), "1080p": (1920, 1080)}
        width, height = res_map.get(config.get("resolution", "720p"), (1280, 720))
        camera.set_resolution(width, height)

        try:
            session.db_session_id = storage.create_session(
                mode="websocket",
                camera_index=0,
                width=width,
                height=height,
                fps=config.get("targetFps", 15),
            )
            print(f"[DB] Created session ID: {session.db_session_id}")
        except Exception as exc:
            print(f"[DB] Error: {exc}")
            await send_error(websocket, "SESSION_CREATE_FAILED", str(exc), fatal=True)
            session.is_running = False
            session.session_id = None
            return

        await websocket.send_text(
            json.dumps(
                {
                    **make_base("session_started"),
                    "payload": {
                        "sessionId": session.session_id,
                        "startedAt": session.started_at,
                        "config": config,
                    },
                }
            )
        )

    elif msg_type == "stop_session":
        session.is_running = False
        ended_at = now_ms()
        if session.db_session_id:
            storage.end_session(session.db_session_id)
            storage.commit()

        await websocket.send_text(
            json.dumps(
                {
                    **make_base("session_ended"),
                    "payload": {
                        "sessionId": session.session_id or "",
                        "endedAt": ended_at,
                        "reason": "user_stopped",
                    },
                }
            )
        )
        camera.release()
        session.session_id = None
        session.db_session_id = None

    elif msg_type == "pause_session":
        session.is_paused = True
    elif msg_type == "resume_session":
        session.is_paused = False
    elif msg_type == "update_config":
        session.config.update(payload.get("config", {}))
    elif msg_type == "video_frame":
        frame_bgr = decode_data_url_to_bgr(payload.get("image", ""))
        await process_frame(
            websocket,
            frame_bgr,
            session,
            detector,
            extractor,
            prep,
            emotion_detector,
            au_feature_extractor,
            au_ml_engine,
        )
    elif msg_type == "start_calibration":
        await websocket.send_text(
            json.dumps(
                {
                    **make_base("calibration_done"),
                    "payload": {
                        "success": True,
                        "baselineEar": 0.25,
                        "baselineMar": 0.15,
                        "message": "Calibration completed",
                    },
                }
            )
        )


async def send_error(websocket: WebSocket, code: str, message: str, fatal: bool):
    try:
        await websocket.send_text(
            json.dumps({**make_base("error"), "payload": {"code": code, "message": message, "fatal": fatal}})
        )
    except Exception:
        pass


async def check_and_send_alerts(websocket: WebSocket, features: dict, session: SessionState):
    config = session.config
    stress_score = features.get("tension", {}).get("overallScore", 0.0)
    blink_rate = features.get("blink", {}).get("ratePerMinute", 0.0)
    alerts = []
    if stress_score >= config.get("stressAlertThreshold", 70):
        alerts.append(
            {
                "alertId": str(uuid.uuid4()),
                "alertType": "stress_high" if stress_score < 85 else "stress_critical",
                "severity": "warning" if stress_score < 85 else "critical",
                "message": f"Muc do cang thang cao: {stress_score:.0f}%",
                "data": {
                    "currentValue": stress_score / 100,
                    "threshold": config.get("stressAlertThreshold", 70) / 100,
                },
            }
        )
    if 0 < blink_rate < config.get("blinkAlertThreshold", 8):
        alerts.append(
            {
                "alertId": str(uuid.uuid4()),
                "alertType": "blink_low",
                "severity": "info",
                "message": f"Tan suat nhay mat thap: {blink_rate:.1f} lan/phut",
                "data": {"currentValue": blink_rate, "threshold": config.get("blinkAlertThreshold", 8)},
            }
        )
    for alert in alerts:
        await websocket.send_text(json.dumps({**make_base("alert"), "payload": alert}))


def run_server(host="0.0.0.0", port=8000):
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_server()
