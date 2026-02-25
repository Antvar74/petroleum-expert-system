/**
 * CostTrackingChart.tsx — Daily and cumulative cost tracking vs AFE budget.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import {
  ComposedChart, Bar, Line, XAxis, YAxis, Tooltip, Legend, ReferenceLine,
} from 'recharts';
import ChartContainer, { DarkTooltip } from '../ChartContainer';
import { DollarSign } from 'lucide-react';

interface CostDataPoint {
  day: number;
  date?: string;
  daily_cost: number;
  cumulative_cost: number;
  afe_budget?: number | null;
}

interface CostTrackingChartProps {
  data: CostDataPoint[];
  height?: number;
  title?: string;
}

const CostTrackingChart: React.FC<CostTrackingChartProps> = ({
  data,
  height = 380,
  title = 'Cost vs AFE',
}) => {
  const { t } = useTranslation();

  if (!data || data.length === 0) {
    return (
      <ChartContainer title={title} icon={DollarSign} height={height}>
        <div className="flex items-center justify-center h-full text-white/20 text-sm">
          {t('ddr.charts.noCostData')}
        </div>
      </ChartContainer>
    );
  }

  const afeBudget = data.find(d => d.afe_budget)?.afe_budget;
  const formatter = (v: number) => `$${Number(v).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;

  return (
    <ChartContainer title={title} icon={DollarSign} height={height}>
      <ComposedChart data={data} margin={{ top: 10, right: 20, bottom: 10, left: 20 }}>
        <XAxis
          dataKey="day"
          label={{ value: t('ddr.charts.day'), position: 'insideBottom', offset: -5, style: { fill: 'rgba(255,255,255,0.4)', fontSize: 11 } }}
          tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 11 }}
          stroke="rgba(255,255,255,0.1)"
        />
        <YAxis
          yAxisId="daily"
          orientation="left"
          tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 10 }}
          stroke="rgba(255,255,255,0.1)"
          tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
          label={{ value: t('ddr.charts.dailyCost'), angle: -90, position: 'insideLeft', style: { fill: 'rgba(255,255,255,0.3)', fontSize: 10 } }}
        />
        <YAxis
          yAxisId="cum"
          orientation="right"
          tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 10 }}
          stroke="rgba(255,255,255,0.1)"
          tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
          label={{ value: t('ddr.charts.cumulativeCost'), angle: 90, position: 'insideRight', style: { fill: 'rgba(255,255,255,0.3)', fontSize: 10 } }}
        />
        <Tooltip content={<DarkTooltip formatter={formatter} />} />
        <Legend
          verticalAlign="top"
          height={36}
          wrapperStyle={{ fontSize: 11, color: 'rgba(255,255,255,0.5)' }}
        />
        <Bar
          yAxisId="daily"
          dataKey="daily_cost"
          name={t('ddr.charts.dailyCostLabel')}
          fill="#06b6d4"
          opacity={0.7}
          radius={[4, 4, 0, 0]}
        />
        <Line
          yAxisId="cum"
          type="monotone"
          dataKey="cumulative_cost"
          name={t('ddr.charts.cumulative')}
          stroke="#f97316"
          strokeWidth={2.5}
          dot={{ r: 3, fill: '#f97316' }}
        />
        {afeBudget && (
          <ReferenceLine
            yAxisId="cum"
            y={afeBudget}
            stroke="#ef4444"
            strokeDasharray="6 3"
            label={{ value: t('ddr.charts.afeBudget'), position: 'right', fill: '#ef4444', fontSize: 10 }}
          />
        )}
      </ComposedChart>
    </ChartContainer>
  );
};

export default CostTrackingChart;
