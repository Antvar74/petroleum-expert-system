/**
 * CriticalRPMChart.tsx — Shows operating RPM vs axial/lateral critical RPMs.
 */
import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell, ReferenceLine } from 'recharts';
import ChartContainer, { DarkTooltip } from '../ChartContainer';
import { CHART_DEFAULTS } from '../ChartTheme';
import { Zap } from 'lucide-react';

interface CriticalRPMChartProps {
  axial: { critical_rpm_1st: number; critical_rpm_2nd: number; critical_rpm_3rd: number };
  lateral: { critical_rpm: number };
  operatingRpm: number;
  height?: number;
}

const CriticalRPMChart: React.FC<CriticalRPMChartProps> = ({ axial, lateral, operatingRpm, height = 350 }) => {
  if (!axial || !lateral) return null;

  const data = [
    { name: 'Axial 1st', rpm: axial.critical_rpm_1st, color: '#ef4444' },
    { name: 'Axial 2nd', rpm: axial.critical_rpm_2nd, color: '#f97316' },
    { name: 'Lateral', rpm: lateral.critical_rpm, color: '#8b5cf6' },
  ].filter(d => d.rpm > 0 && d.rpm < 1000);

  return (
    <ChartContainer
      title="RPMs Críticos vs Operación"
      icon={Zap}
      height={height}
      badge={{ text: `Operando: ${operatingRpm} RPM`, color: 'bg-rose-500/20 text-rose-400' }}
    >
      <BarChart data={data} margin={CHART_DEFAULTS.margin}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_DEFAULTS.gridColor} />
        <XAxis dataKey="name" stroke={CHART_DEFAULTS.axisColor} tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }} />
        <YAxis stroke={CHART_DEFAULTS.axisColor} tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }}
          label={{ value: 'RPM', angle: -90, position: 'insideLeft', fill: CHART_DEFAULTS.axisColor }} />
        <Tooltip content={<DarkTooltip />} />
        <ReferenceLine y={operatingRpm} stroke="#f43f5e" strokeDasharray="8 4" strokeWidth={2}
          label={{ value: `Operating ${operatingRpm}`, fill: '#f43f5e', fontSize: 11, position: 'right' }} />
        <Bar dataKey="rpm" name="RPM Crítico" radius={[4, 4, 0, 0]}>
          {data.map((entry, idx) => (
            <Cell key={idx} fill={entry.color} opacity={0.7} />
          ))}
        </Bar>
      </BarChart>
    </ChartContainer>
  );
};

export default CriticalRPMChart;
