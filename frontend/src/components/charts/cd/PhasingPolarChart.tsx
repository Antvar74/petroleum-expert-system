/**
 * PhasingPolarChart.tsx — Phasing sensitivity showing PR for each phasing angle.
 * Displayed as a bar chart with angle labels.
 */
import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell } from 'recharts';
import ChartContainer, { DarkTooltip } from '../ChartContainer';
import { CHART_DEFAULTS } from '../ChartTheme';
import { Compass } from 'lucide-react';

interface PhasingPolarChartProps {
  optimization: {
    optimal_configuration: { spf: number; phasing_deg: number; productivity_ratio: number };
    phasing_sensitivity: { phasing_deg: number; productivity_ratio: number; skin_total: number }[];
  };
  height?: number;
}

const PhasingPolarChart: React.FC<PhasingPolarChartProps> = ({ optimization, height = 350 }) => {
  if (!optimization?.phasing_sensitivity) return null;

  const optimalPhasing = optimization.optimal_configuration.phasing_deg;

  const data = optimization.phasing_sensitivity.map(d => ({
    phasing: `${d.phasing_deg}°`,
    pr: Math.round(d.productivity_ratio * 1000) / 10,
    skin: d.skin_total,
    isOptimal: d.phasing_deg === optimalPhasing,
  }));

  const colors = ['#ef4444', '#f97316', '#22c55e', '#3b82f6', '#a855f7'];

  return (
    <ChartContainer
      title="Sensibilidad Phasing — Ratio Productividad"
      icon={Compass}
      height={height}
      badge={{ text: `Óptimo: ${optimalPhasing}°`, color: 'bg-green-500/20 text-green-400' }}
    >
      <BarChart data={data} margin={CHART_DEFAULTS.margin}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_DEFAULTS.gridColor} />
        <XAxis dataKey="phasing" stroke={CHART_DEFAULTS.axisColor} tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }} />
        <YAxis stroke={CHART_DEFAULTS.axisColor} tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }}
          label={{ value: 'PR %', angle: -90, position: 'insideLeft', fill: CHART_DEFAULTS.axisColor }} />
        <Tooltip content={<DarkTooltip />} />
        <Bar dataKey="pr" name="PR %" radius={[4, 4, 0, 0]}>
          {data.map((entry, idx) => (
            <Cell key={idx} fill={entry.isOptimal ? '#22c55e' : colors[idx % colors.length]} opacity={entry.isOptimal ? 1 : 0.6} />
          ))}
        </Bar>
      </BarChart>
    </ChartContainer>
  );
};

export default PhasingPolarChart;
