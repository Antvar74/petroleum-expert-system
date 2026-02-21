/**
 * SkinComponentsBar.tsx — Grouped bar chart showing S_p, S_v, S_wb per interval.
 * Uses side-by-side bars so each component is visible regardless of magnitude differences.
 */
import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ReferenceLine } from 'recharts';
import ChartContainer, { DarkTooltip } from '../ChartContainer';
import { CHART_DEFAULTS } from '../ChartTheme';
import { BarChart3 } from 'lucide-react';

interface SkinComponentsBarProps {
  intervals: {
    top_md: number; base_md: number;
    skin_total: number;
    skin_components?: { s_p: number; s_v: number; s_wb: number };
  }[];
  height?: number;
}

const COLORS = {
  s_p: '#8b5cf6',
  s_v: '#06b6d4',
  s_wb: '#f97316',
};

const SkinComponentsBar: React.FC<SkinComponentsBarProps> = ({ intervals, height = 350 }) => {
  if (!intervals?.length || !intervals[0]?.skin_components) return null;

  // Build grouped data — one row per interval with all 3 components
  const data = intervals.map(iv => ({
    name: `${iv.top_md}'`,
    S_perf: +(iv.skin_components?.s_p || 0).toFixed(4),
    S_vert: +(iv.skin_components?.s_v || 0).toFixed(4),
    S_wb: +(iv.skin_components?.s_wb || 0).toFixed(4),
    total: +(iv.skin_total || 0).toFixed(4),
  }));

  return (
    <ChartContainer
      title="Componentes de Skin por Intervalo (Karakas-Tariq)"
      icon={BarChart3}
      height={height}
    >
      <BarChart data={data} margin={CHART_DEFAULTS.margin} barCategoryGap="20%" barGap={4}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_DEFAULTS.gridColor} />
        <XAxis dataKey="name" stroke={CHART_DEFAULTS.axisColor} tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }} />
        <YAxis stroke={CHART_DEFAULTS.axisColor} tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }}
          label={{ value: 'Skin', angle: -90, position: 'insideLeft', fill: CHART_DEFAULTS.axisColor }} />
        <Tooltip content={<DarkTooltip />} />
        <Legend wrapperStyle={{ fontSize: 11, color: 'rgba(255,255,255,0.5)' }} />
        <ReferenceLine y={0} stroke="rgba(255,255,255,0.2)" />
        <Bar dataKey="S_perf" fill={COLORS.s_p} radius={[4, 4, 0, 0]} />
        <Bar dataKey="S_vert" fill={COLORS.s_v} radius={[4, 4, 0, 0]} />
        <Bar dataKey="S_wb" fill={COLORS.s_wb} radius={[4, 4, 0, 0]} />
      </BarChart>
    </ChartContainer>
  );
};

export default SkinComponentsBar;
