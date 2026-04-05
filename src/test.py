
import numpy as np
import math
from collections import deque

class FaceAnalyzer:
    def __init__(self, fps=30):
        self.fps = fps  # Tần số frame để tính toán thời gian cho các bộ đếm
        
        # ========================
        # TIME BUFFERS (CÁC BỘ ĐẾM)
        # ========================
        self.closed_eyes_frames = 0  # Bộ đếm cho mắt nhắm (dùng để nhận diện ngủ gật)
        self.yawn_frames = 0         # Bộ đếm cho miệng mở (dùng để nhận diện ngáp)
        self.frown_frames = 0        # Bộ đếm cho brow frown (dùng để nhận diện buồn)
        self.puff_frames = 0         # Bộ đếm cho cheek puff (dùng để nhận diện phồng má)
        
        # ========================
        # SMOOTHING
        # ========================
        self.ear_history = deque(maxlen=5)        #
        self.mar_history = deque(maxlen=5)
        self.brow_history = deque(maxlen=5)       # 
        self.cheek_history = deque(maxlen=5)
        
        # ========================
        # CALIBRATION
        # ========================
        self.calibrated = False
        self.calib_frames = []
        self.CALIB_DURATION = 3 * fps  # 3 giây để hiệu chuẩn
        
        self.EAR_CLOSED = 0.0  # Ngưỡng mắt nhắm (sẽ được hiệu chuẩn)
        self.EAR_WIDEN = 0.0   # Ngưỡng mắt mở to (sẽ được hiệu chuẩn)
        self.MAR_OPEN = 0.0    # Ngưỡng miệng mở (sẽ được hiệu chuẩn)
        self.BROW_FROWN = 0.0  # Ngưỡng brow frown (sẽ được hiệu chuẩn)
        self.CHEEK_PUFF = 0.0  # Ngưỡng cheek puff (sẽ được hiệu chuẩn)
        
        self.SMIRK_TILT = 0.06   # Ngưỡng nghiêng đầu để nhận diện nhếch mép
        self.SLEEP_THRESH_FRAMES = 4 * fps         # Ngưỡng thời gian để nhận diện ngủ gật (4 giây)
        self.YAWN_THRESH_FRAMES = int(1.3 * fps)    # Ngưỡng thời gian để nhận diện ngáp (1.3 giây) 
        self.FROWN_TIME_THRESH = int(0.3 * fps)     # Ngưỡng thời gian để nhận diện nhíu mày (0.3s)
        self.PUFF_TIME_THRESH = int(0.4 * fps)    # Ngưỡng thời gian để nhận diện phồng má (0.4s)

    # ========================
    # BASIC FUNCTIONS
    # ========================
    def calc_distance(self, p1, p2):     # ham tinh khoang cach giua 2 diem (x,y) tren khuon mat
        return math.hypot(p1[0] - p2[0], p1[1] - p2[1])   # math.hypot() tinh can bac 2 cua tong binh phuong (x1-x2) va (y1-y2) => tra ve khoang cach giua 2 diem tren mat

    def calculate_ear(self, eye_pts):    # ham tinh EAR (Eye Aspect Ratio) theo cong thuc: EAR = (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)
        A = self.calc_distance(eye_pts[1], eye_pts[5])
        B = self.calc_distance(eye_pts[2], eye_pts[4])    # p2-p6 va p3-p5 la 2 cap diem dung de tinh EAR, khi mat nhin thang thi EAR cao, khi mat nhin ngang thi EAR thap
        C = self.calc_distance(eye_pts[0], eye_pts[3])    
        return (A + B) / (2.0 * C) if C != 0 else 0.0     # C la khoang cach giua 2 diem p1-p4, neu C = 0 thi tra ve 0.0 de tranh chia cho 0

    def calculate_mar(self, mouth_pts):   # ham tinh MAR (Mouth Aspect Ratio) theo cong thuc: MAR = ||p2-p4|| / ||p1-p3||
        A = self.calc_distance(mouth_pts[1], mouth_pts[3])
        C = self.calc_distance(mouth_pts[0], mouth_pts[2])  # p2-p4 la cap diem dung de tinh MAR, khi mieng mo to thi MAR cao, khi mieng khép lại thi MAR thap; p1-p3 la cap diem dung de tinh MAR, khi mieng mo to thi khoang cach p1-p3 tang len, khi mieng khép lại thi khoang cach p1-p3 giam xuong
        return A / C if C != 0 else 0.0    # C la khoang cach giua 2 diem p1-p3, neu C = 0 thi tra ve 0.0 de tranh chia cho 0

    # ========================
    # CALIBRATION
    # ========================
    def update_calibration(self, ear, mar, brow, cheek):    # ham cap nhat du lieu de hieu chuan, nhan vao cac chi so ear, mar, brow, cheek da duoc smooth, luu vao calib_frames trong vong 3 giay dau tien
        self.calib_frames.append((ear, mar, brow, cheek))
        
        if len(self.calib_frames) >= self.CALIB_DURATION:       # sau 3 giay, tinh baseline cho cac chi so bang trung binh cong thuc: baseline = mean(calib_frames)
            baseline_ear = np.mean([x[0] for x in self.calib_frames])      # baseline_ear la gia tri trung binh cua chi so ear trong 3 giay dau tien, tu do co the tinh duoc ngưỡng mắt nhắm (EAR_CLOSED) va ngưỡng mắt mở to (EAR_WIDEN) theo logic: EAR_CLOSED = baseline_ear * 0.7, EAR_WIDEN = baseline_ear * 1.3
            baseline_mar = np.mean([x[1] for x in self.calib_frames])      # baseline_mar la gia tri trung binh cua chi so mar trong 3 giay dau tien, tu do co the tinh duoc ngưỡng miệng mở (MAR_OPEN) theo logic: MAR_OPEN = max(baseline_mar * 2.5, 0.35) 
            baseline_brow = np.mean([x[2] for x in self.calib_frames])     # baseline_brow la gia tri trung binh cua chi so brow trong 3 giay dau tien, tu do co the tinh duoc ngưỡng brow frown (BROW_FROWN) theo logic: BROW_FROWN = baseline_brow * 0.82
            baseline_cheek = np.mean([x[3] for x in self.calib_frames])    # baseline_cheek la gia tri trung binh cua chi so cheek trong 3 giay dau tien, tu do co the tinh duoc ngưỡng phồng má (CHEEK_PUFF) theo logic: CHEEK_PUFF = baseline_cheek * 1.08 
            
            self.EAR_CLOSED = baseline_ear * 0.7     # Ngưỡng mắt nhắm được đặt ở mức 70% của baseline EAR, nghĩa là khi EAR giảm xuống dưới 70% của giá trị trung bình, ta coi như mắt đã nhắm lại (có thể đang ngủ gật)
            self.EAR_WIDEN = baseline_ear * 1.3      # Ngưỡng mắt mở to được đặt ở mức 130% của baseline EAR, nghĩa là khi EAR tăng lên trên 130% của giá trị trung bình, ta coi như mắt đã mở to 
            self.MAR_OPEN = max(baseline_mar * 2.5, 0.35)    # Ngưỡng miệng mở được đặt ở mức 250% của baseline MAR, nhưng tối thiểu là 0.35 để tránh trường hợp baseline quá thấp dẫn đến ngưỡng quá dễ bị kích hoạt
            self.BROW_FROWN = baseline_brow * 0.82           # Ngưỡng nhíu mày được đặt ở mức 82% của baseline brow ratio, nghĩa là khi brow ratio giảm xuống dưới 82% của giá trị trung bình, ta coi như đang nhíu mày 
            
            # TÍCH HỢP: Ngưỡng phồng má tăng lên 8% (1.08) so với baseline để nhận diện phồng má theo logic: khi phồng má → mép miệng chụm lại → khoảng cách tới viền má GIẢM, do đó ngưỡng CHEEK_PUFF được đặt ở mức 108% của baseline cheek ratio, nghĩa là khi cheek ratio tăng lên trên 108% của giá trị trung bình, ta coi như đang phồng má
            self.CHEEK_PUFF = baseline_cheek * 1.08     # Ngưỡng phồng má được đặt ở mức 108% của baseline cheek ratio, nghĩa là khi cheek ratio tăng lên trên 108% của giá trị trung bình, ta coi như đang phồng má (theo logic giảm khoảng cách từ Mép đến Má)
            
            self.calibrated = True        # Sau khi hiệu chuẩn xong, đặt cờ calibrated thành True để bắt đầu nhận diện trạng thái
            print("[HỆ THỐNG] Hiệu chuẩn xong! Đã sẵn sàng nhận diện.")

    # ========================
    # MAIN FUNCTION
    # ========================
    def analyze_frame(self, frame_points):   # ham phan tich 1 frame, nhan vao frame_points la danh sach cac diem facial landmarks cua frame do, tra ve dictionary chua cac chi so da duoc tinh toan va cac trang thai duoc nhan dien
        output_states = []
        
        # 1. TRÍCH XUẤT ĐIỂM
        left_eye = [frame_points[362], frame_points[385], frame_points[387],    # Các điểm mắt trái theo thứ tự: p1, p2, p3, p4, p5, p6 (theo chuẩn Mediapipe)
                    frame_points[263], frame_points[373], frame_points[380]]    
        right_eye = [frame_points[33], frame_points[160], frame_points[158],    # Các điểm mắt phải theo thứ tự: p1, p2, p3, p4, p5, p6 (theo chuẩn Mediapipe)
                     frame_points[133], frame_points[153], frame_points[144]]
        mouth = [frame_points[61], frame_points[13], frame_points[291], frame_points[14]]   # Các điểm miệng theo thứ tự: p1, p2, p3, p4 (theo chuẩn Mediapipe)
        
        outer_left_eye = frame_points[263]     # Điểm ngoài cùng của mắt trái 
        outer_right_eye = frame_points[33]     # Điểm ngoài cùng của mắt phải 
        cheek_left = frame_points[205]         # Điểm má trái (Dùng để đo khoảng cách từ mép đến má)
        cheek_right = frame_points[425]        # Điểm má phải (Dùng để đo khoảng cách từ mép đến má)
        
        brow_left_inner = frame_points[336]     # Điểm lông mày trái (Dùng để đo khoảng cách từ lông mày đến mắt)
        brow_right_inner = frame_points[107]    # Điểm lông mày phải (Dùng để đo khoảng cách từ lông mày đến mắt)
        eye_left_top = frame_points[386]        # Điểm trên cùng của mắt trái (Dùng để đo khoảng cách từ lông mày đến mắt)
        eye_right_top = frame_points[159]       # Điểm trên cùng của mắt phải (Dùng để đo khoảng cách từ lông mày đến mắt)
        
        nose_tip = frame_points[4] # Điểm chóp mũi (Dùng để đo góc quay đầu)   

        # 2. KIỂM TRA GÓC QUAY ĐẦU (HEAD POSE YAW) THEO LOGIC: khi quay đầu sang phải → khoảng cách từ chóp mũi đến mắt trái tăng lên, khoảng cách từ chóp mũi đến mắt phải giảm xuống → head_turn_ratio = dist_nose_to_left / dist_nose_to_right tăng lên → khi head_turn_ratio > 1.8 thì nhận diện là quay đầu sang phải; ngược lại khi quay đầu sang trái → khoảng cách từ chóp mũi đến mắt trái giảm xuống, khoảng cách từ chóp mũi đến mắt phải tăng lên → head_turn_ratio giảm xuống → khi head_turn_ratio < 0.55 thì nhận diện là quay đầu sang trái
        dist_nose_to_left = abs(nose_tip[0] - outer_left_eye[0])   # Khoảng cách ngang từ chóp mũi đến mắt trái (chỉ xét trục x để đo góc quay đầu sang trái hoặc phải)
        dist_nose_to_right = abs(nose_tip[0] - outer_right_eye[0])   # Khoảng cách ngang từ chóp mũi đến mắt phải (chỉ xét trục x để đo góc quay đầu sang trái hoặc phải)
        
        if dist_nose_to_right == 0: dist_nose_to_right = 0.001    # Tránh chia cho 0 khi chóp mũi trùng với mắt phải 
        if dist_nose_to_left == 0: dist_nose_to_left = 0.001      # Tránh chia cho 0 khi chóp mũi trùng với mắt trái
        
        head_turn_ratio = dist_nose_to_left / dist_nose_to_right    # Tỷ lệ khoảng cách từ chóp mũi đến mắt trái và mắt phải, dùng để nhận diện góc quay đầu sang trái hoặc phải
        is_head_turned = False       
        
        if head_turn_ratio > 1.8:     # Khi head_turn_ratio > 1.8 thì nhận diện là quay đầu sang phải
            is_head_turned = True
            output_states.append("Quay mat sang PHAI")
        elif head_turn_ratio < 0.55:    # Khi head_turn_ratio < 0.55 thì nhận diện là quay đầu sang trái
            is_head_turned = True
            output_states.append("Quay mat sang TRAI")

        # 3. TÍNH TOÁN CÁC CHỈ SỐ KHUÔN MẶT
        ear_l = self.calculate_ear(left_eye)      # goi ham tinh EAR cho mat trai
        ear_r = self.calculate_ear(right_eye)     # goi ham tinh EAR cho mat phai
        ear = (ear_l + ear_r) / 2                 # EAR trung bình của cả hai mắt, dùng để nhận diện trạng thái mắt chung (nhắm hay mở to)
        mar = self.calculate_mar(mouth)           # goi ham tinh MAR cho mieng, dung de nhan dien trang thai mieng (mo to hay khép lai)

        face_width = self.calc_distance(outer_left_eye, outer_right_eye)     # Khoảng cách ngang giữa hai mắt, dùng để chuẩn hóa các tỷ lệ khác theo kích thước khuôn mặt, tránh bị ảnh hưởng bởi khoảng cách từ camera hoặc kích thước khuôn mặt
        face_width = face_width if face_width != 0 else 1.0                 

        cheek_ratio = self.calc_distance(cheek_left, cheek_right) / face_width        # Tỷ lệ khoảng cách từ má trái đến má phải, dùng để nhận diện phồng má theo logic: khi phồng má → mép miệng chụm lại → khoảng cách tới viền má GIẢM, do đó khi cheek_ratio tăng lên trên ngưỡng CHEEK_PUFF => đang phồng má
        tilt_ratio = (frame_points[61][1] - frame_points[291][1]) / face_width        # Tỷ lệ nghiêng của miệng theo trục y, dùng để nhận diện nhếch mép theo logic: khi nhếch mép phải → điểm 61 (mép trái) thấp hơn điểm 291 (mép phải) → tilt_ratio dương và lớn hơn ngưỡng SMIRK_TILT; khi nhếch mép trái → điểm 61 (mép trái) cao hơn điểm 291 (mép phải) → tilt_ratio âm và nhỏ hơn -SMIRK_TILT

        d_left = self.calc_distance(brow_left_inner, eye_left_top)      # Khoảng cách từ lông mày trái đến mắt trái, dùng để nhận diện nhíu mày theo logic: khi nhíu mày → lông mày hạ xuống → khoảng cách từ lông mày đến mắt giảm xuống → khi brow_ratio giảm xuống dưới ngưỡng BROW_FROWN => đang nhíu mày
        d_right = self.calc_distance(brow_right_inner, eye_right_top)    # Khoảng cách từ lông mày phải đến mắt phải, dùng để nhận diện nhíu mày theo logic: khi nhíu mày → lông mày hạ xuống → khoảng cách từ lông mày đến mắt giảm xuống → khi brow_ratio giảm xuống dưới ngưỡng BROW_FROWN => đang nhíu mày
        brow_ratio = (d_left + d_right) / (2.0 * face_width)             # Tỷ lệ khoảng cách từ lông mày đến mắt, được chuẩn hóa theo kích thước khuôn mặt, dùng để nhận diện nhíu mày theo logic: khi nhíu mày → lông mày hạ xuống → khoảng cách từ lông mày đến mắt giảm xuống → khi brow_ratio giảm xuống dưới ngưỡng BROW_FROWN => đang nhíu mày

        # 4. SMOOTHING // luu gia tri vao history va tinh trung binh de lam tron cac chi so, giam nhieu do nhiem va bien dong dot ngot cua cac chi so, giup nhan dien trang thai on dinh hon
        self.ear_history.append(ear)     
        self.mar_history.append(mar)
        self.brow_history.append(brow_ratio)
        self.cheek_history.append(cheek_ratio)
        
        # Tinh gia tri trung binh cua cac chi so trong history de lam tron va giam nhieu do nhiem, giup nhan dien trang thai on dinh hon
        ear_smooth = np.mean(self.ear_history)  
        mar_smooth = np.mean(self.mar_history)
        brow_smooth = np.mean(self.brow_history)
        cheek_smooth = np.mean(self.cheek_history)

        # 5. HIỆU CHUẨN 3 GIÂY ĐẦU
        if not self.calibrated:
            self.update_calibration(ear_smooth, mar_smooth, brow_smooth, cheek_smooth)
            return {
                "EAR_L": round(ear_l, 3), "EAR_R": round(ear_r, 3), "MAR": round(mar_smooth, 3),
                "BROW_R": round(brow_smooth, 3), "CHEEK_R": round(cheek_smooth, 3),
                "States": ["HAY NHIN THANG - TRONG (3 giay)..."]
            }

        # 6. LOGIC NHẬN DIỆN
        
        # ---- MẮT ----
        is_eyes_closed = False
        if ear_smooth < self.EAR_CLOSED:
            self.closed_eyes_frames += 1
            is_eyes_closed = True
            if self.closed_eyes_frames >= self.SLEEP_THRESH_FRAMES:
                output_states.append("NGU GAT")
        else:
            self.closed_eyes_frames = 0
            if ear_smooth > self.EAR_WIDEN:
                output_states.append("Mat mo to")

        if abs(ear_l - ear_r) > 0.08:
            output_states.append("Nhay 1 mat")

        # ---- CHỈ NHẬN DIỆN KHI NHÌN THẲNG ----
        if not is_head_turned:
            # Lông mày
            is_frowning = False
            if brow_smooth < self.BROW_FROWN:
                self.frown_frames += 1
                if self.frown_frames > self.FROWN_TIME_THRESH: 
                    is_frowning = True
                    output_states.append("Nhiu may")
            else:
                self.frown_frames = 0

            # ==========================================
            # TÍCH HỢP LOGIC CHEEK PUFF (CÓ TIME BUFFER)
            # ==========================================
            if cheek_smooth > self.CHEEK_PUFF:
                self.puff_frames += 1
                if self.puff_frames > self.PUFF_TIME_THRESH: # Phải giữ > 0.4s
                    output_states.append("Phong ma")
            else:
                self.puff_frames = 0
            # ==========================================

            # Nhếch mép
            if tilt_ratio > self.SMIRK_TILT:
                output_states.append("Nhech mep phai")
            elif tilt_ratio < -self.SMIRK_TILT:
                output_states.append("Nhech mep trai")
                
            # Tập trung
            if is_frowning and mar_smooth < 0.05 and self.frown_frames > self.fps:
                output_states.append("TRANG THAI: TAP TRUNG")
        else:
            # Chống kẹt bộ đếm khi quay đầu
            self.frown_frames = 0
            self.puff_frames = 0

        # ---- MIỆNG (Ngáp) ----
        is_mouth_open = False
        if mar_smooth > self.MAR_OPEN:
            is_mouth_open = True
            output_states.append("Ha mieng to")

        if is_mouth_open and is_eyes_closed:
            self.yawn_frames += 1
            if self.yawn_frames >= self.YAWN_THRESH_FRAMES:
                output_states.append("TRANG THAI: DANG NGAP")
        else:
            self.yawn_frames = 0

        return {
            "EAR_L": round(ear_l, 3), "EAR_R": round(ear_r, 3), "MAR": round(mar_smooth, 3),
            "BROW_R": round(brow_smooth, 3), "CHEEK_R": round(cheek_smooth, 3),
            "States": output_states
        }


