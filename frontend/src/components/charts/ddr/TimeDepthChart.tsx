/**
 * TimeDepthChart.tsx — Time vs Depth curve (planned vs actual).
 * Classic drilling engineering chart with inverted Y-axis.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import {
  LineChart, Line, XAxis, YAxis, Tooltip, Legend,
} from 'recharts';
import ChartContainer, { DarkTooltip } from '../ChartContainer';
import { TrendingDown } from 'lucide-react';

interface TimeDepthDataPoint {
  day: number;
  date?: string;
  depth_end: number;
  planned_depth?: number | null;
  footage?: number;
}

interface TimeDepthChartProps {
  data: TimeDepthDataPoint[];
  height?: number;
  title?: string;
}

const TimeDepthChart: React.FC<TimeDepthChartProps> = ({
  data,
  height = 380,
  title = 'Time vs Depth',
}) => {
  const { t } = useTranslation();

  if (!data || data.length === 0) {
    return (
      <ChartContainer title={title} icon={TrendingDown} height={height}>
        <div className="flex items-center justify-center h-full text-white/20 text-sm">
          {t('ddr.charts.noDataAvailable')}
        </div>
      </ChartContainer>
    );
  }

  const hasPlanned = data.some(d => d.planned_depth != null);
  const maxDepth = Math.max(...data.map(d => Math.max(d.depth_end || 0, d.planned_depth || 0)));

  return (
    <ChartContainer title={title} icon={TrendingDown} height={height}>
      <LineChart data={data} margin={{ top: 10, right: 20, bottom: 10, left: 20 }}>
        <XAxis
          dataKey="day"
          label={{ value: t('ddr.charts.day'), position: 'insideBottom', offset: -5, style: { fill: 'rgba(255,255,255,0.4)', fontSize: 11 } }}
          tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 11 }}
          stroke="rgba(255,255,255,0.1)"
        />
        <YAxis
          reversed
          domain={[0, Math.ceil(maxDepth / 1000) * 1000]}
          label={{ value: t('ddr.charts.depthFt'), angle: -90, position: 'insideLeft', style: { fill: 'rgba(255,255,255,0.4)', fontSize: 11 } }}
          tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 11 }}
          stroke="rgba(255,255,255,0.1)"
        />
        <Tooltip content={<DarkTooltip formatter={(v: number) => `${Number(v).toLocaleString()} ft`} />} />
        <Legend
          verticalAlign="top"
          height={36}
          wrapperStyle={{ fontSize: 11, color: 'rgba(255,255,255,0.5)' }}
        />
        <Line
          type="stepAfter"
          dataKey="depth_end"
          name={t('ddr.charts.actualDepth')}
          stroke="#f97316"
          strokeWidth={2.5}
          dot={{ r: 3, fill: '#f97316' }}
          activeDot={{ r: 5 }}
        />
        {hasPlanned && (
          <Line
            type="stepAfter"
            dataKey="planned_depth"
            name={t('ddr.charts.plannedDepth')}
            stroke="#3b82f6"
            strokeWidth={1.5}
            strokeDasharray="6 3"
            dot={false}
          />
        )}
      </LineChart>
    </ChartContainer>
  );
};

export default TimeDepthChart;
