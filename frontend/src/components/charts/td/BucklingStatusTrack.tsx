/**
 * BucklingStatusTrack.tsx — Vertical color-coded bar showing buckling status by depth.
 */
import React from 'react';
import { BUCKLING_COLORS } from '../ChartTheme';

interface BucklingPoint {
  md: number;
  buckling_status: string;
}

interface BucklingStatusTrackProps {
  data: BucklingPoint[];
  height?: number;
}

const BucklingStatusTrack: React.FC<BucklingStatusTrackProps> = ({ data, height = 450 }) => {
  if (!data?.length) return null;

  const minMD = data[0]?.md || 0;
  const maxMD = data[data.length - 1]?.md || 1;
  const range = maxMD - minMD || 1;

  return (
    <div className="glass-panel p-4 rounded-xl border border-white/5 print-chart" style={{ height }}>
      <h4 className="font-bold text-xs mb-3 text-center text-white/60">Buckling</h4>
      <div className="relative mx-auto" style={{ width: 30, height: height - 60 }}>
        {/* Background */}
        <div className="absolute inset-0 rounded-full bg-white/5" />

        {/* Colored segments */}
        {data.map((pt, i) => {
          const nextMD = i < data.length - 1 ? data[i + 1].md : maxMD;
          const top = ((pt.md - minMD) / range) * 100;
          const segHeight = ((nextMD - pt.md) / range) * 100;
          const color = BUCKLING_COLORS[pt.buckling_status] || BUCKLING_COLORS.OK;

          return (
            <div
              key={i}
              className="absolute rounded-sm transition-all group"
              style={{
                top: `${top}%`,
                height: `${Math.max(segHeight, 0.5)}%`,
                left: 2,
                right: 2,
                backgroundColor: color,
                opacity: 0.7,
              }}
              title={`${pt.md} ft — ${pt.buckling_status}`}
            >
              <div className="hidden group-hover:block absolute left-10 top-0 z-10 bg-black/90 border border-white/10 rounded px-2 py-1 text-xs whitespace-nowrap">
                {pt.md} ft — {pt.buckling_status}
              </div>
            </div>
          );
        })}

        {/* Depth labels */}
        <span className="absolute -left-10 top-0 text-[9px] text-white/30">{minMD}</span>
        <span className="absolute -left-10 bottom-0 text-[9px] text-white/30">{maxMD}</span>
      </div>

      {/* Legend */}
      <div className="flex justify-center gap-3 mt-3">
        {Object.entries(BUCKLING_COLORS).map(([status, color]) => (
          <div key={status} className="flex items-center gap-1 text-[9px] text-white/40">
            <div className="w-2 h-2 rounded-sm" style={{ backgroundColor: color }} />
            {status}
          </div>
        ))}
      </div>
    </div>
  );
};

export default BucklingStatusTrack;
