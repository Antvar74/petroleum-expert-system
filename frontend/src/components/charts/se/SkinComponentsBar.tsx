/**
 * SkinComponentsBar.tsx — Stacked bar chart showing S_p, S_v, S_wb per interval.
 */
import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';
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

const SkinComponentsBar: React.FC<SkinComponentsBarProps> = ({ intervals, height = 350 }) => {
  if (!intervals?.length || !intervals[0]?.skin_components) return null;

  const data = intervals.map(iv => ({
    name: `${iv.top_md}'`,
    s_p: Math.abs(iv.skin_components?.s_p || 0),
    s_v: iv.skin_components?.s_v || 0,
    s_wb: iv.skin_components?.s_wb || 0,
    total: iv.skin_total,
  }));

  return (
    <ChartContainer
      title="Componentes de Skin por Intervalo (Karakas-Tariq)"
      icon={BarChart3}
      height={height}
    >
      <BarChart data={data} margin={CHART_DEFAULTS.margin}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_DEFAULTS.gridColor} />
        <XAxis dataKey="name" stroke={CHART_DEFAULTS.axisColor} tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }} />
        <YAxis stroke={CHART_DEFAULTS.axisColor} tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }}
          label={{ value: 'Skin', angle: -90, position: 'insideLeft', fill: CHART_DEFAULTS.axisColor }} />
        <Tooltip content={<DarkTooltip />} />
        <Legend wrapperStyle={{ fontSize: 11, color: 'rgba(255,255,255,0.5)' }} />
        <Bar dataKey="s_p" stackId="skin" fill="#8b5cf6" name="S_perf" radius={[0, 0, 0, 0]} />
        <Bar dataKey="s_v" stackId="skin" fill="#06b6d4" name="S_vert" />
        <Bar dataKey="s_wb" stackId="skin" fill="#f97316" name="S_wb" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ChartContainer>
  );
};

export default SkinComponentsBar;
