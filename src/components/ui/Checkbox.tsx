import { Check, Minus } from 'lucide-react';
import { clsx } from 'clsx';

interface CheckboxProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: string;
  description?: string;
  indeterminate?: boolean;
  disabled?: boolean;
  className?: string;
}

export function Checkbox({ checked, onChange, label, description, indeterminate, disabled, className }: CheckboxProps) {
  return (
    <label className={clsx('group flex items-start gap-3', disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer', className)}>
      <span className="relative flex-shrink-0 mt-0.5">
        <input
          type="checkbox"
          checked={checked}
          disabled={disabled}
          onChange={e => onChange(e.target.checked)}
          className="peer sr-only"
        />
        <span
          className={clsx(
            'flex h-[18px] w-[18px] items-center justify-center rounded-[5px] border-2 transition-all duration-150',
            'peer-focus-visible:ring-2 peer-focus-visible:ring-blue-500/60 peer-focus-visible:ring-offset-2 dark:peer-focus-visible:ring-offset-gray-900',
            checked || indeterminate
              ? 'border-blue-600 bg-gradient-to-b from-blue-500 to-blue-600 shadow-sm shadow-blue-600/30'
              : 'border-gray-300 bg-white group-hover:border-blue-400 dark:border-gray-600 dark:bg-gray-700 dark:group-hover:border-blue-500'
          )}
        >
          {indeterminate
            ? <Minus size={12} strokeWidth={3.5} className="text-white" />
            : checked && <Check size={12} strokeWidth={3.5} className="text-white animate-scale-in" />}
        </span>
      </span>
      {(label || description) && (
        <span className="select-none">
          {label && <span className="block text-sm text-gray-700 dark:text-gray-200">{label}</span>}
          {description && <span className="block text-xs text-gray-500 mt-0.5">{description}</span>}
        </span>
      )}
    </label>
  );
}

interface ToggleProps {
  on: boolean;
  onChange: () => void;
  disabled?: boolean;
  size?: 'sm' | 'md';
}

export function Toggle({ on, onChange, disabled, size = 'md' }: ToggleProps) {
  const track = size === 'md' ? 'w-11 h-6' : 'w-9 h-5';
  const knob = size === 'md' ? 'w-[18px] h-[18px] peer-checked:translate-x-5' : 'w-[15px] h-[15px] peer-checked:translate-x-4';
  return (
    <label className={clsx('relative flex-shrink-0', disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer')}>
      <input
        type="checkbox"
        role="switch"
        checked={on}
        disabled={disabled}
        onChange={onChange}
        className="sr-only peer"
      />
      <div
        className={clsx(
          track,
          'rounded-full transition-all duration-200',
          'bg-gray-200 ring-1 ring-inset ring-gray-300/60 dark:bg-gray-700 dark:ring-gray-600/60',
          'peer-checked:bg-gradient-to-b peer-checked:from-blue-500 peer-checked:to-blue-600 peer-checked:ring-blue-600/50 peer-checked:shadow-inner',
          'peer-focus-visible:ring-2 peer-focus-visible:ring-blue-500/60 peer-focus-visible:ring-offset-2 dark:peer-focus-visible:ring-offset-gray-900'
        )}
      />
      <div
        className={clsx(
          knob,
          'absolute left-[3px] top-1/2 -translate-y-1/2 rounded-full bg-white shadow-md shadow-gray-900/20 transition-transform duration-200'
        )}
      />
    </label>
  );
}
