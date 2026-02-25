/**
 * PressureWaterfallChart.tsx — Waterfall-style bar chart showing cumulative pressure losses.
 */
import React, { useMemo } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell, LabelList,
} from 'recharts';
import ChartContainer from '../ChartContainer';
import { HYD_COLORS, CHART_DEFAULTS } from '../ChartTheme';
import { BarChart3 } from 'lucide-react';

interface PressureWaterfallChartProps {
  summary: {
    surface_equipment_psi: number;
    pipe_loss_psi: number;
    bit_loss_psi: number;
    annular_loss_psi: number;
    total_spp_psi: number;
  };
  height?: number;
}

const PressureWaterfallChart: React.FC<PressureWaterfallChartProps> = ({ summary, height = 300 }) => {
  const data = useMemo(() => {
    if (!summary) return [];
    const total = summary.total_spp_psi || 1;
    let cumulative = 0;

    const segments = [
      { name: 'Surface', value: summary.surface_equipment_psi, color: HYD_COLORS.surface },
      { name: 'Pipe', value: summary.pipe_loss_psi, color: HYD_COLORS.pipe },
      { name: 'Bit', value: summary.bit_loss_psi, color: HYD_COLORS.bit },
      { name: 'Annular', value: summary.annular_loss_psi, color: HYD_COLORS.annular },
    ];

    return segments.map(seg => {
      const base = cumulative;
      cumulative += seg.value;
      return {
        name: seg.name,
        base: Math.round(base),
        value: Math.round(seg.value),
        top: Math.round(cumulative),
        color: seg.color,
        pct: Math.round((seg.value / total) * 100),
      };
    }).concat([{
      name: 'Total SPP',
      base: 0,
      value: Math.round(summary.total_spp_psi),
      top: Math.round(summary.total_spp_psi),
      color: '#f97316',
      pct: 100,
    }]);
  }, [summary]);

  if (!data.length) return null;

  return (
    <ChartContainer title="Pressure Loss Distribution (Waterfall)" icon={BarChart3} height={height}>
      <BarChart data={data} margin={{ top: 20, right: 30, bottom: 5, left: 50 }}>
        <CartesianGrid stroke={CHART_DEFAULTS.gridColor} strokeDasharray="3 3" vertical={false} />
        <XAxis
          dataKey="name"
          tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }}
          axisLine={{ stroke: CHART_DEFAULTS.axisColor }}
        />
        <YAxis
          tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }}
          axisLine={{ stroke: CHART_DEFAULTS.axisColor }}
          label={{ value: 'Pressure (psi)', angle: -90, position: 'insideLeft', offset: -35, fill: CHART_DEFAULTS.labelColor, fontSize: 11 }}
        />
        <Tooltip
          content={({ active, payload }) => {
            if (!active || !payload?.length) return null;
            const d = payload[0].payload;
            return (
              <div style={{ backgroundColor: CHART_DEFAULTS.tooltipBg, border: `1px solid ${CHART_DEFAULTS.tooltipBorder}`, borderRadius: 8, padding: '8px 12px', fontSize: 12 }}>
                <p style={{ color: 'white', fontWeight: 700 }}>{d.name}</p>
                <p style={{ color: d.color }}>{d.value} psi ({d.pct}%)</p>
              </div>
            );
          }}
        />
        {/* Invisible base bar */}
        <Bar dataKey="base" stackId="waterfall" fill="transparent" />
        {/* Visible value bar */}
        <Bar dataKey="value" stackId="waterfall" radius={[4, 4, 0, 0]}>
          {data.map((entry, i) => (
            <Cell key={i} fill={entry.color} fillOpacity={i === data.length - 1 ? 0.9 : 0.7} />
          ))}
          <LabelList
            dataKey="value"
            position="top"
            fill="rgba(255,255,255,0.6)"
            fontSize={10}
            formatter={(v: number) => `${v} psi`}
          />
        </Bar>
      </BarChart>
    </ChartContainer>
  );
};

export default PressureWaterfallChart;
