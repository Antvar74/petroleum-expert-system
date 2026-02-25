/**
 * DepthTrack.tsx — Vertical depth chart with Y-axis inverted (0 at top, TD at bottom).
 * Used for T&D force profiles, ECD profiles, wellbore pressure profiles.
 */
import React from 'react';
import {
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  ComposedChart,
} from 'recharts';
import { CHART_DEFAULTS } from './ChartTheme';
import { DarkTooltip } from './ChartContainer';

export interface DepthSeries {
  dataKey: string;
  name: string;
  color: string;
  strokeWidth?: number;
  strokeDasharray?: string;
  dot?: boolean;
}

export interface DepthRefLine {
  y: number;
  label: string;
  color: string;
  strokeDasharray?: string;
}

interface DepthTrackProps {
  data: Array<Record<string, number>>;
  series: DepthSeries[];
  depthKey?: string; // defaults to 'md'
  xLabel?: string;
  yLabel?: string;
  referenceLines?: DepthRefLine[];
  xDomain?: [number | string, number | string];
  xTicks?: number[];
  showLegend?: boolean;
  tooltipFormatter?: (value: number, name: string) => string;
}

const DepthTrack: React.FC<DepthTrackProps> = ({
  data,
  series,
  depthKey = 'md',
  xLabel = '',
  yLabel = 'Depth (ft)',
  referenceLines = [],
  xDomain,
  xTicks,
  showLegend = true,
  tooltipFormatter,
}) => {
  if (!data?.length) return null;

  // Sort data by depth ascending so Recharts plots correctly
  const sorted = [...data].sort((a, b) => (a[depthKey] ?? 0) - (b[depthKey] ?? 0));
  const maxDepth = Math.max(...sorted.map(d => d[depthKey] ?? 0));

  return (
    <ComposedChart
      data={sorted}
      layout="vertical"
      margin={{ top: 10, right: 30, bottom: 30, left: 60 }}
    >
      <CartesianGrid
        stroke={CHART_DEFAULTS.gridColor}
        strokeDasharray="3 3"
        horizontal
        vertical={false}
      />

      <YAxis
        dataKey={depthKey}
        type="number"
        domain={[0, maxDepth]}
        tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }}
        tickLine={{ stroke: CHART_DEFAULTS.axisColor }}
        axisLine={{ stroke: CHART_DEFAULTS.axisColor }}
        label={{
          value: yLabel,
          angle: -90,
          position: 'insideLeft',
          offset: -45,
          fill: CHART_DEFAULTS.labelColor,
          fontSize: 11,
        }}
      />

      <XAxis
        type="number"
        domain={xDomain || ['auto', 'auto']}
        ticks={xTicks}
        tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }}
        tickLine={{ stroke: CHART_DEFAULTS.axisColor }}
        axisLine={{ stroke: CHART_DEFAULTS.axisColor }}
        orientation="top"
        label={{
          value: xLabel,
          position: 'insideTop',
          offset: -25,
          fill: CHART_DEFAULTS.labelColor,
          fontSize: 11,
        }}
      />

      <Tooltip content={<DarkTooltip formatter={tooltipFormatter} />} />

      {showLegend && (
        <Legend
          wrapperStyle={{
            color: 'rgba(255,255,255,0.5)',
            fontSize: 11,
            paddingTop: 10,
          }}
        />
      )}

      {/* Reference lines (e.g., casing shoe, zero force) */}
      {referenceLines.map((ref, i) => (
        <ReferenceLine
          key={i}
          y={ref.y}
          stroke={ref.color}
          strokeDasharray={ref.strokeDasharray || '6 3'}
          label={{
            value: ref.label,
            fill: ref.color,
            fontSize: 10,
            position: 'right',
          }}
        />
      ))}

      {/* Data series */}
      {series.map((s) => (
        <Line
          key={s.dataKey}
          dataKey={s.dataKey}
          name={s.name}
          stroke={s.color}
          strokeWidth={s.strokeWidth || 2}
          strokeDasharray={s.strokeDasharray}
          dot={s.dot !== undefined ? s.dot : false}
          type="monotone"
          animationDuration={CHART_DEFAULTS.animationDuration}
        />
      ))}
    </ComposedChart>
  );
};

export default DepthTrack;
