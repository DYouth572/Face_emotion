import cv2
import numpy as np


class Preprocessor:
    """
    Tiền xử lý ảnh theo đúng sơ đồ đã thống nhất:

        Frame gốc (BGR)
               │
               ▼ [shared] BGR → RGB  (1 lần duy nhất)
               │
        ┌──────┴──────────┐
        ▼                 ▼
    [Luồng 1]         [Luồng 2]
    MediaPipe          DeepFace
    (giữ nguyên)      (resize 224×224, normalize)
    """

    # ──────────────────────────────────────────
    # SHARED: dùng cho cả 2 luồng
    # ──────────────────────────────────────────

    @staticmethod
    def bgr_to_rgb(frame_bgr):
        """
        Bước bắt buộc TRƯỚC KHI feed vào bất kỳ luồng nào.
        OpenCV đọc ảnh dạng BGR, MediaPipe và DeepFace cần RGB.
        """
        return cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

    # ──────────────────────────────────────────
    # LUỒNG 1: MediaPipe FaceMesh
    # ──────────────────────────────────────────

    @staticmethod
    def prepare_for_mediapipe(frame_rgb):
        """
        MediaPipe chỉ cần:
          - Hệ màu RGB (đã làm ở bgr_to_rgb)
          - uint8
          - Không cần resize, không cần normalize
            → MediaPipe tự resize về 192×192 nội bộ

        Hàm này chỉ kiểm tra dtype và đảm bảo ảnh writeable
        (MediaPipe yêu cầu frame không phải read-only).
        """
        if frame_rgb.dtype != np.uint8:
            frame_rgb = frame_rgb.astype(np.uint8)

        # MediaPipe cần mảng writeable
        if not frame_rgb.flags['WRITEABLE']:
            frame_rgb = frame_rgb.copy()

        return frame_rgb

    # ──────────────────────────────────────────
    # LUỒNG 2: DeepFace
    # ──────────────────────────────────────────

    @staticmethod
    def prepare_for_deepface(frame_rgb, target_size=(224, 224)):
        """
        DeepFace emotion model (FER-2013) dùng 48×48 nội bộ,
        nhưng để tương thích với các backbone khác (VGGFace, ArcFace...)
        thì truyền vào 224×224 là an toàn nhất.
        DeepFace sẽ tự resize về kích thước nội bộ cần thiết.

        Nếu truyền face_crop (vùng đã crop) thì kết quả tốt hơn
        vì model không cần tự tìm mặt nữa.
        """
        resized = cv2.resize(frame_rgb, target_size,
                             interpolation=cv2.INTER_AREA)

        # Normalize về [0, 1] — DeepFace thực ra tự normalize bên trong,
        # nhưng làm ở đây để chuẩn bị nếu sau này dùng model custom.
        normalized = resized.astype(np.float32) / 255.0

        return normalized

    # ──────────────────────────────────────────
    # TIỆN ÍCH: đọc và xử lý ảnh từ file (dùng cho offline pipeline)
    # ──────────────────────────────────────────

    @staticmethod
    def load_frame(image_path):
        """
        Đọc ảnh từ file, trả về (frame_bgr, frame_rgb).
        Trả về (None, None) nếu đọc thất bại.
        """
        frame_bgr = cv2.imread(image_path)
        if frame_bgr is None:
            print(f"[Preprocessor] Không đọc được ảnh: {image_path}")
            return None, None

        frame_rgb = Preprocessor.bgr_to_rgb(frame_bgr)
        return frame_bgr, frame_rgb

    @staticmethod
    def get_frame_info(frame):
        """In thông tin frame để debug."""
        print(f"[Preprocessor] Shape: {frame.shape} | "
              f"dtype: {frame.dtype} | "
              f"min: {frame.min()} | max: {frame.max()}")
