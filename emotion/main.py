"""
main.py — Pipeline đến Luồng 1 (Landmarks) + lưu storage.
"""

import cv2
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from camera              import Camera
from face_detector       import FaceDetector
from data_collector      import DataCollector
from preprocessor        import Preprocessor
from landmark_extractor  import LandmarkExtractor
from landmark_storage    import LandmarkStorage

# MODE 5 (AU/FACS)
from au_feature_extractor import AUFeatureExtractor
from au_ml_engine import AU_KEYS, AUMLEngine

# MODE 6 (EmotiEff)
from emotieff_emotion import EmotiEffEmotionDetector

# MODE 7 (FastAPI WebSocket)
from app.main import run_server

# SQLITE
from sqlite_storage import SQLiteStorage

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "face_emotion.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "sql", "schema.sql")


def infer_facs_states(au_scores):
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

    return facs_states or ["Binh thuong"]
# ══════════════════════════════════════════
# CHẾ ĐỘ 1: Realtime
# ══════════════════════════════════════════

def run_realtime():
    camera    = Camera(camera_index=0, width=640, height=480, fps=30)
    detector  = FaceDetector(min_detection_confidence=0.6)
    extractor = LandmarkExtractor()
    prep      = Preprocessor()

    camera.open()

    try:
        while True:
            ret, frame_bgr = camera.read()
            if not ret:
                break

            frame_rgb = prep.prepare_for_mediapipe(prep.bgr_to_rgb(frame_bgr))
            display   = frame_bgr.copy()

            box = detector.get_primary_face(frame_rgb)
            raw_landmarks = extractor.extract(frame_rgb)

            if box:
                cv2.rectangle(display,
                              (box['x1'], box['y1']),
                              (box['x2'], box['y2']),
                              (0, 255, 0), 2)

            if raw_landmarks:
                h, w = frame_bgr.shape[:2]
                coords = extractor.to_pixel_coords(raw_landmarks, w, h)

                for x, y, z in coords[:468]:
                    cv2.circle(display, (int(x), int(y)), 1, (0, 200, 255), -1)

            cv2.imshow("Mode 1: Realtime Landmark", display)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        camera.release()
        detector.release()
        extractor.release()
        cv2.destroyAllWindows()


# ══════════════════════════════════════════
# CHẾ ĐỘ 2: Thu thập dữ liệu
# ══════════════════════════════════════════

def run_collect(duration=20, frame_step=3):
    camera    = Camera(camera_index=0, width=640, height=480, fps=30)
    collector = DataCollector(video_dir="data/videos", frame_dir="data/frames")

    camera.open()
    try:
        video_path = collector.record_video(camera, duration_seconds=duration)
        session_dir, frame_paths = collector.extract_frames(
            video_path, frame_step=frame_step
        )
        return session_dir, frame_paths
    finally:
        camera.release()
        cv2.destroyAllWindows()


# ══════════════════════════════════════════
# CHẾ ĐỘ 3: Offline
# ══════════════════════════════════════════

def run_offline(session_dir):
    import glob

    frame_paths = sorted(glob.glob(os.path.join(session_dir, "*.jpg")))
    if not frame_paths:
        print("[OFFLINE] Khong tim thay frames trong: {}".format(session_dir))
        return
    
    print("\n[OFFLINE MODE] Xu ly {} frames...\n".format(len(frame_paths)))
    extractor = LandmarkExtractor()
    prep      = Preprocessor()

    session_name = os.path.basename(session_dir)
    storage      = LandmarkStorage(base_dir="data/landmarks", session_name=session_name)
    detected = 0
    missed   = 0

    for i, path in enumerate(frame_paths):
        frame_bgr, frame_rgb = prep.load_frame(path)
        if frame_bgr is None:
            continue
        
        frame_rgb = prep.prepare_for_mediapipe(frame_rgb)
        h, w = frame_bgr.shape[:2]
        ts_ms     = i * 33

        raw_landmarks = extractor.extract(frame_rgb)

        if raw_landmarks:
            coords = extractor.to_pixel_coords(raw_landmarks, w, h)
            storage.save_frame(i, coords, i * 33)
            detected += 1
            if i % print_every_n == 0:
                print("Frame {:05d} OK | nose=({:.1f}, {:.1f})".format(
                    i, coords[4, 0], coords[4, 1]))
        else:
            missed += 1
            if i % print_every_n == 0:
                print("Frame {:05d} MISS | khong detect duoc mat".format(i))

    storage.close()
    extractor.release()
    
    print("\n[OFFLINE] Hoan tat: {} detect / {} miss / {} tong".format(
        detected, missed, len(frame_paths)))
    print("[OFFLINE] NPZ san sang: data/landmarks/{}/landmarks.npz".format(session_name))

# ══════════════════════════════════════════
# CHẾ ĐỘ 4: Inspect
# ══════════════════════════════════════════

def run_inspect(npz_path):
    data = LandmarkStorage.load_npz(npz_path)
    coords = data['coords']
    
    print("\n[INSPECT] {}".format(npz_path))
    print(f"Số frames: {coords.shape[0]}")
    print(f"Số landmarks: {coords.shape[1]}")
    print("  Tọa độ / điểm  : {}  (x_px, y_px, z)".format(coords.shape[2]))
    print("\n  Vi du frame 0:")
    print("    Mui  (idx 4)  : x={:.2f}  y={:.2f}".format(
        coords[0, 4, 0], coords[0, 4, 1]))
    print("    Can  (idx 152): x={:.2f}  y={:.2f}".format(
        coords[0, 152, 0], coords[0, 152, 1]))
    print("    Tran (idx 10) : x={:.2f}  y={:.2f}".format(
        coords[0, 10, 0], coords[0, 10, 1]))

# ══════════════════════════════════════════
# CHẾ ĐỘ 5: PHÂN TÍCH AU/FACS
# ══════════════════════════════════════════

def run_face_analysis():
    camera = Camera(camera_index=0, width=640, height=480, fps=30)
    extractor = LandmarkExtractor()
    prep = Preprocessor()
    au_feature_extractor = AUFeatureExtractor()
    au_ml_engine = AUMLEngine(model_dir="models")
    au_ml_engine.load_pretrained_models()
    frame_count = 0

    save_every_n_frames = 10
    last_saved_state_text = None
    min_event_duration_ms = 1000
    active_state = None
    active_start_ms = None

    storage = SQLiteStorage(db_path=DB_PATH, schema_path=SCHEMA_PATH)
    storage.init_schema()
    session_id = storage.create_session(
        mode="mode5_au_facs",
        camera_index=0,
        width=640,
        height=480,
        fps=30.0,
    )
    print(f"[Mode5][AU/FACS][SQLite] session_id={session_id}, db={DB_PATH}")

    camera.open()

    try:
        while True:
            ret, frame_bgr = camera.read()
            if not ret:
                break

            frame_count += 1
            timestamp_ms = int((frame_count / 30.0) * 1000)
            frame_rgb = prep.prepare_for_mediapipe(prep.bgr_to_rgb(frame_bgr))
            display = frame_bgr.copy()

            raw_landmarks = extractor.extract(frame_rgb)
            au_scores = {key: 0.0 for key in AU_KEYS}
            facs_states = ["Binh thuong"]

            if raw_landmarks:
                h, w = frame_bgr.shape[:2]
                display = extractor.draw_landmarks(display, raw_landmarks)
                coords = extractor.to_pixel_coords(raw_landmarks, w, h)

                au_features = au_feature_extractor.extract_features(coords)
                if au_features is not None:
                    au_scores = au_ml_engine.predict_au_scores(au_features)
                facs_states = infer_facs_states(au_scores)

            y = 30
            cv2.putText(display, "AU/FACS Analysis", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 255), 2)
            y += 32

            top_aus = sorted(au_scores.items(), key=lambda item: item[1], reverse=True)[:6]
            for key, score in top_aus:
                cv2.putText(
                    display,
                    f"{key}: {score * 100:.0f}%",
                    (20, y),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0) if score > 0.45 else (180, 180, 180),
                    2,
                )
                y += 25

            y += 10
            for state in facs_states[:5]:
                cv2.putText(display, f"> {state}", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 200, 255), 2)
                y += 28

            primary_state = facs_states[0] if facs_states else "Binh thuong"
            state_text = ", ".join(facs_states)

            if active_state is None:
                active_state = primary_state
                active_start_ms = timestamp_ms
            elif primary_state != active_state:
                duration_ms = timestamp_ms - active_start_ms
                if duration_ms >= min_event_duration_ms and active_state != "Binh thuong":
                    storage.insert_event(
                        session_id=session_id,
                        event_type=f"facs_{active_state}",
                        start_ms=active_start_ms,
                        end_ms=timestamp_ms,
                        severity=None,
                        average_confidence=None,
                    )
                active_state = primary_state
                active_start_ms = timestamp_ms

            periodic_save = frame_count % save_every_n_frames == 0
            state_changed = state_text != last_saved_state_text
            if periodic_save or state_changed:
                storage.insert_frame_metrics(
                    session_id=session_id,
                    frame_index=frame_count,
                    timestamp_ms=timestamp_ms,
                    face_detected=1 if raw_landmarks else 0,
                    ear_l=None,
                    ear_r=None,
                    mar=None,
                    brow_ratio=au_scores.get("AU4", 0.0),
                    cheek_ratio=au_scores.get("AU6", 0.0),
                    head_turn_ratio=None,
                    emotion_label=None,
                    emotion_confidence=None,
                    state_text=state_text,
                    au_scores=au_scores,
                    raw_facs_combination=state_text,
                )
                last_saved_state_text = state_text

            if frame_count % 30 == 0:
                storage.commit()

            cv2.imshow("Mode 5: AU/FACS Analysis", display)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:
        try:
            if active_state is not None and active_start_ms is not None and active_state != "Binh thuong":
                end_ms = int((frame_count / 30.0) * 1000)
                duration_ms = end_ms - active_start_ms
                if duration_ms >= min_event_duration_ms:
                    storage.insert_event(
                        session_id=session_id,
                        event_type=f"facs_{active_state}",
                        start_ms=active_start_ms,
                        end_ms=end_ms,
                        severity=None,
                        average_confidence=None,
                    )
            storage.commit()
            storage.end_session(session_id)
            storage.commit()
            storage.close()
        except Exception as e:
            print(f"[SQLite] close error (mode5 au/facs): {e}")

        camera.release()
        extractor.release()
        cv2.destroyAllWindows()


def run_emotion_detection():
    camera   = Camera(camera_index=0, width=640, height=480, fps=30)
    detector = FaceDetector(min_detection_confidence=0.6)
    prep     = Preprocessor()

    emotion_detector = EmotiEffEmotionDetector(
        analyze_every_n_frames=10,
        engine="onnx",
        model_name="enet_b0_8_best_vgaf",
    )
    frame_count = 0

    # Hybrid save config (Frame_metrics)
    save_every_n_frames = 10
    confidence_delta_threshold = 10.0
    last_saved_emotion = None
    last_saved_confidence = None

    # Emotion segment -> Event
    seg_label = None
    seg_start_ms = None
    seg_conf_sum = 0.0
    seg_conf_count = 0
    min_event_duration_ms = 1000  # chỉ lưu event >= 1 giây

    # Debounce chống nhảy nhãn
    debounce_k = 2
    pending_label = None
    pending_count = 0

    # Mất mặt liên tục mới đóng segment
    no_face_frames = 0
    max_no_face_frames = 30  # ~1 giây ở 30fps

    storage = SQLiteStorage(db_path=DB_PATH, schema_path=SCHEMA_PATH)
    storage.init_schema()

    session_id = storage.create_session(
        mode="mode6_emotion",
        camera_index=0,
        width=640,
        height=480,
        fps=30.0,
    )
    print(f"[Mode6][SQLite] session_id={session_id}, db={DB_PATH}")

    camera.open()

    try:
        while True:
            ret, frame_bgr = camera.read()
            if not ret:
                break

            frame_count += 1
            timestamp_ms = int((frame_count / 30.0) * 1000)

            frame_rgb = prep.prepare_for_mediapipe(prep.bgr_to_rgb(frame_bgr))
            display   = frame_bgr.copy()
            box = detector.get_primary_face(frame_rgb)
            
            if box:
                no_face_frames = 0
            else:
                no_face_frames += 1

            emotion_label = "No face"
            confidence = 0.0

            if box:
                cv2.rectangle(display,
                              (box['x1'], box['y1']),
                              (box['x2'], box['y2']),
                              (0, 255, 0), 2)

                face_roi = detector.crop_face(frame_rgb, box, padding=0.2)

                emotion_label, confidence = emotion_detector.detect(face_roi, frame_count)
            
             # Quy đổi về kiểu lưu DB
            current_emotion = emotion_label if box else None
            current_conf = float(confidence) if box else None

            # ===== Build emotion segment events =====
            if current_emotion is not None:
                if seg_label is None:
                    # bắt đầu segment đầu tiên
                    seg_label = current_emotion
                    seg_start_ms = timestamp_ms
                    seg_conf_sum = (current_conf or 0.0)
                    seg_conf_count = 1 if current_conf is not None else 0
                    pending_label = None
                    pending_count = 0

                elif current_emotion == seg_label:
                    # vẫn cùng segment
                    pending_label = None
                    pending_count = 0
                    if current_conf is not None:
                        seg_conf_sum += current_conf
                        seg_conf_count += 1

                else:
                    # khác nhãn -> debounce
                    if pending_label != current_emotion:
                        pending_label = current_emotion
                        pending_count = 1
                    else:
                        pending_count += 1

                    if pending_count >= debounce_k:
                        # chốt đổi nhãn thật -> đóng segment cũ
                        seg_end_ms = timestamp_ms
                        duration_ms = seg_end_ms - seg_start_ms

                        if duration_ms >= min_event_duration_ms:
                            avg_conf = (seg_conf_sum / seg_conf_count) if seg_conf_count > 0 else None
                            storage.insert_event(
                                session_id=session_id,
                                event_type=f"emotion_{seg_label}",
                                start_ms=seg_start_ms,
                                end_ms=seg_end_ms,
                                severity=None,
                                average_confidence=(round(avg_conf, 2) if avg_conf is not None else None)
                            )

                        # mở segment mới
                        seg_label = current_emotion
                        seg_start_ms = seg_end_ms
                        seg_conf_sum = (current_conf or 0.0)
                        seg_conf_count = 1 if current_conf is not None else 0

                        pending_label = None
                        pending_count = 0

            else:
                # mất mặt ngắn thì bỏ qua, mất lâu thì đóng segment
                if seg_label is not None and seg_start_ms is not None and no_face_frames >= max_no_face_frames:
                    seg_end_ms = timestamp_ms
                    duration_ms = seg_end_ms - seg_start_ms

                    if duration_ms >= min_event_duration_ms:
                        avg_conf = (seg_conf_sum / seg_conf_count) if seg_conf_count > 0 else None
                        storage.insert_event(
                            session_id=session_id,
                            event_type=f"emotion_{seg_label}",
                            start_ms=seg_start_ms,
                            end_ms=seg_end_ms,
                            severity=None,
                            average_confidence=(round(avg_conf, 2) if avg_conf is not None else None)
                        )

                    # reset segment
                    seg_label = None
                    seg_start_ms = None
                    seg_conf_sum = 0.0
                    seg_conf_count = 0
                    pending_label = None
                    pending_count = 0

            # ===== Hybrid save Frame_metrics =====
            periodic_save = (frame_count % save_every_n_frames == 0)
            emotion_changed = (current_emotion != last_saved_emotion)

            confidence_changed = False
            if current_conf is None and last_saved_confidence is not None:
                confidence_changed = True
            elif current_conf is not None and last_saved_confidence is None:
                confidence_changed = True
            elif current_conf is not None and last_saved_confidence is not None:
                confidence_changed = abs(current_conf - last_saved_confidence) >= confidence_delta_threshold

            should_save = periodic_save or emotion_changed or confidence_changed

            if should_save:
                storage.insert_frame_metrics(
                    session_id=session_id,
                    frame_index=frame_count,
                    timestamp_ms=timestamp_ms,
                    face_detected=1 if box else 0,
                    emotion_label=current_emotion,
                    emotion_confidence=current_conf,
                    state_text=None
                )
                last_saved_emotion = current_emotion
                last_saved_confidence = current_conf

            # commit theo lô
            if frame_count % 30 == 0:
                storage.commit()

            cv2.putText(display,
                        f"Emotion: {emotion_label} ({confidence:.1f}%)",
                        (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        (0, 0, 255),
                        2)

            cv2.imshow("Mode 6: Emotion Detection", display)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        try:
            # đóng segment cuối (nếu còn)
            if seg_label is not None and seg_start_ms is not None:
                seg_end_ms = int((frame_count / 30.0) * 1000)
                duration_ms = seg_end_ms - seg_start_ms
                if duration_ms >= min_event_duration_ms:
                    avg_conf = (seg_conf_sum / seg_conf_count) if seg_conf_count > 0 else None
                    storage.insert_event(
                        session_id=session_id,
                        event_type=f"emotion_{seg_label}",
                        start_ms=seg_start_ms,
                        end_ms=seg_end_ms,
                        severity=None,
                        average_confidence=(round(avg_conf, 2) if avg_conf is not None else None)
                    )

            storage.commit()
            storage.end_session(session_id)
            storage.commit()
            storage.close()
        except Exception as e:
            print(f"[SQLite] close error: {e}")
        camera.release()
        detector.release()
        cv2.destroyAllWindows()

# ══════════════════════════════════════════
# CHẾ ĐỘ 7: FASTAPI WEBSOCKET SERVER 
# ══════════════════════════════════════════

def run_server_mode():
    """
    Khởi động FastAPI server để frontend kết nối qua WebSocket.
    Server sẽ xử lý realtime: Landmark + AU/FACS + EmotiEff Emotion.
    """
    print("\n[Server] Khởi động FastAPI WebSocket Server...")
    print("[Server] Frontend kết nối tại: ws://localhost:8000/ws")
    print("[Server] API docs tại: http://localhost:8000/docs")
    print("[Server] Nhấn Ctrl+C để dừng\n")
    run_server()


# ══════════════════════════════════════════
# MENU
# ══════════════════════════════════════════

if __name__ == "__main__":
    while True:
        print("\n=== MENU ===")
        print("1 -> Realtime Landmark")
        print("2 -> Thu thập dữ liệu")
        print("3 -> Offline")
        print("4 -> Inspect")
        print("5 -> Phân tích AU/FACS")
        print("6 -> Nhận diện cảm xúc (EmotiEff)")
        print("7 -> FastAPI WebSocket Server (cho Frontend)")
        print("0 -> Thoát")

        choice = input("Chọn: ").strip()

        if choice == "1":
            run_realtime()
        elif choice == "2":
            run_collect()
        elif choice == "3":
            path = input("Path: ")
            run_offline(path)
        elif choice == "4":
            path = input("NPZ path: ")
            run_inspect(path)
        elif choice == "5":
            run_face_analysis()
        elif choice == "6":
            run_emotion_detection()
        elif choice == "7":
            run_server_mode()
        elif choice == "0":
            break
