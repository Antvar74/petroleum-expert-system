/**
 * SurgeSwabWindow.tsx — Operational window visualization for surge/swab margins.
 * Shows MW, Surge ECD, Swab ECD relative to LOT and pore pressure.
 */
import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell, ReferenceLine } from 'recharts';
import ChartContainer, { DarkTooltip } from '../ChartContainer';
import { CHART_DEFAULTS } from '../ChartTheme';
import { Waves } from 'lucide-react';

interface SurgeSwabWindowProps {
  surgeEcd: number;
  swabEcd: number;
  mudWeight: number;
  lotEmw?: number;
  porePressure?: number;
  surgeMargin: string;
  swabMargin: string;
  height?: number;
}

const SurgeSwabWindow: React.FC<SurgeSwabWindowProps> = ({
  surgeEcd,
  swabEcd,
  mudWeight,
  lotEmw = 16,
  porePressure = 8,
  surgeMargin,
  swabMargin,
  height = 350,
}) => {
  const data = [
    { name: 'Swab', value: swabEcd, color: '#06b6d4' },
    { name: 'MW', value: mudWeight, color: '#ffffff' },
    { name: 'Surge', value: surgeEcd, color: '#f97316' },
  ];

  // Y domain: show full window from below PP to above LOT
  const yMin = Math.floor(Math.min(porePressure, swabEcd) - 1);
  const yMax = Math.ceil(Math.max(lotEmw, surgeEcd) + 1);

  const marginOk = surgeMargin === 'OK' && swabMargin === 'OK';
  const badgeText = marginOk ? 'SAFE' : 'WARNING';
  const badgeColor = marginOk ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400';

  return (
    <ChartContainer title="Operational Window (Surge/Swab)" icon={Waves} height={height} badge={{ text: badgeText, color: badgeColor }}>
      <BarChart data={data} margin={{ top: 20, right: 40, bottom: 5, left: 40 }}>
        <CartesianGrid stroke={CHART_DEFAULTS.gridColor} strokeDasharray="3 3" horizontal vertical={false} />
        <XAxis
          dataKey="name"
          tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 12 }}
          axisLine={{ stroke: CHART_DEFAULTS.axisColor }}
        />
        <YAxis
          domain={[yMin, yMax]}
          tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }}
          axisLine={{ stroke: CHART_DEFAULTS.axisColor }}
          label={{ value: 'EMW (ppg)', angle: -90, position: 'insideLeft', offset: -25, fill: CHART_DEFAULTS.labelColor, fontSize: 11 }}
        />
        <Tooltip content={<DarkTooltip formatter={(v: number) => `${Number(v).toFixed(2)} ppg`} />} />
        {/* LOT reference */}
        <ReferenceLine y={lotEmw} stroke="#ef4444" strokeDasharray="6 3" strokeWidth={1.5} label={{ value: `LOT ${lotEmw.toFixed(1)}`, fill: '#ef4444', position: 'right', fontSize: 11 }} />
        {/* Pore Pressure reference */}
        <ReferenceLine y={porePressure} stroke="#3b82f6" strokeDasharray="6 3" strokeWidth={1.5} label={{ value: `PP ${porePressure.toFixed(1)}`, fill: '#3b82f6', position: 'right', fontSize: 11 }} />
        {/* MW reference */}
        <ReferenceLine y={mudWeight} stroke="rgba(255,255,255,0.4)" strokeDasharray="4 4" strokeWidth={1} label={{ value: `MW ${mudWeight.toFixed(1)}`, fill: 'rgba(255,255,255,0.5)', position: 'left', fontSize: 10 }} />
        <Bar dataKey="value" name="EMW (ppg)" radius={[4, 4, 0, 0]}>
          {data.map((entry, i) => (
            <Cell key={i} fill={entry.color} fillOpacity={0.7} />
          ))}
        </Bar>
      </BarChart>
    </ChartContainer>
  );
};

export default SurgeSwabWindow;
