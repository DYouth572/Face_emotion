import dayjs from 'dayjs';
import duration from 'dayjs/plugin/duration';
import relativeTime from 'dayjs/plugin/relativeTime';
import 'dayjs/locale/vi';

dayjs.extend(duration);
dayjs.extend(relativeTime);
dayjs.locale('vi');

/** Format số thập phân với n chữ số sau dấu phẩy */
export const formatDecimal = (value: number, digits = 2): string => {
  if (isNaN(value)) return '0.' + '0'.repeat(digits);
  return value.toFixed(digits);
};

/** Format phần trăm: 0.85 → "85.0%" */
export const formatPercent = (value: number, digits = 1): string => {
  if (isNaN(value)) return '0%';
  return `${(value * 100).toFixed(digits)}%`;
};

/** Format số nguyên có dấu phân cách hàng nghìn */
export const formatInteger = (value: number): string => {
  return Math.round(value).toLocaleString('vi-VN');
};

/** Format timestamp → "HH:mm:ss" */
export const formatTime = (timestamp: number | string | Date): string => {
  return dayjs(timestamp).format('HH:mm:ss');
};

/** Format timestamp → "DD/MM/YYYY HH:mm" */
export const formatDateTime = (timestamp: number | string | Date): string => {
  return dayjs(timestamp).format('DD/MM/YYYY HH:mm');
};

/** Format timestamp → "DD/MM/YYYY" */
export const formatDate = (timestamp: number | string | Date): string => {
  return dayjs(timestamp).format('DD/MM/YYYY');
};

/** Format duration (ms) → "1 giờ 23 phút 45 giây" */
export const formatDuration = (ms: number): string => {
  if (ms <= 0) return '0 giây';
  const d = dayjs.duration(ms);
  const hours = Math.floor(d.asHours());
  const minutes = d.minutes();
  const seconds = d.seconds();

  const parts: string[] = [];
  if (hours > 0) parts.push(`${hours} giờ`);
  if (minutes > 0) parts.push(`${minutes} phút`);
  if (seconds > 0 || parts.length === 0) parts.push(`${seconds} giây`);
  return parts.join(' ');
};

/** Format duration (ms) → "01:23:45" */
export const formatDurationShort = (ms: number): string => {
  if (ms <= 0) return '00:00:00';
  const totalSeconds = Math.floor(ms / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  return [hours, minutes, seconds]
    .map((v) => String(v).padStart(2, '0'))
    .join(':');
};

/** Thời gian tương đối: "3 phút trước" */
export const formatRelativeTime = (timestamp: number | string | Date): string => {
  return dayjs(timestamp).fromNow();
};

/** Format EAR/MAR: 0.2534 → "0.253" */
export const formatEAR = (value: number): string => formatDecimal(value, 3);
export const formatMAR = (value: number): string => formatDecimal(value, 3);

/** Format brow distance: 18.3456 → "18.3" */
export const formatBrowDistance = (value: number): string => formatDecimal(value, 1);

/** Format stress level: 0.42 → "42%" */
export const formatStressLevel = (value: number): string => formatPercent(value);

/** Format blink rate: 15.333 → "15 lần/phút" */
export const formatBlinkRate = (value: number): string =>
  `${Math.round(value)} lần/phút`;

/** Format blink count: 123 → "123 lần" */
export const formatBlinkCount = (value: number): string =>
  `${formatInteger(value)} lần`;