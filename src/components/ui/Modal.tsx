import { useEffect } from 'react';
import { X } from 'lucide-react';
import { clsx } from 'clsx';

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  footer?: React.ReactNode;
}

const sizes = {
  sm: 'max-w-md',
  md: 'max-w-lg',
  lg: 'max-w-2xl',
  xl: 'max-w-4xl',
};

export function Modal({ open, onClose, title, subtitle, children, size = 'md', footer }: ModalProps) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    if (open) document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [open, onClose]);

  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = prev; };
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-label={title}>
      <div className="absolute inset-0 bg-gray-950/50 backdrop-blur-[3px] animate-fade-in dark:bg-black/70" onClick={onClose} />
      <div
        className={clsx(
          'relative w-full flex flex-col max-h-[90vh] animate-scale-in',
          'bg-white border border-gray-200 rounded-2xl shadow-2xl shadow-gray-950/20',
          'dark:bg-gray-800 dark:border-gray-700 dark:shadow-black/50',
          sizes[size]
        )}
      >
        <div className="flex items-start justify-between px-6 py-4 border-b border-gray-100 dark:border-gray-700">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">{title}</h2>
            {subtitle && <p className="text-xs text-gray-500 mt-0.5">{subtitle}</p>}
          </div>
          <button
            onClick={onClose}
            aria-label="Close"
            className="p-1.5 -mr-1.5 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors dark:hover:bg-gray-700 dark:hover:text-white"
          >
            <X size={18} />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-6 py-5">{children}</div>
        {footer && (
          <div className="px-6 py-4 border-t border-gray-100 bg-gray-50/60 rounded-b-2xl dark:border-gray-700 dark:bg-gray-800/80">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
