/**
 * KillCirculationChart.tsx — Kill circulation step-by-step pressure schedule.
 * Shows DPP and CP vs strokes with ICP/FCP reference lines.
 */
import React from 'react';
import {
  Line, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, ComposedChart,
} from 'recharts';
import ChartContainer from '../ChartContainer';
import { CHART_DEFAULTS, WC_COLORS } from '../ChartTheme';
import { TrendingDown } from 'lucide-react';

interface PressurePoint {
  stroke: number;
  pressure_psi: number;
}

interface KillCirculationChartProps {
  dpp: PressurePoint[];
  cp: PressurePoint[];
  icp: number;
  fcp: number;
  method: string;
  height?: number;
}

const KillCirculationChart: React.FC<KillCirculationChartProps> = ({
  dpp,
  cp,
  icp,
  fcp,
  method,
  height = 340,
}) => {
  if (!dpp?.length) return null;

  // Merge DPP and CP into unified dataset
  const merged = dpp.map((d, i) => ({
    stroke: d.stroke,
    dpp: d.pressure_psi,
    cp: cp[i]?.pressure_psi ?? 0,
  }));

  const methodLabel = method === 'drillers' ? "Driller's Method" : 'Wait & Weight';

  return (
    <ChartContainer title={`Kill Circulation — ${methodLabel}`} icon={TrendingDown} height={height}>
      <ComposedChart data={merged} margin={{ top: 20, right: 30, bottom: 20, left: 50 }}>
        <CartesianGrid stroke={CHART_DEFAULTS.gridColor} strokeDasharray="3 3" vertical={false} />

        <XAxis
          dataKey="stroke"
          tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }}
          axisLine={{ stroke: CHART_DEFAULTS.axisColor }}
          label={{ value: 'Pump Strokes', position: 'insideBottom', offset: -10, fill: CHART_DEFAULTS.labelColor, fontSize: 11 }}
        />

        <YAxis
          tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }}
          axisLine={{ stroke: CHART_DEFAULTS.axisColor }}
          domain={[0, 'auto']}
          label={{ value: 'Pressure (psi)', angle: -90, position: 'insideLeft', fill: CHART_DEFAULTS.labelColor, fontSize: 11 }}
        />

        <Tooltip
          contentStyle={{
            background: CHART_DEFAULTS.tooltipBg,
            border: `1px solid ${CHART_DEFAULTS.tooltipBorder}`,
            borderRadius: '12px',
            fontSize: '11px',
          }}
          labelStyle={{ color: '#999' }}
          labelFormatter={(v) => `Stroke: ${v}`}
        />

        <ReferenceLine y={icp} stroke={WC_COLORS.icp} strokeDasharray="6 4"
          label={{ value: `ICP ${icp} psi`, fill: WC_COLORS.icp, fontSize: 10, position: 'right' }}
        />
        <ReferenceLine y={fcp} stroke={WC_COLORS.fcp} strokeDasharray="6 4"
          label={{ value: `FCP ${fcp} psi`, fill: WC_COLORS.fcp, fontSize: 10, position: 'right' }}
        />

        <Line
          type="monotone"
          dataKey="dpp"
          stroke="#3b82f6"
          strokeWidth={2.5}
          dot={false}
          name="Drill Pipe Pressure"
        />
        <Line
          type="monotone"
          dataKey="cp"
          stroke="#f97316"
          strokeWidth={2}
          dot={false}
          name="Casing Pressure"
          strokeDasharray="4 2"
        />
      </ComposedChart>
    </ChartContainer>
  );
};

export default KillCirculationChart;
