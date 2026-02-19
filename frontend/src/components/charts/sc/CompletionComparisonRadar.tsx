/**
 * CompletionComparisonRadar.tsx — Bar chart comparing completion method scores.
 */
import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';
import ChartContainer, { DarkTooltip } from '../ChartContainer';
import { CHART_DEFAULTS } from '../ChartTheme';
import { Target } from 'lucide-react';

interface CompletionComparisonRadarProps {
  completion: { recommended: string; methods: Array<{ method: string; score: number; pro: string; con: string }> };
  height?: number;
}

const COLORS = ['#22c55e', '#3b82f6', '#f59e0b', '#ef4444'];

const CompletionComparisonRadar: React.FC<CompletionComparisonRadarProps> = ({ completion, height = 350 }) => {
  if (!completion?.methods) return null;

  const data = completion.methods.map((m, i) => ({
    name: m.method.replace(/\s*\(.*?\)\s*/g, '').substring(0, 15),
    fullName: m.method,
    score: m.score,
    fill: COLORS[i % COLORS.length],
  }));

  return (
    <ChartContainer title="Comparación Completaciones" icon={Target} height={height}
      badge={{ text: completion.recommended.substring(0, 20), color: 'bg-green-500/20 text-green-400' }}>
      <BarChart data={data} margin={CHART_DEFAULTS.margin} layout="vertical">
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_DEFAULTS.gridColor} />
        <XAxis type="number" stroke={CHART_DEFAULTS.axisColor} tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 12 }}
          label={{ value: 'Score', position: 'bottom', fill: CHART_DEFAULTS.axisColor }} />
        <YAxis type="category" dataKey="name" stroke={CHART_DEFAULTS.axisColor} tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 10 }} width={100} />
        <Tooltip content={<DarkTooltip />} />
        <Bar dataKey="score" name="Score" radius={[0, 4, 4, 0]}>
          {data.map((entry, idx) => (
            <rect key={idx} fill={entry.fill} />
          ))}
        </Bar>
      </BarChart>
    </ChartContainer>
  );
};

export default CompletionComparisonRadar;
