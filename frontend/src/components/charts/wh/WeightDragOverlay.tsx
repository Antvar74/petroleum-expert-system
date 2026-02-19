/**
 * WeightDragOverlay.tsx — Horizontal bar comparing weight components and drag.
 */
import React from 'react';
import ChartContainer from '../ChartContainer';
import { Weight } from 'lucide-react';

interface WeightDragOverlayProps {
  weightAnalysis: { air_weight_lb: number; buoyancy_factor: number; buoyed_weight_lb: number; axial_component_lb: number };
  dragAnalysis: { drag_force_lb: number; normal_force_lb: number; friction_factor: number };
  params: { inclination: number };
  height?: number;
}

const WeightDragOverlay: React.FC<WeightDragOverlayProps> = ({ weightAnalysis, dragAnalysis, params, height = 350 }) => {
  if (!weightAnalysis || !dragAnalysis) return null;

  const maxVal = Math.max(weightAnalysis.air_weight_lb, weightAnalysis.buoyed_weight_lb, dragAnalysis.drag_force_lb, 1);

  const bars = [
    { label: 'Peso Aire', value: weightAnalysis.air_weight_lb, color: '#94a3b8' },
    { label: 'Peso Flotado', value: weightAnalysis.buoyed_weight_lb, color: '#14b8a6' },
    { label: 'Comp. Axial', value: weightAnalysis.axial_component_lb, color: '#3b82f6' },
    { label: 'Fuerza Normal', value: dragAnalysis.normal_force_lb, color: '#f59e0b' },
    { label: 'Drag', value: dragAnalysis.drag_force_lb, color: '#ef4444' },
  ];

  return (
    <ChartContainer title="Peso y Arrastre" icon={Weight} height={height} isFluid
      badge={{ text: `Incl: ${params.inclination}°`, color: 'bg-blue-500/20 text-blue-400' }}>
      <div className="flex flex-col gap-3 p-4">
        {bars.map((bar, i) => (
          <div key={i} className="flex items-center gap-3">
            <span className="text-xs text-gray-400 w-28 text-right">{bar.label}</span>
            <div className="flex-1 bg-white/5 rounded-full h-6 overflow-hidden">
              <div className="h-full rounded-full flex items-center px-2 text-xs font-bold text-white transition-all"
                style={{ width: `${Math.max((bar.value / maxVal) * 100, 2)}%`, backgroundColor: bar.color }}>
                {bar.value.toLocaleString()} lb
              </div>
            </div>
          </div>
        ))}
        <div className="text-xs text-gray-500 mt-2 text-center">
          BF: {weightAnalysis.buoyancy_factor} | μ: {dragAnalysis.friction_factor}
        </div>
      </div>
    </ChartContainer>
  );
};

export default WeightDragOverlay;
