/**
 * PressureScheduleChart.tsx — Enhanced pressure schedule with ICP/FCP/MAASP references.
 */
import React from 'react';
import {
  Line, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, Area, ComposedChart,
} from 'recharts';
import ChartContainer from '../ChartContainer';
import { WC_COLORS, CHART_DEFAULTS } from '../ChartTheme';
import { TrendingDown } from 'lucide-react';

interface ScheduleStep {
  step: number;
  strokes: number;
  pressure_psi: number;
  percent_complete: number;
}

interface PressureScheduleChartProps {
  schedule: ScheduleStep[];
  icp: number;
  fcp: number;
  maasp?: number;
  height?: number;
}

const PressureScheduleChart: React.FC<PressureScheduleChartProps> = ({
  schedule,
  icp,
  fcp,
  maasp,
  height = 320,
}) => {
  if (!schedule?.length) return null;

  return (
    <ChartContainer title="Pressure Schedule (ICP → FCP)" icon={TrendingDown} height={height}>
      <ComposedChart data={schedule} margin={{ top: 20, right: 30, bottom: 20, left: 50 }}>
        <CartesianGrid stroke={CHART_DEFAULTS.gridColor} strokeDasharray="3 3" vertical={false} />

        <XAxis
          dataKey="strokes"
          tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }}
          axisLine={{ stroke: CHART_DEFAULTS.axisColor }}
          label={{ value: 'Strokes', position: 'insideBottom', offset: -10, fill: CHART_DEFAULTS.labelColor, fontSize: 11 }}
        />
        <YAxis
          tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }}
          axisLine={{ stroke: CHART_DEFAULTS.axisColor }}
          domain={[0, 'auto']}
          label={{ value: 'Pressure (psi)', angle: -90, position: 'insideLeft', offset: -35, fill: CHART_DEFAULTS.labelColor, fontSize: 11 }}
        />

        <Tooltip
          content={({ active, payload }) => {
            if (!active || !payload?.length) return null;
            const d = payload[0].payload;
            return (
              <div style={{ backgroundColor: CHART_DEFAULTS.tooltipBg, border: `1px solid ${CHART_DEFAULTS.tooltipBorder}`, borderRadius: 8, padding: '8px 12px', fontSize: 12 }}>
                <p style={{ color: 'rgba(255,255,255,0.5)', fontSize: 11 }}>Step {d.step}</p>
                <p style={{ color: WC_COLORS.schedule, fontWeight: 700 }}>{d.pressure_psi} psi</p>
                <p style={{ color: 'rgba(255,255,255,0.4)' }}>{d.strokes} strokes ({d.percent_complete}%)</p>
              </div>
            );
          }}
        />

        {/* ICP reference */}
        <ReferenceLine
          y={icp}
          stroke={WC_COLORS.icp}
          strokeDasharray="6 3"
          label={{ value: `ICP: ${icp} psi`, fill: WC_COLORS.icp, fontSize: 10, position: 'right' }}
        />

        {/* FCP reference */}
        <ReferenceLine
          y={fcp}
          stroke={WC_COLORS.fcp}
          strokeDasharray="6 3"
          label={{ value: `FCP: ${fcp} psi`, fill: WC_COLORS.fcp, fontSize: 10, position: 'right' }}
        />

        {/* MAASP reference */}
        {maasp && (
          <ReferenceLine
            y={maasp}
            stroke={WC_COLORS.maasp}
            strokeDasharray="4 2"
            label={{ value: `MAASP: ${maasp} psi`, fill: WC_COLORS.maasp, fontSize: 10, position: 'right' }}
          />
        )}

        {/* Shaded area under schedule */}
        <Area
          type="linear"
          dataKey="pressure_psi"
          fill={WC_COLORS.schedule}
          fillOpacity={0.08}
          stroke="none"
        />

        {/* Schedule line */}
        <Line
          type="linear"
          dataKey="pressure_psi"
          stroke={WC_COLORS.schedule}
          strokeWidth={3}
          dot={{ r: 4, fill: WC_COLORS.schedule, stroke: '#0c0e12', strokeWidth: 2 }}
          activeDot={{ r: 6, fill: WC_COLORS.schedule, stroke: 'white', strokeWidth: 2 }}
          animationDuration={CHART_DEFAULTS.animationDuration}
        />
      </ComposedChart>
    </ChartContainer>
  );
};

export default PressureScheduleChart;
