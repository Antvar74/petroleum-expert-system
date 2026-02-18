/**
 * VolumetricCyclesChart.tsx — Stepped line chart for volumetric kill cycles.
 */
import React from 'react';
import {
  ComposedChart, Line, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, Cell,
} from 'recharts';
import ChartContainer from '../ChartContainer';
import { WC_COLORS, CHART_DEFAULTS } from '../ChartTheme';
import { BarChart3 } from 'lucide-react';

interface RawCycle {
  cycle: number;
  max_pressure?: number;
  max_pressure_psi?: number;
  volume_bled?: number;
  volume_bled_bbl?: number;
  cumulative_volume_bbl?: number;
}

interface NormalizedCycle {
  cycle: number;
  max_pressure_psi: number;
  volume_bled_bbl: number;
  cumulative_volume_bbl: number;
}

interface VolumetricCyclesChartProps {
  cycles: RawCycle[];
  maasp?: number;
  height?: number;
}

const VolumetricCyclesChart: React.FC<VolumetricCyclesChartProps> = ({
  cycles: rawCycles,
  maasp,
  height = 320,
}) => {
  if (!rawCycles?.length) return null;

  // Normalize field names: engine returns max_pressure/volume_bled,
  // but we display as max_pressure_psi/volume_bled_bbl
  let cumulative = 0;
  const cycles: NormalizedCycle[] = rawCycles.map(c => {
    const vol = c.volume_bled_bbl ?? c.volume_bled ?? 0;
    cumulative += vol;
    return {
      cycle: c.cycle,
      max_pressure_psi: c.max_pressure_psi ?? c.max_pressure ?? 0,
      volume_bled_bbl: vol,
      cumulative_volume_bbl: c.cumulative_volume_bbl ?? Math.round(cumulative * 100) / 100,
    };
  });

  return (
    <ChartContainer title="Volumetric Kill Cycles" icon={BarChart3} height={height}>
      <ComposedChart data={cycles} margin={{ top: 20, right: 60, bottom: 20, left: 50 }}>
        <CartesianGrid stroke={CHART_DEFAULTS.gridColor} strokeDasharray="3 3" vertical={false} />

        <XAxis
          dataKey="cycle"
          tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }}
          axisLine={{ stroke: CHART_DEFAULTS.axisColor }}
          label={{ value: 'Cycle', position: 'insideBottom', offset: -10, fill: CHART_DEFAULTS.labelColor, fontSize: 11 }}
        />

        {/* Left Y: Pressure */}
        <YAxis
          yAxisId="left"
          tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }}
          axisLine={{ stroke: CHART_DEFAULTS.axisColor }}
          label={{ value: 'Pressure (psi)', angle: -90, position: 'insideLeft', offset: -35, fill: CHART_DEFAULTS.labelColor, fontSize: 11 }}
        />

        {/* Right Y: Volume */}
        <YAxis
          yAxisId="right"
          orientation="right"
          tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }}
          axisLine={{ stroke: CHART_DEFAULTS.axisColor }}
          label={{ value: 'Volume (bbl)', angle: 90, position: 'insideRight', offset: -40, fill: CHART_DEFAULTS.labelColor, fontSize: 11 }}
        />

        <Tooltip
          content={({ active, payload }) => {
            if (!active || !payload?.length) return null;
            const d = payload[0]?.payload;
            if (!d) return null;
            return (
              <div style={{ backgroundColor: CHART_DEFAULTS.tooltipBg, border: `1px solid ${CHART_DEFAULTS.tooltipBorder}`, borderRadius: 8, padding: '8px 12px', fontSize: 12 }}>
                <p style={{ color: 'rgba(255,255,255,0.5)', fontSize: 11 }}>Cycle {d.cycle}</p>
                <p style={{ color: WC_COLORS.schedule, fontWeight: 700 }}>Pressure: {d.max_pressure_psi} psi</p>
                <p style={{ color: '#3b82f6' }}>Volume bled: {d.volume_bled_bbl} bbl</p>
                <p style={{ color: 'rgba(255,255,255,0.4)' }}>Cumulative: {d.cumulative_volume_bbl} bbl</p>
              </div>
            );
          }}
        />

        {/* MAASP reference line */}
        {maasp && (
          <ReferenceLine
            yAxisId="left"
            y={maasp}
            stroke={WC_COLORS.maasp}
            strokeDasharray="6 3"
            label={{ value: `MAASP: ${maasp} psi`, fill: WC_COLORS.maasp, fontSize: 10, position: 'right' }}
          />
        )}

        {/* Volume bars */}
        <Bar yAxisId="right" dataKey="volume_bled_bbl" barSize={20} radius={[4, 4, 0, 0]} fillOpacity={0.5}>
          {cycles.map((_, i) => (
            <Cell key={i} fill="#3b82f6" />
          ))}
        </Bar>

        {/* Pressure stepped line */}
        <Line
          yAxisId="left"
          type="stepAfter"
          dataKey="max_pressure_psi"
          stroke={WC_COLORS.schedule}
          strokeWidth={2.5}
          dot={{ r: 4, fill: WC_COLORS.schedule, stroke: '#0c0e12', strokeWidth: 2 }}
          animationDuration={CHART_DEFAULTS.animationDuration}
        />
      </ComposedChart>
    </ChartContainer>
  );
};

export default VolumetricCyclesChart;
