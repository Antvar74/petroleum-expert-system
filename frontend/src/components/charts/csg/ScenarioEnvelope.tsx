/**
 * ScenarioEnvelope.tsx — Multi-scenario burst/collapse envelope chart.
 * Overlays all 5 burst + 4 collapse scenarios with distinct colors.
 * Governing scenario shown as thick solid line, others as dashed.
 * Burst on the right (positive), collapse on the left (negative).
 */
import React, { useMemo } from 'react';
import { ComposedChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ReferenceLine } from 'recharts';
import ChartContainer, { DarkTooltip } from '../ChartContainer';
import { CHART_DEFAULTS } from '../ChartTheme';
import { Layers } from 'lucide-react';

/* ---------- color & label maps ---------- */
const BURST_COLORS: Record<string, string> = {
  gas_to_surface: '#ef4444',
  displacement_to_gas: '#f97316',
  tubing_leak: '#eab308',
  injection: '#a855f7',
  dst: '#ec4899',
};

const COLLAPSE_COLORS: Record<string, string> = {
  full_evacuation: '#3b82f6',
  partial_evacuation: '#06b6d4',
  cementing_collapse: '#8b5cf6',
  production_depletion: '#10b981',
};

const SCENARIO_LABELS: Record<string, string> = {
  gas_to_surface: 'Gas a Superficie',
  displacement_to_gas: 'Despl. a Gas',
  tubing_leak: 'Fuga Tubing',
  injection: 'Inyección',
  dst: 'DST',
  full_evacuation: 'Evac. Total',
  partial_evacuation: 'Evac. Parcial',
  cementing_collapse: 'Cementación',
  production_depletion: 'Depleción',
};

/* ---------- props ---------- */
interface ScenarioEnvelopeProps {
  burstScenarios: {
    scenarios: Record<string, { profile: Array<{ tvd_ft: number; burst_load_psi?: number }>; max_burst_psi?: number }>;
    governing_scenario: string;
  } | null;
  collapseScenarios: {
    scenarios: Record<string, { profile: Array<{ tvd_ft: number; collapse_load_psi?: number }>; max_collapse_psi?: number }>;
    governing_scenario: string;
  } | null;
  burstRating: number;
  collapseRating: number;
  height?: number;
}

/* ---------- component ---------- */
const ScenarioEnvelope: React.FC<ScenarioEnvelopeProps> = ({
  burstScenarios,
  collapseScenarios,
  burstRating,
  collapseRating,
  height = 480,
}) => {
  // Build unified depth array and per-scenario data keys
  const { data, burstKeys, collapseKeys } = useMemo(() => {
    const depthSet = new Set<number>();

    // Gather depths from all scenarios
    if (burstScenarios?.scenarios) {
      Object.values(burstScenarios.scenarios).forEach(s =>
        s.profile?.forEach(p => depthSet.add(p.tvd_ft)),
      );
    }
    if (collapseScenarios?.scenarios) {
      Object.values(collapseScenarios.scenarios).forEach(s =>
        s.profile?.forEach(p => depthSet.add(p.tvd_ft)),
      );
    }

    const depths = Array.from(depthSet).sort((a, b) => a - b);
    if (depths.length === 0) return { data: [], burstKeys: [], collapseKeys: [] };

    // Build lookup maps: scenarioKey -> Map(depth -> value)
    const burstMaps: Record<string, Map<number, number>> = {};
    const bKeys: string[] = [];
    if (burstScenarios?.scenarios) {
      for (const [key, scenario] of Object.entries(burstScenarios.scenarios)) {
        const dataKey = `burst_${key}`;
        bKeys.push(dataKey);
        burstMaps[dataKey] = new Map(
          (scenario.profile || []).map(p => [p.tvd_ft, p.burst_load_psi ?? 0]),
        );
      }
    }

    const collapseMaps: Record<string, Map<number, number>> = {};
    const cKeys: string[] = [];
    if (collapseScenarios?.scenarios) {
      for (const [key, scenario] of Object.entries(collapseScenarios.scenarios)) {
        const dataKey = `collapse_${key}`;
        cKeys.push(dataKey);
        collapseMaps[dataKey] = new Map(
          (scenario.profile || []).map(p => [p.tvd_ft, p.collapse_load_psi ?? 0]),
        );
      }
    }

    // Build merged data rows
    const rows = depths.map(d => {
      const row: Record<string, number | null> = { depth: d };
      for (const dk of bKeys) {
        const val = burstMaps[dk].get(d);
        row[dk] = val !== undefined ? val : null;
      }
      for (const dk of cKeys) {
        const val = collapseMaps[dk].get(d);
        // Collapse values shown as negative so they appear on the left of x=0
        row[dk] = val !== undefined ? -val : null;
      }
      return row;
    });

    return { data: rows, burstKeys: bKeys, collapseKeys: cKeys };
  }, [burstScenarios, collapseScenarios]);

  if (data.length === 0) return null;

  const governingBurst = burstScenarios?.governing_scenario
    ? `burst_${burstScenarios.governing_scenario}`
    : '';
  const governingCollapse = collapseScenarios?.governing_scenario
    ? `collapse_${collapseScenarios.governing_scenario}`
    : '';

  return (
    <ChartContainer title="Envolvente Multi-Escenario" icon={Layers} height={height}>
      <ComposedChart
        data={data}
        layout="vertical"
        margin={{ ...CHART_DEFAULTS.margin, left: 50, right: 30, bottom: 40 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_DEFAULTS.gridColor} />
        <XAxis
          type="number"
          stroke={CHART_DEFAULTS.axisColor}
          tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }}
          label={{
            value: 'Presión (psi)',
            position: 'insideBottom',
            offset: -5,
            fill: CHART_DEFAULTS.labelColor,
            fontSize: 11,
          }}
        />
        <YAxis
          dataKey="depth"
          type="number"
          reversed
          stroke={CHART_DEFAULTS.axisColor}
          tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }}
          label={{
            value: 'TVD (ft)',
            angle: -90,
            position: 'insideLeft',
            fill: CHART_DEFAULTS.labelColor,
            fontSize: 11,
          }}
        />
        <Tooltip
          content={
            <DarkTooltip
              formatter={(v: number) => `${Math.abs(Number(v)).toFixed(0)} psi`}
            />
          }
        />
        <Legend wrapperStyle={{ color: CHART_DEFAULTS.axisColor, fontSize: 10, paddingTop: 12 }} />

        {/* Center reference line at x = 0 */}
        <ReferenceLine x={0} stroke="rgba(255,255,255,0.2)" strokeWidth={1} />

        {/* Burst rating reference line (positive) */}
        {burstRating > 0 && (
          <ReferenceLine
            x={burstRating}
            stroke="#ef4444"
            strokeDasharray="8 4"
            strokeWidth={2}
            label={{ value: `Burst Rating: ${burstRating}`, fill: '#ef4444', fontSize: 9, position: 'top' }}
          />
        )}

        {/* Collapse rating reference line (negative) */}
        {collapseRating > 0 && (
          <ReferenceLine
            x={-collapseRating}
            stroke="#3b82f6"
            strokeDasharray="8 4"
            strokeWidth={2}
            label={{ value: `Collapse Rating: -${collapseRating}`, fill: '#3b82f6', fontSize: 9, position: 'top' }}
          />
        )}

        {/* Burst scenario lines */}
        {burstKeys.map(dk => {
          const scenarioKey = dk.replace('burst_', '');
          const isGoverning = dk === governingBurst;
          return (
            <Line
              key={dk}
              dataKey={dk}
              type="monotone"
              stroke={BURST_COLORS[scenarioKey] || '#fff'}
              strokeWidth={isGoverning ? 3 : 1.5}
              strokeDasharray={isGoverning ? undefined : '6 3'}
              dot={false}
              name={SCENARIO_LABELS[scenarioKey] || scenarioKey}
              connectNulls
            />
          );
        })}

        {/* Collapse scenario lines */}
        {collapseKeys.map(dk => {
          const scenarioKey = dk.replace('collapse_', '');
          const isGoverning = dk === governingCollapse;
          return (
            <Line
              key={dk}
              dataKey={dk}
              type="monotone"
              stroke={COLLAPSE_COLORS[scenarioKey] || '#fff'}
              strokeWidth={isGoverning ? 3 : 1.5}
              strokeDasharray={isGoverning ? undefined : '6 3'}
              dot={false}
              name={SCENARIO_LABELS[scenarioKey] || scenarioKey}
              connectNulls
            />
          );
        })}
      </ComposedChart>
    </ChartContainer>
  );
};

export default ScenarioEnvelope;
