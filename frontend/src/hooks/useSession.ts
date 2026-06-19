import { useCallback, useEffect, useRef } from 'react';
import { useSessionStore } from '@/store/useSessionStore';
import { useFeatureStore } from '@/store/useFeatureStore';
import { useEmotionStore } from '@/store/useEmotionStore';
import { useAlertStore } from '@/store/useAlertStore';
import { websocketService } from '@/services/websocketService';
import type { WsSessionConfig } from '@/types/websocket.types';
import type { WsInboundMessage } from '@/types/websocket.types';
import type { AlertType } from '@/types/alert.types';

interface UseSessionReturn {
  isActive:       boolean;
  sessionId:      string | null;
  elapsedMs:      number;
  isCalibrating:  boolean;
  startSession:   (config?: Partial<WsSessionConfig>) => void;
  stopSession:    () => void;
  pauseSession:   () => void;
  resumeSession:  () => void;
}

export function useSession(): UseSessionReturn {
  const store         = useSessionStore();
  const resetFeature  = useFeatureStore((s) => s.reset);
  const updateFeature = useFeatureStore((s) => s.updateFeature);
  const updateAuFacs  = useFeatureStore((s) => s.updateAuFacs);
  const resetEmotion  = useEmotionStore((s) => s.reset);
  const updateEmotion = useEmotionStore((s) => s.updateEmotion);
  const clearAlerts   = useAlertStore((s) => s.clearAlerts);
  const addAlert      = useAlertStore((s) => s.addAlert);
  const tickInterval  = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    websocketService.connect();
  }, []);

  // ===== Xử lý message từ WebSocket =====
  useEffect(() => {
    const unsub = websocketService.onMessage((msg: WsInboundMessage) => {
      switch (msg.type) {
        case 'session_started':
          store.startSession(
            msg.payload.sessionId,
            msg.payload.config,
            msg.payload.startedAt
          );
          break;

        case 'frame_result':
          updateFeature(msg.payload.features);
          updateAuFacs(msg.payload.au_scores, msg.payload.facs_states);
          updateEmotion(msg.payload.emotion, msg.payload.frameIndex);
          store.updateFrameStats(msg.payload.frameIndex, msg.payload.currentFps);
          break;

        case 'alert':
          addAlert({
            alertId: msg.payload.alertId,
            alertType: msg.payload.alertType as AlertType,
            severity: msg.payload.severity,
            message: msg.payload.message,
            triggeredAt: msg.timestamp,
            isRead: false,
            data: msg.payload.data,
          });
          break;

        case 'error':
          addAlert({
            alertId: msg.messageId,
            alertType: 'face_lost' as AlertType,
            severity: msg.payload.fatal ? 'critical' : 'warning',
            message: msg.payload.message,
            triggeredAt: msg.timestamp,
            isRead: false,
            data: { extra: { code: msg.payload.code } },
          });
          if (msg.payload.fatal) {
            store.endSession('error', msg.timestamp);
          }
          break;

        case 'session_ended':
          store.endSession(msg.payload.reason, msg.payload.endedAt);
          break;

        case 'calibration_done':
          if (msg.payload.success) {
            store.finishCalibration(msg.payload.baselineEar, msg.payload.baselineMar);
          }
          break;

        default:
          break;
      }
    });

    return () => unsub();
  }, [addAlert, store, updateAuFacs, updateEmotion, updateFeature]);

  // ===== Tick elapsed time mỗi giây =====
  useEffect(() => {
    const status = store.current?.status;

    if (status === 'running') {
      tickInterval.current = setInterval(() => {
        store.tickElapsed();
      }, 1000);
    } else {
      if (tickInterval.current) {
        clearInterval(tickInterval.current);
        tickInterval.current = null;
      }
    }

    return () => {
      if (tickInterval.current) {
        clearInterval(tickInterval.current);
        tickInterval.current = null;
      }
    };
  }, [store.current?.status]);

  // ===== Actions =====
  const startSession = useCallback((config?: Partial<WsSessionConfig>) => {
    resetFeature();
    resetEmotion();
    clearAlerts();
    store.setStatus('starting');
    websocketService.startSession({
      targetFps:            15,
      resolution:           '720p',
      enableBlink:          true,
      enableEmotion:        true,
      enableMuscleTension:  true,
      enableHeadPose:       true,
      stressAlertThreshold: 70,
      blinkAlertThreshold:  8,
      ...config,
    });
  }, [resetFeature, resetEmotion, clearAlerts, store]);

  const stopSession = useCallback(() => {
    const sessionId = store.current?.sessionId;
    if (!sessionId) return;
    store.setStatus('stopping');
    websocketService.stopSession(sessionId);
  }, [store]);

  const pauseSession = useCallback(() => {
    const sessionId = store.current?.sessionId;
    if (!sessionId) return;
    store.pauseSession();
    websocketService.pauseSession(sessionId);
  }, [store]);

  const resumeSession = useCallback(() => {
    const sessionId = store.current?.sessionId;
    if (!sessionId) return;
    store.resumeSession();
    websocketService.resumeSession(sessionId);
  }, [store]);

  return {
    isActive:      store.current?.status === 'running',
    sessionId:     store.current?.sessionId ?? null,
    elapsedMs:     store.elapsedMs,
    isCalibrating: store.isCalibrating,
    startSession,
    stopSession,
    pauseSession,
    resumeSession,
  };
}
