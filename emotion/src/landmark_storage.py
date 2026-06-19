import os
import csv
import numpy as np
from datetime import datetime


class LandmarkStorage:
    """
    Lưu tọa độ 468 landmarks ra 2 định dạng:
        - CSV  : dễ mở Excel, kiểm tra từng frame
        - NPZ  : numpy compressed, load nhanh khi tính EAR/MAR sau

    Cấu trúc thư mục đầu ra:
        data/landmarks/
            session_20241201_143022/
                landmarks.csv       ← toàn bộ frames, mỗi hàng 1 frame
                landmarks.npz       ← array (N, 468, 3) cho tính toán
                meta.txt            ← thông tin session
    """

    # Tên cột CSV cho 468 điểm × 3 tọa độ = 1404 cột
    # Ví dụ: lm000_x, lm000_y, lm000_z, lm001_x, ...
    LANDMARK_COLS = [
        f"lm{i:03d}_{axis}"
        for i in range(468)
        for axis in ("x", "y", "z")
    ]

    def __init__(self, base_dir="data/landmarks", session_name=None):
        if session_name is None:
            session_name = "session_" + datetime.now().strftime("%Y%m%d_%H%M%S")

        self.session_name = session_name
        self.session_dir  = os.path.join(base_dir, session_name)
        os.makedirs(self.session_dir, exist_ok=True)

        self.csv_path = os.path.join(self.session_dir, "landmarks.csv")
        self.npz_path = os.path.join(self.session_dir, "landmarks.npz")

        # Buffer tích lũy trước khi flush
        self._rows   = []          # list các dict → cho CSV
        self._arrays = []          # list numpy array (468,3) → cho NPZ
        self._frame_ids   = []
        self._timestamps  = []

        # Mở CSV writer
        self._csv_file   = open(self.csv_path, "w", newline="", encoding="utf-8")
        fieldnames       = ["frame_id", "timestamp_ms"] + self.LANDMARK_COLS
        self._csv_writer = csv.DictWriter(self._csv_file, fieldnames=fieldnames)
        self._csv_writer.writeheader()

        print(f"[LandmarkStorage] Session: {self.session_dir}")

    # ─────────────────────────────────────────
    # API chính: gọi mỗi frame
    # ─────────────────────────────────────────

    def save_frame(self, frame_id, coords_px, timestamp_ms=None):
        """
        Lưu 1 frame landmarks.

        Tham số:
            frame_id     : int hoặc str — số thứ tự frame
            coords_px    : numpy array shape (468, 3) hoặc (478, 3)
                           từ LandmarkExtractor.to_pixel_coords()
            timestamp_ms : thời điểm frame (ms), tự tính nếu None
        """
        if timestamp_ms is None:
            import time
            timestamp_ms = int(time.time() * 1000)

        # Chỉ lấy 468 điểm khuôn mặt (bỏ 10 điểm iris nếu có)
        coords = np.array(coords_px[:468], dtype=np.float32)

        # ── Lưu vào buffer NPZ ──
        self._arrays.append(coords)
        self._frame_ids.append(frame_id)
        self._timestamps.append(timestamp_ms)

        # ── Ghi ngay vào CSV (không buffer để không mất data khi crash) ──
        row = {"frame_id": frame_id, "timestamp_ms": timestamp_ms}
        flat = coords.flatten()  # (468*3,) = 1404 giá trị
        for col, val in zip(self.LANDMARK_COLS, flat):
            row[col] = round(float(val), 4)
        self._csv_writer.writerow(row)

    # ─────────────────────────────────────────
    # Flush NPZ khi xong session
    # ─────────────────────────────────────────

    def flush(self):
        """
        Lưu toàn bộ buffer ra file NPZ.
        Gọi 1 lần khi kết thúc session.

        NPZ chứa:
            coords      : shape (N, 468, 3) — N frames
            frame_ids   : shape (N,)
            timestamps  : shape (N,)
        """
        if not self._arrays:
            print("[LandmarkStorage] Không có dữ liệu để flush.")
            return

        coords_all = np.stack(self._arrays, axis=0)  # (N, 468, 3)

        np.savez_compressed(
            self.npz_path,
            coords     = coords_all,
            frame_ids  = np.array(self._frame_ids),
            timestamps = np.array(self._timestamps)
        )

        # Ghi meta
        meta_path = os.path.join(self.session_dir, "meta.txt")
        with open(meta_path, "w", encoding="utf-8") as f:
            f.write(f"session    : {self.session_name}\n")
            f.write(f"frames     : {len(self._arrays)}\n")
            f.write(f"landmarks  : 468 points × 3 coords (x_px, y_px, z)\n")
            f.write(f"csv        : {self.csv_path}\n")
            f.write(f"npz        : {self.npz_path}\n")
            f.write(f"npz shape  : {coords_all.shape}\n")

        print(f"[LandmarkStorage] Đã lưu {len(self._arrays)} frames")
        print(f"  CSV : {self.csv_path}")
        print(f"  NPZ : {self.npz_path}  shape={coords_all.shape}")

    def close(self):
        self._csv_file.flush()
        self._csv_file.close()
        self.flush()
        print("[LandmarkStorage] Đã đóng storage.")

    # ─────────────────────────────────────────
    # Load lại để dùng sau
    # ─────────────────────────────────────────

    @staticmethod
    def load_npz(npz_path):
        """
        Load file NPZ để tính EAR/MAR sau này.

        Trả về dict:
            coords     : numpy (N, 468, 3)  — tọa độ pixel
            frame_ids  : numpy (N,)
            timestamps : numpy (N,)

        Ví dụ dùng:
            data   = LandmarkStorage.load_npz("data/landmarks/session_xxx/landmarks.npz")
            coords = data['coords']          # shape (N, 468, 3)
            frame0 = coords[0]               # shape (468, 3) — frame đầu tiên
            nose   = coords[:, 4, :2]        # shape (N, 2) — tọa độ mũi qua tất cả frames
        """
        data = np.load(npz_path)
        print(f"[LandmarkStorage] Loaded: {npz_path}")
        print(f"  coords shape : {data['coords'].shape}")
        print(f"  frames       : {len(data['frame_ids'])}")
        return {
            'coords'    : data['coords'],
            'frame_ids' : data['frame_ids'],
            'timestamps': data['timestamps']
        }

    @staticmethod
    def get_landmark(coords_array, landmark_index):
        """
        Lấy tọa độ 1 điểm landmark qua tất cả frames.

        Ví dụ:
            nose_coords = LandmarkStorage.get_landmark(coords, 4)
            # → shape (N, 3): x, y, z của mũi qua N frames
        """
        return coords_array[:, landmark_index, :]
