/**
 * SafetyFactorTrack.tsx — Horizontal bar chart showing SF for burst, collapse, tension.
 * Color-coded: green if passing, red if failing.
 */
import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell, ReferenceLine } from 'recharts';
import ChartContainer, { DarkTooltip } from '../ChartContainer';
import { CHART_DEFAULTS } from '../ChartTheme';
import { CheckCircle } from 'lucide-react';

interface SafetyFactorTrackProps {
  safetyFactors: any;
  height?: number;
}

const SafetyFactorTrack: React.FC<SafetyFactorTrackProps> = ({ safetyFactors, height = 300 }) => {
  if (!safetyFactors?.results) return null;

  const results = safetyFactors.results;
  const data = ['burst', 'collapse', 'tension'].map(criterion => {
    const sf = results[criterion];
    if (!sf) return null;
    return {
      name: criterion.charAt(0).toUpperCase() + criterion.slice(1),
      sf: sf.safety_factor,
      minSf: sf.minimum_sf,
      passes: sf.passes,
    };
  }).filter(Boolean);

  const allPass = data.every((d: any) => d.passes);

  return (
    <ChartContainer
      title="Factores de Seguridad"
      icon={CheckCircle}
      height={height}
      badge={{ text: allPass ? 'ALL PASS' : 'FAIL', color: allPass ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400' }}
    >
      <BarChart data={data} layout="vertical" margin={{ ...CHART_DEFAULTS.margin, left: 60 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_DEFAULTS.gridColor} />
        <XAxis
          type="number"
          stroke={CHART_DEFAULTS.axisColor}
          tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }}
          label={{ value: 'Safety Factor', position: 'insideBottom', offset: -5, fill: CHART_DEFAULTS.labelColor, fontSize: 11 }}
        />
        <YAxis
          dataKey="name"
          type="category"
          stroke={CHART_DEFAULTS.axisColor}
          tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 12, fontWeight: 600 }}
          width={80}
        />
        <Tooltip content={<DarkTooltip formatter={(v: any) => Number(v).toFixed(2)} />} />
        <ReferenceLine x={1.0} stroke="rgba(255,255,255,0.3)" strokeDasharray="4 4"
          label={{ value: 'SF = 1.0', fill: 'rgba(255,255,255,0.4)', fontSize: 10 }} />
        <Bar dataKey="sf" name="Safety Factor" radius={[0, 4, 4, 0]} barSize={28}>
          {(data as any[]).map((entry, idx) => (
            <Cell key={idx} fill={entry.passes ? '#22c55e' : '#ef4444'} opacity={0.7} />
          ))}
        </Bar>
      </BarChart>
    </ChartContainer>
  );
};

export default SafetyFactorTrack;
