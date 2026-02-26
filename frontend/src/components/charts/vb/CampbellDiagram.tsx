/**
 * CampbellDiagram.tsx — Natural frequency vs RPM with excitation lines.
 * Crossings indicate resonance hazards.
 */
import React from 'react';
import {
  ComposedChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  Scatter, ReferenceArea,
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
  height = 450,
}) => {
  if (!rpmValues?.length) return null;

  // Build merged data array: { rpm, mode_1, mode_2, ..., exc_1x, exc_2x, ... }
  const data = rpmValues.map((rpm, i) => {
    const row: Record<string, number> = { rpm };
    Object.entries(naturalFreqCurves).forEach(([key, vals]) => {
      row[key] = vals[i];
    });
    Object.entries(excitationLines).forEach(([key, vals]) => {
      row[`exc_${key}`] = vals[i];
    });
    return row;
  });

  // Crossing scatter data
  const crossingData = crossings.map(c => ({
    rpm: c.rpm,
    frequency_hz: c.frequency_hz,
    label: `${c.mode} x ${c.excitation}`,
    risk: c.risk,
  }));

  const modeKeys = Object.keys(naturalFreqCurves);
  const excKeys = Object.keys(excitationLines);

  return (
    <ChartContainer title="Campbell Diagram (FEA)" icon={Activity} height={height}>
      <ComposedChart data={data} margin={{ top: 10, right: 30, bottom: 10, left: 10 }}>
        <CartesianGrid stroke={CHART_DEFAULTS.gridColor} />
        <XAxis
          dataKey="rpm"
          type="number"
          tick={{ fill: CHART_DEFAULTS.labelColor, fontSize: 11 }}
          label={{ value: 'RPM', position: 'insideBottom', fill: CHART_DEFAULTS.labelColor, fontSize: 12, offset: -5 }}
        />
        <YAxis
          type="number"
          tick={{ fill: CHART_DEFAULTS.labelColor, fontSize: 11 }}
          label={{ value: 'Frequency (Hz)', angle: -90, position: 'insideLeft', fill: CHART_DEFAULTS.labelColor, fontSize: 12 }}
        />
        <Tooltip content={<DarkTooltip />} />
        <Legend />

        {/* Operating RPM band */}
        {operatingRpm && (
          <ReferenceArea
            x1={operatingRpm - 10}
            x2={operatingRpm + 10}
            fill="#f43f5e"
            fillOpacity={0.08}
            label={{ value: `${operatingRpm} RPM`, fill: '#f43f5e', fontSize: 10 }}
          />
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
