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
        return

    extractor = LandmarkExtractor()
    prep      = Preprocessor()

    session_name = os.path.basename(session_dir)
    storage      = LandmarkStorage(base_dir="data/landmarks", session_name=session_name)

    for i, path in enumerate(frame_paths):
        frame_bgr, frame_rgb = prep.load_frame(path)
        if frame_bgr is None:
            continue

        frame_rgb = prep.prepare_for_mediapipe(frame_rgb)
        h, w = frame_bgr.shape[:2]

        raw_landmarks = extractor.extract(frame_rgb)

        if raw_landmarks:
            coords = extractor.to_pixel_coords(raw_landmarks, w, h)
            storage.save_frame(i, coords, i * 33)

    storage.close()
    extractor.release()


# ══════════════════════════════════════════
# CHẾ ĐỘ 4: Inspect
# ══════════════════════════════════════════

def run_inspect(npz_path):
    data = LandmarkStorage.load_npz(npz_path)
    coords = data['coords']

    print(f"Số frames: {coords.shape[0]}")
    print(f"Số landmarks: {coords.shape[1]}")


# ══════════════════════════════════════════
# CHẾ ĐỘ 5: PHÂN TÍCH TRẠNG THÁI
# ══════════════════════════════════════════

def run_face_analysis():
    camera    = Camera(camera_index=0, width=640, height=480, fps=30)
    extractor = LandmarkExtractor()
    prep      = Preprocessor()
    analyzer  = FaceAnalyzer(fps=30)

    camera.open()

    try:
        while True:
            ret, frame_bgr = camera.read()
            if not ret:
                break

            frame_rgb = prep.prepare_for_mediapipe(prep.bgr_to_rgb(frame_bgr))
            display   = frame_bgr.copy()

            raw_landmarks = extractor.extract(frame_rgb)

            if raw_landmarks:
                h, w = frame_bgr.shape[:2]
                display = extractor.draw_landmarks(display, raw_landmarks)

                coords = extractor.to_pixel_coords(raw_landmarks, w, h)
                result = analyzer.analyze_frame(coords)

                cv2.putText(display, f"EAR: {result['EAR_L']:.2f}",
                            (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 200, 0), 2)

            cv2.imshow("Mode 5: Face Analysis", display)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
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

    emotion_detector = EmotionDetector(analyze_every_n_frames=30)
    frame_count = 0

    camera.open()

    try:
        while True:
            ret, frame_bgr = camera.read()
            if not ret:
                break

            frame_count += 1

            frame_rgb = prep.prepare_for_mediapipe(prep.bgr_to_rgb(frame_bgr))
            display   = frame_bgr.copy()

            box = detector.get_primary_face(frame_rgb)

            emotion_label = "No face"
            confidence = 0.0

            if box:
                cv2.rectangle(display,
                              (box['x1'], box['y1']),
                              (box['x2'], box['y2']),
                              (0, 255, 0), 2)

                face_roi = detector.crop_face(frame_rgb, box, padding=0.2)

                emotion_label, confidence = emotion_detector.detect(face_roi, frame_count)

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
