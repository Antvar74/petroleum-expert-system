/**
 * DrawdownLimitGauge.tsx — Visual gauge for critical drawdown pressure.
 */
import React from 'react';
import ChartContainer from '../ChartContainer';
import { Gauge } from 'lucide-react';

interface DrawdownLimitGaugeProps {
  drawdown: { critical_drawdown_psi: number; sanding_risk: string; recommendation: string };
  height?: number;
}

const DrawdownLimitGauge: React.FC<DrawdownLimitGaugeProps> = ({ drawdown, height = 350 }) => {
  if (!drawdown) return null;

  const maxDrawdown = 3000;
  const ratio = Math.min(drawdown.critical_drawdown_psi / maxDrawdown, 1);

  const getColor = () => {
    const risk = drawdown.sanding_risk;
    if (risk?.includes('Very High') || risk?.includes('High')) return { bar: '#ef4444', text: 'text-red-400', bg: 'bg-red-500/10' };
    if (risk?.includes('Moderate')) return { bar: '#f59e0b', text: 'text-yellow-400', bg: 'bg-yellow-500/10' };
    if (risk?.includes('Low')) return { bar: '#22c55e', text: 'text-green-400', bg: 'bg-green-500/10' };
    return { bar: '#22c55e', text: 'text-green-400', bg: 'bg-green-500/10' };
  };
  const colors = getColor();

  return (
    <ChartContainer title="Drawdown Crítico" icon={Gauge} height={height} isFluid
      badge={{ text: drawdown.sanding_risk, color: `${colors.bg} ${colors.text}` }}>
      <div className="flex flex-col items-center justify-center gap-6 p-6">
        {/* Semi-circular gauge */}
        <div className="relative w-56 h-28 overflow-hidden">
          <svg viewBox="0 0 200 100" className="w-full h-full">
            <path d="M 20 90 A 80 80 0 0 1 180 90" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="14" strokeLinecap="round" />
            <path d="M 20 90 A 80 80 0 0 1 180 90" fill="none" stroke={colors.bar} strokeWidth="14" strokeLinecap="round"
              strokeDasharray={`${ratio * 251} 251`} className="transition-all duration-1000" />
          </svg>
          <div className="absolute bottom-0 left-1/2 transform -translate-x-1/2 text-center">
            <span className={`text-2xl font-bold ${colors.text}`}>{drawdown.critical_drawdown_psi}</span>
            <span className="text-xs text-gray-500 block">psi</span>
          </div>
        </div>

        {/* Risk zones */}
        <div className="flex gap-4 text-xs">
          <div className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500" /> &lt;200</div>
          <div className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-yellow-500" /> 200-1000</div>
          <div className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-green-500" /> &gt;1000</div>
        </div>

        <p className="text-xs text-gray-400 text-center max-w-xs">{drawdown.recommendation}</p>
      </div>
    </ChartContainer>
  );
};

export default DrawdownLimitGauge;
