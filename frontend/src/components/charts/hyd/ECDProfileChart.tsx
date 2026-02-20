/**
 * ECDProfileChart.tsx — ECD vs TVD with MW, LOT, and frac gradient reference lines.
 */
import React from 'react';
import ChartContainer from '../ChartContainer';
import DepthTrack from '../DepthTrack';
import type { DepthSeries } from '../DepthTrack';
import { HYD_COLORS } from '../ChartTheme';
import { TrendingUp } from 'lucide-react';

interface ECDProfileChartProps {
  /** Array of { tvd, ecd } from ecd_profile */
  data: { tvd: number; ecd: number }[];
  /** Mud weight for reference line */
  mudWeight?: number;
  /** LOT EMW for reference line */
  lotEmw?: number;
  height?: number;
}

const ECDProfileChart: React.FC<ECDProfileChartProps> = ({
  data,
  mudWeight,
  lotEmw,
  height = 400,
}) => {
  if (!data?.length) return null;

  // Add MW and LOT as extra columns for reference lines (as data series)
  const enrichedData = data.map(pt => ({
    ...pt,
    ...(mudWeight !== undefined ? { mw: mudWeight } : {}),
    ...(lotEmw !== undefined ? { lot: lotEmw } : {}),
  }));

  const series: DepthSeries[] = [
    { dataKey: 'ecd', name: 'ECD (ppg)', color: HYD_COLORS.ecd_line, strokeWidth: 3 },
  ];

  if (mudWeight !== undefined) {
    series.push({ dataKey: 'mw', name: 'MW', color: HYD_COLORS.mw_ref, strokeWidth: 1, strokeDasharray: '6 3', dot: false });
  }
  if (lotEmw !== undefined) {
    series.push({ dataKey: 'lot', name: 'LOT', color: HYD_COLORS.lot_ref, strokeWidth: 1, strokeDasharray: '4 4', dot: false });
  }

  return (
    <ChartContainer
      title="ECD Profile vs Depth"
      icon={TrendingUp}
      height={height}
      badge={mudWeight && lotEmw ? { text: `Window: ${(lotEmw - mudWeight).toFixed(1)} ppg`, color: 'bg-green-500/20 text-green-400' } : undefined}
    >
      <DepthTrack
        data={enrichedData}
        series={series}
        depthKey="tvd"
        xLabel="ECD / EMW (ppg)"
        yLabel="TVD (ft)"
        xDomain={[0, 20]}
        xTicks={[0, 5, 10, 15, 20]}
        tooltipFormatter={(val) => `${Number(val).toFixed(2)} ppg`}
      />
    </ChartContainer>
  );
};

export default ECDProfileChart;
