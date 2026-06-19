import {
  EmotionLabel,
  EmotionScore,
  EmotionResult,
  EmotionSnapshot,
  EmotionStats,
  DeepFaceRawEmotion,
  EMOTION_LABELS,
  EMOTION_LABELS_VI,
  EMOTION_COLORS,
  EMOTION_ICONS,
} from '@/types/emotion.types';

/** Background màu nhạt tương ứng với từng cảm xúc */
export const EMOTION_BG_COLORS: Record<EmotionLabel, string> = {
  angry:    '#fee2e2',
  disgust:  '#f7fee7',
  fear:     '#f3e8ff',
  happy:    '#ccfbf1',
  sad:      '#dbeafe',
  surprise: '#fff7ed',
  neutral:  '#f1f5f9',
};

export const getEmotionLabelVI = (emotion: EmotionLabel): string =>
  EMOTION_LABELS_VI[emotion] ?? emotion;

export const getEmotionColor = (emotion: EmotionLabel): string =>
  EMOTION_COLORS[emotion] ?? '#9CA3AF';

export const getEmotionBgColor = (emotion: EmotionLabel): string =>
  EMOTION_BG_COLORS[emotion] ?? '#f1f5f9';

export const getEmotionIcon = (emotion: EmotionLabel): string =>
  EMOTION_ICONS[emotion] ?? '😐';

/** @deprecated Dùng getEmotionIcon thay thế */
export const getEmotionEmoji = getEmotionIcon;

/**
 * Chuyển đổi raw output từ DeepFace sang EmotionResult chuẩn
 * DeepFace trả về score 0-100, cần normalize về 0-1
 */
export const parseDeepFaceEmotion = (
  raw: DeepFaceRawEmotion,
  frameIndex = 0
): EmotionResult => {
  const scores: EmotionScore[] = EMOTION_LABELS.map((label) => {
    const rawScore = raw.emotion[label] ?? 0;
    return {
      label,
      score:      rawScore / 100,
      percentage: rawScore,
    };
  });

  const dominant = raw.dominant_emotion;
  const dominantScore =
    scores.find((s) => s.label === dominant)?.score ?? 0;

  return {
    dominant,
    dominantScore,
    scores,
    processedAt: Date.now(),
  };
};

/**
 * Tạo EmotionSnapshot từ EmotionResult
 */
export const createEmotionSnapshot = (
  result: EmotionResult,
  frameIndex: number
): EmotionSnapshot => ({
  timestamp:  Date.now(),
  result,
  frameIndex,
});

/**
 * Lấy dominant emotion từ EmotionResult
 */
export const getDominantEmotion = (result: EmotionResult): EmotionLabel =>
  result.dominant;

/**
 * Lấy top N cảm xúc từ EmotionResult (sắp xếp theo score giảm dần)
 */
export const getTopEmotions = (
  result: EmotionResult,
  topN = 3
): EmotionScore[] =>
  [...result.scores]
    .sort((a, b) => b.score - a.score)
    .slice(0, topN);

/**
 * Lấy score của một cảm xúc cụ thể từ EmotionResult
 */
export const getEmotionScore = (
  result: EmotionResult,
  label: EmotionLabel
): number =>
  result.scores.find((s) => s.label === label)?.score ?? 0;

/**
 * Lấy percentage của một cảm xúc cụ thể từ EmotionResult
 */
export const getEmotionPercentage = (
  result: EmotionResult,
  label: EmotionLabel
): number =>
  result.scores.find((s) => s.label === label)?.percentage ?? 0;

/** Kiểm tra cảm xúc có tiêu cực không */
export const isNegativeEmotion = (emotion: EmotionLabel): boolean =>
  ['angry', 'disgust', 'fear', 'sad'].includes(emotion);

/** Kiểm tra cảm xúc có tích cực không */
export const isPositiveEmotion = (emotion: EmotionLabel): boolean =>
  ['happy', 'surprise'].includes(emotion);

/**
 * Tính tổng điểm cảm xúc tiêu cực (0-1)
 */
export const getNegativeEmotionScore = (result: EmotionResult): number => {
  const negativeLabels: EmotionLabel[] = ['angry', 'disgust', 'fear', 'sad'];
  return negativeLabels.reduce(
    (sum, label) => sum + getEmotionScore(result, label),
    0
  );
};

/**
 * Tính tổng điểm cảm xúc tích cực (0-1)
 */
export const getPositiveEmotionScore = (result: EmotionResult): number => {
  const positiveLabels: EmotionLabel[] = ['happy', 'surprise'];
  return positiveLabels.reduce(
    (sum, label) => sum + getEmotionScore(result, label),
    0
  );
};

/**
 * Tính phân bố cảm xúc từ lịch sử snapshots
 * Trả về tỉ lệ % mỗi cảm xúc xuất hiện là dominant
 */
export const calcEmotionDistribution = (
  history: EmotionSnapshot[]
): Record<EmotionLabel, number> => {
  const counts: Partial<Record<EmotionLabel, number>> = {};

  history.forEach((snap) => {
    const label = snap.result.dominant;
    counts[label] = (counts[label] ?? 0) + 1;
  });

  const total = history.length || 1;

  return Object.fromEntries(
    EMOTION_LABELS.map((label) => [label, (counts[label] ?? 0) / total])
  ) as Record<EmotionLabel, number>;
};

/**
 * Tìm cảm xúc xuất hiện nhiều nhất trong lịch sử
 */
export const getMostFrequentEmotion = (
  history: EmotionSnapshot[]
): EmotionLabel => {
  if (history.length === 0) return 'neutral';

  const distribution = calcEmotionDistribution(history);
  return (Object.entries(distribution) as [EmotionLabel, number][]).reduce(
    (max, cur) => (cur[1] > max[1] ? cur : max),
    ['neutral', 0] as [EmotionLabel, number]
  )[0];
};

/**
 * Tạo EmotionStats từ lịch sử snapshots
 */
export const calcEmotionStats = (
  history: EmotionSnapshot[],
  durationMs: number
): EmotionStats => {
  const distribution = calcEmotionDistribution(history);
  const mostFrequent = getMostFrequentEmotion(history);

  return {
    mostFrequent,
    distribution,
    totalFrames: history.length,
    durationMs,
  };
};

/**
 * Normalize EmotionScore[] sao cho tổng score = 1
 */
export const normalizeEmotionScores = (scores: EmotionScore[]): EmotionScore[] => {
  const total = scores.reduce((sum, s) => sum + s.score, 0);
  if (total === 0) return scores;
  return scores.map((s) => ({
    ...s,
    score:      s.score / total,
    percentage: (s.score / total) * 100,
  }));
};

/**
 * Chuyển EmotionScore[] sang Record<EmotionLabel, number> (score 0-1)
 * Tiện dùng khi cần format cũ
 */
export const scoresToRecord = (
  scores: EmotionScore[]
): Record<EmotionLabel, number> =>
  Object.fromEntries(scores.map((s) => [s.label, s.score])) as Record<
    EmotionLabel,
    number
  >;

/**
 * Chuyển Record<EmotionLabel, number> sang EmotionScore[]
 * Tiện dùng khi nhận data từ API cũ
 */
export const recordToScores = (
  record: Record<EmotionLabel, number>
): EmotionScore[] =>
  EMOTION_LABELS.map((label) => ({
    label,
    score:      record[label] ?? 0,
    percentage: (record[label] ?? 0) * 100,
  }));
