/**
 * VibrationMapHeatmap.tsx — RPM vs WOB stability heatmap.
 */
import React from 'react';
import ChartContainer from '../ChartContainer';
import { Grid3x3 } from 'lucide-react';

interface VibrationMapHeatmapProps {
  vibrationMap: {
    map_data: {
      wob_klb: number; rpm: number;
      stability_index: number; status: string;
    }[];
    wob_range: number[];
    rpm_range: number[];
    optimal_point: { wob: number; rpm: number; score: number };
    critical_rpm_axial: number;
    critical_rpm_lateral: number;
  };
  height?: number;
}

const VibrationMapHeatmap: React.FC<VibrationMapHeatmapProps> = ({ vibrationMap, height = 380 }) => {
  if (!vibrationMap?.map_data?.length) return null;

  const { wob_range, rpm_range, map_data, optimal_point } = vibrationMap;

  const getColor = (score: number) => {
    if (score >= 80) return '#22c55e';
    if (score >= 60) return '#84cc16';
    if (score >= 40) return '#eab308';
    if (score >= 20) return '#f97316';
    return '#ef4444';
  };

  const cellW = Math.min(40, 280 / rpm_range.length);
  const cellH = Math.min(35, 220 / wob_range.length);

  return (
    <ChartContainer
      title="Mapa de Vibraciones (RPM × WOB)"
      icon={Grid3x3}
      height={height}
      badge={{ text: `Óptimo: ${optimal_point.rpm} RPM @ ${optimal_point.wob} klb`, color: 'bg-green-500/20 text-green-400' }}
      isFluid
    >
      <div className="flex flex-col items-center justify-center h-full overflow-auto p-2">
        <div className="flex items-end gap-0.5">
          {/* Y axis label */}
          <div className="flex flex-col items-end pr-1" style={{ width: 40 }}>
            <div className="text-[9px] text-gray-500 mb-1 -rotate-90 whitespace-nowrap origin-bottom-right">WOB (klb)</div>
            {[...wob_range].reverse().map(w => (
              <div key={w} className="text-[10px] text-gray-500 font-mono flex items-center justify-end" style={{ height: cellH }}>{w}</div>
            ))}
          </div>
          {/* Grid */}
          <div>
            {/* Cells */}
            <div className="flex flex-col gap-0.5">
              {[...wob_range].reverse().map(wob => (
                <div key={wob} className="flex gap-0.5">
                  {rpm_range.map(rpm => {
                    const pt = map_data.find(d => d.wob_klb === wob && d.rpm === rpm);
                    const score = pt?.stability_index || 0;
                    const isOptimal = wob === optimal_point.wob && rpm === optimal_point.rpm;
                    return (
                      <div
                        key={`${wob}-${rpm}`}
                        className="rounded-sm flex items-center justify-center text-[8px] font-bold relative"
                        style={{
                          width: cellW, height: cellH,
                          backgroundColor: getColor(score),
                          opacity: isOptimal ? 1 : 0.7,
                          border: isOptimal ? '2px solid white' : 'none',
                          color: score >= 60 ? '#000' : '#fff',
                        }}
                        title={`WOB: ${wob}, RPM: ${rpm}, Score: ${score.toFixed(0)}`}
                      >
                        {score.toFixed(0)}
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>
            {/* X axis */}
            <div className="flex gap-0.5 mt-1">
              {rpm_range.map(r => (
                <div key={r} className="text-[10px] text-gray-500 font-mono text-center" style={{ width: cellW }}>{r}</div>
              ))}
            </div>
            <div className="text-[9px] text-gray-500 text-center mt-1">RPM</div>
          </div>
        </div>
        {/* Legend */}
        <div className="flex gap-2 mt-3 text-[9px]">
          {[
            { label: 'Stable', color: '#22c55e' },
            { label: 'Good', color: '#84cc16' },
            { label: 'Marginal', color: '#eab308' },
            { label: 'Unstable', color: '#f97316' },
            { label: 'Critical', color: '#ef4444' },
          ].map(l => (
            <div key={l.label} className="flex items-center gap-1">
              <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: l.color }} />
              <span className="text-gray-400">{l.label}</span>
            </div>
          ))}
        </div>
      </div>
    </ChartContainer>
  );
};

export default VibrationMapHeatmap;
