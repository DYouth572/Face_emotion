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

# MODE 5
from test import FaceAnalyzer

# MODE 6 (DeepFace)
from deepface_emotion import EmotionDetector

# SQLITE
from sqlite_storage import SQLiteStorage

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "face_emotion.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "sql", "schema.sql")

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

    print("\n[COLLECT MODE] Quay {}s, cat moi {} frames\n".format(duration, frame_step))

    camera    = Camera(camera_index=0, width=640, height=480, fps=30)
    collector = DataCollector(video_dir="data/videos", frame_dir="data/frames")

    camera.open()
    try:
        video_path = collector.record_video(camera, duration_seconds=duration)
        session_dir, frame_paths = collector.extract_frames(
            video_path, frame_step=frame_step
        )
        print("\n[COLLECT] Xong! {} frames -> {}".format(len(frame_paths), session_dir))
        return session_dir, frame_paths
    finally:
        camera.release()
        cv2.destroyAllWindows()


# ══════════════════════════════════════════
# CHẾ ĐỘ 3: Offline
# ══════════════════════════════════════════

def run_offline(session_dir, print_every_n=30):
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
        h, w      = frame_bgr.shape[:2]
        ts_ms     = i * 33

        raw_landmarks = extractor.extract(frame_rgb)

        if raw_landmarks:
            coords = extractor.to_pixel_coords(raw_landmarks, w, h)
            storage.save_frame(frame_id=i, coords_px=coords, timestamp_ms=ts_ms)
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
    print("  So frames    : {}".format(coords.shape[0]))
    print("  So landmarks : {}".format(coords.shape[1]))
    print("  Toa do/diem  : {}  (x_px, y_px, z)".format(coords.shape[2]))
    print("\n  Vi du frame 0:")
    print("    Mui  (idx 4)  : x={:.2f}  y={:.2f}".format(
        coords[0, 4, 0], coords[0, 4, 1]))
    print("    Can  (idx 152): x={:.2f}  y={:.2f}".format(
        coords[0, 152, 0], coords[0, 152, 1]))
    print("    Tran (idx 10) : x={:.2f}  y={:.2f}".format(
        coords[0, 10, 0], coords[0, 10, 1]))


# ══════════════════════════════════════════
# CHẾ ĐỘ 5: PHÂN TÍCH TRẠNG THÁI
# ══════════════════════════════════════════

def run_face_analysis():
    camera    = Camera(camera_index=0, width=640, height=480, fps=30)
    extractor = LandmarkExtractor()
    prep      = Preprocessor()
    analyzer  = FaceAnalyzer(fps=30)  # Khởi tạo bộ phân tích
    frame_count = 0

    # Hybrid save config (Frame_metrics)
    save_every_n_frames = 10
    last_saved_state_text = None

    # Segment config (Event)
    min_event_duration_ms = 1000
    active_state = None
    active_start_ms = None

    storage = SQLiteStorage(db_path=DB_PATH, schema_path=SCHEMA_PATH)
    storage.init_schema()
    session_id = storage.create_session(
        mode="mode5_analysis",
        camera_index=0,
        width=640,
        height=480,
        fps=30.0,
    )
    print(f"[Mode5][SQLite] session_id={session_id}, db={DB_PATH}")

    def _pick_primary_state(states):
        """Map theo đúng state text của FaceAnalyzer; không match thì normal."""
        if not states:
            return "normal"
        joined = " | ".join(states).lower()
        if "ngu gat" in joined:
            return "sleepy"
        if "dang ngap" in joined:
            return "yawn"
        if "quay mat sang phai" in joined:
            return "head_turn_right"
        if "quay mat sang trai" in joined:
            return "head_turn_left"
        if "nhiu may" in joined:
            return "frown"
        if "phong ma" in joined:
            return "cheek_puff"
        if "mat mo to" in joined:
            return "eye_wide"
        if "nhay 1 mat" in joined:
            return "wink"
        if "nhech mep phai" in joined:
            return "smirk_right"
        if "nhech mep trai" in joined:
            return "smirk_left"
        if "tap trung" in joined:
            return "focus"
        if "ha mieng to" in joined:
            return "mouth_open"
        return "normal"

    def _calc_mode5_severity(state: str, duration_ms: int):
        """
        Tính severity (1..5) cho mode 5:
        - nền theo thời lượng event
        - cộng trọng số theo mức nguy cơ của trạng thái
        """
        if state == "normal":
            return None
        if duration_ms < 2000:
            base = 1
        elif duration_ms < 4000:
            base = 2
        elif duration_ms < 7000:
            base = 3
        elif duration_ms < 10000:
            base = 4
        else:
            base = 5

        state_boost = {
            "sleepy": 2,
            "yawn": 1,
            "head_turn_right": 1,
            "head_turn_left": 1,
            "frown": 0,
            "cheek_puff": 0,
            "eye_wide": 0,
            "wink": 0,
            "smirk_right": 0,
            "smirk_left": 0,
            "focus": 0,
            "mouth_open": 0,
            "normal": 0,
        }.get(state, 0)

        return max(1, min(5, base + state_boost))

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
            result = None

            raw_landmarks = extractor.extract(frame_rgb)

            if raw_landmarks:
                h, w = frame_bgr.shape[:2]
                # Vẽ các điểm landmark lên mặt để dễ quan sát
                display = extractor.draw_landmarks(display, raw_landmarks)

                coords = extractor.to_pixel_coords(raw_landmarks, w, h)
                # Nhận kết quả phân tích từ test.py
                result = analyzer.analyze_frame(coords)

                # 1. Hiển thị các chỉ số cơ bản (Góc trái trên)
                cv2.putText(display, f"EAR: {result['EAR_L']:.2f}", (20, 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                cv2.putText(display, f"MAR: {result['MAR']:.2f}", (20, 60), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

                # 2. Hiển thị DANH SÁCH TRẠNG THÁI (Góc phải trên hoặc dưới EAR)
                # Chúng ta sẽ vẽ mỗi trạng thái trên một dòng mới
                y0, dy = 100, 30  # Tọa độ y bắt đầu và khoảng cách giữa các dòng
                for i, state in enumerate(result['States']):
                    color = (0, 0, 255) if "NGU GAT" in state or "NGAP" in state else (0, 255, 0)
                    cv2.putText(display, f"> {state}", (20, y0 + i * dy), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

            # ===== Build mode5 events =====
            states = result["States"] if result else []
            primary_state = _pick_primary_state(states)
            state_text = ", ".join(states) if states else "NORMAL"

            if active_state is None:
                active_state = primary_state
                active_start_ms = timestamp_ms
            elif primary_state != active_state:
                duration_ms = timestamp_ms - active_start_ms
                if duration_ms >= min_event_duration_ms:
                    severity = _calc_mode5_severity(active_state, duration_ms)
                    storage.insert_event(
                        session_id=session_id,
                        event_type=f"mode5_{active_state}",
                        start_ms=active_start_ms,
                        end_ms=timestamp_ms,
                        severity=severity,
                        average_confidence=None,
                    )
                active_state = primary_state
                active_start_ms = timestamp_ms

            # ===== Hybrid save Frame_metrics =====
            periodic_save = (frame_count % save_every_n_frames == 0)
            state_changed = (state_text != last_saved_state_text)
            if periodic_save or state_changed:
                storage.insert_frame_metrics(
                    session_id=session_id,
                    frame_index=frame_count,
                    timestamp_ms=timestamp_ms,
                    face_detected=1 if raw_landmarks else 0,
                    ear_l=(result.get("EAR_L") if result else None),
                    ear_r=(result.get("EAR_R") if result else None),
                    mar=(result.get("MAR") if result else None),
                    brow_ratio=(result.get("BROW_R") if result else None),
                    cheek_ratio=(result.get("CHEEK_R") if result else None),
                    head_turn_ratio=None,
                    emotion_label=None,
                    emotion_confidence=None,
                    state_text=state_text,
                )
                last_saved_state_text = state_text

            if frame_count % 30 == 0:
                storage.commit()

            cv2.imshow("Mode 5: Face Analysis System", display)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        try:
            if active_state is not None and active_start_ms is not None:
                end_ms = int((frame_count / 30.0) * 1000)
                duration_ms = end_ms - active_start_ms
                if duration_ms >= min_event_duration_ms:
                    severity = _calc_mode5_severity(active_state, duration_ms)
                    storage.insert_event(
                        session_id=session_id,
                        event_type=f"mode5_{active_state}",
                        start_ms=active_start_ms,
                        end_ms=end_ms,
                        severity=severity,
                        average_confidence=None,
                    )
            storage.commit()
            storage.end_session(session_id)
            storage.commit()
            storage.close()
        except Exception as e:
            print(f"[SQLite] close error (mode5): {e}")

        camera.release()
        extractor.release()
        cv2.destroyAllWindows()


# ══════════════════════════════════════════
# CHẾ ĐỘ 6: DEEPFACE EMOTION
# ══════════════════════════════════════════

def run_emotion_detection():
    camera   = Camera(camera_index=0, width=640, height=480, fps=30)
    detector = FaceDetector(min_detection_confidence=0.6)
    prep     = Preprocessor()

    # DeepFace: phân tích mỗi 10 frame
    emotion_detector = EmotionDetector(analyze_every_n_frames=10)
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
            display = frame_bgr.copy()

            box = detector.get_primary_face(frame_rgb)

            if box:
                no_face_frames = 0
            else:
                no_face_frames += 1

            emotion_label = "No face"
            confidence = 0.0

            if box:
                cv2.rectangle(
                    display,
                    (box["x1"], box["y1"]),
                    (box["x2"], box["y2"]),
                    (0, 255, 0),
                    2
                )

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

            cv2.putText(
                display,
                f"Emotion: {emotion_label} ({confidence:.1f}%)",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 0, 255),
                2
            )

            cv2.imshow("Mode 6: Emotion Detection", display)

            if cv2.waitKey(1) & 0xFF == ord("q"):
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
# MENU
# ══════════════════════════════════════════

if __name__ == "__main__":
    while True:
        print("\n=== MENU ===")
        print("1 → Realtime Landmark")
        print("2 → Thu thập dữ liệu")
        print("3 → Offline")
        print("4 → Inspect")
        print("5 → Phân tích trạng thái")
        print("6 → Nhận diện cảm xúc (DeepFace)")
        print("0 → Thoát")

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
        elif choice == "0":
            break
