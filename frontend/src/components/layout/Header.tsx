import { Wifi, WifiOff } from 'lucide-react';
import { useSessionStore } from '@/store/useSessionStore';
import { formatDurationShort } from '@/utils/formatters';

interface HeaderProps {
  wsConnected?: boolean;
}

export default function Header({ wsConnected = false }: HeaderProps) {
  const elapsedMs     = useSessionStore((s) => s.elapsedMs);
  const isRunning     = useSessionStore((s) => s.current?.status === 'running');

  return (
    <header className="h-14 bg-gray-950 border-b border-gray-800 flex items-center justify-between px-4 shrink-0">
      {/* Left: Session timer */}
      <div className="flex items-center gap-3">
        {isRunning && (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-green-950/40 border border-green-800/40">
            <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
            <span className="text-xs font-mono text-green-300">
              {formatDurationShort(elapsedMs)}
            </span>
          </div>
        )}
      </div>

      {/* Right: Status indicators */}
      <div className="flex items-center gap-3">
        {/* WS Connection */}
        <div className={`flex items-center gap-1.5 text-xs ${wsConnected ? 'text-green-400' : 'text-gray-500'}`}>
          {wsConnected ? <Wifi size={14} /> : <WifiOff size={14} />}
          <span className="hidden sm:inline">{wsConnected ? 'Đã kết nối' : 'Mất kết nối'}</span>
        </div>
      </div>
    </header>
  );
}
