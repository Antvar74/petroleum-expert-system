/**
 * CTPressureProfile.tsx — Bar chart showing CT pipe vs annular pressure losses.
 */
import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';
import ChartContainer, { DarkTooltip } from '../ChartContainer';
import { CHART_DEFAULTS } from '../ChartTheme';
import { BarChart3 } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface CTPressureProfileProps {
  hydraulics: { pipe_loss_psi: number; annular_loss_psi: number; total_loss_psi: number };
  ctDims?: { ct_od_in: number; ct_id_in: number };
  height?: number;
}

const CTPressureProfile: React.FC<CTPressureProfileProps> = ({ hydraulics, height = 350 }) => {
  const { t } = useTranslation();
  if (!hydraulics) return null;

  const pressureLabel = t('workoverHyd.charts.pressure');
  const data = [
    { name: 'Pipe (CT)', value: hydraulics.pipe_loss_psi, fill: '#14b8a6' },
    { name: 'Annular', value: hydraulics.annular_loss_psi, fill: '#06b6d4' },
    { name: 'Total', value: hydraulics.total_loss_psi, fill: '#8b5cf6' },
  ];

  return (
    <ChartContainer title={t('workoverHyd.charts.pressureProfile')} icon={BarChart3} height={height}
      badge={{ text: `${hydraulics.total_loss_psi} psi`, color: 'bg-teal-500/20 text-teal-400' }}>
      <BarChart data={data} margin={CHART_DEFAULTS.margin}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_DEFAULTS.gridColor} />
        <XAxis dataKey="name" stroke={CHART_DEFAULTS.axisColor} tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 12 }} />
        <YAxis stroke={CHART_DEFAULTS.axisColor} tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 12 }}
          label={{ value: pressureLabel, angle: -90, position: 'insideLeft', fill: CHART_DEFAULTS.axisColor }} />
        <Tooltip content={<DarkTooltip />} />
        <Bar dataKey="value" name={pressureLabel} radius={[4, 4, 0, 0]}>
          {data.map((entry, idx) => (
            <rect key={idx} fill={entry.fill} />
          ))}
        </Bar>
      </BarChart>
    </ChartContainer>
  );
};

export default CTPressureProfile;
