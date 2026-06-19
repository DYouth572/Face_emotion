import { create } from 'zustand';
import type {
  SessionState,
  Session,
  SessionSummary,
  SessionStatus,
  SessionEndReason,
} from '@/types/session.types';
import { DEFAULT_SESSION_CONFIG } from '@/types/session.types';
import type { WsSessionConfig } from '@/types/websocket.types';

interface SessionStore extends SessionState {
  // ===== Actions =====

  /** Bắt đầu phiên mới — gọi sau khi backend xác nhận session_started */
  startSession: (
    sessionId: string,
    config?: Partial<WsSessionConfig>,
    startedAt?: number
  ) => void;

  /** Chuyển trạng thái sang 'paused' */
  pauseSession: () => void;

  /** Tiếp tục từ 'paused' → 'running' */
  resumeSession: () => void;

  /** Kết thúc phiên với lý do cụ thể */
  endSession: (reason: SessionEndReason, endedAt?: number) => void;

  /** Cập nhật trạng thái phiên (dùng khi nhận WS message) */
  setStatus: (status: SessionStatus) => void;

  /** Cập nhật elapsed time — gọi mỗi giây từ interval */
  tickElapsed: () => void;

  /** Cập nhật frame count và FPS */
  updateFrameStats: (totalFrames: number, averageFps: number) => void;

  /** Lưu summary vào history sau khi phiên kết thúc */
  saveToHistory: (summary: SessionSummary) => void;

  /** Bắt đầu calibration */
  startCalibration: () => void;

  /** Kết thúc calibration với baseline values */
  finishCalibration: (baselineEar: number, baselineMar: number) => void;

  /** Reset toàn bộ store về trạng thái ban đầu */
  reset: () => void;
}

// ============================================================
// Initial State
// ============================================================

const initialState: SessionState = {
  current:       null,
  history:       [],
  elapsedMs:     0,
  isCalibrating: false,
  baselineEar:   null,
  baselineMar:   null,
};

// ============================================================
// Store
// ============================================================

export const useSessionStore = create<SessionStore>((set, get) => ({
  ...initialState,

  // ===== startSession =====
  startSession: (
    sessionId: string,
    config?: Partial<WsSessionConfig>,
    startedAt?: number
  ) => {
    const mergedConfig: WsSessionConfig = {
      ...DEFAULT_SESSION_CONFIG,
      ...config,
    };

    const newSession: Session = {
      sessionId,
      status:      'running',
      startedAt:   startedAt ?? Date.now(),
      endedAt:     null,
      endReason:   null,
      config:      mergedConfig,
      totalFrames: 0,
      averageFps:  0,
    };

    set({
      current:   newSession,
      elapsedMs: 0,
    });
  },

  // ===== pauseSession =====
  pauseSession: () => {
    const { current } = get();
    if (!current || current.status !== 'running') return;

    set({
      current: { ...current, status: 'paused' },
    });
  },

  // ===== resumeSession =====
  resumeSession: () => {
    const { current } = get();
    if (!current || current.status !== 'paused') return;

    set({
      current: { ...current, status: 'running' },
    });
  },

  // ===== endSession =====
  endSession: (reason: SessionEndReason, endedAt?: number) => {
    const { current } = get();
    if (!current) return;

    set({
      current: {
        ...current,
        status:    'ended',
        endedAt:   endedAt ?? Date.now(),
        endReason: reason,
      },
    });
  },

  // ===== setStatus =====
  setStatus: (status: SessionStatus) => {
    const { current } = get();
    if (!current) return;

    set({ current: { ...current, status } });
  },

  // ===== tickElapsed =====
  tickElapsed: () => {
    const { current } = get();
    if (!current || current.status !== 'running') return;

    set((state) => ({ elapsedMs: state.elapsedMs + 1000 }));
  },

  // ===== updateFrameStats =====
  updateFrameStats: (totalFrames: number, averageFps: number) => {
    const { current } = get();
    if (!current) return;

    set({
      current: { ...current, totalFrames, averageFps },
    });
  },

  // ===== saveToHistory =====
  saveToHistory: (summary: SessionSummary) => {
    set((state) => ({
      history: [summary, ...state.history].slice(0, 50), // Giữ tối đa 50 phiên
    }));
  },

  // ===== startCalibration =====
  startCalibration: () => {
    set({ isCalibrating: true });
  },

  // ===== finishCalibration =====
  finishCalibration: (baselineEar: number, baselineMar: number) => {
    set({
      isCalibrating: false,
      baselineEar,
      baselineMar,
    });
  },

  // ===== reset =====
  reset: () => {
    set(initialState);
  },
}));
