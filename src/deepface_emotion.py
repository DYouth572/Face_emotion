from deepface import DeepFace
import numpy as np


class EmotionDetector:
    """
    nhận diện cảm xúc bằng DeepFace.
    Chỉ nhận face ROI đã được crop sẵn và trả về:
        - emotion label
        - confidence (%) cảm xúc đó 
    """

    def __init__(self, analyze_every_n_frames=30):
        """
        analyze_every_n_frames:
            Chỉ chạy DeepFace mỗi N frame để giảm lag.
        """
        self.analyze_every_n_frames = analyze_every_n_frames
        self.last_emotion = "Detecting..."
        self.last_confidence = 0.0

        print("[EmotionDetector] Đã khởi tạo DeepFace Emotion Detector.")

    def detect(self, face_roi, frame_count):
        """
        Nhận face ROI (ảnh khuôn mặt đã crop) và frame_count.
        Chỉ chạy DeepFace mỗi N frame để tối ưu tốc độ.

        Trả về:
            emotion_label (str)
            confidence (float)
        """

        # Nếu face_roi rỗng / lỗi thì trả kết quả cũ
        if face_roi is None or face_roi.size == 0:
            return self.last_emotion, self.last_confidence

        # Chỉ chạy DeepFace mỗi N frame
        if frame_count % self.analyze_every_n_frames != 0:
            return self.last_emotion, self.last_confidence

        try:
            result = DeepFace.analyze(
                face_roi,
                actions=['emotion'],
                enforce_detection=False
            )

            if isinstance(result, list):
                result = result[0]

            emotion_scores = result['emotion']
            emotion_label = result['dominant_emotion']
            confidence = float(emotion_scores[emotion_label])

            self.last_emotion = emotion_label
            self.last_confidence = confidence

        except Exception as e:
            print(f"[EmotionDetector] Lỗi DeepFace: {e}")

        return self.last_emotion, self.last_confidence