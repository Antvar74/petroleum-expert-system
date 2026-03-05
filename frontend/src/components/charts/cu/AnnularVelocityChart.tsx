/**
 * AnnularVelocityChart.tsx — Bar chart comparing actual vs minimum annular velocity.
 */
import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';
import ChartContainer, { DarkTooltip } from '../ChartContainer';
import { CHART_DEFAULTS } from '../ChartTheme';
import { ArrowUpDown } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface AnnularVelocityChartProps {
  actualVelocity: number;
  minimumVelocity: number;
  slipVelocity: number;
  transportVelocity: number;
  height?: number;
}

const AnnularVelocityChart: React.FC<AnnularVelocityChartProps> = ({
  actualVelocity, minimumVelocity, slipVelocity, transportVelocity, height = 350
}) => {
  const { t } = useTranslation();

  const data = [
    { name: t('wellboreCleanup.charts.annularVelocity.annular'), value: actualVelocity, fill: '#3b82f6' },
    { name: t('wellboreCleanup.charts.annularVelocity.minimum'), value: minimumVelocity, fill: '#f59e0b' },
    { name: t('wellboreCleanup.charts.annularVelocity.slip'), value: slipVelocity, fill: '#ef4444' },
    { name: t('wellboreCleanup.charts.annularVelocity.transport'), value: transportVelocity, fill: '#10b981' },
  ];

  const adequate = actualVelocity >= minimumVelocity;

  return (
    <ChartContainer
      title={t('wellboreCleanup.charts.annularVelocity.title')}
      icon={ArrowUpDown}
      height={height}
      badge={{ text: adequate ? t('wellboreCleanup.charts.annularVelocity.adequate') : t('wellboreCleanup.charts.annularVelocity.low'), color: adequate ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400' }}
    >
      <BarChart data={data} margin={CHART_DEFAULTS.margin}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_DEFAULTS.gridColor} />
        <XAxis dataKey="name" stroke={CHART_DEFAULTS.axisColor} tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 12 }} />
        <YAxis stroke={CHART_DEFAULTS.axisColor} tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 12 }} label={{ value: t('wellboreCleanup.charts.annularVelocity.yAxis'), angle: -90, position: 'insideLeft', fill: CHART_DEFAULTS.axisColor }} />
        <Tooltip content={<DarkTooltip />} />
        <Bar dataKey="value" name={t('wellboreCleanup.charts.annularVelocity.velocityLabel')} radius={[4, 4, 0, 0]}>
          {data.map((entry, idx) => (
            <rect key={idx} fill={entry.fill} />
          ))}
        </Bar>
      </BarChart>
    </ChartContainer>
  );
};

export default AnnularVelocityChart;
