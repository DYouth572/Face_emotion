import { create } from 'zustand';
import { FaceFeatures, FeatureState } from '@/types/feature.types';
import type { AuKey } from '@/types/websocket.types';

interface FeatureStore extends FeatureState {
  history: FaceFeatures[];
  auScores: Partial<Record<AuKey, number>>;
  facsStates: string[];
  updateFeature: (feature: FaceFeatures) => void;
  updateAuFacs: (
    auScores?: Partial<Record<AuKey, number>>,
    facsStates?: string[]
  ) => void;
  setFaceDetected: (detected: boolean) => void;
  clearHistory: () => void;
  reset: () => void;
}

const MAX_HISTORY = 300; // ~5 phút @ 1fps

export const useFeatureStore = create<FeatureStore>((set) => ({
  // ===== State =====
  current: null,
  faceDetected: false,
  lastUpdated: null,
  history: [],
  auScores: {},
  facsStates: ['Bình thường'],

  // ===== Actions =====
  updateFeature: (feature: FaceFeatures) =>
    set((state) => ({
      current: feature,
      faceDetected: feature.boundingBox !== null,
      lastUpdated: feature.extractedAt,
      history: [...state.history.slice(-MAX_HISTORY + 1), feature],
    })),

  updateAuFacs: (auScores, facsStates) =>
    set((state) => ({
      auScores: auScores
        ? {
            ...state.auScores,
            ...Object.fromEntries(
              Object.entries(auScores).map(([key, value]) => [key, Number(value ?? 0)])
            ),
          }
        : state.auScores,
      facsStates:
        Array.isArray(facsStates) && facsStates.length > 0
          ? facsStates
          : state.facsStates,
    })),

  setFaceDetected: (detected: boolean) =>
    set({ faceDetected: detected }),

  clearHistory: () =>
    set({ history: [] }),

  reset: () =>
    set({
      current: null,
      faceDetected: false,
      lastUpdated: null,
      history: [],
      auScores: {},
      facsStates: ['Bình thường'],
    }),
}));
