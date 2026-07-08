import { clsx } from 'clsx';

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'success' | 'outline';
type ButtonSize = 'sm' | 'md' | 'lg';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  icon?: React.ReactNode;
  loading?: boolean;
}

const variants: Record<ButtonVariant, string> = {
  primary:
    'bg-gradient-to-b from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white border border-blue-600/60 shadow-sm shadow-blue-600/25 hover:shadow-md hover:shadow-blue-600/30',
  secondary:
    'bg-white hover:bg-gray-50 text-gray-700 border border-gray-200 shadow-sm hover:border-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 dark:text-gray-200 dark:border-gray-600 dark:hover:border-gray-500',
  ghost:
    'bg-transparent hover:bg-gray-100 text-gray-500 hover:text-gray-800 border border-transparent dark:hover:bg-gray-700/60 dark:text-gray-400 dark:hover:text-gray-200',
  danger:
    'bg-red-50 hover:bg-red-100 text-red-600 border border-red-200 hover:border-red-300 dark:bg-red-900/40 dark:hover:bg-red-900/60 dark:text-red-400 dark:border-red-800',
  success:
    'bg-gradient-to-b from-emerald-500 to-emerald-600 hover:from-emerald-600 hover:to-emerald-700 text-white border border-emerald-600/60 shadow-sm shadow-emerald-600/25',
  outline:
    'bg-transparent hover:bg-blue-50 text-blue-600 border border-blue-300 hover:border-blue-400 dark:hover:bg-blue-900/20 dark:text-blue-400 dark:border-blue-700',
};

const sizes: Record<ButtonSize, string> = {
  sm: 'px-3 py-1.5 text-xs rounded-lg',
  md: 'px-4 py-2 text-sm rounded-lg',
  lg: 'px-5 py-2.5 text-base rounded-xl',
};

export function Button({ variant = 'secondary', size = 'md', icon, loading, children, className, disabled, ...props }: ButtonProps) {
  return (
    <button
      disabled={disabled || loading}
      className={clsx(
        'inline-flex items-center justify-center gap-2 font-medium transition-all duration-150',
        'focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/60 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-gray-900',
        'active:scale-[0.97]',
        variants[variant],
        sizes[size],
        (disabled || loading) && 'opacity-50 cursor-not-allowed pointer-events-none',
        className
      )}
      {...props}
    >
      {loading ? <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" /> : icon}
      {children}
    </button>
  );
}
