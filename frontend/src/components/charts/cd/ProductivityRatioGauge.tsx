/**
 * ProductivityRatioGauge.tsx — SPF sensitivity chart showing PR vs SPF.
 */
import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell } from 'recharts';
import ChartContainer, { DarkTooltip } from '../ChartContainer';
import { CHART_DEFAULTS } from '../ChartTheme';
import { Gauge } from 'lucide-react';

interface ProductivityRatioGaugeProps {
  optimization: {
    optimal_configuration: { spf: number; phasing_deg: number; productivity_ratio: number };
    spf_sensitivity: { spf: number; productivity_ratio: number; skin_total: number }[];
  };
  height?: number;
}

const ProductivityRatioGauge: React.FC<ProductivityRatioGaugeProps> = ({ optimization, height = 350 }) => {
  if (!optimization?.spf_sensitivity) return null;

  const optimalSpf = optimization.optimal_configuration.spf;

  const data = optimization.spf_sensitivity.map(d => ({
    spf: `${d.spf} SPF`,
    pr: Math.round(d.productivity_ratio * 1000) / 10,
    skin: d.skin_total,
    isOptimal: d.spf === optimalSpf,
  }));

  return (
    <ChartContainer
      title="Sensibilidad SPF — Ratio Productividad"
      icon={Gauge}
      height={height}
      badge={{ text: `Óptimo: ${optimalSpf} SPF`, color: 'bg-violet-500/20 text-violet-400' }}
    >
      <BarChart data={data} margin={CHART_DEFAULTS.margin}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_DEFAULTS.gridColor} />
        <XAxis dataKey="spf" stroke={CHART_DEFAULTS.axisColor} tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }} />
        <YAxis stroke={CHART_DEFAULTS.axisColor} tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }}
          label={{ value: 'PR %', angle: -90, position: 'insideLeft', fill: CHART_DEFAULTS.axisColor }} />
        <Tooltip content={<DarkTooltip />} />
        <Bar dataKey="pr" name="PR %" radius={[4, 4, 0, 0]}>
          {data.map((entry, idx) => (
            <Cell key={idx} fill={entry.isOptimal ? '#8b5cf6' : 'rgba(139,92,246,0.3)'} />
          ))}
        </Bar>
      </BarChart>
    </ChartContainer>
  );
};

export default ProductivityRatioGauge;
