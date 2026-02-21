/**
 * ROPProgressChart.tsx — Rate of Penetration progress chart over days.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import {
  ComposedChart, Bar, Line, XAxis, YAxis, Tooltip, Legend,
} from 'recharts';
import ChartContainer, { DarkTooltip } from '../ChartContainer';
import { Zap } from 'lucide-react';

interface ROPDataPoint {
  day: number;
  date?: string;
  footage?: number;
  avg_rop?: number;
}

interface ROPProgressChartProps {
  data: ROPDataPoint[];
  height?: number;
  title?: string;
}

const ROPProgressChart: React.FC<ROPProgressChartProps> = ({
  data,
  height = 320,
  title = 'ROP Progress',
}) => {
  const { t } = useTranslation();

  if (!data || data.length === 0) {
    return (
      <ChartContainer title={title} icon={Zap} height={height}>
        <div className="flex items-center justify-center h-full text-white/20 text-sm">
          {t('ddr.charts.noROPData')}
        </div>
      </ChartContainer>
    );
  }

  return (
    <ChartContainer title={title} icon={Zap} height={height}>
      <ComposedChart data={data} margin={{ top: 10, right: 20, bottom: 10, left: 10 }}>
        <XAxis
          dataKey="day"
          label={{ value: t('ddr.charts.day'), position: 'insideBottom', offset: -5, style: { fill: 'rgba(255,255,255,0.4)', fontSize: 11 } }}
          tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 11 }}
          stroke="rgba(255,255,255,0.1)"
        />
        <YAxis
          yAxisId="footage"
          orientation="left"
          tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 10 }}
          stroke="rgba(255,255,255,0.1)"
          label={{ value: t('ddr.charts.footageFt'), angle: -90, position: 'insideLeft', style: { fill: 'rgba(255,255,255,0.3)', fontSize: 10 } }}
        />
        <YAxis
          yAxisId="rop"
          orientation="right"
          tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 10 }}
          stroke="rgba(255,255,255,0.1)"
          label={{ value: t('ddr.charts.ropFtHr'), angle: 90, position: 'insideRight', style: { fill: 'rgba(255,255,255,0.3)', fontSize: 10 } }}
        />
        <Tooltip content={<DarkTooltip />} />
        <Legend
          verticalAlign="top"
          height={36}
          wrapperStyle={{ fontSize: 11, color: 'rgba(255,255,255,0.5)' }}
        />
        <Bar
          yAxisId="footage"
          dataKey="footage"
          name={t('ddr.charts.dailyFootage')}
          fill="#22c55e"
          opacity={0.6}
          radius={[4, 4, 0, 0]}
        />
        <Line
          yAxisId="rop"
          type="monotone"
          dataKey="avg_rop"
          name={t('ddr.charts.avgROP')}
          stroke="#f97316"
          strokeWidth={2.5}
          dot={{ r: 3, fill: '#f97316' }}
        />
      </ComposedChart>
    </ChartContainer>
  );
};

export default ROPProgressChart;
