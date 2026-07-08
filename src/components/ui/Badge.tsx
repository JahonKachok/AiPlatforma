import { clsx } from 'clsx';

type BadgeVariant = 'default' | 'success' | 'warning' | 'danger' | 'info' | 'purple';

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  size?: 'sm' | 'md';
  dot?: boolean;
  className?: string;
}

const variants: Record<BadgeVariant, string> = {
  default: 'bg-gray-100 text-gray-600 ring-1 ring-inset ring-gray-200 dark:bg-gray-700/70 dark:text-gray-300 dark:ring-gray-600',
  success: 'bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-200 dark:bg-emerald-900/40 dark:text-emerald-400 dark:ring-emerald-800',
  warning: 'bg-amber-50 text-amber-700 ring-1 ring-inset ring-amber-200 dark:bg-amber-900/40 dark:text-amber-400 dark:ring-amber-800',
  danger: 'bg-red-50 text-red-700 ring-1 ring-inset ring-red-200 dark:bg-red-900/40 dark:text-red-400 dark:ring-red-800',
  info: 'bg-blue-50 text-blue-700 ring-1 ring-inset ring-blue-200 dark:bg-blue-900/40 dark:text-blue-400 dark:ring-blue-800',
  purple: 'bg-purple-50 text-purple-700 ring-1 ring-inset ring-purple-200 dark:bg-purple-900/40 dark:text-purple-400 dark:ring-purple-800',
};

const dotColors: Record<BadgeVariant, string> = {
  default: 'bg-gray-400',
  success: 'bg-emerald-500',
  warning: 'bg-amber-500',
  danger: 'bg-red-500',
  info: 'bg-blue-500',
  purple: 'bg-purple-500',
};

export function Badge({ children, variant = 'default', size = 'sm', dot, className }: BadgeProps) {
  return (
    <span className={clsx(
      'inline-flex items-center gap-1.5 font-medium rounded-full whitespace-nowrap',
      size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-sm',
      variants[variant],
      className
    )}>
      {dot && <span className={clsx('w-1.5 h-1.5 rounded-full flex-shrink-0', dotColors[variant])} />}
      {children}
    </span>
  );
}

export function getTaskStatusBadge(status: string) {
  const map: Record<string, BadgeVariant> = {
    new: 'info', in_progress: 'purple', review: 'warning',
    revision: 'danger', approved: 'success', completed: 'default'
  };
  return map[status] || 'default';
}

export function getPriorityBadge(priority: string) {
  const map: Record<string, BadgeVariant> = {
    low: 'default', medium: 'info', high: 'warning', critical: 'danger'
  };
  return map[priority] || 'default';
}

export function getProjectStatusBadge(status: string) {
  const map: Record<string, BadgeVariant> = {
    active: 'success', completed: 'default', paused: 'warning', cancelled: 'danger', planning: 'info'
  };
  return map[status] || 'default';
}
