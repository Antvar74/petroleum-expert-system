/**
 * HookloadComparisonBar.tsx — Horizontal bar chart comparing hookloads across operations.
 */
import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
  ReferenceLine,
  LabelList,
} from 'recharts';
import ChartContainer, { DarkTooltip } from '../ChartContainer';
import { TD_COLORS, CHART_DEFAULTS } from '../ChartTheme';
import { BarChart3 } from 'lucide-react';

interface HookloadComparisonBarProps {
  /** Array of { operation, hookload_klb } */
  data: { operation: string; hookload_klb: number; label: string }[];
  /** Buoyed string weight for reference line */
  buoyedWeight?: number;
  height?: number;
}

const HookloadComparisonBar: React.FC<HookloadComparisonBarProps> = ({
  data,
  buoyedWeight,
  height = 200,
}) => {
  if (!data?.length) return null;

  return (
    <ChartContainer title="Hookload by Operation" icon={BarChart3} height={height}>
      <BarChart data={data} layout="vertical" margin={{ top: 5, right: 50, bottom: 5, left: 80 }}>
        <CartesianGrid stroke={CHART_DEFAULTS.gridColor} strokeDasharray="3 3" horizontal={false} />
        <XAxis
          type="number"
          tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }}
          axisLine={{ stroke: CHART_DEFAULTS.axisColor }}
          label={{ value: 'Hookload (klb)', position: 'insideBottom', offset: -5, fill: CHART_DEFAULTS.labelColor, fontSize: 11 }}
        />
        <YAxis
          dataKey="label"
          type="category"
          tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }}
          axisLine={{ stroke: CHART_DEFAULTS.axisColor }}
          width={75}
        />
        <Tooltip content={<DarkTooltip />} />
        {buoyedWeight && (
          <ReferenceLine
            x={buoyedWeight}
            stroke="rgba(255,255,255,0.3)"
            strokeDasharray="6 3"
            label={{ value: 'Buoyed Wt', fill: 'rgba(255,255,255,0.4)', fontSize: 10, position: 'top' }}
          />
        )}
        <Bar dataKey="hookload_klb" name="Hookload" radius={[0, 4, 4, 0]}>
          {data.map((entry, i) => (
            <Cell key={i} fill={TD_COLORS[entry.operation] || '#888'} fillOpacity={0.8} />
          ))}
          <LabelList dataKey="hookload_klb" position="right" fill="rgba(255,255,255,0.6)" fontSize={11} formatter={(v: any) => `${v} klb`} />
        </Bar>
      </BarChart>
    </ChartContainer>
  );
};

export default HookloadComparisonBar;
