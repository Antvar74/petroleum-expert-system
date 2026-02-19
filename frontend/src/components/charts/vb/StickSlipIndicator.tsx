/**
 * StickSlipIndicator.tsx — Visual indicator showing stick-slip severity.
 */
import React from 'react';
import ChartContainer from '../ChartContainer';
import { RotateCw } from 'lucide-react';

interface StickSlipIndicatorProps {
  stickSlip: {
    severity_index: number;
    classification: string;
    color: string;
    rpm_min_at_bit: number;
    rpm_max_at_bit: number;
    surface_rpm: number;
    friction_torque_ftlb: number;
    angular_displacement_deg: number;
    recommendation: string;
  };
  height?: number;
}

const StickSlipIndicator: React.FC<StickSlipIndicatorProps> = ({ stickSlip, height = 320 }) => {
  if (!stickSlip) return null;

  const sev = stickSlip.severity_index;
  const colorMap: Record<string, string> = { green: '#22c55e', yellow: '#eab308', orange: '#f97316', red: '#ef4444' };
  const fillColor = colorMap[stickSlip.color] || '#22c55e';

  // Normalize severity to 0-100 for display (cap at 2.0)
  const barPct = Math.min(100, (sev / 2.0) * 100);

  // Zones
  const zones = [
    { label: 'Mild', start: 0, end: 25, color: '#22c55e' },
    { label: 'Moderate', start: 25, end: 50, color: '#eab308' },
    { label: 'Severe', start: 50, end: 75, color: '#f97316' },
    { label: 'Critical', start: 75, end: 100, color: '#ef4444' },
  ];

  return (
    <ChartContainer
      title="Indicador Stick-Slip"
      icon={RotateCw}
      height={height}
      badge={{ text: stickSlip.classification, color: `bg-[${fillColor}]/20` }}
      isFluid
    >
      <div className="flex flex-col items-center justify-center h-full gap-4 px-4">
        {/* Severity bar */}
        <div className="w-full">
          <div className="flex justify-between text-xs text-gray-500 mb-1">
            <span>0</span>
            <span>Severidad: {sev.toFixed(2)}</span>
            <span>2.0</span>
          </div>
          <div className="relative w-full h-8 rounded-full overflow-hidden flex">
            {zones.map(z => (
              <div key={z.label} className="h-full" style={{ width: `${z.end - z.start}%`, backgroundColor: z.color, opacity: 0.2 }} />
            ))}
            {/* Marker */}
            <div className="absolute top-0 h-full w-1 rounded-full z-10"
              style={{ left: `${barPct}%`, backgroundColor: fillColor, boxShadow: `0 0 10px ${fillColor}` }}>
              <div className="absolute -top-5 -translate-x-1/2 text-xs font-bold whitespace-nowrap" style={{ color: fillColor }}>
                {sev.toFixed(2)}
              </div>
            </div>
          </div>
          <div className="flex justify-between text-[9px] text-gray-600 mt-0.5">
            {zones.map(z => <span key={z.label} style={{ color: z.color }}>{z.label}</span>)}
          </div>
        </div>

        {/* RPM at bit visualization */}
        <div className="w-full bg-white/5 p-4 rounded-xl">
          <div className="text-xs text-gray-400 mb-2 text-center">RPM en Broca (estimado)</div>
          <div className="flex items-center gap-3 justify-center">
            <div className="text-center">
              <div className="text-lg font-bold text-blue-400">{stickSlip.rpm_min_at_bit}</div>
              <div className="text-[10px] text-gray-500">Mín</div>
            </div>
            <div className="flex-1 h-3 bg-white/5 rounded-full relative mx-2 max-w-[120px]">
              <div className="absolute top-0 h-full rounded-full" style={{
                left: `${(stickSlip.rpm_min_at_bit / (stickSlip.rpm_max_at_bit || 1)) * 40}%`,
                width: `${60}%`,
                backgroundColor: fillColor,
                opacity: 0.4,
              }} />
              <div className="absolute top-1/2 -translate-y-1/2 w-2 h-2 rounded-full bg-white"
                style={{ left: '50%', transform: 'translate(-50%, -50%)' }}
                title={`Surface: ${stickSlip.surface_rpm}`}
              />
            </div>
            <div className="text-center">
              <div className="text-lg font-bold text-red-400">{stickSlip.rpm_max_at_bit}</div>
              <div className="text-[10px] text-gray-500">Máx</div>
            </div>
          </div>
        </div>

        {/* Recommendation */}
        <p className="text-xs text-gray-400 italic text-center px-2">{stickSlip.recommendation}</p>
      </div>
    </ChartContainer>
  );
};

export default StickSlipIndicator;
