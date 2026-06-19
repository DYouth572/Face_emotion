import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { clsx } from 'clsx';
import {
  ChevronRight,
  FileDown,
  History,
  Loader2,
  RefreshCcw,
  Trash2,
} from 'lucide-react';
import Card from '@/components/common/Card';
import Button from '@/components/common/Button';
import { deleteAllSessions, deleteSession, getSessions } from '@/api/sessionApi';
import { formatBlinkRate, formatDateTime, formatDuration } from '@/utils/formatters';
import { getEmotionEmoji, getEmotionLabelVI } from '@/utils/emotionHelpers';
import { classifyStress } from '@/utils/statisticsUtils';
import type { EmotionLabel } from '@/types/emotion.types';
import type { SessionSummary as ApiSessionSummary } from '@/types/session.types';

type HistorySession = ApiSessionSummary & {
  dominantEmotion: EmotionLabel;
};

const MODE_LABELS: Record<string, string> = {
  websocket: 'Theo dõi thời gian thực',
  mode5_au_facs: 'Phân tích AU/FACS',
  mode6_emotion: 'Nhận diện cảm xúc',
};

const FACS_LABELS: Record<string, string> = {
  'Binh thuong': 'Bình thường',
  'Vui ve: AU6 + AU12': 'Vui vẻ: AU6 + AU12',
  'Buon: AU1 + AU4 + AU15': 'Buồn: AU1 + AU4 + AU15',
  'Tuc gian: AU4 + AU5/AU7/AU23': 'Tức giận: AU4 + AU5/AU7/AU23',
  'Ngac nhien: AU1 + AU2 + AU5 + AU26': 'Ngạc nhiên: AU1 + AU2 + AU5 + AU26',
  'So hai: AU1 + AU2 + AU4 + AU20/AU25/AU26': 'Sợ hãi: AU1 + AU2 + AU4 + AU20/AU25/AU26',
  'Ghe tom: AU9/AU10': 'Ghê tởm: AU9/AU10',
};

const getModeLabel = (mode?: string) => {
  if (!mode) return 'Không rõ chế độ';
  return MODE_LABELS[mode] ?? mode;
};

const getFacsLabel = (value?: string) => {
  if (!value) return 'Bình thường';
  return value
    .split(',')
    .map((item) => {
      const trimmed = item.trim();
      return FACS_LABELS[trimmed] ?? trimmed;
    })
    .join(', ');
};

export default function HistoryPage() {
  const [sessions, setSessions] = useState<HistorySession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const navigate = useNavigate();

  const fetchSessions = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await getSessions();
      if (res.success) {
        setSessions(res.data.items as HistorySession[]);
      } else {
        setError('Backend không trả về dữ liệu lịch sử hợp lệ.');
      }
    } catch (err) {
      console.error('Không tải được danh sách phiên:', err);
      setError('Không kết nối được backend tại localhost:8000. Hãy chạy backend rồi bấm Tải lại.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSessions();
  }, []);

  useEffect(() => {
    const handleFocus = () => fetchSessions();
    window.addEventListener('focus', handleFocus);
    return () => window.removeEventListener('focus', handleFocus);
  }, []);

  const handleDeleteAll = async () => {
    if (!window.confirm('Xóa tất cả lịch sử phiên học?')) return;

    try {
      await deleteAllSessions();
      setSessions([]);
      setSelected(null);
    } catch {
      alert('Không thể xóa lịch sử phiên học.');
    }
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm('Xóa phiên học này?')) return;

    try {
      await deleteSession(id);
      setSessions((prev) => prev.filter((s) => s.sessionId !== id));
      if (selected === id) setSelected(null);
    } catch {
      alert('Không thể xóa phiên học.');
    }
  };

  return (
    <div className="flex flex-col gap-5 p-5 overflow-y-auto">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-gray-100">Lịch sử phiên học</h1>
          <p className="text-sm text-gray-400 mt-0.5">
            {loading ? 'Đang tải...' : `${sessions.length} phiên đã ghi nhận`}
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="ghost"
            size="sm"
            leftIcon={<RefreshCcw size={14} />}
            onClick={fetchSessions}
            disabled={loading}
          >
            Tải lại
          </Button>
          <Button
            variant="ghost"
            size="sm"
            leftIcon={<Trash2 size={14} />}
            onClick={handleDeleteAll}
            disabled={loading || sessions.length === 0}
          >
            Xóa tất cả
          </Button>
        </div>
      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center py-20 text-indigo-400">
          <Loader2 size={40} className="animate-spin mb-3" />
          <p>Đang tải dữ liệu...</p>
        </div>
      ) : error ? (
        <Card>
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <History size={48} className="mb-3 text-red-400" />
            <p className="text-base font-medium text-gray-100">Không tải được lịch sử phiên</p>
            <p className="mt-1 max-w-md text-sm text-gray-400">{error}</p>
            <Button
              className="mt-4"
              variant="secondary"
              size="sm"
              leftIcon={<RefreshCcw size={14} />}
              onClick={fetchSessions}
            >
              Tải lại
            </Button>
          </div>
        </Card>
      ) : sessions.length > 0 ? (
        <div className="space-y-3">
          {sessions.map((session) => {
            const stressClass = classifyStress(session.avgStressScore / 100);
            const isSelected = selected === session.sessionId;
            const facsLabel = getFacsLabel(session.facsSummary);

            return (
              <Card
                key={session.sessionId}
                className={clsx(
                  'cursor-pointer transition-all',
                  isSelected ? 'border-indigo-600/50 bg-indigo-950/20' : 'hover:border-gray-700'
                )}
              >
                <div
                  className="flex items-center gap-4"
                  onClick={() => setSelected(isSelected ? null : session.sessionId)}
                >
                  <div className="text-3xl shrink-0">
                    {getEmotionEmoji(session.dominantEmotion)}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-sm font-semibold text-gray-100">
                        {formatDateTime(session.startedAt)}
                      </p>
                      <span
                        className={clsx(
                          'text-xs px-2 py-0.5 rounded-full',
                          stressClass === 'low'
                            ? 'bg-green-950 text-green-400'
                            : stressClass === 'medium'
                              ? 'bg-yellow-950 text-yellow-400'
                              : 'bg-red-950 text-red-400'
                        )}
                      >
                        Độ căng thẳng: {session.avgStressScore.toFixed(0)}%
                      </span>
                      <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-300">
                        {getModeLabel(session.mode)}
                      </span>
                    </div>
                    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-1 text-xs text-gray-400">
                      <span>{formatDuration(session.durationMs)}</span>
                      <span>{session.totalBlinks} lần nháy</span>
                      <span>{formatBlinkRate(session.avgBlinkRate)}</span>
                      <span>{getEmotionLabelVI(session.dominantEmotion)}</span>
                      <span>FACS: {facsLabel}</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <Button
                      size="sm"
                      variant="secondary"
                      leftIcon={<FileDown size={14} />}
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/report/${session.sessionId}`);
                      }}
                    >
                      Báo cáo
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      leftIcon={<Trash2 size={14} />}
                      onClick={(e) => handleDelete(session.sessionId, e)}
                    >
                      Xóa
                    </Button>
                    <ChevronRight
                      size={16}
                      className={clsx(
                        'text-gray-500 transition-transform',
                        isSelected && 'rotate-90'
                      )}
                    />
                  </div>
                </div>

                {isSelected && (
                  <div className="mt-4 pt-4 border-t border-gray-800 grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div>
                      <p className="text-xs text-gray-400">Mã phiên</p>
                      <p className="text-sm font-semibold text-gray-100 mt-1">
                        {session.sessionCode ?? `Phiên ${session.sessionId}`}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-400">Thời lượng</p>
                      <p className="text-sm font-semibold text-gray-100 mt-1">
                        {formatDuration(session.durationMs)}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-400">Cảm xúc chủ đạo</p>
                      <p className="text-sm font-semibold text-gray-100 mt-1">
                        {getEmotionEmoji(session.dominantEmotion)} {getEmotionLabelVI(session.dominantEmotion)}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-400">Trạng thái FACS</p>
                      <p className="text-sm font-semibold text-gray-100 mt-1">
                        {facsLabel}
                      </p>
                    </div>
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      ) : (
        <Card>
          <div className="flex flex-col items-center justify-center py-16 text-gray-500">
            <History size={48} className="mb-3" />
            <p className="text-base font-medium">Chưa có phiên học nào</p>
            <p className="text-sm mt-1">Bắt đầu một phiên học từ bảng điều khiển</p>
          </div>
        </Card>
      )}
    </div>
  );
}
