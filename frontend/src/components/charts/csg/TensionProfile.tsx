/**
 * TensionProfile.tsx — Stacked bar showing tension load components
 * plus optional Tension vs Depth line chart.
 */
import React, { useMemo } from 'react';
import {
  BarChart, Bar, ComposedChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ReferenceLine,
} from 'recharts';
import ChartContainer, { DarkTooltip } from '../ChartContainer';
import { CHART_DEFAULTS } from '../ChartTheme';
import { ArrowUp } from 'lucide-react';

interface TensionProfileProps {
  tensionLoad?: {
    buoyant_weight_lbs?: number;
    shock_load_lbs?: number;
    bending_load_lbs?: number;
    overpull_lbs?: number;
    total_tension_lbs?: number;
    pipe_body_yield_lbs?: number;
  } | null;
  tensionProfile?: {
    profile?: Array<{
      tvd_ft: number;
      buoyant_weight_lbs: number;
      total_tension_lbs: number;
    }>;
    pipe_body_yield_lbs?: number;
    max_tension_lbs?: number;
  } | null;
  height?: number;
}

const TensionProfile: React.FC<TensionProfileProps> = ({
  tensionLoad,
  tensionProfile,
  height = 500,
}) => {
  /* ── Stacked bar data (single bar with load components) ── */
  const barData = useMemo(() => {
    if (!tensionLoad) return null;
    return [
      {
        name: 'Tension',
        buoyant: Math.round(tensionLoad.buoyant_weight_lbs || 0),
        shock: Math.round(tensionLoad.shock_load_lbs || 0),
        bending: Math.round(tensionLoad.bending_load_lbs || 0),
        overpull: Math.round(tensionLoad.overpull_lbs || 0),
      },
    ];
  }, [tensionLoad]);

  const total = tensionLoad?.total_tension_lbs || 0;
  const rating = tensionLoad?.pipe_body_yield_lbs || 0;

  /* ── Tension vs Depth line data ── */
  const lineData = useMemo(() => {
    if (!tensionProfile?.profile?.length) return [];
    return tensionProfile.profile.map((p) => ({
      depth: p.tvd_ft,
      total: Math.round(p.total_tension_lbs / 1000),
      buoyant: Math.round(p.buoyant_weight_lbs / 1000),
    }));
  }, [tensionProfile]);

  const yieldKlbs = useMemo(() => {
    const y = tensionProfile?.pipe_body_yield_lbs
      || tensionLoad?.pipe_body_yield_lbs || 0;
    return Math.round(y / 1000);
  }, [tensionProfile, tensionLoad]);

  if (!barData && !lineData.length) return null;

  return (
    <>
      {/* Stacked bar — tension load components */}
      {barData && (
        <div data-chart-id="tension-bar">
          <ChartContainer
            title="Tension Load Profile"
            icon={ArrowUp}
            height={height}
            badge={{ text: `Total: ${(total / 1000).toFixed(0)}k lbs`, color: 'bg-indigo-500/20 text-indigo-400' }}
          >
            <BarChart data={barData} margin={{ ...CHART_DEFAULTS.margin, left: 50 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={CHART_DEFAULTS.gridColor} />
              <XAxis
                dataKey="name"
                stroke={CHART_DEFAULTS.axisColor}
                tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 12 }}
              />
              <YAxis
                stroke={CHART_DEFAULTS.axisColor}
                tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }}
                tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}k`}
                label={{ value: 'Load (lbs)', angle: -90, position: 'insideLeft', fill: CHART_DEFAULTS.labelColor, fontSize: 11 }}
              />
              <Tooltip content={<DarkTooltip formatter={(v: number) => `${Number(v).toLocaleString()} lbs`} />} />
              <Legend wrapperStyle={{ color: CHART_DEFAULTS.axisColor, fontSize: 11 }} />
              <Bar dataKey="buoyant" stackId="a" fill="#6366f1" fillOpacity={0.7} name="Buoyant Weight" radius={[0, 0, 0, 0]} />
              <Bar dataKey="shock" stackId="a" fill="#ef4444" fillOpacity={0.7} name="Shock" />
              <Bar dataKey="bending" stackId="a" fill="#f97316" fillOpacity={0.7} name="Bending" />
              <Bar dataKey="overpull" stackId="a" fill="#eab308" fillOpacity={0.7} name="Overpull" radius={[4, 4, 0, 0]} />
              {rating > 0 && (
                <ReferenceLine y={rating} stroke="#22c55e" strokeDasharray="8 4" strokeWidth={2}
                  label={{ value: `Yield: ${(rating / 1000).toFixed(0)}k`, fill: '#22c55e', fontSize: 10, position: 'right' }} />
              )}
            </BarChart>
          </ChartContainer>
        </div>
      )}

      {/* Tension vs Depth line chart */}
      {lineData.length > 0 && (
        <div data-chart-id="tension-depth">
          <ChartContainer
            title="Tension vs Depth"
            icon={ArrowUp}
            height={height}
            badge={{ text: `Surface: ${(tensionProfile?.max_tension_lbs ? (tensionProfile.max_tension_lbs / 1000).toFixed(0) : '—')}k lbs`, color: 'bg-indigo-500/20 text-indigo-400' }}
          >
            <ComposedChart data={lineData} layout="vertical" margin={{ top: 10, right: 30, bottom: 20, left: 50 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis
                type="number"
                domain={[0, 'auto']}
                stroke="#9CA3AF"
                fontSize={11}
                tickFormatter={(v: number) => `${v}k`}
                label={{ value: 'Tension (klbs)', position: 'insideBottom', offset: -5, fill: '#9CA3AF', fontSize: 11 }}
              />
              <YAxis
                type="number"
                dataKey="depth"
                stroke="#9CA3AF"
                fontSize={11}
                label={{ value: 'Depth (ft)', angle: -90, position: 'insideLeft', fill: '#9CA3AF', fontSize: 11 }}
              />
              <Tooltip
                contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', borderRadius: 8 }}
                labelFormatter={(v) => `${v} ft`}
                formatter={(v, name) => [`${v ?? 0}k lbs`, name ?? '']}
              />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              {yieldKlbs > 0 && (
                <ReferenceLine
                  x={yieldKlbs}
                  stroke="#22c55e"
                  strokeDasharray="8 4"
                  strokeWidth={2}
                  label={{ value: `Yield: ${yieldKlbs}k`, fill: '#22c55e', fontSize: 10, position: 'top' }}
                />
              )}
              <Line dataKey="total" stroke="#6366f1" name="Total Tension" dot={false} strokeWidth={2} />
              <Line
                dataKey="buoyant" stroke="#6366f1" strokeOpacity={0.4}
                strokeDasharray="4 4" name="Buoyant Weight" dot={false} strokeWidth={1.5}
              />
            </ComposedChart>
          </ChartContainer>
        </div>
      )}
    </>
  );
};

export default TensionProfile;
