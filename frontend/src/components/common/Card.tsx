import { ReactNode } from 'react';
import { clsx } from 'clsx';

interface CardProps {
  children: ReactNode;
  title?: string;
  subtitle?: string;
  headerRight?: ReactNode;
  footer?: ReactNode;
  className?: string;
  bodyClassName?: string;
  noPadding?: boolean;
}

export default function Card({
  children,
  title,
  subtitle,
  headerRight,
  footer,
  className,
  bodyClassName,
  noPadding = false,
}: CardProps) {
  const hasHeader = title || subtitle || headerRight;

  return (
    <div
      className={clsx(
        'bg-gray-900 border border-gray-800 rounded-xl shadow-lg',
        className
      )}
    >
      {hasHeader && (
        <div className="flex items-start justify-between px-5 pt-4 pb-3 border-b border-gray-800">
          <div>
            {title && (
              <h3 className="text-sm font-semibold text-gray-100">{title}</h3>
            )}
            {subtitle && (
              <p className="text-xs text-gray-400 mt-0.5">{subtitle}</p>
            )}
          </div>
          {headerRight && <div className="ml-4 shrink-0">{headerRight}</div>}
        </div>
      )}

      <div className={clsx(!noPadding && 'p-5', bodyClassName)}>
        {children}
      </div>

      {footer && (
        <div className="px-5 py-3 border-t border-gray-800 bg-gray-900/50 rounded-b-xl">
          {footer}
        </div>
      )}
    </div>
  );
}
