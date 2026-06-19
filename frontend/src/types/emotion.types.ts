export type EmotionLabel =
  | "angry"      // Tức giận
  | "disgust"    // Ghê tởm
  | "fear"       // Sợ hãi
  | "happy"      // Vui vẻ
  | "sad"        // Buồn
  | "surprise"   // Ngạc nhiên
  | "neutral";   // Tự nhiên

export const EMOTION_LABELS: EmotionLabel[] = [
  "angry", "disgust", "fear", "happy", "sad", "surprise", "neutral",
];

export const EMOTION_LABELS_VI: Record<EmotionLabel, string> = {
  angry: "Tức giận",
  disgust: "Ghê tởm",
  fear: "Sợ hãi",
  happy: "Vui vẻ",
  sad: "Buồn",
  surprise: "Ngạc nhiên",
  neutral: "Tự nhiên",
};

export const EMOTION_COLORS: Record<EmotionLabel, string> = {
  angry: "#FF4444",
  disgust: "#A3E635",
  fear: "#A78BFA",
  happy: "#4ECDC4",
  sad: "#6B9FFF",
  surprise: "#FFB347",
  neutral: "#9CA3AF",
};

export const EMOTION_ICONS: Record<EmotionLabel, string> = {
  angry: "😠",
  disgust: "🤢",
  fear: "😨",
  happy: "😊",
  sad: "😢",
  surprise: "😲",
  neutral: "😐",
};

export interface DeepFaceRawEmotion {
  dominant_emotion: EmotionLabel;
  emotion: Record<EmotionLabel, number>;  // 0–100 (%)
}

export interface EmotionScore {
  label: EmotionLabel;
  score: number;      // 0.0 – 1.0  (đã chia 100 từ raw)
  percentage: number;      // 0 – 100    (giữ nguyên raw, dùng cho UI)
}

export interface EmotionResult {
  /** Cảm xúc có confidence cao nhất — map từ dominant_emotion */
  dominant: EmotionLabel;
  dominantScore: number;
  scores: EmotionScore[];
  processedAt: number;
}

export interface EmotionSnapshot {
  timestamp: number;        // Unix ms
  result: EmotionResult;
  frameIndex: number;        // Thứ tự frame liên tục trong phiên
}

export interface EmotionStats {
  mostFrequent: EmotionLabel;
  distribution: Record<EmotionLabel, number>;
  totalFrames: number;
  durationMs: number;
}

export interface EmotionState {
  current: EmotionResult | null;
  history: EmotionSnapshot[];
  stats: EmotionStats | null;
  isProcessing: boolean;
  lastUpdated: number | null;
}
