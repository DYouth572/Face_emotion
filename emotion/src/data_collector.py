import cv2
import os
import time
from datetime import datetime


class DataCollector:
    """
    Chức năng 1: Quay video từ webcam và lưu ra file .mp4
    Chức năng 2: Cắt frames từ video đã quay và lưu ra file .jpg

    Quy trình:
        1. Quay video → data/videos/session_YYYYMMDD_HHMMSS.mp4
        2. Cắt frames → data/frames/session_YYYYMMDD_HHMMSS/frame_00001.jpg
    """

    def __init__(self, video_dir="data/videos", frame_dir="data/frames"):
        self.video_dir = video_dir
        self.frame_dir = frame_dir

        os.makedirs(video_dir, exist_ok=True)
        os.makedirs(frame_dir, exist_ok=True)

    # ──────────────────────────────────────────
    # CHỨC NĂNG 1: Quay video
    # ──────────────────────────────────────────

    def record_video(self, camera, duration_seconds=30, session_name=None):
        """
        Quay video từ camera trong N giây, lưu vào thư mục video_dir.

        Tham số:
            camera          : object Camera đã open()
            duration_seconds: thời gian quay (giây)
            session_name    : tên session, tự tạo từ timestamp nếu None

        Trả về: đường dẫn file video đã lưu
        """
        if session_name is None:
            session_name = "session_" + datetime.now().strftime("%Y%m%d_%H%M%S")

        video_path = os.path.join(self.video_dir, f"{session_name}.mp4")

        # Lấy thông số từ camera
        fps    = camera.get_fps() or 30
        _, sample_frame = camera.read()
        if sample_frame is None:
            raise RuntimeError("Không đọc được frame từ camera.")

        h, w = sample_frame.shape[:2]

        # Khởi tạo VideoWriter
        # mp4v codec → file .mp4
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(video_path, fourcc, fps, (w, h))

        print(f"[DataCollector] Bắt đầu quay video: {video_path}")
        print(f"[DataCollector] Thời gian: {duration_seconds}s | FPS: {fps} | Size: {w}x{h}")
        print("[DataCollector] Nhấn 'q' để dừng sớm.")

        start_time   = time.time()
        frame_count  = 0

        while True:
            ret, frame = camera.read()
            if not ret:
                print("[DataCollector] Lỗi đọc frame, dừng quay.")
                break

            writer.write(frame)
            frame_count += 1

            # Hiển thị preview với countdown
            elapsed   = time.time() - start_time
            remaining = max(0, duration_seconds - elapsed)

            preview = frame.copy()
            cv2.putText(preview, f"REC  {remaining:.1f}s", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            cv2.putText(preview, f"Frames: {frame_count}", (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            cv2.imshow("Recording - Nhan Q de dung", preview)

            # Dừng khi hết thời gian hoặc nhấn Q
            if elapsed >= duration_seconds:
                break
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("[DataCollector] Người dùng dừng quay.")
                break

        writer.release()
        cv2.destroyAllWindows()

        print(f"[DataCollector] Đã lưu video: {video_path} ({frame_count} frames)")
        return video_path

    # ──────────────────────────────────────────
    # CHỨC NĂNG 2: Cắt frames từ video
    # ──────────────────────────────────────────

    def extract_frames(self, video_path, frame_step=1, max_frames=None):
        """
        Cắt frames từ file video và lưu thành ảnh .jpg.

        Tham số:
            video_path  : đường dẫn file .mp4
            frame_step  : lấy 1 frame mỗi N frame (1=lấy tất cả, 3=lấy 1/3)
            max_frames  : giới hạn số frame tối đa (None = không giới hạn)

        Trả về:
            session_dir : thư mục chứa frames đã cắt
            frame_paths : list đường dẫn các file frame
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Không tìm thấy video: {video_path}")

        # Tạo thư mục session từ tên file video
        video_name  = os.path.splitext(os.path.basename(video_path))[0]
        session_dir = os.path.join(self.frame_dir, video_name)
        os.makedirs(session_dir, exist_ok=True)

        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps          = cap.get(cv2.CAP_PROP_FPS)

        print(f"[DataCollector] Bắt đầu cắt frames từ: {video_path}")
        print(f"[DataCollector] Tổng frame video: {total_frames} | FPS: {fps:.1f}")
        print(f"[DataCollector] frame_step={frame_step} → lấy ~{total_frames // frame_step} frames")

        frame_paths   = []
        frame_idx     = 0   # đếm tất cả frame đọc được
        saved_count   = 0   # đếm frame đã lưu

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Chỉ lưu frame theo bước nhảy
            if frame_idx % frame_step == 0:
                filename   = f"frame_{saved_count:05d}.jpg"
                save_path  = os.path.join(session_dir, filename)

                # Lưu với chất lượng JPEG 95 để giữ độ nét
                cv2.imwrite(save_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
                frame_paths.append(save_path)
                saved_count += 1

                # In tiến độ mỗi 100 frame
                if saved_count % 100 == 0:
                    print(f"[DataCollector]   Đã lưu {saved_count} frames...")

                # Giới hạn số frame nếu cần
                if max_frames and saved_count >= max_frames:
                    print(f"[DataCollector] Đã đạt giới hạn {max_frames} frames.")
                    break

            frame_idx += 1

        cap.release()
        print(f"[DataCollector] Hoàn tất: {saved_count} frames → {session_dir}")
        return session_dir, frame_paths
