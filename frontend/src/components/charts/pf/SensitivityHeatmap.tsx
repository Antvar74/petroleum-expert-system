/**
 * SensitivityHeatmap.tsx — Table/heatmap showing force sensitivity to pressure and temperature changes.
 */
import React from 'react';
import ChartContainer from '../ChartContainer';
import { Grid3X3 } from 'lucide-react';

interface SensitivityHeatmapProps {
  data: { deltaP: number; deltaT: number; totalForce: number }[];
  height?: number;
}

const SensitivityHeatmap: React.FC<SensitivityHeatmapProps> = ({ data, height = 350 }) => {
  if (!data?.length) return null;

  // Get unique deltaP and deltaT values
  const deltaPValues = [...new Set(data.map(d => d.deltaP))].sort((a, b) => a - b);
  const deltaTValues = [...new Set(data.map(d => d.deltaT))].sort((a, b) => a - b);

  const getForce = (dp: number, dt: number) => {
    const match = data.find(d => d.deltaP === dp && d.deltaT === dt);
    return match?.totalForce ?? null;
  };

  const getColor = (force: number | null) => {
    if (force === null) return 'bg-gray-800';
    if (force > 50000) return 'bg-green-600/60 text-green-200';
    if (force > 0) return 'bg-green-500/30 text-green-300';
    if (force > -50000) return 'bg-yellow-500/30 text-yellow-300';
    return 'bg-red-500/40 text-red-300';
  };

  return (
    <ChartContainer title="Sensitivity Analysis" icon={Grid3X3} height={height} isFluid>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr>
              <th className="p-2 text-gray-400 border-b border-white/10">ΔP \ ΔT</th>
              {deltaTValues.map(dt => (
                <th key={dt} className="p-2 text-gray-400 border-b border-white/10">{dt}°F</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {deltaPValues.map(dp => (
              <tr key={dp}>
                <td className="p-2 text-gray-400 font-medium border-r border-white/10">{dp} psi</td>
                {deltaTValues.map(dt => {
                  const force = getForce(dp, dt);
                  return (
                    <td key={dt} className={`p-2 text-center font-mono ${getColor(force)} rounded`}>
                      {force !== null ? (force / 1000).toFixed(0) + 'k' : '-'}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
        <div className="text-xs text-gray-500 mt-2 text-center">Values in lbs (÷1000). Green = Tension, Red = Compression</div>
      </div>
    </ChartContainer>
  );
};

export default SensitivityHeatmap;
