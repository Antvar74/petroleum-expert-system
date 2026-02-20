/**
 * ECDDuringCementChart.tsx — ECD at shoe vs cumulative volume pumped during cement job.
 * Shows ECD with fracture-gradient reference line and color bands.
 */
import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, ReferenceArea } from 'recharts';
import ChartContainer, { DarkTooltip } from '../ChartContainer';
import { CHART_DEFAULTS } from '../ChartTheme';
import { TrendingUp } from 'lucide-react';

interface ECDDuringCementChartProps {
  ecd: any;
  height?: number;
}

const ECDDuringCementChart: React.FC<ECDDuringCementChartProps> = ({ ecd, height = 350 }) => {
  if (!ecd?.snapshots?.length) return null;

  const data = ecd.snapshots.map((snap: any) => ({
    volume: Math.round(snap.fill_pct * 10) / 10,
    ecd: Math.round(snap.ecd_ppg * 100) / 100,
    stage: snap.current_fluid ?? `${snap.fill_pct}%`,
  }));

  const maxEcd = Math.max(...data.map((d: any) => d.ecd));
  const fracGrad = ecd.fracture_gradient_ppg;
  const poreP = ecd.pore_pressure_ppg;

  return (
    <ChartContainer
      title="ECD durante Cementación"
      icon={TrendingUp}
      height={height}
      badge={{
        text: `Max: ${maxEcd} ppg`,
        color: maxEcd > fracGrad ? 'bg-red-500/20 text-red-400' : 'bg-green-500/20 text-green-400',
      }}
    >
      <LineChart data={data} margin={{ ...CHART_DEFAULTS.margin, left: 40 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_DEFAULTS.gridColor} />
        <XAxis
          dataKey="volume"
          stroke={CHART_DEFAULTS.axisColor}
          tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }}
          label={{ value: '% Llenado Anular', position: 'insideBottom', offset: -5, fill: CHART_DEFAULTS.labelColor, fontSize: 11 }}
        />
        <YAxis
          stroke={CHART_DEFAULTS.axisColor}
          tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }}
          domain={[poreP ? poreP - 1 : 'auto', fracGrad ? fracGrad + 1 : 'auto']}
          label={{ value: 'ECD (ppg)', angle: -90, position: 'insideLeft', fill: CHART_DEFAULTS.labelColor, fontSize: 11 }}
        />
        <Tooltip content={<DarkTooltip formatter={(v: any) => `${Number(v).toFixed(2)} ppg`} />} />
        {fracGrad && poreP && (
          <ReferenceArea y1={poreP} y2={fracGrad} fill="#22c55e" fillOpacity={0.05} />
        )}
        {fracGrad && (
          <ReferenceLine y={fracGrad} stroke="#ef4444" strokeDasharray="8 4" strokeWidth={2}
            label={{ value: `Frac: ${fracGrad}`, fill: '#ef4444', fontSize: 10, position: 'right' }} />
        )}
        {poreP && (
          <ReferenceLine y={poreP} stroke="#a855f7" strokeDasharray="6 3"
            label={{ value: `Pore: ${poreP}`, fill: '#a855f7', fontSize: 10, position: 'right' }} />
        )}
        <Line type="monotone" dataKey="ecd" stroke="#14b8a6" strokeWidth={3} dot={false}
          name="ECD" animationDuration={CHART_DEFAULTS.animationDuration} />
      </LineChart>
    </ChartContainer>
  );
};

export default ECDDuringCementChart;
