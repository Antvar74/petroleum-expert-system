/**
 * ForceComponentsBar.tsx — Stacked/grouped bar showing piston, ballooning, temperature forces.
 */
import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine } from 'recharts';
import ChartContainer, { DarkTooltip } from '../ChartContainer';
import { CHART_DEFAULTS } from '../ChartTheme';
import { BarChart3 } from 'lucide-react';

interface ForceComponentsBarProps {
  forces: { piston: number; ballooning: number; temperature: number; total: number };
  height?: number;
}

const ForceComponentsBar: React.FC<ForceComponentsBarProps> = ({ forces, height = 350 }) => {
  const data = [
    { name: 'Piston', value: forces.piston, fill: '#3b82f6' },
    { name: 'Ballooning', value: forces.ballooning, fill: '#8b5cf6' },
    { name: 'Temperature', value: forces.temperature, fill: '#f59e0b' },
    { name: 'Total', value: forces.total, fill: forces.total > 0 ? '#10b981' : '#ef4444' },
  ];

  return (
    <ChartContainer
      title="Force Components"
      icon={BarChart3}
      height={height}
      badge={{ text: forces.total > 0 ? 'TENSION' : 'COMPRESSION', color: forces.total > 0 ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400' }}
    >
      <BarChart data={data} margin={CHART_DEFAULTS.margin}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_DEFAULTS.gridColor} />
        <XAxis dataKey="name" stroke={CHART_DEFAULTS.axisColor} tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 12 }} />
        <YAxis stroke={CHART_DEFAULTS.axisColor} tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 12 }} label={{ value: 'Force (lbs)', angle: -90, position: 'insideLeft', fill: CHART_DEFAULTS.axisColor }} />
        <Tooltip content={<DarkTooltip />} />
        <ReferenceLine y={0} stroke="#fff" strokeWidth={1} />
        <Bar dataKey="value" name="Force (lbs)" radius={[4, 4, 0, 0]}>
          {data.map((entry, idx) => (
            <rect key={idx} fill={entry.fill} />
          ))}
        </Bar>
      </BarChart>
    </ChartContainer>
  );
};

export default ForceComponentsBar;
