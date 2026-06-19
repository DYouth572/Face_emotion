import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { BarChart2, Clock, FileDown, Loader2 } from 'lucide-react';
import Card from '@/components/common/Card';
import Button from '@/components/common/Button';
import ProgressBar from '@/components/common/ProgressBar';
import { exportSessionReport as exportBackendReport, getSessionReport } from '@/api/reportApi';
import { useEmotionStore } from '@/store/useEmotionStore';
import { useFeatureStore } from '@/store/useFeatureStore';
import { useSessionStore } from '@/store/useSessionStore';
import { exportFaceFeaturesCSV, exportSessionReportPDF } from '@/utils/exportUtils';
import { formatDateTime, formatDuration } from '@/utils/formatters';
import { getEmotionIcon, getEmotionLabelVI } from '@/utils/emotionHelpers';
import { calcEmotionDistribution } from '@/utils/statisticsUtils';
import type { EmotionLabel } from '@/types/emotion.types';
import type { FaceFeatures } from '@/types/feature.types';
import type { SessionReport } from '@/types/report.types';
import type { AuKey } from '@/types/websocket.types';

const AU_DEFINITIONS: Array<{
  key: AuKey;
  title: string;
  name: string;
  description: string;
}> = [
  { key: 'AU1', title: 'AU1 - Nâng chân mày trong', name: 'Inner Brow Raiser', description: 'Nâng vùng chân mày giữa và trán.' },
  { key: 'AU2', title: 'AU2 - Nâng chân mày ngoài', name: 'Outer Brow Raiser', description: 'Nâng vùng chân mày ngoài và trán bên.' },
  { key: 'AU4', title: 'AU4 - Nhíu mày', name: 'Brow Lowerer', description: 'Hạ chân mày, liên quan đến nhíu mày hoặc căng thẳng.' },
  { key: 'AU5', title: 'AU5 - Mở mí trên', name: 'Upper Lid Raiser', description: 'Kéo mí trên lên làm mắt mở rộng.' },
  { key: 'AU6', title: 'AU6 - Nâng gò má', name: 'Cheek Raiser', description: 'Siết vùng quanh mắt ngoài và nâng gò má.' },
  { key: 'AU7', title: 'AU7 - Siết mí mắt', name: 'Lid Tightener', description: 'Siết vòng cơ quanh mí mắt.' },
  { key: 'AU9', title: 'AU9 - Nhăn mũi', name: 'Nose Wrinkler', description: 'Co vùng mũi, làm sống mũi hoặc đầu mũi nhăn lại.' },
  { key: 'AU10', title: 'AU10 - Nâng môi trên', name: 'Upper Lip Raiser', description: 'Nâng môi trên, thường xuất hiện trong biểu cảm ghê tởm.' },
  { key: 'AU12', title: 'AU12 - Cười', name: 'Lip Corner Puller', description: 'Kéo khóe môi lên, ra sau và sang hai bên.' },
  { key: 'AU15', title: 'AU15 - Hạ khóe môi', name: 'Lip Corner Depressor', description: 'Kéo khóe môi xuống.' },
  { key: 'AU20', title: 'AU20 - Kéo căng môi', name: 'Lip Stretcher', description: 'Kéo khóe môi sang ngang, làm môi căng.' },
  { key: 'AU23', title: 'AU23 - Siết môi', name: 'Lip Tightener', description: 'Làm môi mỏng lại do siết chặt.' },
  { key: 'AU25', title: 'AU25 - Mở miệng', name: 'Lips Part', description: 'Hai môi tách nhau, liên quan đến nói hoặc ngáp.' },
  { key: 'AU26', title: 'AU26 - Hạ hàm', name: 'Jaw Drop', description: 'Hạ hàm dưới một cách thả lỏng.' },
];

const EMOTION_AU_MAP: Record<EmotionLabel, { aus: string[]; note: string }> = {
  happy: { aus: ['AU6', 'AU12'], note: 'Nâng gò má kết hợp kéo khóe môi.' },
  sad: { aus: ['AU1', 'AU4', 'AU15'], note: 'Nâng chân mày trong, nhíu mày và hạ khóe môi.' },
  angry: { aus: ['AU4', 'AU5', 'AU7', 'AU23'], note: 'Nhíu mày, mở mí trên, siết mí và siết môi.' },
  surprise: { aus: ['AU1', 'AU2', 'AU5', 'AU26'], note: 'Nâng mày, mở mắt và hạ hàm.' },
  fear: { aus: ['AU1', 'AU2', 'AU4', 'AU5', 'AU20', 'AU25/AU26'], note: 'Nâng mày, nhíu mày, mở mắt, kéo căng môi và mở miệng.' },
  disgust: { aus: ['AU9', 'AU10'], note: 'Nhăn mũi và nâng môi trên.' },
  neutral: { aus: [], note: 'Không có AU nào kích hoạt nổi bật.' },
};

const formatAuScore = (score?: number) => `${Math.round((score ?? 0) * 100)}%`;

function countBlinkEvents(features: FaceFeatures[]): number {
  let total = 0;
  let wasBlinking = false;

  for (const feature of features) {
    const isBlinking = feature.blink.isBlinking;
    if (isBlinking && !wasBlinking) total += 1;
    wasBlinking = isBlinking;
  }

  return total;
}

function buildLiveReport(
  session: ReturnType<typeof useSessionStore.getState>['current'],
  elapsedMs: number,
  featureHistory: FaceFeatures[],
  emotionHistory: ReturnType<typeof useEmotionStore.getState>['history'],
  auScores: Partial<Record<AuKey, number>>,
  facsStates: string[]
): SessionReport | null {
  if (!session) return null;
  const startTime = session.startedAt;

  const emotionDist = calcEmotionDistribution(
    emotionHistory.map((snap) => snap.result.dominant)
  );
  const sortedEmotions = Object.entries(emotionDist)
    .sort((a, b) => b[1] - a[1]) as [EmotionLabel, number][];

  const stressValues = featureHistory.map((f) => f.tension.overallScore ?? 0);
  const avgStress = stressValues.length
    ? stressValues.reduce((sum, value) => sum + value, 0) / stressValues.length
    : 0;
  const avgEAR = featureHistory.length
    ? featureHistory.reduce((sum, f) => sum + f.blink.ear.average, 0) / featureHistory.length
    : 0;
  const blinkCount = countBlinkEvents(featureHistory);
  const blinkRate = elapsedMs > 0 ? blinkCount / (elapsedMs / 60000) : 0;

  return {
    reportId: `live_report_${startTime}`,
    sessionId: session.sessionId,
    generatedAt: Date.now(),
    overview: {
      startedAt: startTime,
      endedAt: session.endedAt ?? Date.now(),
      durationMs: session.endedAt ? session.endedAt - startTime : elapsedMs,
      totalFrames: featureHistory.length,
      averageFps: session.averageFps ?? 0,
      faceDetectedFrames: featureHistory.filter((f) => f.boundingBox !== null).length,
      faceDetectionRate: featureHistory.length
        ? featureHistory.filter((f) => f.boundingBox !== null).length / featureHistory.length
        : 0,
    },
    emotion: {
      dominant: sortedEmotions[0]?.[0] ?? 'neutral',
      engine: 'EmotiEff',
      distribution: Object.fromEntries(
        Object.entries(emotionDist).map(([label, ratio]) => [label, ratio * 100])
      ) as Record<EmotionLabel, number>,
      avgConfidence: 0,
      transitionCount: 0,
    },
    auFacs: {
      engine: 'AU/FACS',
      avgAuScores: auScores,
      activeAus: AU_DEFINITIONS
        .map((item) => item.key)
        .filter((key) => (auScores[key] ?? 0) >= 0.35),
      dominantFacs: facsStates[0] ?? 'Binh thuong',
      facsDistribution: Object.fromEntries(
        facsStates.map((state) => [state, facsStates.length ? 100 / facsStates.length : 0])
      ),
    },
    blink: {
      totalBlinks: blinkCount,
      avgRatePerMin: blinkRate,
      minRatePerMin: 0,
      maxRatePerMin: 0,
      avgEar: avgEAR,
      longNoBlinkMs: 0,
    },
    stress: {
      avgScore: avgStress,
      peakScore: stressValues.length ? Math.max(...stressValues) : 0,
      minScore: stressValues.length ? Math.min(...stressValues) : 0,
      highStressMs: 0,
      criticalStressMs: 0,
      avgForeheadScore: featureHistory.length
        ? featureHistory.reduce((sum, f) => sum + f.tension.foreheadScore, 0) / featureHistory.length
        : 0,
      avgJawScore: featureHistory.length
        ? featureHistory.reduce((sum, f) => sum + f.tension.jawScore, 0) / featureHistory.length
        : 0,
      avgPeriocularScore: featureHistory.length
        ? featureHistory.reduce((sum, f) => sum + f.tension.periocularScore, 0) / featureHistory.length
        : 0,
    },
    focus: {
      distribution: { high: 0, medium: 0, low: 0 },
      highFocusMs: 0,
      lowFocusMs: 0,
    },
    alerts: {
      totalCount: 0,
      byType: {},
      bySeverity: { info: 0, warning: 0, critical: 0 },
    },
    timeline: [],
  };
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export default function ReportPage() {
  const { sessionId } = useParams();
  const { current: session, elapsedMs } = useSessionStore();
  const { history: featureHistory } = useFeatureStore();
  const auScores = useFeatureStore((s) => s.auScores);
  const facsStates = useFeatureStore((s) => s.facsStates);
  const { history: emotionHistory } = useEmotionStore();
  const [savedReport, setSavedReport] = useState<SessionReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    if (!sessionId) {
      setSavedReport(null);
      setError(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    getSessionReport(sessionId)
      .then((res) => {
        if (!cancelled) setSavedReport(res.data);
      })
      .catch((err) => {
        console.error('Failed to fetch report:', err);
        if (!cancelled) setError('Không tải được báo cáo từ backend.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  const liveReport = useMemo(
    () => buildLiveReport(session, elapsedMs, featureHistory, emotionHistory, auScores, facsStates),
    [session, elapsedMs, featureHistory, emotionHistory, auScores, facsStates]
  );
  const report = sessionId ? savedReport : liveReport;
  const dominantAu = report ? EMOTION_AU_MAP[report.emotion.dominant] : null;
  const hasAuScores = AU_DEFINITIONS.some(({ key }) => typeof auScores[key] === 'number');

  const emotionEntries = report
    ? (Object.entries(report.emotion.distribution)
        .sort((a, b) => b[1] - a[1]) as [EmotionLabel, number][])
    : [];
  const emotionDistributionSubtitle = report
    ? `Tỉ lệ các cảm xúc trong phiên phân tích kéo dài ${formatDuration(
        report.overview.durationMs
      )}, từ ${formatDateTime(report.overview.startedAt)} đến ${formatDateTime(
        report.overview.endedAt
      )}`
    : 'Tỉ lệ các cảm xúc trong phiên phân tích.';

  const handleExportPDF = async () => {
    if (!report) return;
    setExporting(true);
    try {
      await exportSessionReportPDF(report);
    } finally {
      setExporting(false);
    }
  };

  const handleExportCSV = async () => {
    if (sessionId) {
      const blob = await exportBackendReport(sessionId, 'csv');
      downloadBlob(blob, `report_${sessionId}.csv`);
      return;
    }

    exportFaceFeaturesCSV(featureHistory);
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-indigo-400">
        <Loader2 size={40} className="animate-spin mb-3" />
        <p>Đang tải báo cáo...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col gap-4 p-5">
        <Card>
          <div className="py-12 text-center text-gray-400">{error}</div>
        </Card>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="flex flex-col gap-4 p-5">
        <Card>
          <div className="py-12 text-center text-gray-400">
            Chưa có dữ liệu báo cáo. Hãy bắt đầu một phiên phân tích hoặc mở báo cáo từ lịch sử.
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-5 p-5 overflow-y-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-100">
            Báo cáo thống kê
          </h1>
          <p className="text-sm text-gray-400 mt-0.5">
            Bắt đầu: {formatDateTime(report.overview.startedAt)}
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="secondary"
            size="sm"
            leftIcon={<FileDown size={14} />}
            onClick={handleExportCSV}
            disabled={report.overview.totalFrames === 0}
          >
            Xuất CSV
          </Button>
          <Button
            variant="primary"
            size="sm"
            leftIcon={<FileDown size={14} />}
            onClick={handleExportPDF}
            loading={exporting}
          >
            Xuất PDF
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card title="Thời gian">
          <div className="flex items-center gap-2">
            <Clock size={20} className="text-indigo-400" />
            <span className="text-lg font-bold text-gray-100">
              {formatDuration(report.overview.durationMs)}
            </span>
          </div>
        </Card>
      </div>

      <Card title="Phân bố cảm xúc" subtitle={emotionDistributionSubtitle}>
        {emotionEntries.length > 0 ? (
          <div className="space-y-3">
            {emotionEntries.map(([label, percentage]) => (
              <div key={label} className="flex items-center gap-3">
                <span className="text-lg">{getEmotionIcon(label)}</span>
                <span className="text-sm text-gray-300 w-24 shrink-0">
                  {getEmotionLabelVI(label)}
                </span>
                <ProgressBar value={percentage} size="sm" className="flex-1" />
                <span className="text-sm text-gray-400 w-12 text-right">
                  {percentage.toFixed(1)}%
                </span>
              </div>
            ))}
          </div>
        ) : (
          <div className="flex items-center justify-center py-8 text-gray-500">
            <BarChart2 size={32} className="mr-2" />
            <p>Chưa có dữ liệu cảm xúc</p>
          </div>
        )}
      </Card>

      <Card
        title="Chỉ số AU/FACS"
        subtitle={
          sessionId
            ? 'Báo cáo đã lưu hiển thị nhóm AU liên quan đến cảm xúc chủ đạo; điểm AU realtime chỉ có khi phiên đang chạy.'
            : 'Điểm AU được cập nhật từ khung hình realtime mới nhất của phiên hiện tại.'
        }
      >
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
          <div className="xl:col-span-2 space-y-3">
            {AU_DEFINITIONS.map((item) => {
              const score = auScores[item.key] ?? 0;
              return (
                <div key={item.key} className="rounded-lg border border-gray-800 bg-gray-900/40 p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-gray-100">{item.title}</p>
                      <p className="text-xs text-gray-400">{item.name}</p>
                    </div>
                    <span className="text-sm font-semibold text-indigo-300">
                      {hasAuScores ? formatAuScore(score) : 'Chưa có'}
                    </span>
                  </div>
                  <p className="mt-2 text-xs text-gray-400">{item.description}</p>
                  <ProgressBar value={hasAuScores ? score * 100 : 0} size="sm" className="mt-3" />
                </div>
              );
            })}
          </div>

          <div className="space-y-4">
            <div className="rounded-lg border border-gray-800 bg-gray-900/40 p-4">
              <p className="text-sm font-semibold text-gray-100">AU theo cảm xúc chủ đạo</p>
              <p className="mt-1 text-sm text-gray-300">
                {report.emotion.dominant
                  ? `${getEmotionLabelVI(report.emotion.dominant)}: ${
                      dominantAu?.aus.length ? dominantAu.aus.join(', ') : 'Không có AU nổi bật'
                    }`
                  : 'Chưa xác định'}
              </p>
              <p className="mt-2 text-xs text-gray-400">{dominantAu?.note}</p>
            </div>

            <div className="rounded-lg border border-gray-800 bg-gray-900/40 p-4">
              <p className="text-sm font-semibold text-gray-100">Trạng thái FACS</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {facsStates.map((state, index) => (
                  <span
                    key={`${state}-${index}`}
                    className="rounded-full bg-indigo-950/60 px-3 py-1 text-xs text-indigo-200"
                  >
                    {state}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </Card>

    </div>
  );
}
