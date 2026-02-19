/**
 * MSEBreakdownChart.tsx — Pie/donut showing rotary vs thrust MSE components.
 */
import React from 'react';
import { PieChart, Pie, Cell, Tooltip } from 'recharts';
import ChartContainer, { DarkTooltip } from '../ChartContainer';
import { CHART_DEFAULTS } from '../ChartTheme';
import { PieChart as PieIcon } from 'lucide-react';

interface MSEBreakdownChartProps {
  mse: {
    mse_total_psi: number;
    mse_rotary_psi: number;
    mse_thrust_psi: number;
    rotary_pct: number;
    thrust_pct: number;
    classification: string;
    efficiency_pct: number;
  };
  height?: number;
}

const MSEBreakdownChart: React.FC<MSEBreakdownChartProps> = ({ mse, height = 350 }) => {
  if (!mse) return null;

  const data = [
    { name: 'Rotario', value: mse.mse_rotary_psi, color: '#8b5cf6' },
    { name: 'Empuje', value: mse.mse_thrust_psi, color: '#f97316' },
  ];

  return (
    <ChartContainer
      title="MSE — Desglose Rotario vs Empuje"
      icon={PieIcon}
      height={height}
      badge={{ text: `${(mse.mse_total_psi / 1000).toFixed(0)}k psi`, color: 'bg-violet-500/20 text-violet-400' }}
    >
      <PieChart margin={CHART_DEFAULTS.margin}>
        <Pie
          data={data}
          cx="50%" cy="45%"
          innerRadius={55} outerRadius={90}
          paddingAngle={4}
          dataKey="value"
          label={({ name, value }) => `${name}: ${(value / 1000).toFixed(0)}k`}
        >
          {data.map((entry, idx) => (
            <Cell key={idx} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip content={<DarkTooltip />} />
        <text x="50%" y="44%" textAnchor="middle" fill="white" fontSize={20} fontWeight="bold">
          {mse.efficiency_pct}%
        </text>
        <text x="50%" y="52%" textAnchor="middle" fill="rgba(255,255,255,0.4)" fontSize={10}>
          Eficiencia
        </text>
      </PieChart>
    </ChartContainer>
  );
};

export default MSEBreakdownChart;
