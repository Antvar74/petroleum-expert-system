import { useMemo } from 'react';
import {
  ComposedChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ReferenceLine, ResponsiveContainer,
} from 'recharts';

interface SFvsDepthChartProps {
  sfVsDepth: {
    profile?: Array<{
      tvd_ft: number;
      sf_burst: number;
      sf_collapse: number;
      sf_tension: number;
      governing_sf: number;
    }>;
    min_sf?: number;
    min_sf_depth_ft?: number;
  } | null;
  sfBurstMin?: number;
  sfCollapseMin?: number;
  sfTensionMin?: number;
  height?: number;
}

export default function SFvsDepthChart({
  sfVsDepth,
  sfBurstMin = 1.1,
  sfCollapseMin = 1.0,
  sfTensionMin = 1.6,
  height = 400,
}: SFvsDepthChartProps) {
  const data = useMemo(() => {
    if (!sfVsDepth?.profile) return [];
    return sfVsDepth.profile
      .filter((p) => p.sf_burst < 90 || p.sf_collapse < 90 || p.sf_tension < 90)
      .map((p) => ({
        depth: p.tvd_ft,
        burst: Math.min(p.sf_burst, 10),
        collapse: Math.min(p.sf_collapse, 10),
        tension: Math.min(p.sf_tension, 10),
      }));
  }, [sfVsDepth]);

  if (!data.length) {
    return (
      <div className="glass-card p-4 flex items-center justify-center" style={{ height }}>
        <span className="text-gray-500 text-sm">No SF vs Depth data</span>
      </div>
    );
  }

  return (
    <div className="glass-card p-4">
      <h4 className="text-sm font-semibold text-gray-300 mb-3">
        Safety Factor vs Depth
      </h4>
      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart data={data} layout="vertical">
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis type="number" domain={[0, 'auto']} stroke="#9CA3AF" fontSize={11}
                 label={{ value: 'Safety Factor', position: 'insideBottom', offset: -5, fill: '#9CA3AF' }} />
          <YAxis type="number" dataKey="depth" reversed stroke="#9CA3AF" fontSize={11}
                 label={{ value: 'TVD (ft)', angle: -90, position: 'insideLeft', fill: '#9CA3AF' }} />
          <Tooltip
            contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', borderRadius: 8 }}
            labelFormatter={(v) => `${v} ft`}
            formatter={(v: number, name: string) => [v.toFixed(2), name]}
          />
          <Legend />
          <ReferenceLine x={sfBurstMin} stroke="#EF4444" strokeDasharray="5 5" label={{ value: `SF Burst min=${sfBurstMin}`, fill: '#EF4444', fontSize: 10 }} />
          <ReferenceLine x={sfCollapseMin} stroke="#3B82F6" strokeDasharray="5 5" />
          <ReferenceLine x={sfTensionMin} stroke="#8B5CF6" strokeDasharray="5 5" />
          <Line dataKey="burst" stroke="#EF4444" name="Burst" dot={false} strokeWidth={2} />
          <Line dataKey="collapse" stroke="#3B82F6" name="Collapse" dot={false} strokeWidth={2} />
          <Line dataKey="tension" stroke="#8B5CF6" name="Tension" dot={false} strokeWidth={2} />
        </ComposedChart>
      </ResponsiveContainer>
      {sfVsDepth?.min_sf != null && (
        <div className="mt-2 text-xs text-center text-gray-400">
          Min SF: <span className={sfVsDepth.min_sf < 1 ? 'text-red-400 font-bold' : 'text-green-400'}>
            {sfVsDepth.min_sf.toFixed(2)}
          </span> at {sfVsDepth.min_sf_depth_ft?.toFixed(0)} ft
        </div>
      )}
    </div>
  );
}
