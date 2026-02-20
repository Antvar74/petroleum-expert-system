/**
 * BiaxialEllipse.tsx — API 5C3 biaxial ellipse visualization.
 * Shows the yield ellipse and operating point (axial stress, collapse load).
 */
import React from 'react';
import ChartContainer from '../ChartContainer';
import { CircleDot } from 'lucide-react';

interface BiaxialEllipseProps {
  biaxial: any;
  height?: number;
}

const BiaxialEllipse: React.FC<BiaxialEllipseProps> = ({ biaxial, height = 350 }) => {
  if (!biaxial) return null;

  const yieldStrength = biaxial.yield_strength_psi || 80000;
  const axialStress = biaxial.axial_stress_psi || 0;
  const originalCollapse = biaxial.original_collapse_psi || 0;
  const correctedCollapse = biaxial.corrected_collapse_psi || 0;
  const reductionFactor = biaxial.reduction_factor || 1.0;

  // SVG viewBox dimensions
  const w = 400, h = 350;
  const cx = w / 2, cy = h / 2;
  const rx = 160, ry = 130;

  // Normalize axial and collapse to ellipse coordinates
  const normAxial = axialStress / yieldStrength;
  const normCollapse = originalCollapse / (yieldStrength * 0.8); // approximate collapse/yield ratio

  // Point on SVG
  const ptX = cx + normAxial * rx;
  const ptY = cy - normCollapse * ry;

  return (
    <ChartContainer title="Elipse Biaxial API 5C3" icon={CircleDot} height={height} isFluid>
      <div className="flex flex-col h-full">
        <svg viewBox={`0 0 ${w} ${h}`} className="flex-1" preserveAspectRatio="xMidYMid meet">
          {/* Grid lines */}
          <line x1={0} y1={cy} x2={w} y2={cy} stroke="rgba(255,255,255,0.1)" />
          <line x1={cx} y1={0} x2={cx} y2={h} stroke="rgba(255,255,255,0.1)" />

          {/* Yield ellipse */}
          <ellipse cx={cx} cy={cy} rx={rx} ry={ry}
            fill="none" stroke="#6366f1" strokeWidth={2} strokeDasharray="4 4" opacity={0.6} />

          {/* Safe zone fill */}
          <ellipse cx={cx} cy={cy} rx={rx} ry={ry}
            fill="#6366f1" opacity={0.05} />

          {/* Operating point */}
          <circle cx={ptX} cy={ptY} r={8} fill="#ef4444" opacity={0.8} />
          <circle cx={ptX} cy={ptY} r={12} fill="none" stroke="#ef4444" strokeWidth={1} opacity={0.4} />

          {/* Axis labels */}
          <text x={w - 10} y={cy - 8} fill="rgba(255,255,255,0.4)" fontSize={10} textAnchor="end">
            +σ_axial
          </text>
          <text x={10} y={cy - 8} fill="rgba(255,255,255,0.4)" fontSize={10}>
            -σ_axial
          </text>
          <text x={cx + 5} y={18} fill="rgba(255,255,255,0.4)" fontSize={10}>
            +Collapse
          </text>
          <text x={cx + 5} y={h - 8} fill="rgba(255,255,255,0.4)" fontSize={10}>
            -Collapse
          </text>

          {/* Legend */}
          <text x={cx} y={cy + ry + 25} fill="rgba(255,255,255,0.3)" fontSize={9} textAnchor="middle">
            Yield Envelope (API 5C3)
          </text>
        </svg>

        {/* Data summary */}
        <div className="grid grid-cols-3 gap-3 text-xs border-t border-white/10 pt-3 pb-4">
          <div className="text-center">
            <div className="text-gray-500">Collapse Original</div>
            <div className="font-mono font-bold text-white">{originalCollapse} psi</div>
          </div>
          <div className="text-center">
            <div className="text-gray-500">Collapse Corregido</div>
            <div className="font-mono font-bold text-yellow-400">{correctedCollapse} psi</div>
          </div>
          <div className="text-center">
            <div className="text-gray-500">Factor Reducción</div>
            <div className="font-mono font-bold text-indigo-400">{reductionFactor}</div>
          </div>
        </div>
      </div>
    </ChartContainer>
  );
};

export default BiaxialEllipse;
