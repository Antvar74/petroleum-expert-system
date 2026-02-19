/**
 * MaxReachIndicator.tsx — Visual gauge showing max CT reach vs current length.
 */
import React from 'react';
import ChartContainer from '../ChartContainer';
import { Target } from 'lucide-react';

interface MaxReachIndicatorProps {
  maxReach: { max_reach_ft: number; helical_buckling_load_lb: number; yield_load_lb: number; limiting_factor: string };
  ctLength: number;
  height?: number;
}

const MaxReachIndicator: React.FC<MaxReachIndicatorProps> = ({ maxReach, ctLength, height = 350 }) => {
  if (!maxReach) return null;

  const ratio = maxReach.max_reach_ft > 0 ? (ctLength / maxReach.max_reach_ft) * 100 : 100;
  const clampedRatio = Math.min(ratio, 100);

  const getColor = () => {
    if (ratio > 90) return { bar: '#ef4444', text: 'text-red-400', label: 'CRÍTICO' };
    if (ratio > 70) return { bar: '#f59e0b', text: 'text-yellow-400', label: 'PRECAUCIÓN' };
    return { bar: '#22c55e', text: 'text-green-400', label: 'OK' };
  };
  const colors = getColor();

  return (
    <ChartContainer title="Alcance Máximo CT" icon={Target} height={height} isFluid={true}
      badge={{ text: colors.label, color: ratio > 90 ? 'bg-red-500/20 text-red-400' : ratio > 70 ? 'bg-yellow-500/20 text-yellow-400' : 'bg-green-500/20 text-green-400' }}>
      <div className="flex flex-col items-center justify-center gap-6 p-6">
        {/* Circular gauge */}
        <div className="relative w-48 h-48">
          <svg viewBox="0 0 200 200" className="transform -rotate-90">
            <circle cx="100" cy="100" r="85" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="12" />
            <circle cx="100" cy="100" r="85" fill="none" stroke={colors.bar} strokeWidth="12"
              strokeDasharray={`${clampedRatio * 5.34} ${534 - clampedRatio * 5.34}`}
              strokeLinecap="round" className="transition-all duration-1000" />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className={`text-3xl font-bold ${colors.text}`}>{Math.round(ratio)}%</span>
            <span className="text-xs text-gray-500">Utilizado</span>
          </div>
        </div>

        {/* Details */}
        <div className="grid grid-cols-2 gap-4 text-sm w-full">
          <div className="text-center">
            <div className="text-gray-500 text-xs">Longitud CT</div>
            <div className="font-bold text-white">{ctLength.toLocaleString()} ft</div>
          </div>
          <div className="text-center">
            <div className="text-gray-500 text-xs">Alcance Máximo</div>
            <div className="font-bold text-teal-400">{maxReach.max_reach_ft.toLocaleString()} ft</div>
          </div>
          <div className="text-center">
            <div className="text-gray-500 text-xs">Carga Buckling</div>
            <div className="font-mono text-white">{maxReach.helical_buckling_load_lb.toLocaleString()} lb</div>
          </div>
          <div className="text-center">
            <div className="text-gray-500 text-xs">Factor Limitante</div>
            <div className="font-mono text-white text-xs">{maxReach.limiting_factor}</div>
          </div>
        </div>
      </div>
    </ChartContainer>
  );
};

export default MaxReachIndicator;
