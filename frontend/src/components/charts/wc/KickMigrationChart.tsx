/**
 * KickMigrationChart.tsx — Visualizes gas kick migration over time.
 * Shows casing pressure and kick volume expansion as gas rises.
 */
import React from 'react';
import {
  Line, XAxis, YAxis, CartesianGrid, Tooltip, ComposedChart, Area,
} from 'recharts';
import ChartContainer from '../ChartContainer';
import { CHART_DEFAULTS } from '../ChartTheme';
import { TrendingUp } from 'lucide-react';

interface KickMigrationPoint {
  time_min: number;
  kick_top_tvd: number;
  casing_pressure_psi: number;
  kick_volume_bbl: number;
  z_factor: number;
}

interface KickMigrationChartProps {
  data: KickMigrationPoint[];
  maxCasingPressure?: number;
  surfaceArrivalMin?: number | null;
  height?: number;
}

const KickMigrationChart: React.FC<KickMigrationChartProps> = ({
  data,
  maxCasingPressure,
  surfaceArrivalMin,
  height = 340,
}) => {
  if (!data?.length) return null;

  const badge = maxCasingPressure
    ? { text: `Max CP: ${maxCasingPressure} psi${surfaceArrivalMin ? ` | Surface: ${surfaceArrivalMin} min` : ''}`, color: 'text-red-400' }
    : undefined;

  return (
    <ChartContainer title="Gas Kick Migration — Pressure & Volume" icon={TrendingUp} height={height} badge={badge}>
      <ComposedChart data={data} margin={{ top: 20, right: 60, bottom: 20, left: 50 }}>
        <CartesianGrid stroke={CHART_DEFAULTS.gridColor} strokeDasharray="3 3" vertical={false} />

        <XAxis
          dataKey="time_min"
          tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }}
          axisLine={{ stroke: CHART_DEFAULTS.axisColor }}
          label={{ value: 'Time (min)', position: 'insideBottom', offset: -10, fill: CHART_DEFAULTS.labelColor, fontSize: 11 }}
        />

        <YAxis
          yAxisId="pressure"
          tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }}
          axisLine={{ stroke: CHART_DEFAULTS.axisColor }}
          label={{ value: 'Casing Pressure (psi)', angle: -90, position: 'insideLeft', fill: CHART_DEFAULTS.labelColor, fontSize: 11 }}
        />

        <YAxis
          yAxisId="volume"
          orientation="right"
          tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }}
          axisLine={{ stroke: CHART_DEFAULTS.axisColor }}
          label={{ value: 'Kick Volume (bbl)', angle: 90, position: 'insideRight', fill: CHART_DEFAULTS.labelColor, fontSize: 11 }}
        />

        <Tooltip
          contentStyle={{
            background: CHART_DEFAULTS.tooltipBg,
            border: `1px solid ${CHART_DEFAULTS.tooltipBorder}`,
            borderRadius: '12px',
            fontSize: '11px',
          }}
          labelStyle={{ color: '#999' }}
          labelFormatter={(v) => `Time: ${v} min`}
        />

        <Area
          yAxisId="volume"
          type="monotone"
          dataKey="kick_volume_bbl"
          fill="rgba(251,146,60,0.15)"
          stroke="#fb923c"
          strokeWidth={2}
          name="Kick Volume (bbl)"
        />

        <Line
          yAxisId="pressure"
          type="monotone"
          dataKey="casing_pressure_psi"
          stroke="#ef4444"
          strokeWidth={2.5}
          dot={false}
          name="Casing Pressure (psi)"
        />
      </ComposedChart>
    </ChartContainer>
  );
};

export default KickMigrationChart;
