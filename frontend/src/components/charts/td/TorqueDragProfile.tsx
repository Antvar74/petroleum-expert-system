/**
 * TorqueDragProfile.tsx — Torque and Drag vs Depth with dual X-axes.
 */
import React from 'react';
import ChartContainer from '../ChartContainer';
import DepthTrack from '../DepthTrack';
import type { DepthSeries } from '../DepthTrack';
import { Activity } from 'lucide-react';

interface TorqueDragProfileProps {
  /** Station results with md, torque, drag fields */
  data: Array<Record<string, number>>;
  height?: number;
}

const TorqueDragProfile: React.FC<TorqueDragProfileProps> = ({ data, height = 400 }) => {
  if (!data?.length) return null;

  const series: DepthSeries[] = [
    { dataKey: 'torque', name: 'Torque (ft-lb)', color: '#f97316', strokeWidth: 2 },
    { dataKey: 'drag', name: 'Drag (lb)', color: '#3b82f6', strokeWidth: 2, strokeDasharray: '5 3' },
  ];

  return (
    <ChartContainer title="Torque & Drag vs Depth" icon={Activity} height={height}>
      <DepthTrack
        data={data}
        series={series}
        depthKey="md"
        xLabel="Force / Torque"
        yLabel="MD (ft)"
        tooltipFormatter={(val) => `${Number(val).toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
      />
    </ChartContainer>
  );
};

export default TorqueDragProfile;
