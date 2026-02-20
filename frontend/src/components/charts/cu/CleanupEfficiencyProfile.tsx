/**
 * CleanupEfficiencyProfile.tsx — Line chart showing HCI and CTR vs well inclination.
 * Shows how cleaning efficiency degrades as the wellbore deviates from vertical.
 * Dashed lines of the same color = minimum acceptable thresholds.
 */
import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ReferenceLine } from 'recharts';
import ChartContainer, { DarkTooltip } from '../ChartContainer';
import { CHART_DEFAULTS } from '../ChartTheme';
import { Droplets } from 'lucide-react';

const HCI_COLOR = '#3b82f6';
const CTR_COLOR = '#f97316';

interface CleanupEfficiencyProfileProps {
  data: { inclination: number; hci: number; ctr: number }[];
  currentInclination?: number;
  height?: number;
}

const CleanupEfficiencyProfile: React.FC<CleanupEfficiencyProfileProps> = ({
  data, currentInclination, height = 400
}) => {
  if (!data?.length) return null;

  return (
    <ChartContainer title="Cleanup Efficiency vs Inclination" icon={Droplets} height={height}>
      <LineChart data={data} margin={{ ...CHART_DEFAULTS.margin, bottom: 40 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_DEFAULTS.gridColor} />
        <XAxis
          dataKey="inclination"
          stroke={CHART_DEFAULTS.axisColor}
          tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 12 }}
          label={{ value: 'Inclination (°)', position: 'insideBottom', offset: -10, fill: CHART_DEFAULTS.axisColor }}
        />
        <YAxis
          stroke={CHART_DEFAULTS.axisColor}
          tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 12 }}
          label={{ value: 'Index', angle: -90, position: 'insideLeft', fill: CHART_DEFAULTS.axisColor }}
          domain={[0, 'auto']}
        />
        <Tooltip content={<DarkTooltip />} />
        <Legend verticalAlign="bottom" wrapperStyle={{ paddingTop: 24 }} />
        {/* Minimum thresholds — same color as their curve, dashed & thinner */}
        <ReferenceLine y={1.0} stroke={HCI_COLOR} strokeDasharray="6 4" strokeWidth={1} strokeOpacity={0.5} label={{ value: 'Min HCI (1.0)', fill: HCI_COLOR, position: 'insideTopRight', fontSize: 10 }} />
        <ReferenceLine y={0.55} stroke={CTR_COLOR} strokeDasharray="6 4" strokeWidth={1} strokeOpacity={0.5} label={{ value: 'Min CTR (0.55)', fill: CTR_COLOR, position: 'insideTopRight', fontSize: 10 }} />
        {currentInclination !== undefined && currentInclination > 0 && (
          <ReferenceLine x={currentInclination} stroke="#f59e0b" strokeDasharray="3 3" strokeWidth={1} label={{ value: `${currentInclination}°`, fill: '#f59e0b', position: 'top', fontSize: 11 }} />
        )}
        {/* Data curves — solid & bold */}
        <Line type="monotone" dataKey="hci" name="HCI" stroke={HCI_COLOR} strokeWidth={2.5} dot={false} />
        <Line type="monotone" dataKey="ctr" name="CTR" stroke={CTR_COLOR} strokeWidth={2.5} dot={false} />
      </LineChart>
    </ChartContainer>
  );
};

export default CleanupEfficiencyProfile;
