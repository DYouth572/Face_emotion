import { FaceFeatures, FeatureState } from '@/types/feature.types';
import { EmotionLabel } from '@/types/emotion.types';
import { SessionReport } from '@/types/report.types';
import { STRESS_LOW, STRESS_MEDIUM } from './constants';

export const average = (values: number[]): number => {
  if (values.length === 0) return 0;
  return values.reduce((sum, v) => sum + v, 0) / values.length;
};

export const minMax = (values: number[]): { min: number; max: number } => {
  if (values.length === 0) return { min: 0, max: 0 };
  return { min: Math.min(...values), max: Math.max(...values) };
};

export const standardDeviation = (values: number[]): number => {
  if (values.length < 2) return 0;
  const avg = average(values);
  const variance = values.reduce((sum, v) => sum + Math.pow(v - avg, 2), 0) / values.length;
  return Math.sqrt(variance);
};

/**
 * Tính blink rate từ danh sách FaceFeatures trong cửa sổ thời gian
 */
export const calcBlinkRateFromFeatures = (
  features: FaceFeatures[],
  windowMs = 60000
): number => {
  if (features.length === 0) return 0;

  const now = Date.now();
  const windowStart = now - windowMs;

  // Lấy các frame trong cửa sổ thời gian
  const inWindow = features.filter((f) => f.extractedAt >= windowStart);
  if (inWindow.length === 0) return 0;

  // Đếm số frame có isBlinking = true
  const blinkFrames = inWindow.filter((f) => f.blink.isBlinking).length;

  // Tính rate theo phút
  const durationMs = Math.min(windowMs, now - (inWindow[0]?.extractedAt ?? now));
  const minutes = durationMs / 60000;
  return minutes > 0 ? blinkFrames / minutes : 0;
};

/**
 * Lấy blink rate từ feature hiện tại (đã tính sẵn trong BlinkData)
 */
export const getBlinkRate = (feature: FaceFeatures | null): number =>
  feature?.blink.ratePerMinute ?? 0;

/**
 * Tính stress trung bình từ danh sách FaceFeatures
 * Dùng tension.overallScore (0-100) → normalize về 0-1
 */
export const calcAverageStress = (features: FaceFeatures[]): number => {
  const scores = features
    .map((f) => f.tension.overallScore / 100)
    .filter((v) => !isNaN(v));
  return average(scores);
};

/**
 * Tính stress tức thời từ feature hiện tại
 */
export const getCurrentStress = (feature: FaceFeatures | null): number =>
  feature ? feature.tension.overallScore / 100 : 0;

/**
 * Phân loại mức stress
 */
export const classifyStress = (
  level: number
): 'low' | 'medium' | 'high' => {
  if (level <= STRESS_LOW) return 'low';
  if (level <= STRESS_MEDIUM) return 'medium';
  return 'high';
};

/**
 * Tính max stress trong danh sách features
 */
export const calcMaxStress = (features: FaceFeatures[]): number => {
  if (features.length === 0) return 0;
  return Math.max(...features.map((f) => f.tension.overallScore / 100));
};

/**
 * Tính EAR trung bình từ danh sách FaceFeatures
 */
export const calcAverageEAR = (features: FaceFeatures[]): number => {
  const ears = features.map((f) => f.blink.ear.average);
  return average(ears);
};

/**
 * Lấy EAR hiện tại
 */
export const getCurrentEAR = (feature: FaceFeatures | null): number =>
  feature?.blink.ear.average ?? 0;

/**
 * Tính phân bố cảm xúc từ lịch sử
 */
export const calcEmotionDistribution = (
  emotionHistory: EmotionLabel[]
): Record<EmotionLabel, number> => {
  const counts: Partial<Record<EmotionLabel, number>> = {};
  emotionHistory.forEach((e) => {
    counts[e] = (counts[e] ?? 0) + 1;
  });
  const total = emotionHistory.length || 1;
  return Object.fromEntries(
    Object.entries(counts).map(([k, v]) => [k, (v as number) / total])
  ) as Record<EmotionLabel, number>;
};

/**
 * Tính điểm tập trung dựa trên:
 * - Blink rate bình thường (13-20 lần/phút theo BlinkRateCategory)
 * - Stress thấp
 * - Cảm xúc không tiêu cực
 * - Không nhíu mày mạnh
 */
export const calcFocusScore = (
  feature: FaceFeatures,
  dominantEmotion: EmotionLabel
): number => {
  let score = 1.0;

  // Blink rate
  const blinkCategory = feature.blink.rateCategory;
  if (blinkCategory === 'very_slow' || blinkCategory === 'very_fast') {
    score -= 0.25;
  } else if (blinkCategory === 'slow' || blinkCategory === 'fast') {
    score -= 0.1;
  }

  // Stress (tension.overallScore 0-100 → 0-1)
  const stressNorm = feature.tension.overallScore / 100;
  score -= stressNorm * 0.4;

  // Cảm xúc tiêu cực
  if (['angry', 'fear', 'sad', 'disgust'].includes(dominantEmotion)) {
    score -= 0.2;
  }

  // Nhíu mày mạnh
  if (feature.brow.furrowLevel === 'strong') {
    score -= 0.1;
  }

  return Math.max(0, Math.min(1, score));
};

/**
 * Overload đơn giản hơn khi không có FaceFeatures đầy đủ
 */
export const calcFocusScoreSimple = (
  blinkRate: number,
  avgStress: number,
  dominantEmotion: EmotionLabel
): number => {
  let score = 1.0;

  if (blinkRate < 10 || blinkRate > 30) score -= 0.2;
  score -= avgStress * 0.4;

  if (['angry', 'fear', 'sad', 'disgust'].includes(dominantEmotion)) {
    score -= 0.2;
  }

  return Math.max(0, Math.min(1, score));
};

/**
 * Tạo báo cáo tổng hợp từ danh sách FaceFeatures
 */
export const generateSessionReport = (
  features: FaceFeatures[],
  emotionHistory: EmotionLabel[],
  sessionDurationMs: number,
  sessionId = '',
  startedAt = Date.now() - sessionDurationMs,
): Partial<SessionReport> => {
  if (features.length === 0) {
    return {};
  }

  // Blink count = số frame có isBlinking = true
  const blinkCount = features.filter((f) => f.blink.isBlinking).length;

  // Blink rate từ feature cuối cùng (đã tính sẵn)
  const lastFeature = features[features.length - 1];
  const blinkRate = lastFeature?.blink.ratePerMinute ?? 0;

  // Stress
  const avgStress = calcAverageStress(features) * 100;
  const maxStress = calcMaxStress(features) * 100;
  const minStress = features.length > 0
    ? Math.min(...features.map((f) => f.tension.overallScore))
    : 0;

  // EAR
  const avgEAR = calcAverageEAR(features);

  // Emotion distribution
  const emotionDist = calcEmotionDistribution(emotionHistory);

  const dominant = emotionHistory.length > 0
    ? (Object.entries(emotionDist).sort((a, b) => b[1] - a[1])[0]?.[0] as EmotionLabel ?? 'neutral')
    : 'neutral' as EmotionLabel;

  // Chuyển distribution từ 0-1 → 0-100 (%)
  const emotionDistPercent = Object.fromEntries(
    Object.entries(emotionDist).map(([k, v]) => [k, v * 100])
  ) as Record<EmotionLabel, number>;

  return {
    sessionId,
    generatedAt: Date.now(),

    overview: {
      startedAt,
      endedAt: startedAt + sessionDurationMs,
      durationMs: sessionDurationMs,
      totalFrames: features.length,
      averageFps: features.length / (sessionDurationMs / 1000),
      faceDetectedFrames: features.filter((f) => isFaceDetected(f)).length,
      faceDetectionRate: features.filter((f) => isFaceDetected(f)).length / features.length,
    },

    emotion: {
      dominant,
      distribution: emotionDistPercent,
      avgConfidence: 0, // cần thêm nếu có data
      transitionCount: 0, // cần tính nếu cần
    },

    blink: {
      totalBlinks: blinkCount,
      avgRatePerMin: blinkRate,
      minRatePerMin: 0, // cần tính nếu có sliding window
      maxRatePerMin: 0,
      avgEar: avgEAR,
      longNoBlinkMs: 0, // cần tính nếu cần
    },

    stress: {
      avgScore: avgStress,
      peakScore: maxStress,
      minScore: minStress,
      highStressMs: 0,
      criticalStressMs: 0,
      avgForeheadScore: average(features.map((f) => f.tension.foreheadScore ?? 0)),
      avgJawScore: average(features.map((f) => f.tension.jawScore ?? 0)),
      avgPeriocularScore: average(features.map((f) => f.tension.periocularScore ?? 0)),
    },
  };
};


/**
 * Kiểm tra khuôn mặt có được phát hiện không
 */
export const isFaceDetected = (feature: FaceFeatures | null): boolean =>
  feature?.boundingBox !== null && feature?.boundingBox !== undefined;

/**
 * Tính thời gian xử lý trung bình (latency)
 */
export const calcAvgProcessingMs = (features: FaceFeatures[]): number => {
  const times = features.map((f) => f.processingMs);
  return average(times);
};

/**
 * Lấy head pose hiện tại
 */
export const getHeadPose = (feature: FaceFeatures | null) =>
  feature?.headPose ?? { pitch: 0, yaw: 0, roll: 0 };

/**
 * Kiểm tra đầu có lệch quá nhiều không
 */
export const isHeadPoseExtreme = (
  feature: FaceFeatures | null,
  threshold = 30
): boolean => {
  if (!feature) return false;
  const { pitch, yaw, roll } = feature.headPose;
  return Math.abs(pitch) > threshold || Math.abs(yaw) > threshold || Math.abs(roll) > threshold;
};

