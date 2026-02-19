/**
 * GrainDistributionChart.tsx — PSD curve showing cumulative grain size distribution.
 */
import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine } from 'recharts';
import ChartContainer, { DarkTooltip } from '../ChartContainer';
import { CHART_DEFAULTS } from '../ChartTheme';
import { BarChart3 } from 'lucide-react';

interface GrainDistributionChartProps {
  psd: { d10_mm: number; d50_mm: number; d90_mm: number };
  sieveData?: { sieve_sizes_mm?: number[]; cumulative_passing_pct?: number[] };
  height?: number;
}

const GrainDistributionChart: React.FC<GrainDistributionChartProps> = ({ psd, sieveData, height = 350 }) => {
  if (!psd) return null;

  // Build curve data from sieve data or generate from D values
  let data: { size: number; passing: number }[] = [];

  const sizes = sieveData?.sieve_sizes_mm;
  const passing = sieveData?.cumulative_passing_pct;

  if (sizes && passing && sizes.length === passing.length) {
    data = sizes.map((s: number, i: number) => ({
      size: s,
      passing: passing[i],
    })).sort((a, b) => b.size - a.size);
  } else {
    // Approximate from D values
    data = [
      { size: psd.d90_mm * 2, passing: 98 },
      { size: psd.d90_mm, passing: 90 },
      { size: psd.d50_mm, passing: 50 },
      { size: psd.d10_mm, passing: 10 },
      { size: psd.d10_mm * 0.5, passing: 2 },
    ].sort((a, b) => b.size - a.size);
  }

  return (
    <ChartContainer title="Curva Granulométrica (PSD)" icon={BarChart3} height={height}
      badge={{ text: `D50: ${psd.d50_mm} mm`, color: 'bg-amber-500/20 text-amber-400' }}>
      <LineChart data={data} margin={CHART_DEFAULTS.margin}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_DEFAULTS.gridColor} />
        <XAxis dataKey="size" stroke={CHART_DEFAULTS.axisColor} tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }}
          label={{ value: 'Tamaño (mm)', position: 'bottom', fill: CHART_DEFAULTS.axisColor }}
          reversed />
        <YAxis stroke={CHART_DEFAULTS.axisColor} tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 12 }}
          domain={[0, 100]}
          label={{ value: '% Pasante', angle: -90, position: 'insideLeft', fill: CHART_DEFAULTS.axisColor }} />
        <Tooltip content={<DarkTooltip />} />
        <ReferenceLine y={10} stroke="#ef4444" strokeDasharray="5 5" label={{ value: 'D10', fill: '#ef4444', fontSize: 10 }} />
        <ReferenceLine y={50} stroke="#f59e0b" strokeDasharray="5 5" label={{ value: 'D50', fill: '#f59e0b', fontSize: 10 }} />
        <ReferenceLine y={90} stroke="#22c55e" strokeDasharray="5 5" label={{ value: 'D90', fill: '#22c55e', fontSize: 10 }} />
        <Line type="monotone" dataKey="passing" stroke="#f59e0b" strokeWidth={2} dot={{ fill: '#f59e0b', r: 4 }} name="% Pasante" />
      </LineChart>
    </ChartContainer>
  );
};

export default GrainDistributionChart;
