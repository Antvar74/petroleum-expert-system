/**
 * NPTBreakdownChart.tsx — NPT breakdown by category (donut + bar).
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import {
  PieChart, Pie, Cell, Tooltip, Legend,
} from 'recharts';
import ChartContainer, { DarkTooltip } from '../ChartContainer';
import { AlertTriangle } from 'lucide-react';

interface NPTBreakdownProps {
  byCategory: Record<string, number>;
  totalHours?: number;
  height?: number;
  title?: string;
}

const COLORS = ['#ef4444', '#f97316', '#eab308', '#22c55e', '#3b82f6', '#a855f7', '#6b7280'];

const NPTBreakdownChart: React.FC<NPTBreakdownProps> = ({
  byCategory,
  totalHours = 0,
  height = 320,
  title = 'NPT Breakdown',
}) => {
  const { t } = useTranslation();
  const chartData = Object.entries(byCategory).map(([name, value]) => ({ name, value }));

  if (chartData.length === 0) {
    return (
      <ChartContainer title={title} icon={AlertTriangle} height={height}
        badge={{ text: `${totalHours.toFixed(1)} hrs`, color: 'bg-yellow-500/20 text-yellow-400' }}>
        <div className="flex items-center justify-center h-full text-white/20 text-sm">
          {t('ddr.charts.noNPTEvents')}
        </div>
      </ChartContainer>
    );
  }

  return (
    <ChartContainer
      title={title}
      icon={AlertTriangle}
      height={height}
      badge={{ text: `${totalHours.toFixed(1)} hrs total`, color: 'bg-yellow-500/20 text-yellow-400' }}
    >
      <PieChart>
        <Pie
          data={chartData}
          cx="50%"
          cy="50%"
          innerRadius={55}
          outerRadius={90}
          paddingAngle={3}
          dataKey="value"
          nameKey="name"
          label={({ name, percent }: any) => `${name || ''} ${((percent ?? 0) * 100).toFixed(0)}%`}
          labelLine={false}
        >
          {chartData.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip content={<DarkTooltip formatter={(v) => `${Number(v).toFixed(1)} hrs`} />} />
        <Legend
          verticalAlign="bottom"
          wrapperStyle={{ fontSize: 10, color: 'rgba(255,255,255,0.5)' }}
        />
      </PieChart>
    </ChartContainer>
  );
};

export default NPTBreakdownChart;
