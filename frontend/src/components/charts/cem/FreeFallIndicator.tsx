/**
 * FreeFallIndicator.tsx — Visual indicator for free-fall height and U-tube effect.
 * Shows whether free-fall / U-tube occurs, with severity gauge.
 */
import React from 'react';
import ChartContainer from '../ChartContainer';
import { ArrowDownCircle } from 'lucide-react';

interface FreeFallIndicatorProps {
  freeFall: any;
  utube: any;
  height?: number;
}

const FreeFallIndicator: React.FC<FreeFallIndicatorProps> = ({ freeFall, utube, height = 350 }) => {
  if (!freeFall && !utube) return null;

  const ffOccurs = freeFall?.free_fall_occurs;
  const ffHeight = freeFall?.free_fall_height_ft || 0;
  const utubeOccurs = utube?.utube_occurs;
  const utubePressure = utube?.pressure_imbalance_psi || 0;

  // Gauge for free-fall: 0-2000 ft range
  const ffPct = Math.min((ffHeight / 2000) * 100, 100);
  // Gauge for U-tube: 0-500 psi range
  const utPct = Math.min((Math.abs(utubePressure) / 500) * 100, 100);

  const getColor = (pct: number) => {
    if (pct < 25) return '#22c55e';
    if (pct < 60) return '#eab308';
    return '#ef4444';
  };

  return (
    <ChartContainer title="Free-Fall & U-Tube" icon={ArrowDownCircle} height={height} isFluid>
      <div className="flex flex-col h-full justify-center gap-8 px-2">
        {/* Free-Fall Section */}
        <div>
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm font-bold">Free-Fall</span>
            <span className={`text-sm font-bold px-2 py-0.5 rounded ${ffOccurs ? 'bg-yellow-500/20 text-yellow-400' : 'bg-green-500/20 text-green-400'}`}>
              {ffOccurs ? 'OCURRE' : 'NO OCURRE'}
            </span>
          </div>
          <div className="w-full bg-white/5 rounded-full h-6 overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-700 flex items-center justify-end pr-2"
              style={{ width: `${Math.max(ffPct, 5)}%`, backgroundColor: getColor(ffPct) }}
            >
              <span className="text-[10px] font-bold text-white">{ffHeight} ft</span>
            </div>
          </div>
          <p className="text-xs text-gray-500 mt-1">{freeFall?.explanation || ''}</p>
        </div>

        {/* U-Tube Section */}
        <div>
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm font-bold">U-Tube Effect</span>
            <span className={`text-sm font-bold px-2 py-0.5 rounded ${utubeOccurs ? 'bg-yellow-500/20 text-yellow-400' : 'bg-green-500/20 text-green-400'}`}>
              {utubeOccurs ? 'OCURRE' : 'EQUILIBRADO'}
            </span>
          </div>
          <div className="w-full bg-white/5 rounded-full h-6 overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-700 flex items-center justify-end pr-2"
              style={{ width: `${Math.max(utPct, 5)}%`, backgroundColor: getColor(utPct) }}
            >
              <span className="text-[10px] font-bold text-white">{Math.abs(utubePressure)} psi</span>
            </div>
          </div>
          <p className="text-xs text-gray-500 mt-1">{utube?.explanation || ''}</p>
        </div>

        {/* Lift Pressure */}
        {utube?.lift_pressure_psi !== undefined && (
          <div className="border-t border-white/10 pt-3">
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Lift Pressure Required:</span>
              <span className="font-mono font-bold text-orange-400">{utube.lift_pressure_psi || '—'} psi</span>
            </div>
          </div>
        )}
      </div>
    </ChartContainer>
  );
};

export default FreeFallIndicator;
