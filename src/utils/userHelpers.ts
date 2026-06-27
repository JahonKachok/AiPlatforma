import type { User } from '../types';

export function getUserName(user: User | undefined | null): string {
  if (!user) return 'Unknown';
  return user.full_name || user.name || 'User';
}

export function getUserInitials(user: User | undefined | null): string {
  const name = getUserName(user);
  return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
}
