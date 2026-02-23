/**
 * AdvancedLogTrack.tsx — Professional 5-track log display.
 * Track 1: GR (filled), Track 2: Resistivity (log scale),
 * Track 3: Density + Neutron, Track 4: Porosity + Sw, Track 5: Pay flag
 */
import React from 'react';
import {
  ComposedChart, Line, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, Bar, ReferenceLine,
} from 'recharts';
import ChartContainer, { DarkTooltip } from '../ChartContainer';
import { CHART_DEFAULTS } from '../ChartTheme';
import { BarChart3 } from 'lucide-react';

interface EvalPoint {
  md: number; gr: number; rhob: number; nphi: number; rt: number;
  vsh: number; phi_total: number; phi_effective: number; sw: number;
  k_md: number; is_pay: boolean; hc_saturation: number; sw_model: string;
}

interface AdvancedLogTrackProps {
  data: EvalPoint[];
  cutoffs?: { phi_min: number; sw_max: number; vsh_max: number };
  height?: number;
}

const AdvancedLogTrack: React.FC<AdvancedLogTrackProps> = ({ data, cutoffs, height = 520 }) => {
  if (!data?.length) return null;

  const chartData = data.map(d => ({
    depth: d.md,
    gr: Math.round(d.gr * 10) / 10,
    rhob: Math.round(d.rhob * 1000) / 1000,
    nphi: Math.round(d.nphi * 1000) / 10,
    rt: Math.round(d.rt * 10) / 10,
    phi: Math.round(d.phi_effective * 1000) / 10,
    sw: Math.round(d.sw * 1000) / 10,
    vsh: Math.round(d.vsh * 1000) / 10,
    pay: d.is_pay ? 1 : 0,
    hc: Math.round(d.hc_saturation * 1000) / 10,
  }));

  return (
    <div className="grid grid-cols-1 lg:grid-cols-5 gap-2">
      {/* Track 1: Gamma Ray */}
      <ChartContainer title="GR" icon={BarChart3} height={height}
        badge={{ text: 'GAPI', color: 'bg-green-500/20 text-green-400' }}>
        <ComposedChart data={chartData} layout="vertical" margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART_DEFAULTS.gridColor} />
          <XAxis type="number" domain={[0, 150]} stroke={CHART_DEFAULTS.axisColor}
            tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 9 }} />
          <YAxis dataKey="depth" type="number" reversed tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 9 }}
            stroke={CHART_DEFAULTS.axisColor} />
          <Tooltip content={<DarkTooltip />} />
          <Area dataKey="gr" fill="#22c55e33" stroke="#22c55e" strokeWidth={1.5} />
          {cutoffs && <ReferenceLine x={(cutoffs.vsh_max * 100 + 20)} stroke="#f97316" strokeDasharray="4 4" />}
        </ComposedChart>
      </ChartContainer>

      {/* Track 2: Resistivity */}
      <ChartContainer title="Rt" icon={BarChart3} height={height}
        badge={{ text: 'Ω·m', color: 'bg-yellow-500/20 text-yellow-400' }}>
        <ComposedChart data={chartData} layout="vertical" margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART_DEFAULTS.gridColor} />
          <XAxis type="number" scale="log" domain={[0.1, 1000]}
            stroke={CHART_DEFAULTS.axisColor} tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 9 }} />
          <YAxis dataKey="depth" type="number" reversed tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 9 }}
            stroke={CHART_DEFAULTS.axisColor} />
          <Tooltip content={<DarkTooltip />} />
          <Line dataKey="rt" stroke="#eab308" strokeWidth={1.5} dot={false} />
        </ComposedChart>
      </ChartContainer>

      {/* Track 3: Density + Neutron */}
      <ChartContainer title="ρ / φN" icon={BarChart3} height={height}
        badge={{ text: 'g/cc | %', color: 'bg-red-500/20 text-red-400' }}>
        <ComposedChart data={chartData} layout="vertical" margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART_DEFAULTS.gridColor} />
          <XAxis type="number" domain={[0, 50]}
            stroke={CHART_DEFAULTS.axisColor} tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 9 }} />
          <YAxis dataKey="depth" type="number" reversed tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 9 }}
            stroke={CHART_DEFAULTS.axisColor} />
          <Tooltip content={<DarkTooltip />} />
          <Line dataKey="nphi" stroke="#3b82f6" strokeWidth={1.5} dot={false} name="NPHI %" />
          <Line dataKey="phi" stroke="#ef4444" strokeWidth={1.5} dot={false} name="φ Density %" />
          <Legend wrapperStyle={{ fontSize: 10, color: 'rgba(255,255,255,0.5)' }} />
        </ComposedChart>
      </ChartContainer>

      {/* Track 4: Porosity + Sw */}
      <ChartContainer title="φe / Sw" icon={BarChart3} height={height}
        badge={{ text: '%', color: 'bg-blue-500/20 text-blue-400' }}>
        <ComposedChart data={chartData} layout="vertical" margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART_DEFAULTS.gridColor} />
          <XAxis type="number" domain={[0, 100]}
            stroke={CHART_DEFAULTS.axisColor} tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 9 }} />
          <YAxis dataKey="depth" type="number" reversed tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 9 }}
            stroke={CHART_DEFAULTS.axisColor} />
          <Tooltip content={<DarkTooltip />} />
          <Area dataKey="hc" fill="#22c55e22" stroke="#22c55e" strokeWidth={1} name="HC %" />
          <Line dataKey="phi" stroke="#06b6d4" strokeWidth={1.5} dot={false} name="φe %" />
          <Line dataKey="sw" stroke="#3b82f6" strokeWidth={1.5} dot={false} name="Sw %" />
          {cutoffs && <>
            <ReferenceLine x={cutoffs.phi_min * 100} stroke="#22c55e" strokeDasharray="3 3" />
            <ReferenceLine x={cutoffs.sw_max * 100} stroke="#ef4444" strokeDasharray="3 3" />
          </>}
          <Legend wrapperStyle={{ fontSize: 10, color: 'rgba(255,255,255,0.5)' }} />
        </ComposedChart>
      </ChartContainer>

      {/* Track 5: Pay Flag */}
      <ChartContainer title="Pay" icon={BarChart3} height={height}
        badge={{ text: 'Flag', color: 'bg-emerald-500/20 text-emerald-400' }}>
        <ComposedChart data={chartData} layout="vertical" margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART_DEFAULTS.gridColor} />
          <XAxis type="number" domain={[0, 1]} hide />
          <YAxis dataKey="depth" type="number" reversed tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 9 }}
            stroke={CHART_DEFAULTS.axisColor} />
          <Bar dataKey="pay" fill="#22c55e" barSize={20} radius={[2, 2, 2, 2]} />
        </ComposedChart>
      </ChartContainer>
    </div>
  );
};

export default AdvancedLogTrack;
