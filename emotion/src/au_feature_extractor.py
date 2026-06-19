import math
from typing import Dict, Optional, Sequence, Tuple

Point = Tuple[float, float]


class AUFeatureExtractor:
    """
    Extract normalized geometric measurements from MediaPipe Face Mesh landmarks.

    The returned metrics are intentionally low-level. AUMLEngine maps them to
    FACS Action Units (AU) with rule-based thresholds.
    """

    def _point(self, frame_points: Sequence[Sequence[float]], index: int) -> Point:
        point = frame_points[index]
        return float(point[0]), float(point[1])

    def _calc_distance(self, p1: Point, p2: Point) -> float:
        return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

    def _midpoint(self, p1: Point, p2: Point) -> Point:
        return (p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0

    def _avg_y(self, *points: Point) -> float:
        return sum(point[1] for point in points) / max(len(points), 1)

    def _avg_abs_y_delta(self, *point_pairs: Tuple[Point, Point]) -> float:
        return sum(abs(a[1] - b[1]) for a, b in point_pairs) / max(len(point_pairs), 1)

    def _safe_ratio(self, numerator: float, denominator: float) -> float:
        return numerator / denominator if denominator > 1e-6 else 0.0

    def extract_features(self, frame_points: Sequence[Sequence[float]]) -> Optional[Dict[str, float]]:
        """
        frame_points: list of (x, y) coordinates for 468+ MediaPipe landmarks.

        Output metrics are normalized by face width so they are more stable when
        the user moves closer to or farther from the camera.
        """
        if frame_points is None or len(frame_points) < 468:
            return None

        left_eye_outer = self._point(frame_points, 263)
        left_eye_inner = self._point(frame_points, 362)
        left_eye_top = self._point(frame_points, 386)
        left_eye_bottom = self._point(frame_points, 374)

        right_eye_outer = self._point(frame_points, 33)
        right_eye_inner = self._point(frame_points, 133)
        right_eye_top = self._point(frame_points, 159)
        right_eye_bottom = self._point(frame_points, 145)

        left_brow_inner = self._point(frame_points, 336)
        left_brow_outer = self._point(frame_points, 300)
        right_brow_inner = self._point(frame_points, 107)
        right_brow_outer = self._point(frame_points, 70)

        nose_tip = self._point(frame_points, 1)
        nose_bridge = self._point(frame_points, 168)
        nose_left = self._point(frame_points, 98)
        nose_right = self._point(frame_points, 327)

        mouth_left = self._point(frame_points, 61)
        mouth_right = self._point(frame_points, 291)
        upper_lip = self._point(frame_points, 13)
        lower_lip = self._point(frame_points, 14)
        upper_lip_outer = self._point(frame_points, 0)
        lower_lip_outer = self._point(frame_points, 17)
        left_upper_lip = self._point(frame_points, 37)
        right_upper_lip = self._point(frame_points, 267)
        left_lower_lip = self._point(frame_points, 84)
        right_lower_lip = self._point(frame_points, 314)
        chin = self._point(frame_points, 152)

        left_cheek = self._point(frame_points, 205)
        right_cheek = self._point(frame_points, 425)

        face_width = self._calc_distance(left_eye_outer, right_eye_outer)
        if face_width <= 1e-6:
            return None

        left_eye_center = self._midpoint(left_eye_top, left_eye_bottom)
        right_eye_center = self._midpoint(right_eye_top, right_eye_bottom)
        mouth_center = self._midpoint(mouth_left, mouth_right)
        upper_lip_center_y = self._avg_y(upper_lip, upper_lip_outer, left_upper_lip, right_upper_lip)
        lower_lip_center_y = self._avg_y(lower_lip, lower_lip_outer, left_lower_lip, right_lower_lip)
        mouth_lip_center_y = (upper_lip_center_y + lower_lip_center_y) / 2.0
        upper_lip_thickness = self._avg_abs_y_delta(
            (upper_lip_outer, upper_lip),
            (left_upper_lip, upper_lip),
            (right_upper_lip, upper_lip),
        )
        lower_lip_thickness = self._avg_abs_y_delta(
            (lower_lip_outer, lower_lip),
            (left_lower_lip, lower_lip),
            (right_lower_lip, lower_lip),
        )

        left_eye_width = self._calc_distance(left_eye_outer, left_eye_inner)
        right_eye_width = self._calc_distance(right_eye_outer, right_eye_inner)
        left_eye_height = self._calc_distance(left_eye_top, left_eye_bottom)
        right_eye_height = self._calc_distance(right_eye_top, right_eye_bottom)
        eye_open_avg = (
            self._safe_ratio(left_eye_height, left_eye_width)
            + self._safe_ratio(right_eye_height, right_eye_width)
        ) / 2.0

        return {
            "face_width": face_width,
            "inner_brow_distance": self._calc_distance(left_brow_inner, right_brow_inner) / face_width,
            "inner_brow_eye_distance": (
                self._calc_distance(left_brow_inner, left_eye_center)
                + self._calc_distance(right_brow_inner, right_eye_center)
            ) / (2.0 * face_width),
            "outer_brow_eye_distance": (
                self._calc_distance(left_brow_outer, left_eye_outer)
                + self._calc_distance(right_brow_outer, right_eye_outer)
            ) / (2.0 * face_width),
            "eye_open_avg": eye_open_avg,
            "eye_squeeze_avg": 1.0 - eye_open_avg,
            "cheek_eye_distance": (
                self._calc_distance(left_cheek, left_eye_bottom)
                + self._calc_distance(right_cheek, right_eye_bottom)
            ) / (2.0 * face_width),
            "nose_width": self._calc_distance(nose_left, nose_right) / face_width,
            "nose_tip_bridge_distance": self._calc_distance(nose_tip, nose_bridge) / face_width,
            "upper_lip_to_nose": abs(upper_lip_center_y - nose_tip[1]) / face_width,
            "mouth_width": self._calc_distance(mouth_left, mouth_right) / face_width,
            "mouth_open": abs(lower_lip_center_y - upper_lip_center_y) / face_width,
            "mouth_corner_drop": (
                ((mouth_left[1] - mouth_lip_center_y) + (mouth_right[1] - mouth_lip_center_y))
                / (2.0 * face_width)
            ),
            "lip_thickness": (upper_lip_thickness + lower_lip_thickness) / face_width,
            "jaw_drop": abs(chin[1] - lower_lip_center_y) / face_width,
            "mouth_chin_distance": self._calc_distance(mouth_center, chin) / face_width,
        }
