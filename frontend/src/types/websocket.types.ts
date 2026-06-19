import type { EmotionResult }  from "./emotion.types";
import type { FaceFeatures }   from "./feature.types";

export type AuKey =
  | "AU1"
  | "AU2"
  | "AU4"
  | "AU5"
  | "AU6"
  | "AU7"
  | "AU9"
  | "AU10"
  | "AU12"
  | "AU15"
  | "AU20"
  | "AU23"
  | "AU25"
  | "AU26";

export type WsConnectionStatus =
  | "idle"          // Chưa khởi tạo
  | "connecting"    // Đang kết nối
  | "connected"     // Đã kết nối, đang nhận data
  | "reconnecting"  // Mất kết nối, đang thử lại
  | "disconnected"  // Đã ngắt kết nối có chủ ý
  | "error";        // Lỗi không thể recover

export type WsInboundType =
  | "frame_result"       // Kết quả xử lý 1 frame (features + emotion)
  | "session_started"    // Backend xác nhận bắt đầu phiên
  | "session_ended"      // Backend thông báo kết thúc phiên
  | "alert"              // Cảnh báo (stress cao, blink thấp, …)
  | "heartbeat"          // Ping giữ kết nối
  | "error"              // Lỗi từ backend
  | "calibration_done";  // Hoàn thành calibration khuôn mặt

export type WsOutboundType =
  | "start_session"     // Yêu cầu bắt đầu ghi nhận
  | "stop_session"      // Yêu cầu dừng ghi nhận
  | "pause_session"     // Tạm dừng (giữ nguyên phiên)
  | "resume_session"    // Tiếp tục sau khi pause
  | "start_calibration" // Bắt đầu hiệu chỉnh khuôn mặt
  | "video_frame"       // Gui frame camera preview len backend
  | "heartbeat_ack"     // Phản hồi ping
  | "update_config";    // Cập nhật cấu hình realtime

export interface WsBaseMessage {
  /** Loại message để phân biệt handler */
  type:      string;
 
  /** Unix ms — thời điểm message được tạo */
  timestamp: number;
 
  /** ID duy nhất của message (UUID v4), dùng để debug */
  messageId: string;
}

export interface WsFrameResultMessage extends WsBaseMessage {
  type: "frame_result";
  payload: {
    features: FaceFeatures;
    emotion: EmotionResult;

    au_scores?: Partial<Record<AuKey, number>>;

    facs_states?: string[];

    /** Số thứ tự frame trong phiên hiện tại */
    frameIndex: number;

    /** FPS thực tế của backend tại thời điểm này */
    currentFps: number;
  };
}

export interface WsSessionStartedMessage extends WsBaseMessage {
  type:     "session_started";
  payload: {
    sessionId:   string;
    startedAt:   number;    // Unix ms
    config:      WsSessionConfig;
  };
}

export interface WsSessionEndedMessage extends WsBaseMessage {
  type:     "session_ended";
  payload: {
    sessionId:  string;
    endedAt:    number;
    reason:     "user_stopped" | "timeout" | "error" | "camera_lost";
  };
}

export interface WsAlertMessage extends WsBaseMessage {
  type:     "alert";
  payload: {
    alertId:    string;
    alertType:  string;
    severity:   "info" | "warning" | "critical";
    message:    string;
    data:       Record<string, unknown>;
  };
}

export interface WsHeartbeatMessage extends WsBaseMessage {
  type: "heartbeat";
  payload: {
    serverTime: number;
  };
}

export interface WsErrorMessage extends WsBaseMessage {
  type:     "error";
  payload: {
    code:    string;    // VD: "CAMERA_NOT_FOUND", "MODEL_LOAD_FAILED"
    message: string;
    fatal:   boolean;   // true = phải reconnect / reload
  };
}

export interface WsCalibrationDoneMessage extends WsBaseMessage {
  type:     "calibration_done";
  payload: {
    success:      boolean;
    baselineEar:  number;   // EAR baseline cá nhân hoá
    baselineMar:  number;   // MAR baseline
    message:      string;
  };
}

export type WsInboundMessage =
  | WsFrameResultMessage
  | WsSessionStartedMessage
  | WsSessionEndedMessage
  | WsAlertMessage
  | WsHeartbeatMessage
  | WsErrorMessage
  | WsCalibrationDoneMessage;

export interface WsSessionConfig {
  /** Số frame xử lý mỗi giây (1–30) */
  targetFps:           number;
 
  /** Độ phân giải camera */
  resolution:          "480p" | "720p" | "1080p";
 
  /** Bật/tắt tính năng */
  enableBlink:         boolean;
  enableEmotion:       boolean;
  enableMuscleTension: boolean;
  enableHeadPose:      boolean;
 
  /** Ngưỡng cảnh báo stress (0–100) */
  stressAlertThreshold: number;
 
  /** Ngưỡng cảnh báo blink rate (lần/phút) */
  blinkAlertThreshold:  number;
}
 
export interface WsStartSessionMessage extends WsBaseMessage {
  type:    "start_session";
  payload: { config: WsSessionConfig };
}

export interface WsStopSessionMessage extends WsBaseMessage {
  type:    "stop_session";
  payload: { sessionId: string };
}
 
export interface WsPauseSessionMessage extends WsBaseMessage {
  type:    "pause_session";
  payload: { sessionId: string };
}
 
export interface WsResumeSessionMessage extends WsBaseMessage {
  type:    "resume_session";
  payload: { sessionId: string };
}
 
export interface WsHeartbeatAckMessage extends WsBaseMessage {
  type:    "heartbeat_ack";
  payload: { clientTime: number };
}
 
export interface WsUpdateConfigMessage extends WsBaseMessage {
  type:    "update_config";
  payload: { config: Partial<WsSessionConfig> };
}

export interface WsVideoFrameMessage extends WsBaseMessage {
  type:    "video_frame";
  payload: {
    image: string;
    width: number;
    height: number;
  };
}

export type WsOutboundMessage =
  | WsStartSessionMessage
  | WsStopSessionMessage
  | WsPauseSessionMessage
  | WsResumeSessionMessage
  | WsHeartbeatAckMessage
  | WsUpdateConfigMessage
  | WsVideoFrameMessage;
 
export interface WsConnectionState {
  status:         WsConnectionStatus;
  url:            string;
  sessionId:      string | null;
  connectedAt:    number | null;
  lastMessageAt:  number | null;
  reconnectCount: number;
  latencyMs:      number | null;
  error:          string | null;
}

