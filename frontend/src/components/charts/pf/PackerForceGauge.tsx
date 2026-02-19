/**
 * PackerForceGauge.tsx — Visual gauge showing total force vs buckling limit.
 */
import React from 'react';
import { PieChart, Pie, Cell } from 'recharts';
import ChartContainer from '../ChartContainer';
import { Gauge } from 'lucide-react';

interface PackerForceGaugeProps {
  totalForce: number;
  bucklingCritical: number;
  bucklingStatus: string;
  forceDirection: string;
  height?: number;
}

const PackerForceGaugeComponent: React.FC<PackerForceGaugeProps> = ({
  totalForce, bucklingCritical, bucklingStatus, forceDirection, height = 300
}) => {
  const statusColor = bucklingStatus === 'OK' ? '#10b981' : bucklingStatus === 'Sinusoidal Buckling' ? '#f59e0b' : '#ef4444';

  // Normalize force for gauge (compression side)
  const compressiveForce = totalForce < 0 ? Math.abs(totalForce) : 0;
  const ratio = bucklingCritical > 0 ? Math.min(compressiveForce / bucklingCritical, 1.5) : 0;
  const gaugePercent = Math.min(ratio / 1.5, 1.0);

  const gaugeData = [
    { value: gaugePercent * 100 },
    { value: (1 - gaugePercent) * 100 },
  ];

  return (
    <ChartContainer
      title="Packer Force & Buckling"
      icon={Gauge}
      height={height}
      isFluid
      badge={{ text: bucklingStatus, color: bucklingStatus === 'OK' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400' }}
    >
      <div className="flex flex-col items-center gap-4">
        <div className="relative">
          <PieChart width={200} height={110}>
            <Pie
              data={gaugeData}
              cx={100} cy={100}
              startAngle={180} endAngle={0}
              innerRadius={60} outerRadius={85}
              dataKey="value"
              stroke="none"
            >
              <Cell fill={statusColor} />
              <Cell fill="#334155" />
            </Pie>
          </PieChart>
          <div className="absolute inset-0 flex flex-col items-center justify-end pb-2">
            <span className="text-xl font-bold" style={{ color: statusColor }}>
              {Math.abs(totalForce).toLocaleString()}
            </span>
            <span className="text-xs text-gray-400">lbs ({forceDirection})</span>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-6 text-center">
          <div>
            <div className="text-lg font-bold text-blue-400">{bucklingCritical.toLocaleString()}</div>
            <div className="text-xs text-gray-500">Critical Load (lbs)</div>
          </div>
          <div>
            <div className="text-lg font-bold" style={{ color: statusColor }}>{bucklingStatus}</div>
            <div className="text-xs text-gray-500">Buckling Status</div>
          </div>
        </div>
      </div>
    </ChartContainer>
  );
};

export default PackerForceGaugeComponent;
