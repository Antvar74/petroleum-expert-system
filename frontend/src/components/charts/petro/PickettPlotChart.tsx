/**
 * PickettPlotChart.tsx — Log-log Pickett plot (Rt vs porosity) with iso-Sw lines.
 */
import React from 'react';
import {
  Scatter, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  Line, ComposedChart,
} from 'recharts';
import ChartContainer, { DarkTooltip } from '../ChartContainer';
import { CHART_DEFAULTS } from '../ChartTheme';
import { Crosshair } from 'lucide-react';

interface PickettPlotProps {
  points: { log_phi: number; log_rt: number; sw?: number }[];
  isoSwLines: Record<string, { log_phi: number; log_rt: number }[]>;
  regression?: { slope: number; intercept: number; estimated_m: number };
  height?: number;
}

const SW_COLORS: Record<string, string> = {
  'Sw=20%': '#22c55e',
  'Sw=40%': '#06b6d4',
  'Sw=60%': '#eab308',
  'Sw=80%': '#f97316',
  'Sw=100%': '#ef4444',
};

const PickettPlotChart: React.FC<PickettPlotProps> = ({ points, isoSwLines, regression, height = 420 }) => {
  if (!points?.length) return null;

  // Build combined data for iso-Sw lines + scatter
  const allData: any[] = [];

  // Add iso-Sw line points
  Object.entries(isoSwLines || {}).forEach(([label, linePoints]) => {
    linePoints.forEach(pt => {
      allData.push({ ...pt, [label]: pt.log_rt });
    });
  });

  return (
    <ChartContainer
      title="Pickett Plot — log(Rt) vs log(φ)"
      icon={Crosshair}
      height={height}
      badge={regression ? {
        text: `m ≈ ${regression.estimated_m}`,
        color: 'bg-cyan-500/20 text-cyan-400',
      } : undefined}
    >
      <ComposedChart margin={{ ...CHART_DEFAULTS.margin, left: 10, bottom: 30 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_DEFAULTS.gridColor} />
        <XAxis type="number" dataKey="log_phi"
          domain={[-1.5, -0.3]}
          stroke={CHART_DEFAULTS.axisColor}
          tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 10 }}
          label={{ value: 'log₁₀(φ)', position: 'bottom', fill: CHART_DEFAULTS.axisColor, fontSize: 11 }}
        />
        <YAxis type="number"
          domain={[-0.5, 3.5]}
          stroke={CHART_DEFAULTS.axisColor}
          tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 10 }}
          label={{ value: 'log₁₀(Rt)', angle: -90, position: 'insideLeft', fill: CHART_DEFAULTS.axisColor }}
        />
        <Tooltip content={<DarkTooltip />} />

        {/* Iso-Sw lines */}
        {Object.entries(isoSwLines || {}).map(([label, linePoints]) => (
          <Line
            key={label}
            data={linePoints}
            dataKey="log_rt"
            stroke={SW_COLORS[label] || '#94a3b8'}
            strokeWidth={1}
            strokeDasharray="4 4"
            dot={false}
            name={label}
          />
        ))}

        {/* Data points */}
        <Scatter
          data={points}
          fill="#06b6d4"
          stroke="#0891b2"
          strokeWidth={1}
          name="Data"
        />

        <Legend wrapperStyle={{ fontSize: 10, color: 'rgba(255,255,255,0.5)' }} />
      </ComposedChart>
    </ChartContainer>
  );
};

export default PickettPlotChart;
