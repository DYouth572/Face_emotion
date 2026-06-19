import type { EmotionLabel }  from "./emotion.types";
import type { AlertType }     from "./alert.types";
import type { AuKey }         from "./websocket.types";

export type FocusLevel = "high" | "medium" | "low";

export interface SessionReport {
  reportId:    string;    // UUID
  sessionId:   string;
  generatedAt: number;    // Unix ms
 
  overview:    ReportOverview;
  emotion:     ReportEmotion;
  auFacs?:     ReportAuFacs;
  blink:       ReportBlink;
  stress:      ReportStress;
  focus:       ReportFocus;
  alerts:      ReportAlerts;
  timeline:    ReportTimelinePoint[];
}

export interface ReportOverview {
  startedAt:    number;   // Unix ms
  endedAt:      number;
  durationMs:   number;
  totalFrames:  number;
  averageFps:   number;
 
  /** Số frame có khuôn mặt được phát hiện */
  faceDetectedFrames: number;
 
  /** Tỉ lệ frame có mặt / tổng frame (0.0 – 1.0) */
  faceDetectionRate:  number;
}

export interface ReportEmotion {
  /** Cảm xúc xuất hiện nhiều nhất */
  dominant:      EmotionLabel;

  /** Engine nhận diện cảm xúc đang dùng cho báo cáo */
  engine?:        string;
 
  /** Phân phối % thời gian cho từng cảm xúc */
  distribution:  Record<EmotionLabel, number>;  // 0–100 (%)
 
  /** Confidence trung bình của cảm xúc dominant */
  avgConfidence: number;
 
  /** Số lần chuyển đổi cảm xúc trong phiên */
  transitionCount: number;
}

export interface ReportAuFacs {
  /** Engine phân tích Action Unit/FACS */
  engine: string;

  /** Điểm AU trung bình toàn phiên, thang 0.0-1.0 */
  avgAuScores: Partial<Record<AuKey, number>>;

  /** Các AU nổi bật theo ngưỡng của backend */
  activeAus: AuKey[];

  /** Tổ hợp FACS xuất hiện nhiều nhất */
  dominantFacs: string;

  /** Phân phối % trạng thái FACS trong phiên */
  facsDistribution: Record<string, number>;
}

export interface ReportBlink {
  totalBlinks:     number;
 
  /** Tần suất trung bình toàn phiên (lần/phút) */
  avgRatePerMin:   number;
 
  /** Tần suất thấp nhất ghi nhận (lần/phút) */
  minRatePerMin:   number;
 
  /** Tần suất cao nhất ghi nhận (lần/phút) */
  maxRatePerMin:   number;
 
  /** EAR trung bình toàn phiên */
  avgEar:          number;
 
  /** Tổng thời gian không nháy mắt > 5s (ms) */
  longNoBlinkMs:   number;
}

export interface ReportStress {
  avgScore:    number;   // 0–100
  peakScore:   number;
  minScore:    number;
 
  /** Tổng thời gian stress > ngưỡng warning (ms) */
  highStressMs:     number;
 
  /** Tổng thời gian stress > ngưỡng critical (ms) */
  criticalStressMs: number;
 
  /** Chỉ số từng vùng cơ mặt trung bình */
  avgForeheadScore:   number;
  avgJawScore:        number;
  avgPeriocularScore: number;
}

export interface ReportFocus {
  /** Phân phối % thời gian cho từng mức tập trung */
  distribution: Record<FocusLevel, number>;  // 0–100 (%)
 
  /** Tổng thời gian tập trung tốt (ms) */
  highFocusMs:  number;
 
  /** Tổng thời gian mất tập trung (ms) */
  lowFocusMs:   number;
}

export interface ReportAlerts {
  totalCount:  number;
 
  /** Số lần theo từng loại alert */
  byType:      Partial<Record<AlertType, number>>;
 
  /** Số lần theo từng mức độ */
  bySeverity: {
    info:     number;
    warning:  number;
    critical: number;
  };
}

export interface ReportTimelinePoint {
  /** Unix ms */
  timestamp:   number;
 
  /** Giây tính từ đầu phiên — dùng làm trục X */
  elapsedSec:  number;
 
  stressScore: number;
  blinkRate:   number;    // lần/phút tại thời điểm này
  earAverage:  number;
  emotion:     EmotionLabel;
  emotionEngine?: string;
  auScores?:   Partial<Record<AuKey, number>>;
  facsStates?: string[];
  focusLevel:  FocusLevel;
}

export type ReportExportFormat = "json" | "csv" | "pdf";
 
export interface ReportExportOptions {
  format:         ReportExportFormat;
  includeTimeline: boolean;
  filename?:      string;
}
