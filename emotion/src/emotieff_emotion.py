import cv2
import numpy as np


class EmotiEffEmotionDetector:
    def __init__(
        self,
        analyze_every_n_frames=5,
        engine="onnx",
        model_name="enet_b0_8_best_vgaf",
    ):
        """
        Detector thay thế DeepFace bằng EmotiEffLib.

        File runtime.py hiện đang cần method:
        - detect_with_scores(face_roi_rgb, frame_index)

        Method đó phải trả về:
        - emotion_label: str
        - raw_scores: dict, ví dụ {"happy": 80.0, "neutral": 20.0, ...}
        """

        self.analyze_every_n_frames = analyze_every_n_frames
        self.engine = engine
        self.model_name = model_name

        self.labels = [
            "angry",
            "disgust",
            "fear",
            "happy",
            "neutral",
            "sad",
            "surprise",
        ]

        self.last_label = "neutral"
        self.last_scores = {label: 0.0 for label in self.labels}
        self.last_scores["neutral"] = 100.0

        self.recognizer = None

        try:
            from emotiefflib.facial_analysis import EmotiEffLibRecognizer

            self.recognizer = EmotiEffLibRecognizer(
                engine=self.engine,
                model_name=self.model_name,
                device="cpu",
            )

            print(
                f"[EmotiEffLib] Loaded model: {self.model_name} | engine={self.engine}"
            )

        except Exception as e:
            print(f"[EmotiEffLib][ERROR] Could not load model: {e!r}")
            self.recognizer = None

    def _prepare_face(self, face_roi_rgb):
        if face_roi_rgb is None:
            return None

        if face_roi_rgb.size == 0:
            return None

        face = face_roi_rgb.copy()

        if face.dtype != np.uint8:
            face = np.clip(face, 0, 255).astype(np.uint8)

        h, w = face.shape[:2]

        if h < 64 or w < 64:
            face = cv2.resize(face, (224, 224))

        return face

    def _normalize_label(self, label):
        """
        Chuẩn hóa nhãn từ EmotiEffLib về đúng nhãn frontend đang dùng.
        """
        if label is None:
            return "neutral"

        label = str(label).strip().lower()

        mapping = {
            "anger": "angry",
            "angry": "angry",
            "disgust": "disgust",
            "fear": "fear",
            "happiness": "happy",
            "happy": "happy",
            "joy": "happy",
            "neutral": "neutral",
            "sadness": "sad",
            "sad": "sad",
            "surprise": "surprise",
            "surprised": "surprise",
        }

        return mapping.get(label, "neutral")

    def _scores_to_dict(self, scores, predicted_label):
        """
        Chuyển output score của EmotiEffLib thành dict giống DeepFace cũ.
        Frontend/backend hiện cần dạng:
        {
            "angry": 0.0,
            "disgust": 0.0,
            ...
            "happy": 85.0
        }
        """

        raw_scores = {label: 0.0 for label in self.labels}

        if scores is None or len(scores) == 0:
            raw_scores[predicted_label] = 100.0
            return raw_scores

        arr = np.array(scores[0], dtype=np.float32)

        if arr.ndim == 0:
            raw_scores[predicted_label] = 100.0
            return raw_scores

        # Nếu là logits thì softmax, nếu là probability cũng vẫn dùng được.
        exp = np.exp(arr - np.max(arr))
        probs = exp / np.sum(exp)

        # Giả định thứ tự 7 lớp phổ biến của AffectNet.
        # Nếu model trả khác thứ tự thì nhãn dominant vẫn lấy từ EmotiEffLib,
        # còn các thanh phần trăm dùng để hiển thị tương đối.
        for i, label in enumerate(self.labels):
            if i < len(probs):
                raw_scores[label] = float(probs[i] * 100.0)

        # Đảm bảo nhãn dominant từ EmotiEffLib có điểm cao nhất.
        max_score = max(raw_scores.values()) if raw_scores else 0.0
        raw_scores[predicted_label] = max(raw_scores.get(predicted_label, 0.0), max_score)

        return raw_scores

    def detect_with_scores(self, face_roi_rgb, frame_index):
        """
        Hàm này thay thế hàm detect_with_scores của DeepFace detector cũ.
        runtime.py sẽ gọi hàm này.
        """

        if self.recognizer is None:
            return self.last_label, self.last_scores

        if frame_index % self.analyze_every_n_frames != 0:
            return self.last_label, self.last_scores

        face = self._prepare_face(face_roi_rgb)

        if face is None:
            return "neutral", self.last_scores

        try:
            emotions, scores = self.recognizer.predict_emotions(
                [face],
                logits=True,
            )

            predicted_label = self._normalize_label(emotions[0])
            raw_scores = self._scores_to_dict(scores, predicted_label)

            self.last_label = predicted_label
            self.last_scores = raw_scores

            return predicted_label, raw_scores

        except Exception as e:
            print(f"[EmotiEffLib][ERROR] Detect failed: {e!r}")
            return self.last_label, self.last_scores

    def detect(self, face_roi_rgb, frame_index):
        """
        Hàm phụ, nếu chỗ khác cần label + confidence.
        """
        label, scores = self.detect_with_scores(face_roi_rgb, frame_index)
        confidence = float(scores.get(label, 0.0))
        return label, confidence
