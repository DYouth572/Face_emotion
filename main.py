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

# BỘ NÃO PHÂN TÍCH (MODE 5)
from test import FaceAnalyzer

from emotion_detector import EmotionDetector


# ══════════════════════════════════════════
# CHẾ ĐỘ 1: Realtime
# ══════════════════════════════════════════

def run_realtime():
    print("\n[REALTIME MODE] Nhấn:")
    print("  'p' → print landmarks ra console (summary)")
    print("  'g' → print theo nhóm")
    print("  's' → bắt đầu / dừng ghi landmarks")
    print("  'q' → thoát\n")

    camera    = Camera(camera_index=0, width=640, height=480, fps=30)
    detector  = FaceDetector(min_detection_confidence=0.6)
    extractor = LandmarkExtractor()
    prep      = Preprocessor()
    storage   = None
    recording = False
    frame_count = 0

    camera.open()

    try:
        while True:
            ret, frame_bgr = camera.read()
            if not ret:
                break

            frame_count += 1
            h, w = frame_bgr.shape[:2]
            ts_ms = int(time.time() * 1000)

            # Shared preprocessing
            frame_rgb = prep.bgr_to_rgb(frame_bgr)
            frame_rgb = prep.prepare_for_mediapipe(frame_rgb)

            # Detect + landmarks
            box           = detector.get_primary_face(frame_rgb)
            raw_landmarks = extractor.extract(frame_rgb)
            display       = frame_bgr.copy()

            if box:
                cv2.rectangle(display,
                              (box['x1'], box['y1']),
                              (box['x2'], box['y2']),
                              (0, 255, 0), 2)

            if raw_landmarks:
                coords = extractor.to_pixel_coords(raw_landmarks, w, h)

                # Vẽ điểm landmark
                for x, y, z in coords[:468]:
                    cv2.circle(display, (int(x), int(y)), 1, (0, 200, 255), -1)

                # Lưu nếu đang recording
                if recording and storage:
                    storage.save_frame(frame_count, coords, ts_ms)

                status = f"468 lm  |  Frame #{frame_count}"
                if recording:
                    status += "  [GHI]"
                cv2.putText(display, status, (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 100), 2)
            else:
                cv2.putText(display, "Khong tim thay khuon mat", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 255), 2)

            # Ghi chú phím bấm
            hint = "P=print  G=groups  S=rec  Q=quit"
            cv2.putText(display, hint, (10, h - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)

            cv2.imshow("Luong 1: Landmark Extractor", display)

            key = cv2.waitKey(1) & 0xFF

            if key == ord('q'):
                break
            elif key == ord('p') and raw_landmarks:
                extractor.print_landmarks(raw_landmarks, w, h, mode="summary")
            elif key == ord('g') and raw_landmarks:
                extractor.print_landmarks(raw_landmarks, w, h, mode="groups")
            elif key == ord('s'):
                if not recording:
                    storage   = LandmarkStorage(base_dir="data/landmarks")
                    recording = True
                    print("[REALTIME] Bắt đầu ghi landmarks...")
                else:
                    recording = False
                    storage.close()
                    storage = None
                    print("[REALTIME] Đã dừng ghi.")

    finally:
        if recording and storage:
            storage.close()
        camera.release()
        detector.release()
        extractor.release()
        cv2.destroyAllWindows()


# ══════════════════════════════════════════
# CHẾ ĐỘ 2: Thu thập dữ liệu
# ══════════════════════════════════════════

def run_collect(duration=20, frame_step=3):
    print(f"\n[COLLECT MODE] Quay {duration}s, cắt mỗi {frame_step} frames\n")

    camera    = Camera(camera_index=0, width=640, height=480, fps=30)
    collector = DataCollector(video_dir="data/videos", frame_dir="data/frames")

    camera.open()
    try:
        video_path = collector.record_video(camera, duration_seconds=duration)
        session_dir, frame_paths = collector.extract_frames(
            video_path, frame_step=frame_step
        )
        print(f"\n[COLLECT] Xong! {len(frame_paths)} frames → {session_dir}")
        return session_dir, frame_paths
    finally:
        camera.release()
        cv2.destroyAllWindows()


# ══════════════════════════════════════════
# CHẾ ĐỘ 3: Offline — xử lý frames + lưu storage
# ══════════════════════════════════════════

def run_offline(session_dir, print_every_n=30):
    import glob

    frame_paths = sorted(glob.glob(os.path.join(session_dir, "*.jpg")))
    if not frame_paths:
        print(f"[OFFLINE] Không tìm thấy frames trong: {session_dir}")
        return

    print(f"\n[OFFLINE MODE] Xử lý {len(frame_paths)} frames...\n")

    extractor = LandmarkExtractor()
    prep      = Preprocessor()

    # Tạo storage với tên session từ tên thư mục
    session_name = os.path.basename(session_dir)
    storage      = LandmarkStorage(
        base_dir="data/landmarks",
        session_name=session_name
    )

    detected = 0
    missed   = 0

    for i, path in enumerate(frame_paths):
        frame_bgr, frame_rgb = prep.load_frame(path)
        if frame_bgr is None:
            continue

        frame_rgb = prep.prepare_for_mediapipe(frame_rgb)
        h, w      = frame_bgr.shape[:2]
        ts_ms     = i * 33  # giả lập 30fps → mỗi frame cách nhau ~33ms

        raw_landmarks = extractor.extract(frame_rgb)

        if raw_landmarks:
            coords = extractor.to_pixel_coords(raw_landmarks, w, h)
            storage.save_frame(frame_id=i, coords_px=coords, timestamp_ms=ts_ms)
            detected += 1

            if i % print_every_n == 0:
                print(f"Frame {i:05d} ✓ | nose=({coords[4,0]:.1f}, {coords[4,1]:.1f})")
        else:
            missed += 1
            if i % print_every_n == 0:
                print(f"Frame {i:05d} ✗ | không detect được mặt")

    storage.close()
    extractor.release()

    print(f"\n[OFFLINE] Hoàn tất: {detected} detect / {missed} miss / {len(frame_paths)} tổng")
    print(f"[OFFLINE] NPZ sẵn sàng để tính EAR/MAR: data/landmarks/{session_name}/landmarks.npz")


# ══════════════════════════════════════════
# CHẾ ĐỘ 4: Kiểm tra file đã lưu
# ══════════════════════════════════════════

def run_inspect(npz_path):
    """Load và in thông tin file NPZ đã lưu."""
    data   = LandmarkStorage.load_npz(npz_path)
    coords = data['coords']   # (N, 468, 3)

    print(f"\n[INSPECT] {npz_path}")
    print(f"  Số frames     : {coords.shape[0]}")
    print(f"  Số landmarks  : {coords.shape[1]}")
    print(f"  Tọa độ/điểm   : {coords.shape[2]}  (x_px, y_px, z)")
    print(f"\n  Ví dụ frame 0:")
    print(f"    Mũi  (idx 4)  : x={coords[0, 4,  0]:.2f}  y={coords[0, 4,  1]:.2f}")
    print(f"    Cằm  (idx 152): x={coords[0, 152, 0]:.2f}  y={coords[0, 152, 1]:.2f}")
    print(f"    Trán (idx 10) : x={coords[0, 10,  0]:.2f}  y={coords[0, 10,  1]:.2f}")
    print(f"\n  Ví dụ lấy tọa độ mũi qua {min(5, coords.shape[0])} frames đầu:")
    nose = coords[:5, 4, :2]
    for i, (x, y) in enumerate(nose):
        print(f"    Frame {i}: ({x:.2f}, {y:.2f})")


# ══════════════════════════════════════════
# CHẾ ĐỘ 5: NHẬN DIỆN TRẠNG THÁI 
# ══════════════════════════════════════════

def run_face_analysis():
    print("\n[FACE ANALYSIS MODE] Nhấn 'q' để thoát\n")
    
    camera    = Camera(camera_index=0, width=640, height=480, fps=30)
    extractor = LandmarkExtractor()
    prep      = Preprocessor()
    analyzer  = FaceAnalyzer(fps=30)

    emotion_detector = EmotionDetector(analyze_every_n_frames=30)
    frame_count = 0

    if not camera.open():
        print("[Lỗi] Không thể mở Camera.")
        return

    try:
        while True:
            ret, frame_bgr = camera.read()
            if not ret:
                break

            frame_count += 1

            frame_rgb = prep.prepare_for_mediapipe(prep.bgr_to_rgb(frame_bgr))
            h, w = frame_bgr.shape[:2]

            box = detector.get_primary_face(frame_rgb)
            raw_landmarks = extractor.extract(frame_rgb)
            display_frame = frame_bgr.copy()

            # ĐÃ SỬA: Chỉ cần check có raw_landmarks là chạy, không check len()
            if raw_landmarks:
                display_frame = extractor.draw_landmarks(display_frame, raw_landmarks)

                # Vẽ box mặt nếu có
                if box:
                    cv2.rectangle(display_frame,
                                  (box['x1'], box['y1']),
                                  (box['x2'], box['y2']),
                                  (0, 255, 0), 2)
                
                coords = extractor.to_pixel_coords(raw_landmarks, w, h)
                analysis_result = analyzer.analyze_frame(coords)

                # ===== PHẦN CỦA LAM hehehe: DEEPFACE EMOTION =====
                emotion_label = "Detecting..."
                confidence = 0.0

                if box:
                    face_roi = detector.crop_face(frame_rgb, box, padding=0.2)
                    emotion_label, confidence = emotion_detector.detect(face_roi, frame_count)

                # ===== HIỂN THỊ CẢM XÚC =====
                cv2.putText(display_frame,
                            f"Emotion: {emotion_label} ({confidence:.1f}%)",
                            (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 100, 255), 2)
                
                # In thông số EAR, MAR lên góc trái trên
                cv2.putText(display_frame, f"EAR L: {analysis_result['EAR_L']:.2f} | EAR R: {analysis_result['EAR_R']:.2f}", 
                            (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 200, 0), 2)
                cv2.putText(display_frame, f"MAR: {analysis_result['MAR']:.2f}", 
                            (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 200, 0), 2)
                
                # In Trạng thái (Nhắm mắt, Ngáp...) xuống dưới
                states = analysis_result["States"]
                y_offset = 130
                if len(states) == 0:
                    cv2.putText(display_frame, "Binh thuong", (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                else:
                    for state in states:
                        cv2.putText(display_frame, f">> {state}", (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                        y_offset += 30

            cv2.imshow("Mode 5: Face Analysis System", display_frame)
            if cv2.waitKey(1) & 0xFF == ord('q'): break

    except Exception as e:
        print(f"[Lỗi trong quá trình chạy]: {e}")
    finally:
        if hasattr(camera, 'cap') and camera.cap is not None: camera.cap.release()

        detector.release()
        extractor.release()
        
        cv2.destroyAllWindows()

# ══════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════

if __name__ == "__main__":
    while True:
        print("\n" + "=" * 50)
        print("  FACE ANALYSIS — Landmarks + Storage")
        print("=" * 50)
        print("\nChọn chế độ:")
        print("  1 → Realtime  (webcam + nhấn S để ghi)")
        print("  2 → Thu thập  (quay video + cắt frames)")
        print("  3 → Offline   (xử lý frames → lưu CSV + NPZ)")
        print("  4 → Inspect   (xem nội dung file NPZ)")
        print("  5 → Nhận diện (Phân tích trạng thái Realtime)")
        print("  0 → Thoát chương trình")

        choice = input("\nNhập lựa chọn (0/1/2/3/4/5): ").strip()

        if choice == "1":
            run_realtime()

        elif choice == "2":
            dur  = int(input("Thời gian quay (giây, mặc định 20): ").strip() or "20")
            step = int(input("Frame step (mặc định 3): ").strip() or "3")
            
            # Sửa lại gọi đúng tên hàm gốc của bạn: run_collect
            try:
                session_dir, _ = run_collect(duration=dur, frame_step=step)
                if session_dir:
                    cont = input("\nChạy offline + lưu landmarks? (y/n): ").strip()
                    if cont.lower() == "y":
                        run_offline(session_dir)
            except Exception as e:
                print(f"Lỗi khi thu thập: {e}")

        elif choice == "3":
            path = input("Đường dẫn thư mục frames: ").strip()
            # Sửa lại gọi đúng tên hàm gốc của bạn: run_offline
            run_offline(path)

        elif choice == "4":
            path = input("Đường dẫn file .npz (hoặc thư mục session): ").strip()
            
            # Kỹ thuật sửa lỗi: Nếu người dùng lỡ nhập thư mục, tự động nối thêm file landmarks.npz
            if os.path.isdir(path):
                path = os.path.join(path, "landmarks.npz")
                
            if os.path.exists(path):
                run_inspect(path)
            else:
                print(f"[Lỗi] Không tìm thấy file tại: {path}")
            
            
        elif choice == "5":
            run_face_analysis()

        elif choice == "0":
            print("Đã thoát chương trình!")
            break

        else:
            print("Lựa chọn không hợp lệ.")
