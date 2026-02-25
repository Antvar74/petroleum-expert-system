/**
 * TensionProfile.tsx — Stacked bar showing tension load components.
 * Air weight, buoyancy correction, shock, bending, overpull.
 */
import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ReferenceLine } from 'recharts';
import ChartContainer, { DarkTooltip } from '../ChartContainer';
import { CHART_DEFAULTS } from '../ChartTheme';
import { ArrowUp } from 'lucide-react';

interface TensionProfileProps {
  tensionLoad: { buoyant_weight_lbs?: number; shock_load_lbs?: number; bending_load_lbs?: number; overpull_lbs?: number; total_tension_lbs?: number; pipe_body_yield_lbs?: number } | null;
  height?: number;
}

const TensionProfile: React.FC<TensionProfileProps> = ({ tensionLoad, height = 350 }) => {
  if (!tensionLoad) return null;

  const data = [
    {
      name: 'Tensión',
      buoyant: Math.round(tensionLoad.buoyant_weight_lbs || 0),
      shock: Math.round(tensionLoad.shock_load_lbs || 0),
      bending: Math.round(tensionLoad.bending_load_lbs || 0),
      overpull: Math.round(tensionLoad.overpull_lbs || 0),
    },
  ];

  const total = tensionLoad.total_tension_lbs || 0;
  const rating = tensionLoad.pipe_body_yield_lbs || 0;

  return (
    <ChartContainer
      title="Perfil de Tensión"
      icon={ArrowUp}
      height={height}
      badge={{ text: `Total: ${(total / 1000).toFixed(0)}k lbs`, color: 'bg-indigo-500/20 text-indigo-400' }}
    >
      <BarChart data={data} margin={{ ...CHART_DEFAULTS.margin, left: 50 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_DEFAULTS.gridColor} />
        <XAxis
          dataKey="name"
          stroke={CHART_DEFAULTS.axisColor}
          tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 12 }}
        />
        <YAxis
          stroke={CHART_DEFAULTS.axisColor}
          tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }}
          tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}k`}
          label={{ value: 'Carga (lbs)', angle: -90, position: 'insideLeft', fill: CHART_DEFAULTS.labelColor, fontSize: 11 }}
        />
        <Tooltip content={<DarkTooltip formatter={(v: number) => `${Number(v).toLocaleString()} lbs`} />} />
        <Legend wrapperStyle={{ color: CHART_DEFAULTS.axisColor, fontSize: 11 }} />
        <Bar dataKey="buoyant" stackId="a" fill="#6366f1" fillOpacity={0.7} name="Peso Flotado" radius={[0, 0, 0, 0]} />
        <Bar dataKey="shock" stackId="a" fill="#ef4444" fillOpacity={0.7} name="Shock" />
        <Bar dataKey="bending" stackId="a" fill="#f97316" fillOpacity={0.7} name="Flexión" />
        <Bar dataKey="overpull" stackId="a" fill="#eab308" fillOpacity={0.7} name="Overpull" radius={[4, 4, 0, 0]} />
        {rating > 0 && (
          <ReferenceLine y={rating} stroke="#22c55e" strokeDasharray="8 4" strokeWidth={2}
            label={{ value: `Yield: ${(rating / 1000).toFixed(0)}k`, fill: '#22c55e', fontSize: 10, position: 'right' }} />
        )}
      </BarChart>
    </ChartContainer>
  );
};

export default TensionProfile;
