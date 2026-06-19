export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
export const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws';

export const EAR_THRESHOLD_BLINK = 0.21;       // Dưới ngưỡng này = đang nháy mắt
export const EAR_THRESHOLD_FATIGUE = 0.23;     // Dưới ngưỡng này liên tục = mệt mỏi
export const EAR_CONSEC_FRAMES = 3;            // Số frame liên tiếp để xác nhận nháy mắt

export const MAR_THRESHOLD_YAWN = 0.6;         // Trên ngưỡng này = ngáp
export const MAR_THRESHOLD_OPEN = 0.4;         // Há miệng nhẹ

export const BROW_THRESHOLD_FROWN = 15.0;      // Dưới ngưỡng này = nhíu mày
export const BROW_THRESHOLD_RAISE = 30.0;      // Trên ngưỡng này = nhướng mày

export const STRESS_LOW = 0.3;                 // 0 - 0.3: Thấp
export const STRESS_MEDIUM = 0.6;              // 0.3 - 0.6: Trung bình
export const STRESS_HIGH = 1.0;

export const FATIGUE_ALERT_DURATION_MS = 5000;         // Thời gian hiển thị alert mệt mỏi
export const STRESS_ALERT_COOLDOWN_MS = 30000;         // Cooldown giữa 2 lần cảnh báo stress
export const BLINK_RATE_WINDOW_SEC = 60;               // Cửa sổ tính blink rate (giây)
export const LOW_BLINK_RATE_THRESHOLD = 10;            // Nháy mắt/phút thấp bất thường

export const BUFFER_SIZE = 100;                        // Số frame lưu trong buffer
export const CHART_HISTORY_POINTS = 60;                // Số điểm hiển thị trên chart

export const SESSION_STORAGE_KEY = 'face_emotion_session';
export const MAX_SESSION_DURATION_MS = 4 * 60 * 60 * 1000; // 4 giờ tối đa

export const EMOTION_LABELS = [
  'angry', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise'
] as const;

export const EMOTION_LABELS_VI: Record<string, string> = {
  angry: 'Tức giận',
  disgust: 'Ghê tởm',
  fear: 'Sợ hãi',
  happy: 'Vui vẻ',
  neutral: 'Bình thường',
  sad: 'Buồn bã',
  surprise: 'Ngạc nhiên',
};

export const LANDMARK_COLOR = '#00FF88';
export const LANDMARK_RADIUS = 1.5;
export const CONNECTION_COLOR = '#00AAFF';
export const CONNECTION_WIDTH = 1;
export const BOUNDING_BOX_COLOR = '#FF6B35';
export const BOUNDING_BOX_WIDTH = 2;

export const EXPORT_DATE_FORMAT = 'DD-MM-YYYY_HH-mm';
export const PDF_TITLE = 'Báo Cáo Phiên Học - Face Emotion Monitor';