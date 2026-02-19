/**
 * CuttingsConcentrationGauge.tsx — Gauge showing cuttings concentration and HCI.
 */
import React from 'react';
import { PieChart, Pie, Cell } from 'recharts';
import ChartContainer from '../ChartContainer';
import { Activity } from 'lucide-react';

interface CuttingsConcentrationGaugeProps {
  concentration: number;
  hci: number;
  ctr: number;
  cleaningQuality: string;
  height?: number;
}

const CuttingsConcentrationGauge: React.FC<CuttingsConcentrationGaugeProps> = ({
  concentration, hci, ctr, cleaningQuality, height = 300
}) => {
  const qualityColor = cleaningQuality === 'Good' ? '#10b981' : cleaningQuality === 'Marginal' ? '#f59e0b' : '#ef4444';

  // Gauge data for HCI (0 to 1.5 range)
  const hciNormalized = Math.min(hci / 1.5, 1.0);
  const gaugeData = [
    { value: hciNormalized * 100 },
    { value: (1 - hciNormalized) * 100 },
  ];

  return (
    <ChartContainer
      title="Cleaning Performance"
      icon={Activity}
      height={height}
      isFluid
      badge={{ text: cleaningQuality, color: cleaningQuality === 'Good' ? 'bg-green-500/20 text-green-400' : cleaningQuality === 'Marginal' ? 'bg-yellow-500/20 text-yellow-400' : 'bg-red-500/20 text-red-400' }}
    >
      <div className="flex flex-col items-center gap-4">
        {/* HCI Gauge */}
        <div className="relative">
          <PieChart width={180} height={100}>
            <Pie
              data={gaugeData}
              cx={90} cy={90}
              startAngle={180} endAngle={0}
              innerRadius={55} outerRadius={75}
              dataKey="value"
              stroke="none"
            >
              <Cell fill={qualityColor} />
              <Cell fill="#334155" />
            </Pie>
          </PieChart>
          <div className="absolute inset-0 flex flex-col items-center justify-end pb-2">
            <span className="text-2xl font-bold" style={{ color: qualityColor }}>{hci.toFixed(2)}</span>
            <span className="text-xs text-gray-400">HCI</span>
          </div>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-3 gap-4 w-full text-center">
          <div>
            <div className="text-lg font-bold text-blue-400">{ctr.toFixed(3)}</div>
            <div className="text-xs text-gray-500">CTR</div>
          </div>
          <div>
            <div className="text-lg font-bold" style={{ color: concentration > 5 ? '#ef4444' : '#10b981' }}>
              {concentration.toFixed(1)}%
            </div>
            <div className="text-xs text-gray-500">Cuttings Vol%</div>
          </div>
          <div>
            <div className="text-lg font-bold" style={{ color: qualityColor }}>
              {cleaningQuality}
            </div>
            <div className="text-xs text-gray-500">Quality</div>
          </div>
        </div>
      </div>
    </ChartContainer>
  );
};

export default CuttingsConcentrationGauge;
