import { ReactNode } from 'react';
import { clsx } from 'clsx';
import { AlertTriangle, Info, CheckCircle, XCircle, X } from 'lucide-react';

type AlertBannerVariant = 'info' | 'success' | 'warning' | 'error';

interface AlertBannerProps {
  variant?: AlertBannerVariant;
  title?: string;
  message: ReactNode;
  onClose?: () => void;
  className?: string;
}

const config: Record<AlertBannerVariant, {
  icon: ReactNode;
  containerClass: string;
  iconClass: string;
  titleClass: string;
  textClass: string;
}> = {
  info: {
    icon: <Info size={16} />,
    containerClass: 'bg-blue-950/60 border-blue-700/50',
    iconClass: 'text-blue-400',
    titleClass: 'text-blue-300',
    textClass: 'text-blue-200',
  },
  success: {
    icon: <CheckCircle size={16} />,
    containerClass: 'bg-green-950/60 border-green-700/50',
    iconClass: 'text-green-400',
    titleClass: 'text-green-300',
    textClass: 'text-green-200',
  },
  warning: {
    icon: <AlertTriangle size={16} />,
    containerClass: 'bg-yellow-950/60 border-yellow-700/50',
    iconClass: 'text-yellow-400',
    titleClass: 'text-yellow-300',
    textClass: 'text-yellow-200',
  },
  error: {
    icon: <XCircle size={16} />,
    containerClass: 'bg-red-950/60 border-red-700/50',
    iconClass: 'text-red-400',
    titleClass: 'text-red-300',
    textClass: 'text-red-200',
  },
};

export default function AlertBanner({
  variant = 'info',
  title,
  message,
  onClose,
  className,
}: AlertBannerProps) {
  const c = config[variant];

  return (
    <div
      className={clsx(
        'flex items-start gap-3 px-4 py-3 rounded-xl border',
        c.containerClass,
        className
      )}
      role="alert"
    >
      <span className={clsx('mt-0.5 shrink-0', c.iconClass)}>{c.icon}</span>

      <div className="flex-1 min-w-0">
        {title && (
          <p className={clsx('text-sm font-semibold', c.titleClass)}>{title}</p>
        )}
        <div className={clsx('text-sm', c.textClass)}>{message}</div>
      </div>

      {onClose && (
        <button
          onClick={onClose}
          className={clsx(
            'shrink-0 p-0.5 rounded transition-opacity hover:opacity-70',
            c.iconClass
          )}
          aria-label="Đóng"
        >
          <X size={14} />
        </button>
      )}
    </div>
  );
}
