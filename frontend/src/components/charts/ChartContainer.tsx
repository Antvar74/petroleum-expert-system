/**
 * ChartContainer.tsx — Reusable wrapper for all charts.
 * Provides glass-panel styling, title, badge, and responsive sizing.
 */
import React from 'react';
import { ResponsiveContainer } from 'recharts';
import type { LucideIcon } from 'lucide-react';
import { CHART_DEFAULTS } from './ChartTheme';

interface ChartContainerProps {
  title: string;
  icon?: LucideIcon;
  height?: number;
  badge?: { text: string; color: string };
  children: React.ReactNode;
  className?: string;
  noPadding?: boolean;
  isFluid?: boolean;
}

const ChartContainer: React.FC<ChartContainerProps> = ({
  title,
  icon: Icon,
  height = 350,
  badge,
  children,
  className = '',
  noPadding = false,
  isFluid = false,
}) => {
  const content = isFluid ? (
    <div className="w-full h-full">
      {children}
    </div>
  ) : (
    <div style={{ width: '100%', height }}>
      <ResponsiveContainer width="100%" height="100%">
        {children as React.ReactElement}
      </ResponsiveContainer>
    </div>
  );

  return (
    <div className={`glass-panel ${noPadding ? 'p-0' : 'p-6'} rounded-2xl border border-white/5 print-chart ${className} ${isFluid ? 'h-full' : ''}`}>
      <div className={`flex justify-between items-center ${noPadding ? 'px-6 pt-6' : ''} mb-4`}>
        <div className="flex items-center gap-2">
          {Icon && <Icon size={18} className="text-industrial-400" />}
          <h4 className="font-bold text-sm">{title}</h4>
        </div>
        {badge && (
          <span className={`px-3 py-1 rounded-full text-xs font-bold ${badge.color}`}>
            {badge.text}
          </span>
        )}
      </div>
      {content}
    </div>
  );
};

// Custom tooltip wrapper matching dark theme
export const DarkTooltip: React.FC<{ active?: boolean; payload?: any[]; label?: any; formatter?: (value: any, name: string) => string }> = ({
  active,
  payload,
  label,
  formatter,
}) => {
  if (!active || !payload?.length) return null;

  return (
    <div
      style={{
        backgroundColor: CHART_DEFAULTS.tooltipBg,
        border: `1px solid ${CHART_DEFAULTS.tooltipBorder}`,
        borderRadius: '8px',
        padding: '10px 14px',
        fontFamily: CHART_DEFAULTS.fontFamily,
        fontSize: '12px',
      }}
    >
      {label !== undefined && (
        <p style={{ color: 'rgba(255,255,255,0.5)', marginBottom: 6, fontSize: 11 }}>
          {label}
        </p>
      )}
      {payload.map((entry, i) => (
        <p key={i} style={{ color: entry.color || '#fff', margin: '2px 0', fontWeight: 600 }}>
          {entry.name}: {formatter ? formatter(entry.value, entry.name) : (typeof entry.value === 'number' ? entry.value.toLocaleString(undefined, { maximumFractionDigits: 1 }) : entry.value)}
        </p>
      ))}
    </div>
  );
};

export default ChartContainer;
