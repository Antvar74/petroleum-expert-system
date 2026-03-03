/**
 * CutoffSensitivityChart.tsx — Shows cutoff values vs avg values for phi, sw, vsh.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import ChartContainer from '../ChartContainer';
import { SlidersHorizontal } from 'lucide-react';

interface CutoffSensitivityChartProps {
  summary: {
    avg_porosity: number; avg_sw: number; avg_vsh: number;
    net_pay_intervals_count: number; total_net_pay_ft: number;
    min_interval_thickness_ft?: number | null;
  };
  parameters: {
    cutoffs: { phi_min: number; sw_max: number; vsh_max: number; min_thickness_ft?: number };
  };
  height?: number;
}

const CutoffSensitivityChart: React.FC<CutoffSensitivityChartProps> = ({ summary, parameters, height = 280 }) => {
  const { t } = useTranslation();
  if (!summary || !parameters) return null;

  const items = [
    {
      label: 'Porosidad (φ)',
      cutoff: parameters.cutoffs.phi_min * 100,
      avg: summary.avg_porosity * 100,
      unit: '%',
      direction: 'min' as const,
      color: '#22c55e',
    },
    {
      label: 'Saturación Agua (Sw)',
      cutoff: parameters.cutoffs.sw_max * 100,
      avg: summary.avg_sw * 100,
      unit: '%',
      direction: 'max' as const,
      color: '#3b82f6',
    },
    {
      label: 'Volumen Arcilla (Vsh)',
      cutoff: parameters.cutoffs.vsh_max * 100,
      avg: summary.avg_vsh * 100,
      unit: '%',
      direction: 'max' as const,
      color: '#f97316',
    },
    ...(parameters.cutoffs.min_thickness_ft != null && summary.min_interval_thickness_ft != null
      ? [{
          label: 'Espesor Mín. (ft)',
          cutoff: parameters.cutoffs.min_thickness_ft,
          avg: summary.min_interval_thickness_ft,
          unit: ' ft',
          direction: 'min' as const,
          color: '#a855f7',
        }]
      : []),
  ];

  return (
    <ChartContainer
      title={t('shotEfficiency.charts.cutoffsTitle')}
      icon={SlidersHorizontal}
      height={height}
      isFluid
    >
      <div className="space-y-5 px-2 py-2">
        {items.map((item, i) => {
          const maxVal = Math.max(item.cutoff, item.avg) * 1.3;
          const cutoffPct = (item.cutoff / maxVal) * 100;
          const avgPct = (item.avg / maxVal) * 100;
          const passes = item.direction === 'min'
            ? item.avg > item.cutoff
            : item.avg < item.cutoff;

          return (
            <div key={i}>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-gray-400">{item.label}</span>
                <span className={passes ? 'text-green-400' : 'text-red-400'}>
                  Avg: {item.avg.toFixed(1)}{item.unit} | Cutoff: {item.cutoff.toFixed(1)}{item.unit} {passes ? '✓' : '✗'}
                </span>
              </div>
              <div className="relative w-full h-5 bg-white/5 rounded-full overflow-hidden">
                {/* Average bar */}
                <div className="absolute top-0 h-full rounded-full" style={{ width: `${avgPct}%`, backgroundColor: item.color, opacity: 0.4 }} />
                {/* Cutoff line */}
                <div className="absolute top-0 h-full w-0.5" style={{ left: `${cutoffPct}%`, backgroundColor: item.color }}>
                  <div className="absolute -top-4 -translate-x-1/2 text-[9px] font-bold whitespace-nowrap" style={{ color: item.color }}>
                    {item.direction === 'min' ? 'MIN' : 'MAX'}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
        <div className="text-center text-xs text-gray-500 pt-2">
          {summary.net_pay_intervals_count} intervalo(s) | {summary.total_net_pay_ft} ft net pay
        </div>
      </div>
    </ChartContainer>
  );
};

export default CutoffSensitivityChart;
