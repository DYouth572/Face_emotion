import cv2
import mediapipe as mp
import numpy as np


class FaceDetector:
    """
    Detect bounding box khuôn mặt bằng MediaPipe Face Detection.
    Module này CHỈ làm 1 việc: tìm vị trí khuôn mặt trong frame.
    Việc extract 468 landmarks là nhiệm vụ của landmark_extractor.py.

    Tại sao dùng MediaPipe Face Detection thay vì Haar Cascade?
    - Nhanh hơn, chính xác hơn với nhiều góc độ khuôn mặt
    - Trả về bounding box chuẩn để crop cho cả 2 luồng
    """

    def __init__(self, min_detection_confidence=0.6, model_selection=0):
        """
        min_detection_confidence : ngưỡng tin cậy (0.0–1.0)
        model_selection          : 0 = model gần (trong vòng 2m, phù hợp webcam)
                                   1 = model xa (tối đa 5m)
        """
        self.mp_face_detection = mp.solutions.face_detection
        self.mp_draw = mp.solutions.drawing_utils

        self.detector = self.mp_face_detection.FaceDetection(
            model_selection=model_selection,
            min_detection_confidence=min_detection_confidence
        )

        print("[FaceDetector] Đã khởi tạo MediaPipe Face Detection.")

    def detect(self, frame_rgb):
        """
        Nhận frame RGB (uint8), trả về list các bounding box.
        Mỗi bounding box là dict:
            {
                'x1': int, 'y1': int,   # góc trên trái (pixel)
                'x2': int, 'y2': int,   # góc dưới phải (pixel)
                'confidence': float      # độ tin cậy 0.0–1.0
            }
        """
        h, w = frame_rgb.shape[:2]
        results = self.detector.process(frame_rgb)

        boxes = []
        if not results.detections:
            return boxes  # không tìm thấy mặt → trả về list rỗng

        for detection in results.detections:
            bbox = detection.location_data.relative_bounding_box

            # MediaPipe trả về tọa độ tương đối [0.0–1.0] → convert sang pixel
            x1 = int(bbox.xmin * w)
            y1 = int(bbox.ymin * h)
            x2 = int((bbox.xmin + bbox.width)  * w)
            y2 = int((bbox.ymin + bbox.height) * h)

            # Clamp để không vượt ra ngoài frame
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(w, x2)
            y2 = min(h, y2)

            boxes.append({
                'x1': x1,
                'y1': y1,
                'x2': x2,
                'y2': y2,
                'confidence': detection.score[0]
            })

        return boxes

    def get_primary_face(self, frame_rgb):
        """
        Trả về bounding box của khuôn mặt có confidence cao nhất.
        Trả về None nếu không tìm thấy mặt.
        """
        boxes = self.detect(frame_rgb)
        if not boxes:
            return None
        return max(boxes, key=lambda b: b['confidence'])

    def crop_face(self, frame_rgb, box, padding=0.2):
        """
        Crop vùng khuôn mặt từ frame, có thêm padding %.
        padding=0.2 → thêm 20% mỗi phía để không bị cắt sát mặt.

        Trả về ảnh RGB đã crop, hoặc None nếu box không hợp lệ.
        """
        if box is None:
            return None

        h, w = frame_rgb.shape[:2]
        x1, y1, x2, y2 = box['x1'], box['y1'], box['x2'], box['y2']

        face_w = x2 - x1
        face_h = y2 - y1

        # Thêm padding
        pad_x = int(face_w * padding)
        pad_y = int(face_h * padding)

        x1_pad = max(0, x1 - pad_x)
        y1_pad = max(0, y1 - pad_y)
        x2_pad = min(w, x2 + pad_x)
        y2_pad = min(h, y2 + pad_y)

        face_crop = frame_rgb[y1_pad:y2_pad, x1_pad:x2_pad]
        return face_crop

    def draw_boxes(self, frame_bgr, boxes):
        """
        Vẽ bounding box lên frame BGR để preview.
        Trả về frame đã vẽ (không thay đổi frame gốc).
        """
        output = frame_bgr.copy()
        for box in boxes:
            cv2.rectangle(
                output,
                (box['x1'], box['y1']),
                (box['x2'], box['y2']),
                (0, 255, 0), 2
            )
            label = f"{box['confidence']:.2f}"
            cv2.putText(
                output, label,
                (box['x1'], box['y1'] - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                (0, 255, 0), 1
            )
        return output

    def release(self):
        self.detector.close()
        print("[FaceDetector] Đã đóng detector.")
