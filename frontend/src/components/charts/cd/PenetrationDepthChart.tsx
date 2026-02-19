/**
 * PenetrationDepthChart.tsx — Horizontal bar showing API RP 19B correction factors
 * and their cumulative effect on Berea penetration depth.
 */
import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, Cell } from 'recharts';
import ChartContainer, { DarkTooltip } from '../ChartContainer';
import { CHART_DEFAULTS } from '../ChartTheme';
import { Crosshair } from 'lucide-react';

interface PenetrationDepthChartProps {
  penetration: {
    penetration_berea_in: number;
    penetration_corrected_in: number;
    efficiency_pct: number;
    correction_factors: {
      cf_stress: number;
      cf_temperature: number;
      cf_fluid: number;
      cf_cement: number;
      cf_casing: number;
      cf_total: number;
    };
  };
  height?: number;
}

const PenetrationDepthChart: React.FC<PenetrationDepthChartProps> = ({ penetration, height = 350 }) => {
  if (!penetration) return null;

  const cf = penetration.correction_factors;
  const data = [
    { name: 'Stress', value: cf.cf_stress, color: cf.cf_stress < 0.8 ? '#ef4444' : cf.cf_stress < 0.9 ? '#eab308' : '#22c55e' },
    { name: 'Temp', value: cf.cf_temperature, color: cf.cf_temperature < 0.85 ? '#ef4444' : cf.cf_temperature < 0.95 ? '#eab308' : '#22c55e' },
    { name: 'Fluid', value: cf.cf_fluid, color: cf.cf_fluid < 0.8 ? '#ef4444' : cf.cf_fluid < 0.9 ? '#eab308' : '#22c55e' },
    { name: 'Cement', value: cf.cf_cement, color: cf.cf_cement < 0.95 ? '#eab308' : '#22c55e' },
    { name: 'Casing', value: cf.cf_casing, color: cf.cf_casing < 0.93 ? '#ef4444' : cf.cf_casing < 0.97 ? '#eab308' : '#22c55e' },
    { name: 'TOTAL', value: cf.cf_total, color: '#8b5cf6' },
  ];

  return (
    <ChartContainer
      title="Factores Corrección Penetración (API RP 19B)"
      icon={Crosshair}
      height={height}
      badge={{ text: `${penetration.penetration_corrected_in}" (${penetration.efficiency_pct}%)`, color: 'bg-violet-500/20 text-violet-400' }}
    >
      <BarChart data={data} layout="vertical" margin={{ ...CHART_DEFAULTS.margin, left: 50 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_DEFAULTS.gridColor} />
        <XAxis type="number" domain={[0.5, 1.1]} stroke={CHART_DEFAULTS.axisColor}
          tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }} />
        <YAxis type="category" dataKey="name" stroke={CHART_DEFAULTS.axisColor}
          tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 12 }} width={50} />
        <Tooltip content={<DarkTooltip />} />
        <ReferenceLine x={1.0} stroke="rgba(255,255,255,0.3)" strokeDasharray="5 5" label={{ value: '1.0', fill: 'rgba(255,255,255,0.4)', fontSize: 10 }} />
        <Bar dataKey="value" radius={[0, 4, 4, 0]} name="Factor">
          {data.map((entry, idx) => (
            <Cell key={idx} fill={entry.color} />
          ))}
        </Bar>
      </BarChart>
    </ChartContainer>
  );
};

export default PenetrationDepthChart;
