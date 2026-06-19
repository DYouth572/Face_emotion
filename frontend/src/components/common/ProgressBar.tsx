import { clsx } from 'clsx';

type ProgressVariant = 'default' | 'stress' | 'success' | 'warning' | 'danger';
type ProgressSize = 'xs' | 'sm' | 'md' | 'lg';

interface ProgressBarProps {
  value: number;           // 0 - 100
  max?: number;
  variant?: ProgressVariant;
  size?: ProgressSize;
  label?: string;
  showValue?: boolean;
  animated?: boolean;
  className?: string;
}

// Tự động chọn màu theo giá trị (dùng cho stress)
const getStressColor = (value: number): string => {
  if (value <= 30) return 'bg-green-500';
  if (value <= 60) return 'bg-yellow-500';
  return 'bg-red-500';
};

const variantColorMap: Record<ProgressVariant, string> = {
  default: 'bg-indigo-500',
  stress:  '',           // Tính động theo value
  success: 'bg-green-500',
  warning: 'bg-yellow-500',
  danger:  'bg-red-500',
};

const sizeMap: Record<ProgressSize, string> = {
  xs: 'h-1',
  sm: 'h-1.5',
  md: 'h-2.5',
  lg: 'h-4',
};

export default function ProgressBar({
  value,
  max = 100,
  variant = 'default',
  size = 'md',
  label,
  showValue = false,
  animated = false,
  className,
}: ProgressBarProps) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  const barColor =
    variant === 'stress'
      ? getStressColor(pct)
      : variantColorMap[variant];

  return (
    <div className={clsx('w-full', className)}>
      {(label || showValue) && (
        <div className="flex justify-between items-center mb-1.5">
          {label && <span className="text-xs text-gray-400">{label}</span>}
          {showValue && (
            <span className="text-xs font-mono text-gray-300">
              {pct.toFixed(0)}%
            </span>
          )}
        </div>
      )}
      <div className={clsx('w-full bg-gray-800 rounded-full overflow-hidden', sizeMap[size])}>
        <div
          className={clsx(
            'h-full rounded-full transition-all duration-500',
            barColor,
            animated && 'animate-pulse'
          )}
          style={{ width: `${pct}%` }}
          role="progressbar"
          aria-valuenow={value}
          aria-valuemin={0}
          aria-valuemax={max}
        />
      </div>
    </div>
  );
}
