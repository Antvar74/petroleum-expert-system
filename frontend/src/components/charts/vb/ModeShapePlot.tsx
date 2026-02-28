/**
 * ModeShapePlot.tsx — Vertical mode shape visualization.
 * Shows BHA deflection profile for each vibration mode.
 * Y-axis = depth (reversed, bit at bottom), X-axis = normalized deflection.
 */
import React, { useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';
import ChartContainer, { DarkTooltip } from '../ChartContainer';
import { CHART_DEFAULTS } from '../ChartTheme';
import { Waves } from 'lucide-react';

interface ModeShapePlotProps {
  nodePositions: number[];
  modeShapes: number[][];
  frequenciesHz: number[];
  height?: number;
}

const MODE_COLORS = ['#3b82f6', '#22c55e', '#f97316', '#a855f7', '#06b6d4'];

const ModeShapePlot: React.FC<ModeShapePlotProps> = ({
  nodePositions,
  modeShapes,
  frequenciesHz,
  height = 450,
}) => {
  const [visibleModes, setVisibleModes] = useState<Set<number>>(new Set([0, 1, 2]));

  if (!nodePositions?.length || !modeShapes?.length) return null;

  // Compute nice tick interval based on depth range
  const depthMin = Math.min(...nodePositions);
  const depthMax = Math.max(...nodePositions);
  const depthRange = depthMax - depthMin;
  // Choose tick count: 5-10 ticks regardless of range
  const rawStep = depthRange / 8;
  const magnitude = Math.pow(10, Math.floor(Math.log10(rawStep)));
  const niceSteps = [1, 2, 5, 10, 20, 25, 50];
  const tickStep = niceSteps.find(s => s * magnitude >= rawStep)! * magnitude;
  const ticks: number[] = [];
  const firstTick = Math.ceil(depthMin / tickStep) * tickStep;
  for (let t = firstTick; t <= depthMax; t += tickStep) {
    ticks.push(Math.round(t * 100) / 100);
  }
  if (ticks.length === 0 || ticks[0] > depthMin) ticks.unshift(Math.round(depthMin));
  if (ticks[ticks.length - 1] < depthMax) ticks.push(Math.round(depthMax));

  // Build data: each row = { depth, mode_0, mode_1, mode_2, ... }
  const data = nodePositions.map((depth, i) => {
    const row: Record<string, number> = { depth };
    modeShapes.forEach((shape, modeIdx) => {
      if (shape[i] !== undefined) {
        row[`mode_${modeIdx}`] = shape[i];
      }
    });
    return row;
  });

  const toggleMode = (idx: number) => {
    setVisibleModes(prev => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  return (
    <ChartContainer title="Mode Shapes (FEA)" icon={Waves} height={height}>
      <LineChart data={data} layout="vertical" margin={{ top: 10, right: 30, bottom: 10, left: 60 }}>
        <CartesianGrid stroke={CHART_DEFAULTS.gridColor} />
        <YAxis
          dataKey="depth"
          type="number"
          reversed
          domain={[depthMin, depthMax]}
          ticks={ticks}
          tick={{ fill: CHART_DEFAULTS.labelColor, fontSize: 11 }}
          tickFormatter={(v: number) => Math.round(v).toLocaleString()}
          label={{ value: 'MD (ft)', angle: -90, position: 'insideLeft', fill: CHART_DEFAULTS.labelColor, fontSize: 12 }}
        />
        <XAxis
          type="number"
          domain={[-1.1, 1.1]}
          tick={{ fill: CHART_DEFAULTS.labelColor, fontSize: 11 }}
          label={{ value: 'Deflection (normalized)', position: 'insideBottom', fill: CHART_DEFAULTS.labelColor, fontSize: 12, offset: -5 }}
        />
        <Tooltip content={<DarkTooltip />} />
        <Legend
          onClick={(e: any) => {
            const idx = parseInt(e.dataKey?.replace('mode_', '') || '0');
            toggleMode(idx);
          }}
          wrapperStyle={{ cursor: 'pointer' }}
        />
        {modeShapes.map((_, modeIdx) => (
          visibleModes.has(modeIdx) && (
            <Line
              key={`mode_${modeIdx}`}
              dataKey={`mode_${modeIdx}`}
              name={`Mode ${modeIdx + 1} (${frequenciesHz[modeIdx]?.toFixed(2)} Hz)`}
              stroke={MODE_COLORS[modeIdx % MODE_COLORS.length]}
              strokeWidth={2}
              dot={false}
              type="monotone"
            />
          )
        ))}
      </LineChart>
    </ChartContainer>
  );
};

export default ModeShapePlot;
