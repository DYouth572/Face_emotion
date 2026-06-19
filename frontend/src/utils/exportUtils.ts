import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';
import { saveAs } from 'file-saver';
import dayjs from 'dayjs';

import type { SessionReport, ReportExportFormat, ReportExportOptions } from '@/types/report.types';
import type { EmotionLabel, EmotionSnapshot } from '@/types/emotion.types';
import type { FaceFeatures } from '@/types/feature.types';
import type { AuKey } from '@/types/websocket.types';
import {
  EXPORT_DATE_FORMAT,
  PDF_TITLE,
} from './constants';
import {
  EMOTION_LABELS_VI,
  EMOTION_LABELS,
} from '@/types/emotion.types';
import {
  formatDuration,
  formatDateTime,
  formatDecimal,
  formatPercent,
  formatBlinkRate,
} from './formatters';
import { classifyStress } from './statisticsUtils';

const getTimestamp = (): string =>
  dayjs().format(EXPORT_DATE_FORMAT);

const AU_REPORT_KEYS: AuKey[] = [
  'AU1',
  'AU2',
  'AU4',
  'AU5',
  'AU6',
  'AU7',
  'AU9',
  'AU10',
  'AU12',
  'AU15',
  'AU20',
  'AU23',
  'AU25',
  'AU26',
];

const PDF_FONT = 'DejaVuSans';
const PDF_FONT_REGULAR_FILE = 'DejaVuSans.ttf';
const PDF_FONT_BOLD_FILE = 'DejaVuSans-Bold.ttf';
const PDF_FONT_BASE_URL = import.meta.env.BASE_URL;

const fetchFontAsBase64 = async (url: string): Promise<string> => {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to load PDF font: ${url}`);
  }

  const buffer = await response.arrayBuffer();
  const bytes = new Uint8Array(buffer);
  let binary = '';

  for (let index = 0; index < bytes.length; index += 0x8000) {
    const chunk = bytes.subarray(index, index + 0x8000);
    binary += String.fromCharCode(...chunk);
  }

  return btoa(binary);
};

const registerPdfFonts = async (doc: jsPDF): Promise<void> => {
  const [regularFont, boldFont] = await Promise.all([
    fetchFontAsBase64(`${PDF_FONT_BASE_URL}fonts/DejaVuSans.ttf`),
    fetchFontAsBase64(`${PDF_FONT_BASE_URL}fonts/DejaVuSans-Bold.ttf`),
  ]);

  doc.addFileToVFS(PDF_FONT_REGULAR_FILE, regularFont);
  doc.addFont(PDF_FONT_REGULAR_FILE, PDF_FONT, 'normal');
  doc.addFileToVFS(PDF_FONT_BOLD_FILE, boldFont);
  doc.addFont(PDF_FONT_BOLD_FILE, PDF_FONT, 'bold');
  doc.setFont(PDF_FONT, 'normal');
};

const getStressLabel = (score: number): string => {
  // score là 0-100 (theo ReportStress.avgScore)
  const normalized = score / 100;
  const cls = classifyStress(normalized);
  return cls === 'low' ? 'Thấp' : cls === 'medium' ? 'Trung bình' : 'Cao';
};

export const exportSessionReportPDF = (
  report: SessionReport,
  sessionLabel = 'Phiên học'
): Promise<void> => {
  const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
  const pageWidth = doc.internal.pageSize.getWidth();

  return registerPdfFonts(doc).then(() => {
  // ===== Header =====
  doc.setFontSize(18);
  doc.setFont(PDF_FONT, 'bold');
  doc.text(PDF_TITLE, pageWidth / 2, 18, { align: 'center' });

  doc.setFontSize(11);
  doc.setFont(PDF_FONT, 'normal');
  doc.text(`Phiên: ${sessionLabel}`, pageWidth / 2, 26, { align: 'center' });
  doc.text(`Xuất lúc: ${formatDateTime(report.generatedAt)}`, pageWidth / 2, 32, { align: 'center' });

  // ===== 1. Tổng quan =====
  doc.setFontSize(13);
  doc.setFont(PDF_FONT, 'bold');
  doc.text('1. Tổng Quan Phiên Học', 14, 44);

  autoTable(doc, {
    startY: 48,
    head: [['Chỉ số', 'Giá trị']],
    body: [
      ['Thời gian bắt đầu',   formatDateTime(report.overview.startedAt)],
      ['Thời gian kết thúc',  formatDateTime(report.overview.endedAt)],
      ['Tổng thời gian',      formatDuration(report.overview.durationMs)],
      ['Tổng số frame',       report.overview.totalFrames.toString()],
      ['FPS trung bình',      formatDecimal(report.overview.averageFps, 1)],
      ['Frame có khuôn mặt',  report.overview.faceDetectedFrames.toString()],
      ['Tỉ lệ nhận diện',     formatPercent(report.overview.faceDetectionRate)],
    ],
    styles: { font: PDF_FONT, fontSize: 10 },
    headStyles: { fillColor: [99, 102, 241] },
    alternateRowStyles: { fillColor: [245, 245, 255] },
    margin: { left: 14, right: 14 },
  });

  // ===== 2. Nháy mắt =====
  const y2 = (doc as any).lastAutoTable.finalY + 10;
  doc.setFontSize(13);
  doc.setFont(PDF_FONT, 'bold');
  doc.text('2. Chỉ Số Nháy Mắt', 14, y2);

  autoTable(doc, {
    startY: y2 + 4,
    head: [['Chỉ số', 'Giá trị']],
    body: [
      ['Tổng số nháy mắt',        report.blink.totalBlinks.toString()],
      ['Tần suất trung bình',      formatBlinkRate(report.blink.avgRatePerMin)],
      ['Tần suất thấp nhất',       formatBlinkRate(report.blink.minRatePerMin)],
      ['Tần suất cao nhất',        formatBlinkRate(report.blink.maxRatePerMin)],
      ['EAR trung bình',           formatDecimal(report.blink.avgEar, 3)],
      ['Thời gian không nháy dài', formatDuration(report.blink.longNoBlinkMs)],
    ],
    styles: { font: PDF_FONT, fontSize: 10 },
    headStyles: { fillColor: [14, 165, 233] },
    alternateRowStyles: { fillColor: [240, 249, 255] },
    margin: { left: 14, right: 14 },
  });

  // ===== 3. Căng thẳng =====
  const y3 = (doc as any).lastAutoTable.finalY + 10;
  doc.setFontSize(13);
  doc.setFont(PDF_FONT, 'bold');
  doc.text('3. Chỉ Số Căng Thẳng', 14, y3);

  autoTable(doc, {
    startY: y3 + 4,
    head: [['Chỉ số', 'Giá trị', 'Mức độ']],
    body: [
      ['Stress trung bình',   `${formatDecimal(report.stress.avgScore, 1)}%`,  getStressLabel(report.stress.avgScore)],
      ['Stress cao nhất',     `${formatDecimal(report.stress.peakScore, 1)}%`, getStressLabel(report.stress.peakScore)],
      ['Stress thấp nhất',    `${formatDecimal(report.stress.minScore, 1)}%`,  getStressLabel(report.stress.minScore)],
      ['Vùng trán TB',        formatDecimal(report.stress.avgForeheadScore, 1), ''],
      ['Vùng hàm TB',         formatDecimal(report.stress.avgJawScore, 1),      ''],
      ['Vùng quanh mắt TB',   formatDecimal(report.stress.avgPeriocularScore, 1), ''],
    ],
    styles: { font: PDF_FONT, fontSize: 10 },
    headStyles: { fillColor: [239, 68, 68] },
    alternateRowStyles: { fillColor: [255, 245, 245] },
    margin: { left: 14, right: 14 },
  });

  // ===== 4. Cảm xúc =====
  const y4 = (doc as any).lastAutoTable.finalY + 10;
  doc.setFontSize(13);
  doc.setFont(PDF_FONT, 'bold');
  doc.text('4. Phân Bố Cảm Xúc', 14, y4);

  const emotionRows = (Object.entries(report.emotion.distribution) as [EmotionLabel, number][])
    .sort((a, b) => b[1] - a[1])
    .map(([label, pct]: [EmotionLabel, number]) => [
      EMOTION_LABELS_VI[label] ?? label,
      `${formatDecimal(pct, 1)}%`,
      label === report.emotion.dominant ? '⭐ Chủ đạo' : '',
    ]);

  autoTable(doc, {
    startY: y4 + 4,
    head: [['Cảm xúc', 'Tỉ lệ', 'Engine', 'Ghi chú']],
    body: emotionRows.map((row) => [
      row[0],
      row[1],
      report.emotion.engine ?? 'EmotiEff',
      row[2],
    ]),
    styles: { font: PDF_FONT, fontSize: 10 },
    headStyles: { fillColor: [34, 197, 94] },
    alternateRowStyles: { fillColor: [245, 255, 245] },
    margin: { left: 14, right: 14 },
  });

  // ===== 5. Cảnh báo =====
  const auFacs = report.auFacs;
  const yAuFacs = (doc as any).lastAutoTable.finalY + 10;
  doc.setFontSize(13);
  doc.setFont(PDF_FONT, 'bold');
  doc.text('5. AU/FACS', 14, yAuFacs);

  autoTable(doc, {
    startY: yAuFacs + 4,
    head: [['Metric', 'Value']],
    body: [
      ['Emotion engine', report.emotion.engine ?? 'EmotiEff'],
      ['AU/FACS engine', auFacs?.engine ?? 'AU/FACS'],
      ['Dominant FACS', auFacs?.dominantFacs ?? 'Binh thuong'],
      ['Active AUs', auFacs?.activeAus?.join(', ') || 'Khong co'],
      ...AU_REPORT_KEYS.map((key) => [
        `${key} average`,
        formatAuScore(auFacs?.avgAuScores?.[key]),
      ]),
    ],
    styles: { font: PDF_FONT, fontSize: 9 },
    headStyles: { fillColor: [79, 70, 229] },
    alternateRowStyles: { fillColor: [245, 245, 255] },
    margin: { left: 14, right: 14 },
  });
  const y5 = (doc as any).lastAutoTable.finalY + 10;
  doc.setFontSize(13);
  doc.setFont(PDF_FONT, 'bold');
  doc.text('6. Tổng Hợp Cảnh Báo', 14, y5);

  autoTable(doc, {
    startY: y5 + 4,
    head: [['Loại', 'Số lần']],
    body: [
      ['Tổng cảnh báo',     report.alerts.totalCount.toString()],
      ['Thông tin (info)',   report.alerts.bySeverity.info.toString()],
      ['Cảnh báo (warning)', report.alerts.bySeverity.warning.toString()],
      ['Nguy hiểm (critical)', report.alerts.bySeverity.critical.toString()],
    ],
    styles: { font: PDF_FONT, fontSize: 10 },
    headStyles: { fillColor: [245, 158, 11] },
    alternateRowStyles: { fillColor: [255, 251, 235] },
    margin: { left: 14, right: 14 },
  });

  // ===== Footer =====
  const pageCount = doc.getNumberOfPages();
  for (let i = 1; i <= pageCount; i++) {
    doc.setPage(i);
    doc.setFontSize(9);
    doc.setFont(PDF_FONT, 'normal');
    doc.text(
      `Trang ${i}/${pageCount} - Face Emotion Monitor`,
      pageWidth / 2,
      doc.internal.pageSize.getHeight() - 8,
      { align: 'center' }
    );
  }

  doc.save(`bao-cao-phien-hoc_${getTimestamp()}.pdf`);
  });
};

const formatAuScore = (score?: number): string =>
  `${formatDecimal((score ?? 0) * 100, 1)}%`;

const formatFacsStates = (states?: string[]): string =>
  states && states.length > 0 ? states.join('; ') : 'Binh thuong';

export const exportTimelineCSV = (
  report: SessionReport,
  filename?: string
): void => {
  if (report.timeline.length === 0) return;

  const headers = [
    'Thời gian',
    'Giây từ đầu phiên',
    'Stress Score',
    'Blink Rate (lần/phút)',
    'EAR trung bình',
    'Cảm xúc',
    'Mức tập trung',
  ];

  headers.splice(headers.length - 1, 0, 'Emotion engine', 'FACS states', ...AU_REPORT_KEYS);

  const rows = report.timeline.map((point) => [
    formatDateTime(point.timestamp),
    point.elapsedSec.toString(),
    formatDecimal(point.stressScore, 1),
    formatDecimal(point.blinkRate, 1),
    formatDecimal(point.earAverage, 3),
    EMOTION_LABELS_VI[point.emotion] ?? point.emotion,
    point.emotionEngine ?? report.emotion.engine ?? 'EmotiEff',
    formatFacsStates(point.facsStates),
    ...AU_REPORT_KEYS.map((key) => formatDecimal(point.auScores?.[key] ?? 0, 4)),
    point.focusLevel,
  ]);

  const csvContent = [headers, ...rows]
    .map((row) => row.map((cell) => `"${cell}"`).join(','))
    .join('\n');

  const blob = new Blob(['\uFEFF' + csvContent], {
    type: 'text/csv;charset=utf-8;',
  });

  saveAs(blob, filename ?? `timeline_${getTimestamp()}.csv`);
};

export const exportEmotionHistoryCSV = (
  history: EmotionSnapshot[],
  filename?: string
): void => {
  if (history.length === 0) return;

  const headers = [
    'Thời gian',
    'Frame Index',
    'Cảm xúc chủ đạo',
    'Dominant Score (%)',
    ...EMOTION_LABELS.map((k) => EMOTION_LABELS_VI[k] ?? k),
  ];

  const rows = history.map((snap) => {
    const scoreMap: Record<string, number> = {};
    snap.result.scores.forEach((s) => {
      scoreMap[s.label] = s.percentage;
    });

    return [
      formatDateTime(snap.timestamp),
      snap.frameIndex.toString(),
      EMOTION_LABELS_VI[snap.result.dominant] ?? snap.result.dominant,
      formatDecimal(snap.result.dominantScore * 100, 1),
      ...EMOTION_LABELS.map((k) => formatDecimal(scoreMap[k] ?? 0, 1)),
    ];
  });

  const csvContent = [headers, ...rows]
    .map((row) => row.map((cell) => `"${cell}"`).join(','))
    .join('\n');

  const blob = new Blob(['\uFEFF' + csvContent], {
    type: 'text/csv;charset=utf-8;',
  });

  saveAs(blob, filename ?? `emotion-history_${getTimestamp()}.csv`);
};

export const exportFaceFeaturesCSV = (
  features: FaceFeatures[],
  filename?: string
): void => {
  if (features.length === 0) return;

  const headers = [
    'Thời gian',
    'Processing (ms)',
    'EAR trái',
    'EAR phải',
    'EAR trung bình',
    'Đang nháy mắt',
    'Blink Rate (lần/phút)',
    'Blink Category',
    'MAR',
    'Trạng thái miệng',
    'Nhíu mày',
    'Stress tổng',
    'Stress trán',
    'Stress hàm',
    'Stress quanh mắt',
    'Head Pitch',
    'Head Yaw',
    'Head Roll',
  ];

  const rows = features.map((f) => [
    formatDateTime(f.extractedAt),
    f.processingMs.toString(),
    formatDecimal(f.blink.ear.left, 3),
    formatDecimal(f.blink.ear.right, 3),
    formatDecimal(f.blink.ear.average, 3),
    f.blink.isBlinking ? 'Có' : 'Không',
    formatDecimal(f.blink.ratePerMinute, 1),
    f.blink.rateCategory,
    formatDecimal(f.mouth.mar.value, 3),
    f.mouth.state,
    f.brow.furrowLevel,
    formatDecimal(f.tension.overallScore, 1),
    formatDecimal(f.tension.foreheadScore, 1),
    formatDecimal(f.tension.jawScore, 1),
    formatDecimal(f.tension.periocularScore, 1),
    formatDecimal(f.headPose.pitch, 1),
    formatDecimal(f.headPose.yaw, 1),
    formatDecimal(f.headPose.roll, 1),
  ]);

  const csvContent = [headers, ...rows]
    .map((row) => row.map((cell) => `"${cell}"`).join(','))
    .join('\n');

  const blob = new Blob(['\uFEFF' + csvContent], {
    type: 'text/csv;charset=utf-8;',
  });

  saveAs(blob, filename ?? `face-features_${getTimestamp()}.csv`);
};

export const exportSessionDataJSON = (
  data: {
    report: SessionReport;
    features?: FaceFeatures[];
    emotionHistory?: EmotionSnapshot[];
  },
  filename?: string
): void => {
  const json = JSON.stringify(data, null, 2);
  const blob = new Blob([json], { type: 'application/json;charset=utf-8;' });
  saveAs(blob, filename ?? `session-data_${getTimestamp()}.json`);
};

export const exportByOptions = (
  report: SessionReport,
  options: ReportExportOptions,
  extras?: {
    features?: FaceFeatures[];
    emotionHistory?: EmotionSnapshot[];
  }
): void => {
  const filename = options.filename;

  switch (options.format) {
    case 'pdf':
      exportSessionReportPDF(report, filename);
      break;

    case 'csv':
      if (options.includeTimeline) {
        exportTimelineCSV(report, filename);
      }
      if (extras?.emotionHistory) {
        exportEmotionHistoryCSV(extras.emotionHistory, filename);
      }
      if (extras?.features) {
        exportFaceFeaturesCSV(extras.features, filename);
      }
      break;

    case 'json':
      exportSessionDataJSON(
        {
          report,
          features: extras?.features,
          emotionHistory: extras?.emotionHistory,
        },
        filename
      );
      break;
  }
};

export const generateExportFilename = (
  prefix: string,
  ext: ReportExportFormat
): string => `${prefix}_${getTimestamp()}.${ext}`;
