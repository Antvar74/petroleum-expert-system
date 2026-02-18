/**
 * WellboreTrajectory.tsx — 2D scatter plot of wellbore trajectory.
 * Toggles between Plan View (N vs E) and Section View (HD vs TVD).
 */
import React, { useState, useMemo } from 'react';
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
} from 'recharts';
import { CHART_DEFAULTS } from '../ChartTheme';
import { Map } from 'lucide-react';

interface SurveyPoint {
  md: number;
  tvd: number;
  north: number;
  east: number;
  inclination: number;
  azimuth: number;
  dls: number;
}

interface WellboreTrajectoryProps {
  data: SurveyPoint[];
  height?: number;
}

const WellboreTrajectory: React.FC<WellboreTrajectoryProps> = ({ data, height = 400 }) => {
  const [view, setView] = useState<'plan' | 'section'>('section');

  const plotData = useMemo(() => {
    if (!data?.length) return [];
    return data.map(pt => ({
      ...pt,
      horizontal_displacement: Math.sqrt(pt.north ** 2 + pt.east ** 2),
    }));
  }, [data]);

  if (!plotData.length) return null;

  // Color scale by DLS
  const maxDLS = Math.max(...plotData.map(d => d.dls), 1);
  const getColor = (dls: number) => {
    const ratio = dls / maxDLS;
    if (ratio < 0.3) return '#22c55e';
    if (ratio < 0.6) return '#eab308';
    return '#ef4444';
  };

  const xKey = view === 'plan' ? 'east' : 'horizontal_displacement';
  const yKey = view === 'plan' ? 'north' : 'tvd';

  return (
    <div className="glass-panel p-6 rounded-2xl border border-white/5 print-chart">
      <div className="flex justify-between items-center mb-4">
        <div className="flex items-center gap-2">
          <Map size={18} className="text-industrial-400" />
          <h4 className="font-bold text-sm">Well Path</h4>
        </div>
        <div className="flex gap-1">
          <button
            onClick={() => setView('plan')}
            className={`px-3 py-1 rounded-lg text-xs font-bold transition-colors ${view === 'plan' ? 'bg-industrial-600 text-white' : 'bg-white/5 text-white/40 hover:text-white'}`}
          >
            Plan View
          </button>
          <button
            onClick={() => setView('section')}
            className={`px-3 py-1 rounded-lg text-xs font-bold transition-colors ${view === 'section' ? 'bg-industrial-600 text-white' : 'bg-white/5 text-white/40 hover:text-white'}`}
          >
            Section View
          </button>
        </div>
      </div>

      <div style={{ width: '100%', height }}>
        <ScatterChart width={500} height={height} margin={{ top: 20, right: 30, bottom: 40, left: 50 }}>
          <CartesianGrid stroke={CHART_DEFAULTS.gridColor} strokeDasharray="3 3" />
          <XAxis
            dataKey={xKey}
            type="number"
            name={view === 'plan' ? 'East' : 'HD'}
            tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }}
            axisLine={{ stroke: CHART_DEFAULTS.axisColor }}
            label={{ value: view === 'plan' ? 'East (ft)' : 'Horizontal Displacement (ft)', position: 'insideBottom', offset: -10, fill: CHART_DEFAULTS.labelColor, fontSize: 11 }}
          />
          <YAxis
            dataKey={yKey}
            type="number"
            reversed={view === 'section'}
            name={view === 'plan' ? 'North' : 'TVD'}
            tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }}
            axisLine={{ stroke: CHART_DEFAULTS.axisColor }}
            label={{ value: view === 'plan' ? 'North (ft)' : 'TVD (ft)', angle: -90, position: 'insideLeft', offset: -35, fill: CHART_DEFAULTS.labelColor, fontSize: 11 }}
          />
          <Tooltip
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const d = payload[0].payload;
              return (
                <div style={{ backgroundColor: CHART_DEFAULTS.tooltipBg, border: `1px solid ${CHART_DEFAULTS.tooltipBorder}`, borderRadius: 8, padding: '8px 12px', fontSize: 11 }}>
                  <p style={{ color: 'rgba(255,255,255,0.5)', marginBottom: 4 }}>MD: {d.md} ft</p>
                  <p style={{ color: '#f97316' }}>TVD: {d.tvd} ft</p>
                  <p style={{ color: '#3b82f6' }}>Inc: {d.inclination}° | Azi: {d.azimuth}°</p>
                  <p style={{ color: '#eab308' }}>DLS: {d.dls} °/100ft</p>
                </div>
              );
            }}
          />
          <Scatter data={plotData} fill="#f97316">
            {plotData.map((pt, i) => (
              <Cell key={i} fill={getColor(pt.dls)} />
            ))}
          </Scatter>
        </ScatterChart>
      </div>

      {/* DLS legend */}
      <div className="flex justify-center gap-4 mt-2 text-[10px] text-white/40">
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-green-500" /> Low DLS</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-yellow-500" /> Medium DLS</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500" /> High DLS</span>
      </div>
    </div>
  );
};

export default WellboreTrajectory;
