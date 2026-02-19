/**
 * DisplacementScheduleChart.tsx — Shows fluid interfaces vs cumulative volume pumped.
 * X-axis: cumulative bbl pumped. Y-axis: depth (MD). Color-coded fluid zones.
 */
import React from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine } from 'recharts';
import ChartContainer, { DarkTooltip } from '../ChartContainer';
import { CHART_DEFAULTS } from '../ChartTheme';
import { Layers } from 'lucide-react';

interface DisplacementScheduleChartProps {
  displacement: any;
  height?: number;
}

const FLUID_COLORS: Record<string, string> = {
  spacer: '#eab308',
  lead_cement: '#14b8a6',
  tail_cement: '#f97316',
  displacement_mud: '#6366f1',
};

const DisplacementScheduleChart: React.FC<DisplacementScheduleChartProps> = ({ displacement, height = 350 }) => {
  if (!displacement?.schedule?.length) return null;

  const data = displacement.schedule.map((pt: any) => ({
    volume: Math.round(pt.cumulative_bbl * 10) / 10,
    spacer_top: pt.spacer_top_ft,
    spacer_bottom: pt.spacer_bottom_ft,
    cement_top: pt.cement_top_ft,
    cement_bottom: pt.cement_bottom_ft,
    stage: pt.stage,
  }));

  return (
    <ChartContainer
      title="Programa de Desplazamiento"
      icon={Layers}
      height={height}
      badge={{ text: `${displacement.total_time_min ?? '—'} min`, color: 'bg-teal-500/20 text-teal-400' }}
    >
      <AreaChart data={data} margin={{ ...CHART_DEFAULTS.margin, left: 40 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_DEFAULTS.gridColor} />
        <XAxis
          dataKey="volume"
          stroke={CHART_DEFAULTS.axisColor}
          tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }}
          label={{ value: 'Volumen Bombeado (bbl)', position: 'insideBottom', offset: -5, fill: CHART_DEFAULTS.labelColor, fontSize: 11 }}
        />
        <YAxis
          reversed
          stroke={CHART_DEFAULTS.axisColor}
          tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }}
          label={{ value: 'Profundidad (ft MD)', angle: -90, position: 'insideLeft', fill: CHART_DEFAULTS.labelColor, fontSize: 11 }}
        />
        <Tooltip content={<DarkTooltip formatter={(v: any) => `${Number(v).toFixed(0)} ft`} />} />
        <Area type="stepAfter" dataKey="spacer_top" stroke={FLUID_COLORS.spacer} fill={FLUID_COLORS.spacer}
          fillOpacity={0.15} strokeWidth={2} name="Spacer Top" dot={false} />
        <Area type="stepAfter" dataKey="cement_top" stroke={FLUID_COLORS.lead_cement} fill={FLUID_COLORS.lead_cement}
          fillOpacity={0.2} strokeWidth={2} name="Cement Top" dot={false} />
        <Area type="stepAfter" dataKey="cement_bottom" stroke={FLUID_COLORS.tail_cement} fill={FLUID_COLORS.tail_cement}
          fillOpacity={0.15} strokeWidth={2} name="Cement Bottom" dot={false} />
        {displacement.shoe_depth_ft && (
          <ReferenceLine y={displacement.shoe_depth_ft} stroke="#ef4444" strokeDasharray="6 4"
            label={{ value: 'Zapata', fill: '#ef4444', fontSize: 10, position: 'right' }} />
        )}
      </AreaChart>
    </ChartContainer>
  );
};

export default DisplacementScheduleChart;
