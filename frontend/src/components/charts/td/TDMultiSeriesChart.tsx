/**
 * TDMultiSeriesChart.tsx — Multi-operation axial force vs depth overlay.
 * Shows up to 5 operations (trip_out, trip_in, rotating, sliding, lowering) on one chart.
 */
import React from 'react';
import ChartContainer from '../ChartContainer';
import DepthTrack from '../DepthTrack';
import type { DepthSeries, DepthRefLine } from '../DepthTrack';
import { TD_COLORS } from '../ChartTheme';
import { ArrowUpDown } from 'lucide-react';

interface TDMultiSeriesChartProps {
  /** Combined data: each row has { md, trip_out, trip_in, rotating, sliding, lowering } */
  data: Array<Record<string, number>>;
  /** Active operations to display */
  operations?: string[];
  /** Casing shoe MD for reference line */
  casingShoe?: number;
  height?: number;
}

const OP_LABELS: Record<string, string> = {
  trip_out: 'Trip Out',
  trip_in: 'Trip In',
  rotating: 'Rotating',
  sliding: 'Sliding',
  lowering: 'Lowering',
  back_ream: 'Back Ream',
};

const TDMultiSeriesChart: React.FC<TDMultiSeriesChartProps> = ({
  data,
  operations = ['trip_out', 'trip_in', 'rotating', 'sliding'],
  casingShoe,
  height = 450,
}) => {
  if (!data?.length) return null;

  const series: DepthSeries[] = operations
    .filter(op => data.some(d => d[op] !== undefined))
    .map(op => ({
      dataKey: op,
      name: OP_LABELS[op] || op,
      color: TD_COLORS[op] || '#888',
      strokeWidth: 2,
    }));

  const referenceLines: DepthRefLine[] = [];

  if (casingShoe) {
    referenceLines.push({
      y: casingShoe,
      label: 'Casing Shoe',
      color: 'rgba(255,255,255,0.3)',
      strokeDasharray: '8 4',
    });
  }

  return (
    <ChartContainer
      title="Axial Force vs Depth — Multi-Operation"
      icon={ArrowUpDown}
      height={height}
    >
      <DepthTrack
        data={data}
        series={series}
        depthKey="md"
        xLabel="Axial Force (klb)"
        yLabel="MD (ft)"
        referenceLines={referenceLines}
        tooltipFormatter={(val) => `${Number(val).toLocaleString(undefined, { maximumFractionDigits: 0 })} lb`}
      />
    </ChartContainer>
  );
};

export default TDMultiSeriesChart;
