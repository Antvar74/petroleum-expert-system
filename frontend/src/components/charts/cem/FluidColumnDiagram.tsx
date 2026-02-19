/**
 * FluidColumnDiagram.tsx — Stacked bar showing fluid column layout in well.
 * Displays spacer, lead cement, tail cement, rat-hole proportions.
 */
import React from 'react';
import ChartContainer from '../ChartContainer';
import { Cylinder } from 'lucide-react';

interface FluidColumnDiagramProps {
  volumes: any;
  height?: number;
}

const FLUID_SECTIONS = [
  { key: 'spacer', label: 'Spacer', color: '#eab308', field: 'spacer_volume_bbl' },
  { key: 'lead', label: 'Lead Cement', color: '#14b8a6', field: 'lead_cement_bbl' },
  { key: 'tail', label: 'Tail Cement', color: '#f97316', field: 'tail_cement_bbl' },
  { key: 'displacement', label: 'Displacement', color: '#6366f1', field: 'displacement_volume_bbl' },
];

const FluidColumnDiagram: React.FC<FluidColumnDiagramProps> = ({ volumes, height = 350 }) => {
  if (!volumes) return null;

  const total = volumes.total_pump_volume_bbl || 1;
  const sections = FLUID_SECTIONS.map(s => ({
    ...s,
    value: volumes[s.field] || 0,
    pct: ((volumes[s.field] || 0) / total * 100).toFixed(1),
  }));

  return (
    <ChartContainer title="Columna de Fluidos" icon={Cylinder} height={height} isFluid>
      <div className="flex flex-col h-full justify-between">
        {/* Stacked horizontal bar */}
        <div className="flex-1 flex flex-col justify-center px-2">
          <div className="w-full rounded-lg overflow-hidden flex" style={{ height: 40 }}>
            {sections.map(s => (
              <div
                key={s.key}
                style={{ width: `${s.pct}%`, backgroundColor: s.color }}
                className="transition-all duration-500 relative group"
                title={`${s.label}: ${s.value} bbl (${s.pct}%)`}
              >
                {parseFloat(s.pct) > 10 && (
                  <span className="absolute inset-0 flex items-center justify-center text-[10px] font-bold text-white/90">
                    {s.pct}%
                  </span>
                )}
              </div>
            ))}
          </div>

          {/* Legend */}
          <div className="grid grid-cols-2 gap-2 mt-4">
            {sections.map(s => (
              <div key={s.key} className="flex items-center gap-2 text-xs">
                <span className="w-3 h-3 rounded-sm flex-shrink-0" style={{ backgroundColor: s.color }} />
                <span className="text-gray-400">{s.label}:</span>
                <span className="font-mono font-bold text-white">{s.value} bbl</span>
              </div>
            ))}
          </div>
        </div>

        {/* Summary */}
        <div className="border-t border-white/10 pt-3 mt-3">
          <div className="flex justify-between text-sm">
            <span className="text-gray-400">Total Bombeo:</span>
            <span className="font-mono font-bold text-teal-400">{volumes.total_pump_volume_bbl} bbl</span>
          </div>
          <div className="flex justify-between text-sm mt-1">
            <span className="text-gray-400">Total Cemento:</span>
            <span className="font-mono font-bold text-white">
              {((volumes.lead_cement_bbl || 0) + (volumes.tail_cement_bbl || 0)).toFixed(1)} bbl
              ({((volumes.lead_cement_sacks || 0) + (volumes.tail_cement_sacks || 0))} sacos)
            </span>
          </div>
        </div>
      </div>
    </ChartContainer>
  );
};

export default FluidColumnDiagram;
