/**
 * FlowRateSensitivity.tsx — Line chart showing how HCI and CTR vary with flow rate.
 */
import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ReferenceLine } from 'recharts';
import ChartContainer, { DarkTooltip } from '../ChartContainer';
import { CHART_DEFAULTS } from '../ChartTheme';
import { TrendingUp } from 'lucide-react';

interface FlowRateSensitivityProps {
  data: Array<{ flow_rate: number; hci?: number; ctr?: number }>;
  currentFlowRate?: number;
  height?: number;
}

const FlowRateSensitivity: React.FC<FlowRateSensitivityProps> = ({
  data, currentFlowRate, height = 350
}) => {
  if (!data?.length) return null;

  return (
    <ChartContainer title="Flow Rate Sensitivity" icon={TrendingUp} height={height}>
      <LineChart data={data} margin={{ ...CHART_DEFAULTS.margin, bottom: 40 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_DEFAULTS.gridColor} />
        <XAxis
          dataKey="flow_rate"
          stroke={CHART_DEFAULTS.axisColor}
          tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 12 }}
          label={{ value: 'Flow Rate (gpm)', position: 'insideBottom', offset: -10, fill: CHART_DEFAULTS.axisColor }}
        />
        <YAxis
          stroke={CHART_DEFAULTS.axisColor}
          tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 12 }}
          label={{ value: 'Index', angle: -90, position: 'insideLeft', fill: CHART_DEFAULTS.axisColor }}
        />
        <Tooltip content={<DarkTooltip />} />
        <Legend verticalAlign="bottom" wrapperStyle={{ paddingTop: 24, marginBottom: -16 }} />
        <Line type="monotone" dataKey="hci" name="HCI" stroke="#3b82f6" strokeWidth={2} dot={false} />
        <Line type="monotone" dataKey="ctr" name="CTR" stroke="#10b981" strokeWidth={2} dot={false} />
        {currentFlowRate && (
          <ReferenceLine x={currentFlowRate} stroke="#f59e0b" strokeDasharray="3 3" label={{ value: 'Current', fill: '#f59e0b' }} />
        )}
        <ReferenceLine y={1.0} stroke="#22c55e" strokeDasharray="5 5" label={{ value: 'HCI=1.0 (Good)', fill: '#22c55e', position: 'insideTopRight', dy: -20, fontSize: 11 }} />
        <ReferenceLine y={0.55} stroke="#ef4444" strokeDasharray="5 5" label={{ value: 'CTR=0.55 (Min)', fill: '#ef4444', position: 'insideTopRight', dy: -20, fontSize: 11 }} />
      </LineChart>
    </ChartContainer>
  );
};

export default FlowRateSensitivity;
