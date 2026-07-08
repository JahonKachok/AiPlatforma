import { clsx } from 'clsx';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
  hover?: boolean;
}

export function Card({ children, className, onClick, hover }: CardProps) {
  return (
    <div
      onClick={onClick}
      className={clsx(
        'bg-white border border-gray-200/80 rounded-2xl shadow-sm shadow-gray-950/[0.03]',
        'dark:bg-gray-800 dark:border-gray-700 dark:shadow-black/10',
        (hover || onClick) &&
          'cursor-pointer transition-all duration-200 hover:border-gray-300 hover:shadow-md hover:shadow-gray-950/[0.06] hover:-translate-y-0.5 dark:hover:border-gray-600 dark:hover:shadow-black/25',
        className
      )}
    >
      {children}
    </div>
  );
}

export function CardHeader({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={clsx('px-5 py-4 border-b border-gray-100 dark:border-gray-700', className)}>{children}</div>;
}

export function CardContent({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={clsx('px-5 py-4', className)}>{children}</div>;
}
