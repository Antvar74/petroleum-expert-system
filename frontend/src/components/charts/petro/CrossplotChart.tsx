/**
 * CrossplotChart.tsx — Density vs Neutron crossplot with lithology lines and gas detection.
 */
import React from 'react';
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ReferenceLine,
} from 'recharts';
import ChartContainer, { DarkTooltip } from '../ChartContainer';
import { CHART_DEFAULTS } from '../ChartTheme';
import { GitBranchPlus } from 'lucide-react';

interface CrossplotProps {
  points: { rhob: number; nphi: number; gas_flag: boolean; md?: number }[];
  gasCount: number;
  totalPoints: number;
  height?: number;
}

const CrossplotChart: React.FC<CrossplotProps> = ({ points, gasCount, totalPoints, height = 420 }) => {
  if (!points?.length) return null;

  const normalPts = points.filter(p => !p.gas_flag);
  const gasPts = points.filter(p => p.gas_flag);

  return (
    <ChartContainer
      title="Density-Neutron Crossplot"
      icon={GitBranchPlus}
      height={height}
      badge={{
        text: gasCount > 0 ? `${gasCount} gas pts` : `${totalPoints} pts`,
        color: gasCount > 0 ? 'bg-red-500/20 text-red-400' : 'bg-blue-500/20 text-blue-400',
      }}
    >
      <ScatterChart margin={{ ...CHART_DEFAULTS.margin, left: 10, bottom: 30 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_DEFAULTS.gridColor} />
        <XAxis type="number" dataKey="nphi"
          domain={[-0.05, 0.45]}
          stroke={CHART_DEFAULTS.axisColor}
          tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 10 }}
          label={{ value: 'NPHI (v/v)', position: 'bottom', fill: CHART_DEFAULTS.axisColor, fontSize: 11 }}
        />
        <YAxis type="number" dataKey="rhob"
          domain={[1.8, 3.0]} reversed
          stroke={CHART_DEFAULTS.axisColor}
          tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 10 }}
          label={{ value: 'RHOB (g/cc)', angle: -90, position: 'insideLeft', fill: CHART_DEFAULTS.axisColor }}
        />
        <Tooltip content={<DarkTooltip />} />

        {/* Lithology reference lines */}
        <ReferenceLine x={-0.02} stroke="#eab30855" strokeDasharray="6 3" label={{ value: 'SS', fill: '#eab308', fontSize: 9 }} />
        <ReferenceLine x={0.00} stroke="#06b6d455" strokeDasharray="6 3" label={{ value: 'LS', fill: '#06b6d4', fontSize: 9 }} />
        <ReferenceLine x={0.02} stroke="#a855f755" strokeDasharray="6 3" label={{ value: 'DOL', fill: '#a855f7', fontSize: 9 }} />

        {normalPts.length > 0 && (
          <Scatter data={normalPts} fill="#3b82f6" stroke="#2563eb" strokeWidth={1} name="Normal" />
        )}
        {gasPts.length > 0 && (
          <Scatter data={gasPts} fill="#ef4444" stroke="#dc2626" strokeWidth={1} name="Gas Effect" shape="diamond" />
        )}

        <Legend wrapperStyle={{ fontSize: 10, color: 'rgba(255,255,255,0.5)' }} />
      </ScatterChart>
    </ChartContainer>
  );
};

export default CrossplotChart;
