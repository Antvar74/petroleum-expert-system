/**
 * FlowRegimeTrack.tsx — Horizontal bar chart showing pressure loss per section, colored by flow regime.
 */
import React from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell, LabelList,
} from 'recharts';
import ChartContainer from '../ChartContainer';
import { CHART_DEFAULTS } from '../ChartTheme';
import { Layers } from 'lucide-react';

interface SectionResult {
  section_type: string;
  pressure_loss_psi: number;
  velocity_ft_min: number;
  flow_regime: string;
  reynolds: number;
}

interface FlowRegimeTrackProps {
  data: SectionResult[];
  height?: number;
}

const REGIME_COLORS: Record<string, string> = {
  laminar: '#22c55e',
  turbulent: '#f97316',
  none: '#6b7280',
};

const FlowRegimeTrack: React.FC<FlowRegimeTrackProps> = ({ data, height = 250 }) => {
  if (!data?.length) return null;

  const chartData = data.map(s => ({
    name: s.section_type.replace(/_/g, ' '),
    dP: Math.round(s.pressure_loss_psi),
    velocity: Math.round(s.velocity_ft_min),
    regime: s.flow_regime,
    re: Math.round(s.reynolds),
    color: REGIME_COLORS[s.flow_regime] || REGIME_COLORS.none,
  }));

  return (
    <ChartContainer title="Flow Regime by Section" icon={Layers} height={height}>
      <BarChart data={chartData} layout="vertical" margin={{ top: 5, right: 60, bottom: 5, left: 100 }}>
        <CartesianGrid stroke={CHART_DEFAULTS.gridColor} strokeDasharray="3 3" horizontal={false} />
        <XAxis
          type="number"
          tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }}
          axisLine={{ stroke: CHART_DEFAULTS.axisColor }}
          label={{ value: 'Pressure Loss (psi)', position: 'insideBottom', offset: -5, fill: CHART_DEFAULTS.labelColor, fontSize: 11 }}
        />
        <YAxis
          dataKey="name"
          type="category"
          tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 10 }}
          axisLine={{ stroke: CHART_DEFAULTS.axisColor }}
          width={95}
        />
        <Tooltip
          content={({ active, payload }) => {
            if (!active || !payload?.length) return null;
            const d = payload[0].payload;
            return (
              <div style={{ backgroundColor: CHART_DEFAULTS.tooltipBg, border: `1px solid ${CHART_DEFAULTS.tooltipBorder}`, borderRadius: 8, padding: '8px 12px', fontSize: 12 }}>
                <p style={{ color: 'white', fontWeight: 700, marginBottom: 4 }}>{d.name}</p>
                <p style={{ color: d.color }}>dP: {d.dP} psi | {d.regime}</p>
                <p style={{ color: 'rgba(255,255,255,0.5)' }}>Vel: {d.velocity} ft/min | Re: {d.re.toLocaleString()}</p>
              </div>
            );
          }}
        />
        <Bar dataKey="dP" name="Pressure Loss" radius={[0, 4, 4, 0]}>
          {chartData.map((entry, i) => (
            <Cell key={i} fill={entry.color} fillOpacity={0.7} />
          ))}
          <LabelList dataKey="regime" position="right" fill="rgba(255,255,255,0.5)" fontSize={10} />
        </Bar>
      </BarChart>
    </ChartContainer>
  );
};

export default FlowRegimeTrack;
