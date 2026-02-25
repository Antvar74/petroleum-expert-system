/**
 * BHPScheduleChart.tsx — Bottom-hole pressure vs cumulative volume pumped.
 * Shows BHP buildup during cementing with hydrostatic + friction components.
 */
import React from 'react';
import { ComposedChart, Line, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';
import ChartContainer, { DarkTooltip } from '../ChartContainer';
import { CHART_DEFAULTS } from '../ChartTheme';
import { Gauge } from 'lucide-react';

interface BHPScheduleChartProps {
  bhp: { schedule: Array<{ cumulative_bbl: number; bhp_psi: number; hydrostatic_psi?: number; friction_psi?: number; stage?: string }> };
  height?: number;
}

const BHPScheduleChart: React.FC<BHPScheduleChartProps> = ({ bhp, height = 350 }) => {
  if (!bhp?.schedule?.length) return null;

  const data = bhp.schedule.map((pt: { cumulative_bbl: number; bhp_psi: number; hydrostatic_psi?: number; friction_psi?: number; stage?: string }) => ({
    volume: Math.round(pt.cumulative_bbl * 10) / 10,
    bhp: Math.round(pt.bhp_psi),
    hydrostatic: Math.round(pt.hydrostatic_psi || 0),
    friction: Math.round(pt.friction_psi || 0),
    stage: pt.stage,
  }));

  const maxBHP = Math.max(...data.map((d: { volume: number; bhp: number; hydrostatic: number; friction: number; stage?: string }) => d.bhp));

  return (
    <ChartContainer
      title="Presión de Fondo (BHP)"
      icon={Gauge}
      height={height}
      badge={{ text: `Max: ${maxBHP} psi`, color: 'bg-orange-500/20 text-orange-400' }}
    >
      <ComposedChart data={data} margin={{ ...CHART_DEFAULTS.margin, left: 40 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_DEFAULTS.gridColor} />
        <XAxis
          dataKey="volume"
          stroke={CHART_DEFAULTS.axisColor}
          tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }}
          label={{ value: 'Volumen (bbl)', position: 'insideBottom', offset: -5, fill: CHART_DEFAULTS.labelColor, fontSize: 11 }}
        />
        <YAxis
          stroke={CHART_DEFAULTS.axisColor}
          tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }}
          label={{ value: 'Presión (psi)', angle: -90, position: 'insideLeft', fill: CHART_DEFAULTS.labelColor, fontSize: 11 }}
        />
        <Tooltip content={<DarkTooltip formatter={(v: number) => `${Number(v).toLocaleString()} psi`} />} />
        <Legend wrapperStyle={{ color: CHART_DEFAULTS.axisColor, fontSize: 11 }} />
        <Bar dataKey="hydrostatic" stackId="a" fill="#3b82f6" fillOpacity={0.3} name="Hidrostática" />
        <Bar dataKey="friction" stackId="a" fill="#f97316" fillOpacity={0.3} name="Fricción" />
        <Line type="monotone" dataKey="bhp" stroke="#ef4444" strokeWidth={3} dot={false}
          name="BHP Total" animationDuration={CHART_DEFAULTS.animationDuration} />
      </ComposedChart>
    </ChartContainer>
  );
};

export default BHPScheduleChart;
