/**
 * NetPayIntervalChart.tsx — Horizontal bars showing net pay intervals with thickness.
 */
import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell } from 'recharts';
import ChartContainer, { DarkTooltip } from '../ChartContainer';
import { CHART_DEFAULTS } from '../ChartTheme';
import { Layers } from 'lucide-react';

interface NetPayIntervalChartProps {
  intervals: {
    top_md: number; base_md: number; thickness_ft: number;
    avg_phi: number; avg_sw: number; avg_vsh: number;
  }[];
  netPay: { total_net_pay_ft: number; interval_count: number };
  height?: number;
}

const NetPayIntervalChart: React.FC<NetPayIntervalChartProps> = ({ intervals, netPay, height = 350 }) => {
  if (!intervals?.length) return null;

  const data = intervals.map((iv) => ({
    name: `${iv.top_md}-${iv.base_md}'`,
    thickness: iv.thickness_ft,
    phi: Math.round(iv.avg_phi * 1000) / 10,
    color: iv.avg_phi > 0.15 ? '#22c55e' : iv.avg_phi > 0.10 ? '#eab308' : '#f97316',
  }));

  return (
    <ChartContainer
      title="Intervalos Net Pay"
      icon={Layers}
      height={height}
      badge={{ text: `${netPay?.total_net_pay_ft} ft total`, color: 'bg-emerald-500/20 text-emerald-400' }}
    >
      <BarChart data={data} layout="vertical" margin={{ ...CHART_DEFAULTS.margin, left: 80 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_DEFAULTS.gridColor} />
        <XAxis type="number" stroke={CHART_DEFAULTS.axisColor} tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }}
          label={{ value: 'Espesor (ft)', position: 'bottom', fill: CHART_DEFAULTS.axisColor }} />
        <YAxis type="category" dataKey="name" stroke={CHART_DEFAULTS.axisColor}
          tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 10 }} width={75} />
        <Tooltip content={<DarkTooltip />} />
        <Bar dataKey="thickness" name="Espesor (ft)" radius={[0, 4, 4, 0]}>
          {data.map((entry, idx) => (
            <Cell key={idx} fill={entry.color} />
          ))}
        </Bar>
      </BarChart>
    </ChartContainer>
  );
};

export default NetPayIntervalChart;
