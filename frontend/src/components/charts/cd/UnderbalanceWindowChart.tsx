/**
 * UnderbalanceWindowChart.tsx — Shows actual underbalance vs recommended range.
 */
import React from 'react';
import ChartContainer from '../ChartContainer';
import { Target } from 'lucide-react';

interface UnderbalanceWindowChartProps {
  underbalance: {
    underbalance_psi: number;
    is_underbalanced: boolean;
    status: string;
    recommended_range_psi: number[];
    permeability_class: string;
    formation_type: string;
  };
  height?: number;
}

const UnderbalanceWindowChart: React.FC<UnderbalanceWindowChartProps> = ({ underbalance, height = 280 }) => {
  if (!underbalance) return null;

  const [recMin, recMax] = underbalance.recommended_range_psi || [0, 0];
  const actual = underbalance.underbalance_psi;

  // Scale for visualization
  const maxScale = Math.max(recMax * 1.5, Math.abs(actual) * 1.3, 3000);
  const toPct = (v: number) => Math.max(0, Math.min(100, (v / maxScale) * 100));

  const statusColor = underbalance.status === 'Optimal' ? '#22c55e'
    : underbalance.status === 'Insufficient Underbalance' ? '#eab308'
    : underbalance.status === 'Overbalanced' ? '#ef4444' : '#f97316';

  return (
    <ChartContainer
      title="Ventana de Underbalance"
      icon={Target}
      height={height}
      badge={{ text: underbalance.status, color: `text-[${statusColor}]` }}
      isFluid
    >
      <div className="flex flex-col gap-4 h-full justify-center px-4">
        {/* Info Row */}
        <div className="flex justify-between text-xs text-gray-400">
          <span>{underbalance.formation_type} | {underbalance.permeability_class}</span>
          <span>Rango: {recMin} - {recMax} psi</span>
        </div>

        {/* Visual Bar */}
        <div className="relative w-full h-16 bg-white/5 rounded-xl overflow-hidden border border-white/10">
          {/* Recommended range (green zone) */}
          <div
            className="absolute top-0 h-full bg-green-500/15 border-x border-green-500/30"
            style={{ left: `${toPct(recMin)}%`, width: `${toPct(recMax) - toPct(recMin)}%` }}
          >
            <span className="absolute top-1 left-1 text-[9px] text-green-400 font-bold">ÓPTIMO</span>
          </div>

          {/* Actual marker */}
          <div
            className="absolute top-0 h-full w-1 z-10"
            style={{ left: `${toPct(Math.max(0, actual))}%`, backgroundColor: statusColor }}
          >
            <div
              className="absolute -top-6 -translate-x-1/2 whitespace-nowrap text-xs font-bold px-2 py-0.5 rounded"
              style={{ color: statusColor }}
            >
              {actual} psi
            </div>
            <div className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-3 h-3 rounded-full border-2"
              style={{ backgroundColor: statusColor, borderColor: 'white' }} />
          </div>

          {/* Scale labels */}
          <div className="absolute bottom-1 left-2 text-[9px] text-gray-500">0</div>
          <div className="absolute bottom-1 right-2 text-[9px] text-gray-500">{Math.round(maxScale)} psi</div>
        </div>

        {/* Status */}
        <div className="flex items-center gap-2 justify-center">
          <div className="w-2 h-2 rounded-full" style={{ backgroundColor: statusColor }} />
          <span className="text-sm font-bold" style={{ color: statusColor }}>{underbalance.status}</span>
          {!underbalance.is_underbalanced && (
            <span className="text-xs text-red-400 ml-2">&#9888; Overbalanced — recommend UB perforating</span>
          )}
        </div>
      </div>
    </ChartContainer>
  );
};

export default UnderbalanceWindowChart;
