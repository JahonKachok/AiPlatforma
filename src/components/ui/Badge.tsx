import { clsx } from 'clsx';

type BadgeVariant = 'default' | 'success' | 'warning' | 'danger' | 'info' | 'purple';

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  size?: 'sm' | 'md';
  className?: string;
}

const variants: Record<BadgeVariant, string> = {
  default: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300',
  success: 'bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-900/50 dark:text-emerald-400 dark:border-emerald-800',
  warning: 'bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-900/50 dark:text-amber-400 dark:border-amber-800',
  danger: 'bg-red-50 text-red-700 border border-red-200 dark:bg-red-900/50 dark:text-red-400 dark:border-red-800',
  info: 'bg-blue-50 text-blue-700 border border-blue-200 dark:bg-blue-900/50 dark:text-blue-400 dark:border-blue-800',
  purple: 'bg-purple-50 text-purple-700 border border-purple-200 dark:bg-purple-900/50 dark:text-purple-400 dark:border-purple-800',
};

export function Badge({ children, variant = 'default', size = 'sm', className }: BadgeProps) {
  return (
    <span className={clsx(
      'inline-flex items-center font-medium rounded-full',
      size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-sm',
      variants[variant],
      className
    )}>
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
