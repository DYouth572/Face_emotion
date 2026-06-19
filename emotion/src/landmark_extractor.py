import cv2
import mediapipe as mp
import numpy as np


class LandmarkExtractor:
    """
    Luồng 1 — MediaPipe FaceMesh.
    Nhận frame RGB đã qua preprocessor, trả về 468 tọa độ landmarks.

    Tọa độ đầu ra:
        - Dạng tỉ lệ (normalized): x, y ∈ [0.0, 1.0], z ≈ độ sâu tương đối
        - Dạng pixel: x ∈ [0, width], y ∈ [0, height]
        Luôn dùng dạng PIXEL khi tính EAR/MAR/brow distance.
    """

    # ── Index các nhóm điểm quan trọng ──────────────
    # Nguồn: https://github.com/google/mediapipe/blob/master/mediapipe/modules/face_geometry/data/canonical_face_model_uv_visualization.png

    LEFT_EYE    = [362, 385, 387, 263, 373, 380]  # p1..p6 cho EAR
    RIGHT_EYE   = [33,  160, 158, 133, 153, 144]
    LEFT_BROW   = [336, 296, 334, 293, 300]
    RIGHT_BROW  = [70,  63,  105, 66,  107]
    MOUTH_OUTER = [61,  291, 39,  181, 0,   17 ]  # cho MAR
    NOSE_TIP    = [4]
    CHIN        = [152]
    FOREHEAD    = [10]

    def __init__(self,
                 max_num_faces=1,
                 min_detection_confidence=0.5,
                 min_tracking_confidence=0.5,
                 refine_landmarks=True):
        """
        refine_landmarks=True → bật iris refinement
            → tổng điểm tăng lên 478 (thêm 10 điểm iris)
            → để đơn giản, mình chỉ dùng 468 điểm khuôn mặt
        """
        self.mp_face_mesh = mp.solutions.face_mesh
        self.mp_draw      = mp.solutions.drawing_utils
        self.mp_styles    = mp.solutions.drawing_styles

        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=max_num_faces,
            refine_landmarks=refine_landmarks,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )

        print("[LandmarkExtractor] Đã khởi tạo MediaPipe FaceMesh.")
        print(f"[LandmarkExtractor] refine_landmarks={refine_landmarks} "
              f"(478 điểm nếu True, 468 nếu False)")

    def extract(self, frame_rgb):
        """
        Nhận frame RGB uint8, chạy FaceMesh, trả về landmarks.

        Trả về:
            raw_landmarks : list 468 object landmark (thuộc tính .x .y .z)
            Hoặc None nếu không detect được mặt.
        """
        results = self.face_mesh.process(frame_rgb)

        if not results.multi_face_landmarks:
            return None

        # Lấy khuôn mặt đầu tiên (max_num_faces=1)
        raw_landmarks = results.multi_face_landmarks[0].landmark
        return raw_landmarks

    def to_pixel_coords(self, raw_landmarks, frame_width, frame_height):
        """
        Convert 468 landmarks từ tọa độ tỉ lệ [0.0–1.0] sang pixel.

        Trả về: numpy array shape (468, 3) — mỗi hàng là [x_px, y_px, z]
        Trong đó z vẫn giữ dạng tương đối (không có đơn vị pixel cụ thể).
        """
        coords = []
        for lm in raw_landmarks:
            x_px = lm.x * frame_width
            y_px = lm.y * frame_height
            z    = lm.z  # giữ nguyên z tương đối
            coords.append([x_px, y_px, z])

        return np.array(coords, dtype=np.float32)

    def print_landmarks(self, raw_landmarks, frame_width, frame_height,
                        mode="summary", specific_indices=None):
        """
        In tọa độ landmarks ra console để debug/xác nhận.

        Tham số mode:
            "summary"   → in thống kê tổng quan + một số điểm đại diện
            "all"       → in đủ 468 điểm (dài, dùng để kiểm tra)
            "groups"    → in theo nhóm: mắt, mày, miệng
            "specific"  → in các index chỉ định trong specific_indices

        Ví dụ:
            extractor.print_landmarks(lms, w, h, mode="groups")
            extractor.print_landmarks(lms, w, h, mode="specific",
                                       specific_indices=[0, 33, 263, 4, 152])
        """
        coords = self.to_pixel_coords(raw_landmarks, frame_width, frame_height)

        print("\n" + "=" * 60)
        print(f"LANDMARK REPORT  |  Tổng điểm: {len(coords)}")
        print("=" * 60)

        if mode == "summary":
            self._print_summary(coords)

        elif mode == "all":
            self._print_all(coords)

        elif mode == "groups":
            self._print_groups(coords)

        elif mode == "specific" and specific_indices:
            self._print_specific(coords, specific_indices)

        else:
            print("[LandmarkExtractor] mode không hợp lệ. Dùng: summary/all/groups/specific")

        print("=" * 60 + "\n")

    def _print_summary(self, coords):
        """In tổng quan: range tọa độ + một số điểm mốc."""
        x_vals = coords[:, 0]
        y_vals = coords[:, 1]

        print(f"  X range: {x_vals.min():.1f} → {x_vals.max():.1f} px")
        print(f"  Y range: {y_vals.min():.1f} → {y_vals.max():.1f} px")
        print()

        # In một số điểm mốc quan trọng
        key_points = {
            "Mũi (tip)":          4,
            "Cằm":                152,
            "Trán":               10,
            "Góc mắt trái ngoài": 362,
            "Góc mắt phải ngoài": 33,
            "Khóe miệng trái":    61,
            "Khóe miệng phải":    291,
        }
        print("  Một số điểm mốc:")
        print(f"  {'Tên':<28} {'Index':>6}  {'X':>8}  {'Y':>8}  {'Z':>8}")
        print("  " + "-" * 58)
        for name, idx in key_points.items():
            x, y, z = coords[idx]
            print(f"  {name:<28} {idx:>6}  {x:>8.2f}  {y:>8.2f}  {z:>8.4f}")

    def _print_all(self, coords):
        """In đủ 468 điểm."""
        print(f"  {'Index':>6}  {'X':>8}  {'Y':>8}  {'Z':>8}")
        print("  " + "-" * 38)
        for i, (x, y, z) in enumerate(coords):
            print(f"  {i:>6}  {x:>8.2f}  {y:>8.2f}  {z:>8.4f}")

    def _print_groups(self, coords):
        """In theo nhóm chức năng."""
        groups = {
            "Mắt trái  (EAR p1-p6)": self.LEFT_EYE,
            "Mắt phải  (EAR p1-p6)": self.RIGHT_EYE,
            "Lông mày trái":          self.LEFT_BROW,
            "Lông mày phải":          self.RIGHT_BROW,
            "Miệng     (MAR)":        self.MOUTH_OUTER,
            "Mũi tip":                self.NOSE_TIP,
            "Cằm":                    self.CHIN,
            "Trán":                   self.FOREHEAD,
        }
        for group_name, indices in groups.items():
            print(f"\n  [{group_name}]")
            print(f"  {'Index':>6}  {'X':>8}  {'Y':>8}  {'Z':>8}")
            print("  " + "-" * 38)
            for idx in indices:
                x, y, z = coords[idx]
                print(f"  {idx:>6}  {x:>8.2f}  {y:>8.2f}  {z:>8.4f}")

    def _print_specific(self, coords, indices):
        """In các điểm theo index chỉ định."""
        print(f"  {'Index':>6}  {'X':>8}  {'Y':>8}  {'Z':>8}")
        print("  " + "-" * 38)
        for idx in indices:
            if 0 <= idx < len(coords):
                x, y, z = coords[idx]
                print(f"  {idx:>6}  {x:>8.2f}  {y:>8.2f}  {z:>8.4f}")
            else:
                print(f"  {idx:>6}  [index ngoài phạm vi 0-{len(coords)-1}]")

    def draw_landmarks(self, frame_bgr, raw_landmarks):
        """
        Vẽ 468 điểm landmarks lên frame BGR để visualize.
        Trả về frame đã vẽ.
        """
        output = frame_bgr.copy()
        # Convert sang RGB để draw (mp_draw cần RGB)
        frame_rgb = cv2.cvtColor(output, cv2.COLOR_BGR2RGB)

        self.mp_draw.draw_landmarks(
            image=frame_rgb,
            landmark_list=self.mp_face_mesh.FaceMesh.FACE_CONNECTIONS
                          if hasattr(self.mp_face_mesh.FaceMesh, 'FACE_CONNECTIONS')
                          else None,
            connections=self.mp_face_mesh.FACEMESH_TESSELATION,
            landmark_drawing_spec=None,
            connection_drawing_spec=self.mp_styles
                .get_default_face_mesh_tesselation_style()
        )

        return cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)

    def release(self):
        self.face_mesh.close()
        print("[LandmarkExtractor] Đã đóng FaceMesh.")
