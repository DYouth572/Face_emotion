import { useRef, useState, useEffect } from 'react';
import { useFeatureStore } from '@/store/useFeatureStore';
import { useEmotionStore } from '@/store/useEmotionStore';
import { useSession } from '@/hooks/useSession';
import { websocketService } from '@/services/websocketService';
import Card from '@/components/common/Card';
import Button from '@/components/common/Button';
import ProgressBar from '@/components/common/ProgressBar';
import { formatDurationShort } from '@/utils/formatters';
import {
  getEmotionEmoji,
  getEmotionLabelVI,
  getEmotionColor,
} from '@/utils/emotionHelpers';
import {
  Camera, CameraOff, Play, Square,
  Brain,
} from 'lucide-react';
import { clsx } from 'clsx';
import type { EmotionLabel } from '@/types/emotion.types';

type AuKey = 'AU1' | 'AU2' | 'AU4' | 'AU5' | 'AU6' | 'AU7' | 'AU9' | 'AU10' | 'AU12' | 'AU15' | 'AU20' | 'AU23' | 'AU25' | 'AU26';

const AU_DEFINITIONS: Array<{
  key: AuKey;
  title: string;
  name: string;
  description: string;
}> = [
  { key: 'AU1', title: 'AU1 - Nâng chân mày trong', name: 'Inner Brow Raiser', description: 'Nâng vùng chân mày giữa và trán.' },
  { key: 'AU2', title: 'AU2 - Nâng chân mày ngoài', name: 'Outer Brow Raiser', description: 'Nâng vùng chân mày ngoài và trán bên.' },
  { key: 'AU4', title: 'AU4 - Nhíu mày', name: 'Brow Lowerer', description: 'Hạ chân mày, liên quan đến nhíu mày/căng thẳng.' },
  { key: 'AU5', title: 'AU5 - Mở mí trên', name: 'Upper Lid Raiser', description: 'Kéo mí trên lên làm mắt mở rộng.' },
  { key: 'AU6', title: 'AU6 - Nâng gò má', name: 'Cheek Raiser', description: 'Siết vùng quanh mắt ngoài và nâng gò má.' },
  { key: 'AU7', title: 'AU7 - Siết mí mắt', name: 'Lid Tightener', description: 'Siết vòng cơ quanh mí mắt.' },
  { key: 'AU9', title: 'AU9 - Nhăn mũi', name: 'Nose Wrinkler', description: 'Co vùng mũi, làm sống mũi/đầu mũi nhăn lại.' },
  { key: 'AU10', title: 'AU10 - Nâng môi trên', name: 'Upper Lip Raiser', description: 'Nâng môi trên, thường xuất hiện trong biểu cảm ghê tởm.' },
  { key: 'AU12', title: 'AU12 - Cười', name: 'Lip Corner Puller', description: 'Kéo khóe môi lên, ra sau và sang hai bên.' },
  { key: 'AU15', title: 'AU15 - Hạ khóe môi', name: 'Lip Corner Depressor', description: 'Kéo khóe môi xuống.' },
  { key: 'AU20', title: 'AU20 - Kéo căng môi', name: 'Lip Stretcher', description: 'Kéo khóe môi sang ngang, làm môi căng.' },
  { key: 'AU23', title: 'AU23 - Siết môi', name: 'Lip Tightener', description: 'Làm môi mỏng lại do siết chặt.' },
  { key: 'AU25', title: 'AU25 - Mở miệng', name: 'Lips Part', description: 'Hai môi tách nhau, liên quan nói/ngáp.' },
  { key: 'AU26', title: 'AU26 - Hạ hàm', name: 'Jaw Drop', description: 'Hạ hàm dưới một cách thả lỏng.' },
];

const EMOTION_AU_GROUPS = [
  { emotion: 'Happy', vi: 'Hạnh phúc', aus: ['AU6', 'AU12'], note: 'Nâng gò má + kéo khóe môi.' },
  { emotion: 'Sad', vi: 'Buồn bã', aus: ['AU1', 'AU4', 'AU15'], note: 'Nâng chân mày trong + nhíu mày + hạ khóe môi.' },
  { emotion: 'Angry', vi: 'Giận dữ', aus: ['AU4', 'AU5', 'AU7', 'AU23'], note: 'Nhíu mày + mở mí trên + siết mí + siết môi.' },
  { emotion: 'Surprise', vi: 'Ngạc nhiên', aus: ['AU1', 'AU2', 'AU5', 'AU26'], note: 'Nâng mày + mở mắt + hạ hàm.' },
  { emotion: 'Fear', vi: 'Sợ hãi', aus: ['AU1', 'AU2', 'AU4', 'AU5', 'AU20', 'AU25/AU26'], note: 'Nâng mày, nhíu mày, mở mắt, kéo căng môi và mở miệng.' },
  { emotion: 'Disgust', vi: 'Ghê tởm', aus: ['AU9', 'AU10'], note: 'Nhăn mũi và nâng môi trên.' },
  { emotion: 'Neutral', vi: 'Bình thường', aus: [], note: 'Không có AU nào kích hoạt mạnh.' },
];

export default function DashboardPage() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const animationFrameRef = useRef<number | null>(null);
  const frameTimeoutRef = useRef<number | null>(null);
  const awaitingFrameResultRef = useRef(false);
  const lastFrameSentAtRef = useRef(0);
  const [cameraOn, setCameraOn] = useState(false);
  const [autoStartRequested, setAutoStartRequested] = useState(false);
  const [videoDims, setVideoDims] = useState({ width: 640, height: 480 });

  // ✅ Fix: dùng đúng fields từ SessionStore mới
  const { isActive, elapsedMs, startSession, stopSession } = useSession();

  // ✅ Fix: useFeatureStore không có blinkRate trực tiếp
  const feature = useFeatureStore((s) => s.current);
  const auScores = useFeatureStore((s) => s.auScores);
  const facsStates = useFeatureStore((s) => s.facsStates);

  // ✅ Fix: useEmotionStore mới dùng current: EmotionResult | null
  const emotionResult = useEmotionStore((s) => s.current);
  const currentEmotion = emotionResult?.dominant ?? null;

  // ===== Camera =====
  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        setCameraOn(true);
        setAutoStartRequested(true);
      }
    } catch {
      console.error('Không thể truy cập camera');
    }
  };

  const stopCamera = () => {
    if (isActive) {
      stopSession();
    }
    setAutoStartRequested(false);
    const stream = videoRef.current?.srcObject as MediaStream;
    stream?.getTracks().forEach((t) => t.stop());
    if (videoRef.current) videoRef.current.srcObject = null;
    setCameraOn(false);
    awaitingFrameResultRef.current = false;
  };

  const handleLoadedMetadata = () => {
    if (videoRef.current) {
      setVideoDims({
        width: videoRef.current.videoWidth || 640,
        height: videoRef.current.videoHeight || 480,
      });
    }
  };

  // ===== Session toggle =====

  const handleToggleSession = () => {
    if (isActive) {
      setAutoStartRequested(false);
      stopSession();
    } else if (cameraOn) {
      setAutoStartRequested(false);
      startSession();
    } else {
      startCamera();
    }
  };

  useEffect(() => {
    if (!cameraOn || isActive || !autoStartRequested) return;
    const video = videoRef.current;
    if (!video || video.readyState < HTMLMediaElement.HAVE_METADATA) return;

    setAutoStartRequested(false);
    startSession();
  }, [autoStartRequested, cameraOn, isActive, startSession, videoDims.width, videoDims.height]);

  useEffect(() => {
    if (!isActive || !cameraOn || !videoRef.current) return;

    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const sendFrame = (timestamp: number) => {
      const video = videoRef.current;
      const shouldSend =
        video &&
        video.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA &&
        !awaitingFrameResultRef.current &&
        timestamp - lastFrameSentAtRef.current >= 100;

      if (shouldSend) {
        const width = video.videoWidth || 640;
        const height = video.videoHeight || 480;
        canvas.width = width;
        canvas.height = height;
        ctx.drawImage(video, 0, 0, width, height);

        awaitingFrameResultRef.current = true;
        lastFrameSentAtRef.current = timestamp;
        websocketService.sendVideoFrame(canvas.toDataURL('image/jpeg', 0.85), width, height);

        if (frameTimeoutRef.current) {
          window.clearTimeout(frameTimeoutRef.current);
        }
        frameTimeoutRef.current = window.setTimeout(() => {
          awaitingFrameResultRef.current = false;
        }, 1000);
      }

      animationFrameRef.current = window.requestAnimationFrame(sendFrame);
    };

    animationFrameRef.current = window.requestAnimationFrame(sendFrame);

    return () => {
      if (animationFrameRef.current) {
        window.cancelAnimationFrame(animationFrameRef.current);
        animationFrameRef.current = null;
      }
      if (frameTimeoutRef.current) {
        window.clearTimeout(frameTimeoutRef.current);
        frameTimeoutRef.current = null;
      }
      awaitingFrameResultRef.current = false;
    };
  }, [cameraOn, isActive]);

  useEffect(() => {
    const unsub = websocketService.onMessage((msg: any) => {
      if (msg.type !== 'frame_result') return;

      awaitingFrameResultRef.current = false;
      if (frameTimeoutRef.current) {
        window.clearTimeout(frameTimeoutRef.current);
        frameTimeoutRef.current = null;
      }

    });

    return () => unsub();
  }, []);

  const getAuPercent = (key: AuKey) => Math.round((auScores[key] ?? 0) * 100);

  return (
    <div className="flex flex-col gap-5 p-5 h-full overflow-y-auto">
      {/* ===== Top Row: Camera + Emotion ===== */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">

        {/* Camera Feed */}
        <div className="lg:col-span-2">
          <Card
            title="Camera"
            headerRight={
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant={cameraOn ? 'danger' : 'secondary'}
                  leftIcon={cameraOn ? <CameraOff size={14} /> : <Camera size={14} />}
                  onClick={cameraOn ? stopCamera : startCamera}
                >
                  {cameraOn ? 'Tắt' : 'Bật Camera'}
                </Button>
                <Button
                  size="sm"
                  variant={isActive ? 'danger' : 'primary'}
                  leftIcon={isActive ? <Square size={14} /> : <Play size={14} />}
                  onClick={handleToggleSession}
                >
                  {isActive ? 'Dừng' : 'Bắt đầu'}
                </Button>
              </div>
            }
            noPadding
          >
            <div className="relative aspect-video bg-gray-950 rounded-b-xl overflow-hidden">
              <video
                ref={videoRef}
                autoPlay
                muted
                playsInline
                onLoadedMetadata={handleLoadedMetadata}

                className="w-full h-full object-cover"
              />

              {/* Face Bounding Box Overlay */}
              {isActive && feature?.boundingBox && (
                <div
                  className="absolute border-2 border-green-400 rounded-lg pointer-events-none transition-all duration-150 ease-out z-10 shadow-[0_0_15px_rgba(74,222,128,0.3)]"
                  style={{
                    left: `${(feature.boundingBox.x / videoDims.width) * 100}%`,
                    top: `${(feature.boundingBox.y / videoDims.height) * 100}%`,
                    width: `${(feature.boundingBox.width / videoDims.width) * 100}%`,
                    height: `${(feature.boundingBox.height / videoDims.height) * 100}%`,
                  }}
                >
                  <div className="absolute -top-7 left-0 bg-green-400 text-gray-900 text-[10px] font-bold px-2 py-0.5 rounded-t-md whitespace-nowrap flex items-center gap-1.5 shadow-lg">
                    <span className="text-sm">{getEmotionEmoji(currentEmotion || 'neutral' as any)}</span>
                    <span className="uppercase tracking-wider">{getEmotionLabelVI(currentEmotion || 'neutral' as any)}</span>
                  </div>
                </div>
              )}

              {!cameraOn && (
                <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-gray-500">
                  <CameraOff size={48} />
                  <p className="text-sm">Camera chưa được bật</p>
                </div>
              )}
              {/* Session timer overlay */}
              {isActive && (
                <div className="absolute top-3 left-3 px-3 py-1.5 rounded-lg bg-black/60 text-green-400 text-sm font-mono">
                  ⏱ {formatDurationShort(elapsedMs)}
                </div>
              )}
            </div>
          </Card>
        </div>

        {/* Emotion Panel */}
        <div className="flex flex-col gap-4">
          <Card title="Cảm Xúc Hiện Tại">
            {currentEmotion ? (
              <div className="flex flex-col items-center gap-3 py-2">
                <span className="text-5xl">{getEmotionEmoji(currentEmotion)}</span>
                <span
                  className="text-lg font-bold"
                  style={{ color: getEmotionColor(currentEmotion) }}
                >
                  {getEmotionLabelVI(currentEmotion)}
                </span>

                {/* Emotion scores */}
                <div className="w-full space-y-1.5 mt-2">
                  {emotionResult?.scores
                    .slice()
                    .sort((a, b) => b.score - a.score)
                    .map((item) => (
                      <div key={item.label} className="flex items-center gap-2">
                        <span className="text-xs text-gray-400 w-20 shrink-0">
                          {getEmotionLabelVI(item.label as EmotionLabel)}
                        </span>
                        <ProgressBar
                          value={item.percentage}
                          max={100}
                          size="xs"
                          variant="default"
                          className="flex-1"
                        />
                        <span className="text-xs text-gray-400 w-10 text-right">
                          {item.percentage.toFixed(0)}%
                        </span>
                      </div>
                    ))}
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-2 py-6 text-gray-500">
                <Brain size={32} />
                <p className="text-sm">Chưa phát hiện cảm xúc</p>
              </div>
            )}
          </Card>
        </div>
      </div>

      {/* ===== AU / FACS ===== */}
      <div className="grid grid-cols-1 xl:grid-cols-4 gap-4">
        <div className="xl:col-span-3 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {AU_DEFINITIONS.map((au) => {
            const percent = getAuPercent(au.key);
            const active = percent > 50;

            return (
              <Card key={au.key} title={au.title}>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-3xl font-bold text-green-400">{percent}%</span>
                    <span
                      className={clsx(
                        'rounded-full px-3 py-1 text-sm',
                        active ? 'bg-red-500/20 text-red-300' :
                          'bg-gray-500/20 text-gray-300'
                      )}
                    >
                      {active ? 'Đang kích hoạt' : 'Thấp'}
                    </span>
                  </div>
                  <ProgressBar value={percent} />
                  <p className="text-sm font-medium text-gray-200">{au.name}</p>
                  <p className="text-sm text-gray-400">{au.description}</p>
                </div>
              </Card>
            );
          })}
        </div>

        <div className="space-y-4">
          <Card title="Trạng thái FACS">
            <div className="space-y-3">
              <div className="text-2xl font-bold text-purple-300">
                {facsStates[0] ?? 'Bình thường'}
              </div>
              <div className="space-y-2">
                {facsStates.map((state, index) => (
                  <div key={index} className="rounded-lg bg-slate-800 px-3 py-2 text-sm text-gray-200">
                    {state}
                  </div>
                ))}
              </div>
              <p className="text-sm text-gray-400">Suy luận từ các AU đang có trên frontend.</p>
            </div>
          </Card>

          <Card title="AU theo cảm xúc">
            <div className="space-y-3">
              {EMOTION_AU_GROUPS.map((group) => (
                <div key={group.emotion} className="rounded-lg bg-slate-800 px-3 py-2">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm font-semibold text-gray-100">{group.emotion} - {group.vi}</p>
                    <p className="shrink-0 text-xs text-green-300">
                      {group.aus.length > 0 ? group.aus.join(' + ') : 'Không AU mạnh'}
                    </p>
                  </div>
                  <p className="mt-1 text-xs text-gray-400">{group.note}</p>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

