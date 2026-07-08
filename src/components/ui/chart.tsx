import { useStore } from '../../store/useStore';

// Categorical palette validated for CVD separation and surface contrast
// (light on #ffffff, dark on #1f2937). Slot order is the safety mechanism —
// assign in order, never cycle past the end.
export const CHART_COLORS_LIGHT = ['#2a78d6', '#1baf7a', '#eda100', '#008300', '#4a3aa7', '#e34948', '#e87ba4', '#eb6834'];
export const CHART_COLORS_DARK = ['#3987e5', '#199e70', '#c98500', '#008300', '#9085e9', '#e66767', '#d55181', '#d95926'];

export interface ChartTheme {
  colors: string[];
  tick: string;
  grid: string;
  axisLine: string;
  cursorFill: string;
}

export function useChartTheme(): ChartTheme {
  const darkMode = useStore(s => s.darkMode);
  return darkMode
    ? {
        colors: CHART_COLORS_DARK,
        tick: '#9ca3af',
        grid: '#2e3947',
        axisLine: '#394456',
        cursorFill: 'rgba(255,255,255,0.06)',
      }
    : {
        colors: CHART_COLORS_LIGHT,
        tick: '#6b7280',
        grid: '#eef0f3',
        axisLine: '#d8dce2',
        cursorFill: 'rgba(15,23,42,0.05)',
      };
}

interface TooltipPayloadItem {
  name?: string;
  value?: number | string;
  color?: string;
  stroke?: string;
  fill?: string;
  payload?: Record<string, unknown>;
}

interface ChartTooltipProps {
  active?: boolean;
  label?: string | number;
  payload?: TooltipPayloadItem[];
  suffix?: string;
  formatter?: (value: number | string) => string;
}

// Shared tooltip for every Recharts chart: hairline ring, soft shadow,
// colored dot per series, tabular figures.
export function ChartTooltip({ active, label, payload, suffix, formatter }: ChartTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div className="rounded-xl border border-gray-200 bg-white/95 px-3.5 py-2.5 shadow-xl shadow-gray-900/10 backdrop-blur-sm dark:border-gray-600/60 dark:bg-gray-800/95 dark:shadow-black/40">
      {label !== undefined && label !== '' && (
        <p className="mb-1.5 text-xs font-semibold text-gray-900 dark:text-white">{label}</p>
      )}
      <div className="space-y-1">
        {payload.map((item, i) => {
          const dot = item.color || item.stroke || item.fill || '#6b7280';
          const raw = item.value ?? '';
          const shown = formatter ? formatter(raw) : String(raw);
          return (
            <div key={i} className="flex items-center gap-2 text-xs">
              <span className="h-2 w-2 flex-shrink-0 rounded-full" style={{ background: dot }} />
              <span className="text-gray-500 dark:text-gray-400">{item.name}</span>
              <span className="ml-auto pl-4 font-semibold text-gray-900 [font-variant-numeric:tabular-nums] dark:text-white">
                {shown}{suffix ? ` ${suffix}` : ''}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// Legend row rendered above/below a chart — colored dot + label, text in ink tokens.
export function ChartLegend({ items }: { items: { label: string; color: string }[] }) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5">
      {items.map(({ label, color }) => (
        <span key={label} className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
          <span className="h-2 w-2 rounded-full" style={{ background: color }} />
          {label}
        </span>
      ))}
    </div>
  );
}
