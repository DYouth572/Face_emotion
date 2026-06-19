import { create } from 'zustand';
import type {
  EmotionLabel,
  EmotionResult,
  EmotionSnapshot,
  EmotionStats,
  EmotionState,
} from '@/types/emotion.types';
import { EMOTION_LABELS } from '@/types/emotion.types';

interface EmotionStore extends EmotionState {
  // ===== Actions =====

  /** Cập nhật kết quả cảm xúc từ frame mới */
  updateEmotion: (result: EmotionResult, frameIndex: number) => void;

  /** Đánh dấu đang xử lý */
  setProcessing: (value: boolean) => void;

  /** Tính lại stats từ toàn bộ history */
  recalcStats: () => void;

  /** Xóa history (giữ current) */
  clearHistory: () => void;

  /** Reset toàn bộ store */
  reset: () => void;
}

const MAX_HISTORY = 300;

/** Tính EmotionStats từ danh sách snapshots */
const calcStats = (
  history: EmotionSnapshot[],
  durationMs: number
): EmotionStats | null => {
  if (history.length === 0) return null;

  const counts: Partial<Record<EmotionLabel, number>> = {};
  EMOTION_LABELS.forEach((l) => { counts[l] = 0; });

  history.forEach((s) => {
    counts[s.result.dominant] = (counts[s.result.dominant] ?? 0) + 1;
  });

  const total = history.length;

  const distribution = Object.fromEntries(
    EMOTION_LABELS.map((l) => [l, (counts[l] ?? 0) / total])
  ) as Record<EmotionLabel, number>;

  const mostFrequent = EMOTION_LABELS.reduce(
    (max, l) => (distribution[l] > distribution[max] ? l : max),
    EMOTION_LABELS[0]
  );

  return {
    mostFrequent,
    distribution,
    totalFrames: total,
    durationMs,
  };
};

const initialState: EmotionState = {
  current:      null,
  history:      [],
  stats:        null,
  isProcessing: false,
  lastUpdated:  null,
};

export const useEmotionStore = create<EmotionStore>((set, get) => ({
  ...initialState,

  // ===== updateEmotion =====
  updateEmotion: (result: EmotionResult, frameIndex: number) =>
    set((state) => {
      const snapshot: EmotionSnapshot = {
        timestamp:  Date.now(),
        result,
        frameIndex,
      };

      const newHistory = [
        ...state.history.slice(-MAX_HISTORY + 1),
        snapshot,
      ];

      // Tính duration từ snapshot đầu đến cuối
      const durationMs =
        newHistory.length > 1
          ? newHistory[newHistory.length - 1].timestamp - newHistory[0].timestamp
          : 0;

      return {
        current:     result,
        history:     newHistory,
        stats:       calcStats(newHistory, durationMs),
        isProcessing: false,
        lastUpdated: Date.now(),
      };
    }),

  // ===== setProcessing =====
  setProcessing: (value: boolean) =>
    set({ isProcessing: value }),

  // ===== recalcStats =====
  recalcStats: () => {
    const { history } = get();
    const durationMs =
      history.length > 1
        ? history[history.length - 1].timestamp - history[0].timestamp
        : 0;
    set({ stats: calcStats(history, durationMs) });
  },

  // ===== clearHistory =====
  clearHistory: () =>
    set({ history: [], stats: null }),

  // ===== reset =====
  reset: () =>
    set(initialState),
}));