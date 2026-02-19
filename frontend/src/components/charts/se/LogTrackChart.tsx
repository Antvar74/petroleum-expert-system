/**
 * LogTrackChart.tsx — Multi-curve log display (GR, Porosity, Sw, Vsh vs depth).
 */
import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ReferenceLine } from 'recharts';
import ChartContainer, { DarkTooltip } from '../ChartContainer';
import { CHART_DEFAULTS } from '../ChartTheme';
import { BarChart3 } from 'lucide-react';

interface LogTrackChartProps {
  processedLogs: {
    md: number; gr: number; phi: number; sw: number; vsh: number;
  }[];
  cutoffs?: { phi_min: number; sw_max: number; vsh_max: number };
  height?: number;
}

const LogTrackChart: React.FC<LogTrackChartProps> = ({ processedLogs, cutoffs, height = 420 }) => {
  if (!processedLogs?.length) return null;

  const data = processedLogs.map(d => ({
    depth: d.md,
    phi: Math.round(d.phi * 1000) / 10,
    sw: Math.round(d.sw * 1000) / 10,
    vsh: Math.round(d.vsh * 1000) / 10,
  }));

  return (
    <ChartContainer
      title="Log Track — φ, Sw, Vsh vs Profundidad"
      icon={BarChart3}
      height={height}
      badge={{ text: `${processedLogs.length} pts`, color: 'bg-blue-500/20 text-blue-400' }}
    >
      <LineChart data={data} margin={{ ...CHART_DEFAULTS.margin, left: 5, bottom: 30 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_DEFAULTS.gridColor} />
        <XAxis dataKey="depth" stroke={CHART_DEFAULTS.axisColor} tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 10 }}
          label={{ value: 'MD (ft)', position: 'bottom', fill: CHART_DEFAULTS.axisColor, fontSize: 11 }} />
        <YAxis stroke={CHART_DEFAULTS.axisColor} tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 10 }}
          domain={[0, 100]}
          label={{ value: '%', angle: -90, position: 'insideLeft', fill: CHART_DEFAULTS.axisColor }} />
        <Tooltip content={<DarkTooltip />} />
        <Legend wrapperStyle={{ fontSize: 11, color: 'rgba(255,255,255,0.5)' }} />
        {cutoffs && (
          <>
            <ReferenceLine y={cutoffs.phi_min * 100} stroke="#22c55e" strokeDasharray="4 4"
              label={{ value: `φ min ${cutoffs.phi_min * 100}%`, fill: '#22c55e', fontSize: 9, position: 'right' }} />
            <ReferenceLine y={cutoffs.sw_max * 100} stroke="#3b82f6" strokeDasharray="4 4"
              label={{ value: `Sw max ${cutoffs.sw_max * 100}%`, fill: '#3b82f6', fontSize: 9, position: 'right' }} />
            <ReferenceLine y={cutoffs.vsh_max * 100} stroke="#f97316" strokeDasharray="4 4"
              label={{ value: `Vsh max ${cutoffs.vsh_max * 100}%`, fill: '#f97316', fontSize: 9, position: 'right' }} />
          </>
        )}
        <Line type="monotone" dataKey="phi" stroke="#22c55e" strokeWidth={2} dot={{ r: 2 }} name="φ %" />
        <Line type="monotone" dataKey="sw" stroke="#3b82f6" strokeWidth={2} dot={{ r: 2 }} name="Sw %" />
        <Line type="monotone" dataKey="vsh" stroke="#f97316" strokeWidth={2} dot={{ r: 2 }} name="Vsh %" />
      </LineChart>
    </ChartContainer>
  );
};

export default LogTrackChart;
