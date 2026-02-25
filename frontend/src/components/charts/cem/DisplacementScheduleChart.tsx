/**
 * DisplacementScheduleChart.tsx — Shows job progress vs cumulative volume pumped.
 * X-axis: cumulative bbl pumped. Y-axis: job % complete. Color-coded fluid stages.
 * Key events (Spacer Away, Lead Away, Tail Away, Plug Bump) shown as reference lines.
 */
import React from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, Legend } from 'recharts';
import ChartContainer, { DarkTooltip } from '../ChartContainer';
import { CHART_DEFAULTS } from '../ChartTheme';
import { Layers } from 'lucide-react';

interface DisplacementScheduleChartProps {
  displacement: { schedule: Array<{ cumulative_bbl: number; time_min?: number; job_pct_complete: number; current_fluid?: string }>; events?: Array<{ event: string; volume_bbl: number }>; total_time_min?: number };
  height?: number;
}

const FLUID_COLORS: Record<string, string> = {
  Spacer: '#eab308',
  'Lead Cement': '#14b8a6',
  'Tail Cement': '#f97316',
  'Displacement (Mud)': '#6366f1',
};

const DisplacementScheduleChart: React.FC<DisplacementScheduleChartProps> = ({ displacement, height = 350 }) => {
  if (!displacement?.schedule?.length) return null;

  // Build data with one area per fluid stage
  const data = displacement.schedule.map((pt: { cumulative_bbl: number; time_min?: number; job_pct_complete: number; current_fluid?: string }) => {
    const fluid = pt.current_fluid || '';
    return {
      volume: Math.round(pt.cumulative_bbl * 10) / 10,
      time_min: pt.time_min,
      job_pct: pt.job_pct_complete,
      spacer: fluid === 'Spacer' ? pt.job_pct_complete : null,
      lead: fluid === 'Lead Cement' ? pt.job_pct_complete : null,
      tail: fluid === 'Tail Cement' ? pt.job_pct_complete : null,
      mud: fluid === 'Displacement (Mud)' ? pt.job_pct_complete : null,
      fluid,
    };
  });

  // Fill gaps so each area connects: carry forward the last value per stage
  let lastSpacer = 0, lastLead = 0, lastTail = 0, lastMud = 0;
  for (const d of data) {
    if (d.spacer !== null) lastSpacer = d.spacer; else d.spacer = lastSpacer;
    if (d.lead !== null) lastLead = d.lead; else d.lead = lastLead;
    if (d.tail !== null) lastTail = d.tail; else d.tail = lastTail;
    if (d.mud !== null) lastMud = d.mud; else d.mud = lastMud;
  }

  // Event lines
  const events = displacement.events || [];

  return (
    <ChartContainer
      title="Programa de Desplazamiento"
      icon={Layers}
      height={height}
      badge={{ text: `${displacement.total_time_min ?? '—'} min`, color: 'bg-teal-500/20 text-teal-400' }}
    >
      <AreaChart data={data} margin={{ ...CHART_DEFAULTS.margin, left: 40, right: 60, bottom: 40 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_DEFAULTS.gridColor} />
        <XAxis
          dataKey="volume"
          stroke={CHART_DEFAULTS.axisColor}
          tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }}
          label={{ value: 'Volumen Bombeado (bbl)', position: 'insideBottom', offset: -5, fill: CHART_DEFAULTS.labelColor, fontSize: 11 }}
        />
        <YAxis
          domain={[0, 100]}
          stroke={CHART_DEFAULTS.axisColor}
          tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }}
          label={{ value: 'Progreso (%)', angle: -90, position: 'insideLeft', fill: CHART_DEFAULTS.labelColor, fontSize: 11 }}
        />
        <Tooltip content={<DarkTooltip formatter={(v: number, name: string) => {
          const labels: Record<string, string> = { spacer: 'Spacer', lead: 'Lead Cement', tail: 'Tail Cement', mud: 'Displacement Mud' };
          return `${Number(v).toFixed(1)}% — ${labels[name] || name}`;
        }} />} />
        <Legend wrapperStyle={{ color: CHART_DEFAULTS.axisColor, fontSize: 11, paddingTop: 12 }} />
        <Area type="monotone" dataKey="spacer" stroke={FLUID_COLORS.Spacer} fill={FLUID_COLORS.Spacer}
          fillOpacity={0.15} strokeWidth={2} name="Spacer" dot={false} />
        <Area type="monotone" dataKey="lead" stroke={FLUID_COLORS['Lead Cement']} fill={FLUID_COLORS['Lead Cement']}
          fillOpacity={0.2} strokeWidth={2} name="Lead Cement" dot={false} />
        <Area type="monotone" dataKey="tail" stroke={FLUID_COLORS['Tail Cement']} fill={FLUID_COLORS['Tail Cement']}
          fillOpacity={0.15} strokeWidth={2} name="Tail Cement" dot={false} />
        <Area type="monotone" dataKey="mud" stroke={FLUID_COLORS['Displacement (Mud)']} fill={FLUID_COLORS['Displacement (Mud)']}
          fillOpacity={0.15} strokeWidth={2} name="Displacement" dot={false} />
        {/* Event markers */}
        {events.map((ev: { event: string; volume_bbl: number }, i: number) => {
          const SHORT_LABELS: Record<string, string> = {
            'Spacer Away': 'Spacer',
            'Lead Cement Away': 'Lead',
            'Tail Cement Away': 'Tail',
            'Plug Bump / End Displacement': 'Plug Bump',
          };
          const isLast = i === events.length - 1;
          return (
            <ReferenceLine key={i} x={ev.volume_bbl} stroke="rgba(255,255,255,0.3)" strokeDasharray="4 3"
              label={{ value: SHORT_LABELS[ev.event] || ev.event, fill: 'rgba(255,255,255,0.5)', fontSize: 8, position: isLast ? 'insideTopLeft' : 'insideBottomLeft' }} />
          );
        })}
      </AreaChart>
    </ChartContainer>
  );
};

export default DisplacementScheduleChart;
