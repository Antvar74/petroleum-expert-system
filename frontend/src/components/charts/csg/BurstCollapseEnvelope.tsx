/**
 * BurstCollapseEnvelope.tsx — Burst & Collapse load vs depth with rating lines.
 * Shows design load envelopes against casing rating limits.
 */
import React from 'react';
import { ComposedChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ReferenceLine } from 'recharts';
import ChartContainer, { DarkTooltip } from '../ChartContainer';
import { CHART_DEFAULTS } from '../ChartTheme';
import { Shield } from 'lucide-react';

interface BurstCollapseEnvelopeProps {
  burstLoad: any;
  collapseLoad: any;
  burstRating: number;
  collapseRating: number;
  height?: number;
}

const BurstCollapseEnvelope: React.FC<BurstCollapseEnvelopeProps> = ({
  burstLoad, collapseLoad, burstRating, collapseRating, height = 400,
}) => {
  if (!burstLoad?.profile?.length && !collapseLoad?.profile?.length) return null;

  // Merge burst and collapse profiles by depth
  const depthSet = new Set<number>();
  (burstLoad?.profile || []).forEach((p: any) => depthSet.add(p.tvd_ft));
  (collapseLoad?.profile || []).forEach((p: any) => depthSet.add(p.tvd_ft));
  const depths = Array.from(depthSet).sort((a, b) => a - b);

  const burstMap = new Map((burstLoad?.profile || []).map((p: any) => [p.tvd_ft, p.burst_load_psi]));
  const collMap = new Map((collapseLoad?.profile || []).map((p: any) => [p.tvd_ft, p.collapse_load_psi]));

  const data = depths.map(d => ({
    depth: d,
    burst: burstMap.get(d) ?? null,
    collapse: collMap.get(d) ? -(collMap.get(d) as number) : null,
    burst_rating: burstRating || 0,
    collapse_rating: collapseRating ? -collapseRating : 0,
  }));

  return (
    <ChartContainer title="Envolvente Burst / Collapse" icon={Shield} height={height}>
      <ComposedChart data={data} layout="vertical" margin={{ ...CHART_DEFAULTS.margin, left: 50, right: 30, bottom: 40 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_DEFAULTS.gridColor} />
        <XAxis
          type="number"
          stroke={CHART_DEFAULTS.axisColor}
          tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }}
          label={{ value: 'Presión (psi)', position: 'insideBottom', offset: -5, fill: CHART_DEFAULTS.labelColor, fontSize: 11 }}
        />
        <YAxis
          dataKey="depth"
          type="number"
          reversed
          stroke={CHART_DEFAULTS.axisColor}
          tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }}
          label={{ value: 'TVD (ft)', angle: -90, position: 'insideLeft', fill: CHART_DEFAULTS.labelColor, fontSize: 11 }}
        />
        <Tooltip content={<DarkTooltip formatter={(v: any) => `${Math.abs(Number(v)).toFixed(0)} psi`} />} />
        <Legend wrapperStyle={{ color: CHART_DEFAULTS.axisColor, fontSize: 11, paddingTop: 12 }} />
        {/* Burst load area (positive) */}
        <Area type="monotone" dataKey="burst" stroke="#ef4444" fill="#ef4444" fillOpacity={0.1}
          strokeWidth={2} name="Carga Burst" dot={false} />
        {/* Collapse load area (negative) */}
        <Area type="monotone" dataKey="collapse" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.1}
          strokeWidth={2} name="Carga Collapse" dot={false} />
        {/* Burst rating line */}
        {burstRating > 0 && (
          <ReferenceLine x={burstRating} stroke="#ef4444" strokeDasharray="8 4" strokeWidth={2}
            label={{ value: `Burst: ${burstRating}`, fill: '#ef4444', fontSize: 10, position: 'top' }} />
        )}
        {/* Collapse rating line */}
        {collapseRating > 0 && (
          <ReferenceLine x={-collapseRating} stroke="#3b82f6" strokeDasharray="8 4" strokeWidth={2}
            label={{ value: `Collapse: -${collapseRating}`, fill: '#3b82f6', fontSize: 10, position: 'top' }} />
        )}
        <ReferenceLine x={0} stroke="rgba(255,255,255,0.2)" strokeWidth={1} />
      </ComposedChart>
    </ChartContainer>
  );
};

export default BurstCollapseEnvelope;
