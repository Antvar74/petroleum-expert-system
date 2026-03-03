/**
 * CampbellDiagram.tsx — Natural frequency vs RPM with excitation lines.
 * Crossings indicate resonance hazards.
 *
 * Y-axis is clamped to mode frequency range (via yDomainHz) so that
 * excitation lines going to 30+ Hz don't make the modes invisible.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import {
  ComposedChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  Scatter, ReferenceArea, ReferenceLine,
} from 'recharts';
import ChartContainer, { DarkTooltip } from '../ChartContainer';
import { CHART_DEFAULTS } from '../ChartTheme';
import { Activity } from 'lucide-react';

interface CampbellDiagramProps {
  rpmValues: number[];
  naturalFreqCurves: Record<string, number[]>;
  excitationLines: Record<string, number[]>;
  crossings: Array<{
    rpm: number;
    frequency_hz: number;
    excitation: string;
    mode: string;
    risk: string;
  }>;
  operatingRpm?: number;
  yDomainHz?: [number, number];
  height?: number;
}

const MODE_COLORS = ['#3b82f6', '#22c55e', '#a855f7', '#06b6d4', '#f59e0b'];
const EXC_COLORS: Record<string, string> = {
  '1x': '#ef4444',
  '2x': '#f97316',
  '3x': '#eab308',
};

const CampbellDiagram: React.FC<CampbellDiagramProps> = ({
  rpmValues,
  naturalFreqCurves,
  excitationLines,
  crossings,
  operatingRpm,
  yDomainHz,
  height = 450,
}) => {
  const { t } = useTranslation();
  if (!rpmValues?.length) return null;

  // Compute Y domain: use backend hint or auto-compute from mode frequencies
  const allModeFreqs = Object.values(naturalFreqCurves).flatMap(v => v).filter(f => f > 0);
  const maxModeFreq = allModeFreqs.length > 0 ? Math.max(...allModeFreqs) : 1;
  const yMax = yDomainHz ? yDomainHz[1] : maxModeFreq * 1.3;

  // FIX-VIB-008: extend X domain so operating RPM is always visible.
  const rpmDataMax = rpmValues.length > 0 ? Math.max(...rpmValues) : 0;
  const xMax = Math.max(rpmDataMax, operatingRpm ? operatingRpm * 1.25 : 0, 150);

  // Build merged data array
  const data = rpmValues.map((rpm, i) => {
    const row: Record<string, number> = { rpm };
    Object.entries(naturalFreqCurves).forEach(([key, vals]) => {
      row[key] = vals[i];
    });
    Object.entries(excitationLines).forEach(([key, vals]) => {
      // Clamp excitation values to Y domain for proper rendering
      row[`exc_${key}`] = Math.min(vals[i], yMax);
    });
    return row;
  });

  // Append an extra point at xMax when data doesn't reach it,
  // so Recharts lines render across the full extended domain.
  if (xMax > rpmDataMax && rpmValues.length > 0) {
    const lastIdx = rpmValues.length - 1;
    const lastRpm = rpmValues[lastIdx];
    const extra: Record<string, number> = { rpm: xMax };
    // Natural freq curves are horizontal — repeat last value.
    Object.entries(naturalFreqCurves).forEach(([key, vals]) => {
      extra[key] = vals[lastIdx] ?? 0;
    });
    // Excitation lines are linear: extrapolate from slope at last point.
    Object.entries(excitationLines).forEach(([key, vals]) => {
      const slope = lastRpm > 0 ? (vals[lastIdx] ?? 0) / lastRpm : 0;
      extra[`exc_${key}`] = Math.min(slope * xMax, yMax);
    });
    data.push(extra);
  }

  // Crossing scatter data (only those within Y domain)
  const crossingData = crossings
    .filter(c => c.frequency_hz <= yMax)
    .map(c => ({
      rpm: c.rpm,
      frequency_hz: c.frequency_hz,
      label: `${c.mode} x ${c.excitation}`,
      risk: c.risk,
    }));

  const modeKeys = Object.keys(naturalFreqCurves);
  const excKeys = Object.keys(excitationLines);

  return (
    <ChartContainer title={t('vibrations.charts.campbellTitle')} icon={Activity} height={height}>
      <ComposedChart data={data} margin={{ top: 10, right: 30, bottom: 10, left: 10 }}>
        <CartesianGrid stroke={CHART_DEFAULTS.gridColor} />
        <XAxis
          dataKey="rpm"
          type="number"
          domain={[0, Math.ceil(xMax)]}
          tick={{ fill: CHART_DEFAULTS.labelColor, fontSize: 11 }}
          label={{ value: 'RPM', position: 'insideBottom', fill: CHART_DEFAULTS.labelColor, fontSize: 12, offset: -5 }}
        />
        <YAxis
          type="number"
          domain={[0, yMax]}
          tick={{ fill: CHART_DEFAULTS.labelColor, fontSize: 11 }}
          tickFormatter={(v: number) => v.toFixed(2)}
          label={{ value: 'Frequency (Hz)', angle: -90, position: 'insideLeft', fill: CHART_DEFAULTS.labelColor, fontSize: 12 }}
        />
        <Tooltip content={<DarkTooltip />} />
        <Legend />

        {/* Operating RPM band + vertical line */}
        {operatingRpm && (
          <>
            <ReferenceArea
              x1={operatingRpm - 10}
              x2={operatingRpm + 10}
              fill="#f43f5e"
              fillOpacity={0.08}
            />
            <ReferenceLine
              x={operatingRpm}
              stroke="#f43f5e"
              strokeDasharray="6 3"
              strokeWidth={2}
              label={{ value: `Oper. ${operatingRpm} RPM`, fill: '#f43f5e', fontSize: 9, position: 'insideTopRight' }}
            />
          </>
        )}

        {/* Natural frequency curves (solid) */}
        {modeKeys.map((key, i) => (
          <Line
            key={key}
            dataKey={key}
            name={`${key.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase())}`}
            stroke={MODE_COLORS[i % MODE_COLORS.length]}
            strokeWidth={2}
            dot={false}
            type="monotone"
          />
        ))}

        {/* Excitation lines (dashed) */}
        {excKeys.map(key => (
          <Line
            key={`exc_${key}`}
            dataKey={`exc_${key}`}
            name={`${key} RPM`}
            stroke={EXC_COLORS[key] || '#888'}
            strokeWidth={1.5}
            strokeDasharray="6 3"
            dot={false}
            type="linear"
          />
        ))}

        {/* Resonance crossing markers */}
        {crossingData.length > 0 && (
          <Scatter
            data={crossingData}
            dataKey="frequency_hz"
            fill="#ef4444"
            name="Resonance"
            shape="diamond"
          />
        )}
      </ComposedChart>
    </ChartContainer>
  );
};

export default CampbellDiagram;
