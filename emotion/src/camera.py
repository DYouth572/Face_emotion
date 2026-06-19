import cv2


class Camera:
    def __init__(self, camera_index=0, width=640, height=480, fps=30):
        """
        camera_index : 0 = webcam mặc định, 1 = webcam ngoài (nếu có)
        width/height : độ phân giải capture
        fps          : frame rate mong muốn (webcam có thể không đạt đúng)
        """
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.fps = fps
        self.cap = None

    def open(self):
        """Mở kết nối với camera, trả về True nếu thành công."""
        self.cap = cv2.VideoCapture(self.camera_index)

        if not self.cap.isOpened():
            raise RuntimeError(
                f"Không thể mở camera index={self.camera_index}. "
                "Kiểm tra lại kết nối hoặc thử index khác (0, 1, 2...)."
            )

        # Thiết lập các thông số camera
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS,          self.fps)

        # Đọc lại thông số thực tế (camera có thể không hỗ trợ đúng giá trị yêu cầu)
        actual_w   = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h   = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = self.cap.get(cv2.CAP_PROP_FPS)

        print(f"[Camera] Đã mở camera index={self.camera_index}")
        print(f"[Camera] Độ phân giải: {actual_w}x{actual_h} | FPS: {actual_fps}")

        return True

    def read(self):
        """
        Đọc 1 frame từ camera.
        Trả về (True, frame_bgr) nếu thành công, (False, None) nếu lỗi.
        """
        if self.cap is None or not self.cap.isOpened():
            return False, None

        ret, frame = self.cap.read()
        return ret, frame

    def set_resolution(self, width, height):
        """Update desired capture resolution and apply it to an opened camera."""
        self.width = width
        self.height = height
        if self.cap is not None and self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

    def get_fps(self):
        if self.cap:
            return self.cap.get(cv2.CAP_PROP_FPS)
        return 0

    def release(self):
        """Giải phóng tài nguyên camera."""
        if self.cap:
            self.cap.release()
            print("[Camera] Đã đóng camera.")

    # Hỗ trợ dùng với 'with' statement
    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
