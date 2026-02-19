/**
 * CleanupEfficiencyProfile.tsx — Depth track showing cleanup metrics vs depth.
 */
import React from 'react';
import ChartContainer from '../ChartContainer';
import DepthTrack from '../DepthTrack';
import type { DepthSeries } from '../DepthTrack';
import { Droplets } from 'lucide-react';

interface CleanupEfficiencyProfileProps {
  data: any[];
  height?: number;
}

const CleanupEfficiencyProfile: React.FC<CleanupEfficiencyProfileProps> = ({ data, height = 400 }) => {
  if (!data?.length) return null;

  const series: DepthSeries[] = [
    { dataKey: 'annular_velocity', name: 'Annular Vel. (ft/min)', color: '#3b82f6', strokeWidth: 2 },
    { dataKey: 'transport_velocity', name: 'Transport Vel. (ft/min)', color: '#10b981', strokeWidth: 2 },
    { dataKey: 'slip_velocity', name: 'Slip Vel. (ft/min)', color: '#ef4444', strokeWidth: 2, strokeDasharray: '5 5' },
  ];

  return (
    <ChartContainer title="Cleanup Efficiency Profile" icon={Droplets} height={height}>
      <DepthTrack
        data={data}
        series={series}
        depthKey="md"
        xLabel="Velocity (ft/min)"
        yLabel="Depth (ft)"
      />
    </ChartContainer>
  );
};

export default CleanupEfficiencyProfile;
