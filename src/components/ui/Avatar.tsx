import { clsx } from 'clsx';

const colors = ['bg-blue-600', 'bg-purple-600', 'bg-emerald-600', 'bg-orange-600', 'bg-pink-600', 'bg-cyan-600', 'bg-red-600', 'bg-amber-600'];

function getColor(name: string) {
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash += name.charCodeAt(i);
  return colors[hash % colors.length];
}

function getInitials(name: string) {
  return name.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase();
}

interface AvatarProps {
  name: string;
  size?: 'xs' | 'sm' | 'md' | 'lg';
  className?: string;
}

const sizes = { xs: 'w-6 h-6 text-xs', sm: 'w-8 h-8 text-xs', md: 'w-10 h-10 text-sm', lg: 'w-12 h-12 text-base' };

export function Avatar({ name, size = 'md', className }: AvatarProps) {
  return (
    <div className={clsx('rounded-full flex items-center justify-center font-semibold text-white flex-shrink-0', getColor(name), sizes[size], className)}>
      {getInitials(name)}
    </div>
  );
}
