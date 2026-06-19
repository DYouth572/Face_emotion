import type { EmotionLabel } from "./emotion.types";

export type AlertType =
  | "stress_high"
  | "stress_critical"
  | "blink_low"
  | "face_lost";

export type AlertSeverity = "info" | "warning" | "critical";

export interface Alert {
  alertId: string;
  alertType: AlertType;
  severity: AlertSeverity;
  message: string;
  triggeredAt: number;
  isRead: boolean;
  data: AlertData;
}

export interface AlertData {
  currentValue?: number;
  threshold?: number;
  emotion?: EmotionLabel;
  durationMs?: number;
  extra?: Record<string, unknown>;
}

export interface AlertRule {
  alertType: AlertType;
  severity: AlertSeverity;
  enabled: boolean;
  threshold: number;
  debounceMss: number;
  cooldownMs: number;
}

export interface AlertState {
  alerts: Alert[];
  unreadCount: number;
  rules: AlertRule[];
  hasCritical: boolean;
}

export const ALERT_LABELS_VI: Record<AlertType, string> = {
  stress_high: "Cang thang cao",
  stress_critical: "Cang thang nguy hiem",
  blink_low: "Nhay mat qua it",
  face_lost: "Mat khuon mat",
};

export const ALERT_SEVERITY_COLORS: Record<AlertSeverity, string> = {
  info: "#38bdf8",
  warning: "#fb923c",
  critical: "#f87171",
};
