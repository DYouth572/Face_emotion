/** Mức độ nhíu mày (Brow Furrow) — tính từ khoảng cách landmark */
export type BrowFurrowLevel =
  | "none"       // Không nhíu
  | "slight"     // Nhẹ
  | "moderate"   // Vừa
  | "strong";    // Mạnh / rõ rệt

/** Trạng thái miệng */
export type MouthState =
  | "closed"       // Đóng
  | "slightly_open"  // Hé mở
  | "open"         // Mở
  | "wide_open";   // Há rộng (ngáp / ngạc nhiên)
 
/** Mức độ nhếch mép (Lip Corner Pull) */
export type LipCornerState =
  | "none"       // Trung tính
  | "slight"     // Nhếch nhẹ (mỉm cười nhỏ)
  | "smile"      // Cười rõ
  | "frown";     // Mép kéo xuống (buồn / lo)
 
/** Tần suất nháy mắt so với baseline */
export type BlinkRateCategory =
  | "very_slow"  // < 8 lần/phút  → mệt mỏi / căng thẳng cao
  | "slow"       // 8–12 lần/phút → hơi thấp
  | "normal"     // 13–20 lần/phút → bình thường
  | "fast"       // 21–30 lần/phút → kích động nhẹ
  | "very_fast"; // > 30 lần/phút  → lo lắng / mệt

/** Trạng thái một bên mắt tại thời điểm frame */
export type EyeState = "open" | "half_open" | "closed";

export interface Landmark {
  x: number;   // 0.0 – 1.0 (normalized theo width)
  y: number;   // 0.0 – 1.0 (normalized theo height)
  z: number;   // độ sâu tương đối
}

export interface FaceBoundingBox {
  x:      number;  // px, góc trên trái
  y:      number;  // px, góc trên trái
  width:  number;  // px
  height: number;  // px
  confidence: number;
}

/**
 * Eye Aspect Ratio — chỉ số đo độ mở của mắt.
 * EAR = (vertical distances) / (2 * horizontal distance)
 * EAR < 0.2 thường được coi là đang nhắm/nháy mắt.
 */
export interface EyeAspectRatio {
  left:    number;   // EAR mắt trái
  right:   number;   // EAR mắt phải
  average: number;   // Trung bình hai mắt
}

/* Thông tin nháy mắt cho một frame.*/

export interface BlinkData {
  /** true nếu phát hiện nháy mắt trong frame hiện tại */
  isBlinking:     boolean;
 
  /** EAR tại frame này */
  ear:            EyeAspectRatio;
 
  /** Trạng thái từng mắt */
  leftEyeState:   EyeState;
  rightEyeState:  EyeState;
 
  /** Số lần nháy trong cửa sổ cuốn (rolling window, default 60s) */
  countInWindow:  number;
 
  /** Tần suất (lần/phút) trong cửa sổ cuốn */
  ratePerMinute:  number;
 
  /** Phân loại tần suất so với baseline */
  rateCategory:   BlinkRateCategory;
}

/**
 * Thông tin nhíu mày.
 * Tính từ khoảng cách dọc giữa landmark lông mày và khoé mắt.
 */
export interface BrowData {
  furrowLevel:    BrowFurrowLevel;
 
  /** Khoảng cách normalized giữa hai đầu lông mày (0.0 – 1.0) */
  innerDistance:  number;
 
  /** true nếu một bên lông mày nhướng lên bất đối xứng */
  isAsymmetric:   boolean;
 
  /** Độ cao của lông mày so với baseline (trục y, normalized) */
  leftHeight:     number;
  rightHeight:    number;
}

export interface MouthAspectRatio {
  value:    number;    // MAR hiện tại
  baseline: number;    // MAR khi miệng đóng tự nhiên (cá nhân hoá)
}

export interface MouthData {
  state:         MouthState;
  mar:           MouthAspectRatio;
  lipCorner:     LipCornerState;
 
  /** true nếu đang nói / cử động miệng liên tục (≥ 3 frame) */
  isTalking:     boolean;
 
  /** Góc của đuôi môi so với ngang (độ, dương = cười, âm = mếu) */
  cornerAngle:   number;
}

export interface MuscleTensionData {
  /** Chỉ số tổng hợp 0 – 100 */
  overallScore:   number;
 
  /** Căng thẳng vùng trán / lông mày */
  foreheadScore:  number;
 
  /** Căng thẳng vùng hàm (jaw clenching ước lượng) */
  jawScore:       number;
 
  /** Căng thẳng vùng quanh mắt */
  periocularScore: number;
}

export interface HeadPose {
  pitch: number;   // Gật đầu lên/xuống  (+= cúi, -= ngẩng)
  yaw:   number;   // Quay trái/phải     (+= phải, -= trái)
  roll:  number;   // Nghiêng đầu        (+= phải, -= trái)
}

export interface FaceFeatures {
  /** null nếu không phát hiện khuôn mặt trong frame */
  boundingBox:    FaceBoundingBox | null;
 
  /** null nếu không có khuôn mặt */
  landmarks:      Landmark[] | null;   // 468 điểm MediaPipe
 
  blink:          BlinkData;
  brow:           BrowData;
  mouth:          MouthData;
  tension:        MuscleTensionData;
  headPose:       HeadPose;
 
  /** Unix ms */
  extractedAt:    number;
 
  /** Thời gian xử lý frame (ms) — dùng để hiển thị latency */
  processingMs:   number;
}

export interface FeatureState {
  current:       FaceFeatures | null;
  faceDetected:  boolean;
  lastUpdated:   number | null;
}