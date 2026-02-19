/**
 * StabilityGauge.tsx — Radial gauge showing combined stability index (0-100).
 */
import React from 'react';
import ChartContainer from '../ChartContainer';
import { Shield } from 'lucide-react';

interface StabilityGaugeProps {
  stability: {
    stability_index: number;
    status: string;
    color: string;
    mode_scores: Record<string, number>;
    weights: Record<string, number>;
  };
  height?: number;
}

const StabilityGauge: React.FC<StabilityGaugeProps> = ({ stability, height = 320 }) => {
  if (!stability) return null;

  const idx = stability.stability_index;
  const angle = (idx / 100) * 180; // 0-180 degrees for half circle
  const colorMap: Record<string, string> = { green: '#22c55e', yellow: '#eab308', orange: '#f97316', red: '#ef4444' };
  const fillColor = colorMap[stability.color] || '#22c55e';

  // SVG arc
  const cx = 140, cy = 130, r = 100;
  const startAngle = Math.PI;
  const endAngle = Math.PI - (angle * Math.PI / 180);
  const x1 = cx + r * Math.cos(startAngle);
  const y1 = cy + r * Math.sin(startAngle);
  const x2 = cx + r * Math.cos(endAngle);
  const y2 = cy + r * Math.sin(endAngle);
  const largeArcFlag = angle > 90 ? 1 : 0;

  return (
    <ChartContainer
      title="Índice de Estabilidad Global"
      icon={Shield}
      height={height}
      badge={{ text: stability.status, color: `bg-${stability.color === 'green' ? 'green' : stability.color === 'yellow' ? 'yellow' : stability.color === 'orange' ? 'orange' : 'red'}-500/20 text-${stability.color === 'green' ? 'green' : stability.color === 'yellow' ? 'yellow' : stability.color === 'orange' ? 'orange' : 'red'}-400` }}
      isFluid
    >
      <div className="flex flex-col items-center justify-center h-full">
        <svg width="280" height="160" viewBox="0 0 280 160">
          {/* Background arc */}
          <path
            d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
            fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="20" strokeLinecap="round"
          />
          {/* Value arc */}
          {angle > 0 && (
            <path
              d={`M ${x1} ${y1} A ${r} ${r} 0 ${largeArcFlag} 1 ${x2} ${y2}`}
              fill="none" stroke={fillColor} strokeWidth="20" strokeLinecap="round"
              style={{ filter: `drop-shadow(0 0 8px ${fillColor}40)` }}
            />
          )}
          {/* Center text */}
          <text x={cx} y={cy - 10} textAnchor="middle" fill={fillColor} fontSize="36" fontWeight="bold">{idx.toFixed(0)}</text>
          <text x={cx} y={cy + 12} textAnchor="middle" fill="rgba(255,255,255,0.4)" fontSize="11">/100</text>
          {/* Scale labels */}
          <text x={cx - r - 10} y={cy + 20} fill="rgba(255,255,255,0.3)" fontSize="10" textAnchor="middle">0</text>
          <text x={cx} y={cy - r - 10} fill="rgba(255,255,255,0.3)" fontSize="10" textAnchor="middle">50</text>
          <text x={cx + r + 10} y={cy + 20} fill="rgba(255,255,255,0.3)" fontSize="10" textAnchor="middle">100</text>
        </svg>

        {/* Mode scores bar */}
        <div className="flex gap-3 mt-2">
          {Object.entries(stability.mode_scores).map(([mode, score]) => (
            <div key={mode} className="text-center">
              <div className="text-[10px] text-gray-500 capitalize mb-1">{mode}</div>
              <div className={`text-xs font-bold ${score >= 70 ? 'text-green-400' : score >= 40 ? 'text-yellow-400' : 'text-red-400'}`}>
                {score.toFixed(0)}
              </div>
            </div>
          ))}
        </div>
      </div>
    </ChartContainer>
  );
};

export default StabilityGauge;
