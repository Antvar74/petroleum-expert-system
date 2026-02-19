/**
 * SnubbingForceChart.tsx — Visual comparison of pressure force vs buoyed weight.
 */
import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine } from 'recharts';
import ChartContainer, { DarkTooltip } from '../ChartContainer';
import { CHART_DEFAULTS } from '../ChartTheme';
import { ArrowUpDown } from 'lucide-react';

interface SnubbingForceChartProps {
  snubbing: { snubbing_force_lb: number; pressure_force_lb: number; buoyed_weight_lb: number; pipe_light: boolean; light_heavy_depth_ft: number };
  weightAnalysis?: { air_weight_lb: number; buoyancy_factor: number };
  height?: number;
}

const SnubbingForceChart: React.FC<SnubbingForceChartProps> = ({ snubbing, height = 350 }) => {
  if (!snubbing) return null;

  const data = [
    { name: 'Fuerza Presión', value: snubbing.pressure_force_lb, fill: '#ef4444' },
    { name: 'Peso Flotado', value: snubbing.buoyed_weight_lb, fill: '#22c55e' },
    { name: 'Fuerza Neta', value: snubbing.snubbing_force_lb, fill: snubbing.pipe_light ? '#f59e0b' : '#3b82f6' },
  ];

  return (
    <ChartContainer title="Análisis Snubbing" icon={ArrowUpDown} height={height}
      badge={{ text: snubbing.pipe_light ? 'PIPE LIGHT' : 'PIPE HEAVY', color: snubbing.pipe_light ? 'bg-red-500/20 text-red-400' : 'bg-green-500/20 text-green-400' }}>
      <BarChart data={data} margin={CHART_DEFAULTS.margin}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_DEFAULTS.gridColor} />
        <XAxis dataKey="name" stroke={CHART_DEFAULTS.axisColor} tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }} />
        <YAxis stroke={CHART_DEFAULTS.axisColor} tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 12 }}
          label={{ value: 'Fuerza (lb)', angle: -90, position: 'insideLeft', fill: CHART_DEFAULTS.axisColor }} />
        <Tooltip content={<DarkTooltip />} />
        <ReferenceLine y={0} stroke="#fff" strokeWidth={1} />
        <Bar dataKey="value" name="Fuerza (lb)" radius={[4, 4, 0, 0]}>
          {data.map((entry, idx) => (
            <rect key={idx} fill={entry.fill} />
          ))}
        </Bar>
      </BarChart>
    </ChartContainer>
  );
};

export default SnubbingForceChart;
