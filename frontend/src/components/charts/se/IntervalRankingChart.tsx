/**
 * IntervalRankingChart.tsx — Horizontal bar chart showing scored + ranked intervals.
 */
import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell } from 'recharts';
import ChartContainer, { DarkTooltip } from '../ChartContainer';
import { CHART_DEFAULTS } from '../ChartTheme';
import { Award } from 'lucide-react';

interface IntervalRankingChartProps {
  rankings: {
    ranked: {
      rank: number; top_md: number; base_md: number;
      score: number; avg_phi: number; avg_sw: number;
    }[];
    best: any;
  };
  height?: number;
}

const IntervalRankingChart: React.FC<IntervalRankingChartProps> = ({ rankings, height = 350 }) => {
  if (!rankings?.ranked?.length) return null;

  const data = rankings.ranked.slice(0, 8).map(iv => ({
    name: `#${iv.rank} (${iv.top_md}-${iv.base_md}')`,
    score: Math.round(iv.score * 1000) / 1000,
    isBest: iv.rank === 1,
  }));

  return (
    <ChartContainer
      title="Ranking de Intervalos (Score Compuesto)"
      icon={Award}
      height={height}
      badge={{ text: `Top: ${data[0]?.score}`, color: 'bg-emerald-500/20 text-emerald-400' }}
    >
      <BarChart data={data} layout="vertical" margin={{ ...CHART_DEFAULTS.margin, left: 110 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_DEFAULTS.gridColor} />
        <XAxis type="number" domain={[0, 1]} stroke={CHART_DEFAULTS.axisColor}
          tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }}
          label={{ value: 'Score', position: 'bottom', fill: CHART_DEFAULTS.axisColor }} />
        <YAxis type="category" dataKey="name" stroke={CHART_DEFAULTS.axisColor}
          tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 10 }} width={105} />
        <Tooltip content={<DarkTooltip />} />
        <Bar dataKey="score" name="Score" radius={[0, 4, 4, 0]}>
          {data.map((entry, idx) => (
            <Cell key={idx} fill={entry.isBest ? '#10b981' : 'rgba(16,185,129,0.35)'} />
          ))}
        </Bar>
      </BarChart>
    </ChartContainer>
  );
};

export default IntervalRankingChart;
