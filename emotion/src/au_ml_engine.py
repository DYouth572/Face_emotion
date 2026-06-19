from typing import Dict, Mapping, Optional

import numpy as np


AU_KEYS = (
    "AU1",   # Inner Brow Raiser
    "AU2",   # Outer Brow Raiser
    "AU4",   # Brow Lowerer
    "AU5",   # Upper Lid Raiser
    "AU6",   # Cheek Raiser
    "AU7",   # Lid Tightener
    "AU9",   # Nose Wrinkler
    "AU10",  # Upper Lip Raiser
    "AU12",  # Lip Corner Puller
    "AU15",  # Lip Corner Depressor
    "AU20",  # Lip Stretcher
    "AU23",  # Lip Tightener
    "AU25",  # Lips Part
    "AU26",  # Jaw Drop
)


class AUMLEngine:
    def __init__(self, model_dir="models"):
        self.model_dir = model_dir
        self.is_loaded = False

    def load_pretrained_models(self):
        """
        Prototype AU inference.

        This maps normalized Face Mesh geometry to meaningful FACS Action Units.
        Only the AU set used by the 7 DeepFace emotion states is emitted.
        """
        self.is_loaded = True
        print("[AU/FACS] Initialized rule-based AU inference.")
        return True

    def _clip01(self, value: float) -> float:
        return float(np.clip(value, 0.0, 1.0))

    def _score(self, value: float, low: float, high: float, invert: bool = False) -> float:
        if abs(high - low) < 1e-9:
            return 0.0
        normalized = (value - low) / (high - low)
        if invert:
            normalized = 1.0 - normalized
        return self._clip01(normalized)

    def _empty_scores(self) -> Dict[str, float]:
        return {key: 0.0 for key in AU_KEYS}

    def _legacy_vector_to_features(self, feature_vector) -> Optional[Dict[str, float]]:
        if feature_vector is None or len(feature_vector) < 6:
            return None

        brow_dist = float(feature_vector[0])
        brow_eye_left = float(feature_vector[1])
        brow_eye_right = float(feature_vector[2])
        mouth_width = float(feature_vector[3])
        mouth_open = float(feature_vector[4])
        cheek_dist = float(feature_vector[5])

        return {
            "inner_brow_distance": brow_dist,
            "inner_brow_eye_distance": (brow_eye_left + brow_eye_right) / 2.0,
            "outer_brow_eye_distance": (brow_eye_left + brow_eye_right) / 2.0,
            "eye_open_avg": 0.28,
            "eye_squeeze_avg": 0.72,
            "cheek_eye_distance": cheek_dist,
            "nose_width": 0.20,
            "nose_tip_bridge_distance": 0.24,
            "upper_lip_to_nose": 0.10,
            "mouth_width": mouth_width,
            "mouth_open": mouth_open,
            "mouth_corner_drop": 0.0,
            "lip_thickness": mouth_open,
            "jaw_drop": mouth_open * 1.8,
        }

    def _coerce_features(self, feature_vector) -> Optional[Mapping[str, float]]:
        if feature_vector is None:
            return None
        if isinstance(feature_vector, Mapping):
            return feature_vector
        return self._legacy_vector_to_features(feature_vector)

    def predict_au_scores(self, feature_vector) -> Dict[str, float]:
        """
        Output AU scores in the 0.0-1.0 range for:
        AU1, AU2, AU4, AU5, AU6, AU7, AU9, AU10, AU12, AU15,
        AU20, AU23, AU25, AU26.
        """
        features = self._coerce_features(feature_vector)
        if features is None:
            return self._empty_scores()

        inner_brow_eye = float(features.get("inner_brow_eye_distance", 0.0))
        outer_brow_eye = float(features.get("outer_brow_eye_distance", 0.0))
        inner_brow_distance = float(features.get("inner_brow_distance", 0.0))
        eye_open = float(features.get("eye_open_avg", 0.0))
        cheek_eye_distance = float(features.get("cheek_eye_distance", 0.0))
        nose_width = float(features.get("nose_width", 0.0))
        nose_bridge = float(features.get("nose_tip_bridge_distance", 0.0))
        upper_lip_to_nose = float(features.get("upper_lip_to_nose", 0.0))
        mouth_width = float(features.get("mouth_width", 0.0))
        mouth_open = float(features.get("mouth_open", 0.0))
        mouth_corner_drop = float(features.get("mouth_corner_drop", 0.0))
        lip_thickness = float(features.get("lip_thickness", 0.0))
        jaw_drop = float(features.get("jaw_drop", 0.0))

        au25 = self._score(mouth_open, 0.03, 0.14)
        au26 = self._score(jaw_drop, 0.22, 0.40) * self._score(mouth_open, 0.07, 0.18)

        au12_by_width = self._score(mouth_width, 0.55, 0.80)
        au12_open_penalty = self._clip01(1.0 - au26 * 0.65)
        au12 = self._clip01(au12_by_width * au12_open_penalty)

        au20 = self._score(mouth_width, 0.58, 0.86) * self._clip01(1.0 - au12 * 0.45)
        au15 = self._score(max(0.0, mouth_corner_drop), 0.008, 0.065) * self._clip01(1.0 - au12 * 0.35)
        lips_closed = self._score(mouth_open, 0.025, 0.095, invert=True)
        lips_thin = self._score(lip_thickness, 0.035, 0.105, invert=True)
        not_smiling = self._clip01(1.0 - au12 * 0.45)
        au23 = self._clip01((lips_closed * 0.55) + (lips_thin * 0.45)) * not_smiling

        au1 = self._score(inner_brow_eye, 0.12, 0.24)
        au2 = self._score(outer_brow_eye, 0.12, 0.25)
        au4_by_brow_eye = self._score(inner_brow_eye, 0.07, 0.16, invert=True)
        au4_by_brow_dist = self._score(inner_brow_distance, 0.25, 0.42, invert=True)
        au4 = self._clip01((au4_by_brow_eye * 0.7) + (au4_by_brow_dist * 0.3))

        au5 = self._score(eye_open, 0.26, 0.46)
        au7 = self._score(eye_open, 0.12, 0.26, invert=True)
        cheek_raise = self._score(cheek_eye_distance, 0.52, 0.95, invert=True)
        eye_narrow = self._score(eye_open, 0.18, 0.32, invert=True)
        smile_support = self._score(mouth_width, 0.55, 0.80)
        au6 = self._clip01(
            (cheek_raise * 0.65) + (eye_narrow * 0.20) + (smile_support * 0.15)
        ) * self._clip01(1.0 - au5 * 0.25)

        au9 = (
            self._score(nose_width, 0.19, 0.30) * 0.55
            + self._score(nose_bridge, 0.18, 0.30, invert=True) * 0.45
        )
        upper_lip_raise = self._score(upper_lip_to_nose, 0.16, 0.34, invert=True)
        au10 = upper_lip_raise * self._clip01(1.0 - au25 * 0.20)

        return {
            "AU1": self._clip01(au1),
            "AU2": self._clip01(au2),
            "AU4": self._clip01(au4),
            "AU5": self._clip01(au5),
            "AU6": self._clip01(au6),
            "AU7": self._clip01(au7),
            "AU9": self._clip01(au9),
            "AU10": self._clip01(au10),
            "AU12": self._clip01(au12),
            "AU15": self._clip01(au15),
            "AU20": self._clip01(au20),
            "AU23": self._clip01(au23),
            "AU25": self._clip01(au25),
            "AU26": self._clip01(au26),
        }
