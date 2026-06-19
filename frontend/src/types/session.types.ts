import type { WsSessionConfig } from "./websocket.types";

export type SessionStatus =
  | "idle"       // Chưa bắt đầu
  | "starting"   // Đang khởi tạo (chờ backend xác nhận)
  | "running"    // Đang ghi nhận
  | "paused"     // Tạm dừng
  | "stopping"   // Đang dừng
  | "ended"      // Đã kết thúc bình thường
  | "error";     // Kết thúc do lỗi
 
export type SessionEndReason =
  | "user_stopped"
  | "timeout"
  | "error"
  | "camera_lost";

export interface Session {
  /** UUID do backend cấp sau khi session_started */
  sessionId:    string;
 
  status:       SessionStatus;
 
  /** Unix ms */
  startedAt:    number;
 
  /** Unix ms — null nếu còn đang chạy */
  endedAt:      number | null;
 
  endReason:    SessionEndReason | null;
 
  /** Cấu hình đang áp dụng cho phiên này */
  config:       WsSessionConfig;
 
  /** Tổng số frame đã xử lý */
  totalFrames:  number;
 
  /** FPS trung bình thực tế trong phiên */
  averageFps:   number;
}

export interface SessionSummary {
  sessionId:       string;
  sessionCode?:    string;
  mode?:           string;
  startedAt:       number;
  endedAt:         number;
 
  /** Tổng thời lượng phiên (ms) */
  durationMs:      number;
 
  totalFrames:     number;
  averageFps:      number;
 
  /** Tổng số lần nháy mắt trong phiên */
  totalBlinks:     number;
 
  /** Tần suất nháy mắt trung bình (lần/phút) */
  avgBlinkRate:    number;
 
  /** Chỉ số căng thẳng trung bình (0–100) */
  avgStressScore:  number;
 
  /** Chỉ số căng thẳng cao nhất ghi nhận */
  peakStressScore: number;
 
  /** Cảm xúc xuất hiện nhiều nhất trong phiên */
  dominantEmotion: string;
  facsSummary?:    string;
 
  /** Số lần cảnh báo được trigger */
  totalAlerts:     number;
}
 
// ─── Session State (dùng cho Zustand store) ───────────────────────────────────
 
export interface SessionState {
  /** Phiên đang chạy, null nếu chưa bắt đầu */
  current:       Session | null;
 
  /** Lịch sử các phiên đã kết thúc trong app session */
  history:       SessionSummary[];
 
  /** Thời gian đã trôi qua của phiên hiện tại (ms) — cập nhật mỗi giây */
  elapsedMs:     number;
 
  /** true trong khoảng thời gian đang calibrate */
  isCalibrating: boolean;
 
  /** EAR baseline sau calibration — null nếu chưa calibrate */
  baselineEar:   number | null;
 
  /** MAR baseline sau calibration */
  baselineMar:   number | null;
}
 
// ─── Default Config ──────────────────────────────────────────────────────────
 
export const DEFAULT_SESSION_CONFIG: WsSessionConfig = {
  targetFps:            15,
  resolution:           "720p",
  enableBlink:          true,
  enableEmotion:        true,
  enableMuscleTension:  true,
  enableHeadPose:       true,
  stressAlertThreshold: 70,
  blinkAlertThreshold:  8,
};
