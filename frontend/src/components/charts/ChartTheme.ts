/**
 * ChartTheme.ts — Centralized color palettes and defaults for all charts.
 * Matches the industrial dark theme (#0c0e12 background, glass-panel aesthetics).
 */

// Torque & Drag colors — one per operation
export const TD_COLORS: Record<string, string> = {
  trip_out: '#f97316',   // orange-500
  trip_in: '#3b82f6',    // blue-500
  rotating: '#22c55e',   // green-500
  sliding: '#eab308',    // yellow-500
  lowering: '#a855f7',   // purple-500
  back_ream: '#06b6d4',  // cyan-500
};

// Hydraulics colors — one per circuit segment
export const HYD_COLORS: Record<string, string> = {
  surface: '#3b82f6',
  pipe: '#6366f1',
  bit: '#f97316',
  annular: '#22c55e',
  ecd_line: '#06b6d4',
  mw_ref: '#ffffff',
  lot_ref: '#ef4444',
  frac_ref: '#f59e0b',
};

// Risk level colors
export const RISK_COLORS: Record<string, string> = {
  LOW: '#22c55e',
  MEDIUM: '#eab308',
  HIGH: '#f97316',
  CRITICAL: '#ef4444',
};

// Well Control colors
export const WC_COLORS: Record<string, string> = {
  icp: '#ef4444',
  fcp: '#22c55e',
  schedule: '#f97316',
  maasp: '#eab308',
  formation: '#a855f7',
};

// Shared chart defaults
export const CHART_DEFAULTS = {
  backgroundColor: 'transparent',
  gridColor: 'rgba(255,255,255,0.05)',
  axisColor: 'rgba(255,255,255,0.3)',
  labelColor: 'rgba(255,255,255,0.5)',
  tooltipBg: 'rgba(12,14,18,0.95)',
  tooltipBorder: 'rgba(255,255,255,0.1)',
  fontFamily: 'Inter, system-ui, sans-serif',
  animationDuration: 800,
  margin: { top: 20, right: 20, bottom: 20, left: 20 },
};

// Buckling status colors
export const BUCKLING_COLORS: Record<string, string> = {
  OK: '#22c55e',
  SINUSOIDAL: '#eab308',
  HELICAL: '#ef4444',
};

// Gauge thresholds — reusable for various gauges
export interface GaugeThreshold {
  value: number;
  color: string;
}

export const HSI_THRESHOLDS: GaugeThreshold[] = [
  { value: 1.0, color: '#ef4444' },
  { value: 2.5, color: '#eab308' },
  { value: 3.5, color: '#22c55e' },
  { value: 5.0, color: '#eab308' },
];

export const JET_VEL_THRESHOLDS: GaugeThreshold[] = [
  { value: 150, color: '#ef4444' },
  { value: 250, color: '#eab308' },
  { value: 450, color: '#22c55e' },
  { value: 600, color: '#eab308' },
];

export const PERCENT_BIT_THRESHOLDS: GaugeThreshold[] = [
  { value: 30, color: '#ef4444' },
  { value: 50, color: '#eab308' },
  { value: 65, color: '#22c55e' },
  { value: 100, color: '#eab308' },
];
