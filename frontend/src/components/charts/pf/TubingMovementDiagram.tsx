/**
 * TubingMovementDiagram.tsx — Horizontal bar showing tubing movements by effect.
 */
import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine } from 'recharts';
import ChartContainer, { DarkTooltip } from '../ChartContainer';
import { CHART_DEFAULTS } from '../ChartTheme';
import { MoveVertical } from 'lucide-react';

interface TubingMovementDiagramProps {
  movements: { piston_in: number; ballooning_in: number; thermal_in: number; total_in: number };
  height?: number;
}

const TubingMovementDiagram: React.FC<TubingMovementDiagramProps> = ({ movements, height = 300 }) => {
  const data = [
    { name: 'Piston', value: movements.piston_in, fill: '#3b82f6' },
    { name: 'Ballooning', value: movements.ballooning_in, fill: '#8b5cf6' },
    { name: 'Thermal', value: movements.thermal_in, fill: '#f59e0b' },
    { name: 'Total', value: movements.total_in, fill: '#10b981' },
  ];

  return (
    <ChartContainer title="Tubing Movement" icon={MoveVertical} height={height}>
      <BarChart data={data} layout="vertical" margin={{ ...CHART_DEFAULTS.margin, left: 80 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_DEFAULTS.gridColor} />
        <XAxis type="number" stroke={CHART_DEFAULTS.axisColor} tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 12 }} label={{ value: 'Movement (inches)', position: 'insideBottom', offset: -5, fill: CHART_DEFAULTS.axisColor }} />
        <YAxis type="category" dataKey="name" stroke={CHART_DEFAULTS.axisColor} tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 12 }} />
        <Tooltip content={<DarkTooltip />} />
        <ReferenceLine x={0} stroke="#fff" strokeWidth={1} />
        <Bar dataKey="value" name="Movement (in)" radius={[0, 4, 4, 0]}>
          {data.map((entry, idx) => (
            <rect key={idx} fill={entry.fill} />
          ))}
        </Bar>
      </BarChart>
    </ChartContainer>
  );
};

export default TubingMovementDiagram;
