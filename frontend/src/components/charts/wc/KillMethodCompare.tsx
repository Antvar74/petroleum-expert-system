/**
 * KillMethodCompare.tsx — Side-by-side comparison of kill methods.
 */
import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell, LabelList } from 'recharts';
import ChartContainer from '../ChartContainer';
import { CHART_DEFAULTS } from '../ChartTheme';
import { GitCompare } from 'lucide-react';

interface KillMethodCompareProps {
  killResult: { icp_psi?: number; method_detail?: { method?: string } } | null;
  volResult: { initial_conditions?: { working_pressure_psi?: number } } | null;
  bullheadResult: { calculations?: { required_pump_pressure_psi?: number } } | null;
  height?: number;
}

const METHOD_COLORS: Record<string, string> = {
  "Wait & Weight": '#22c55e',
  "Driller's": '#3b82f6',
  "Volumetric": '#f97316',
  "Bullhead": '#a855f7',
};

const KillMethodCompare: React.FC<KillMethodCompareProps> = ({
  killResult,
  volResult,
  bullheadResult,
  height = 350,
}) => {
  // Build comparison data from available results
  const methods: Array<{
    name: string;
    available: boolean;
    circulations: number;
    complexity: number; // 1-5
    maxPressure: number;
    recommended: boolean;
    pros: string[];
    cons: string[];
  }> = [
    {
      name: "Wait & Weight",
      available: !!killResult,
      circulations: 1,
      complexity: 4,
      maxPressure: killResult?.icp_psi || 0,
      recommended: killResult?.method_detail?.method === "Wait and Weight",
      pros: ['Lower casing pressures', 'Single circulation'],
      cons: ['Must wait to weight up', 'More complex calculations'],
    },
    {
      name: "Driller's",
      available: !!killResult,
      circulations: 2,
      complexity: 2,
      maxPressure: killResult?.icp_psi || 0,
      recommended: killResult?.method_detail?.method === "Driller's Method",
      pros: ['Simple execution', 'Fast initial response'],
      cons: ['Higher casing pressures', 'Two full circulations'],
    },
    {
      name: "Volumetric",
      available: !!volResult,
      circulations: 0,
      complexity: 3,
      maxPressure: volResult?.initial_conditions?.working_pressure_psi || 0,
      recommended: false,
      pros: ['No circulation needed', 'For stuck pipe / pump failure'],
      cons: ['Slow gas migration', 'Requires constant monitoring'],
    },
    {
      name: "Bullhead",
      available: !!bullheadResult,
      circulations: 0,
      complexity: 2,
      maxPressure: bullheadResult?.calculations?.required_pump_pressure_psi || 0,
      recommended: false,
      pros: ['Fast for H₂S', 'Simple procedure'],
      cons: ['May fracture shoe', 'Forces influx into formation'],
    },
  ];

  const availableMethods = methods.filter(m => m.available);

  // Bar chart data for pressure comparison
  const pressureData = availableMethods.map(m => ({
    name: m.name,
    pressure: Math.round(m.maxPressure),
    color: METHOD_COLORS[m.name] || '#f97316',
  }));

  return (
    <div className="space-y-6">
      {/* Pressure comparison chart */}
      {pressureData.length > 1 && (
        <ChartContainer title="Max Circulating Pressure by Method" icon={GitCompare} height={Math.min(height, 250)}>
          <BarChart data={pressureData} layout="vertical" margin={{ top: 10, right: 60, bottom: 10, left: 100 }}>
            <CartesianGrid stroke={CHART_DEFAULTS.gridColor} strokeDasharray="3 3" horizontal={false} />
            <XAxis
              type="number"
              tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }}
              axisLine={{ stroke: CHART_DEFAULTS.axisColor }}
              label={{ value: 'Pressure (psi)', position: 'insideBottom', offset: -5, fill: CHART_DEFAULTS.labelColor, fontSize: 11 }}
            />
            <YAxis
              type="category"
              dataKey="name"
              tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }}
              axisLine={{ stroke: CHART_DEFAULTS.axisColor }}
              width={90}
            />
            <Tooltip
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null;
                const d = payload[0].payload;
                return (
                  <div style={{ backgroundColor: CHART_DEFAULTS.tooltipBg, border: `1px solid ${CHART_DEFAULTS.tooltipBorder}`, borderRadius: 8, padding: '8px 12px', fontSize: 12 }}>
                    <p style={{ color: d.color, fontWeight: 700 }}>{d.name}</p>
                    <p style={{ color: 'white' }}>{d.pressure.toLocaleString()} psi</p>
                  </div>
                );
              }}
            />
            <Bar dataKey="pressure" radius={[0, 6, 6, 0]} barSize={28}>
              {pressureData.map((entry, i) => (
                <Cell key={i} fill={entry.color} fillOpacity={0.7} />
              ))}
              <LabelList dataKey="pressure" position="right" fill="rgba(255,255,255,0.6)" fontSize={11} formatter={(v: number) => `${v.toLocaleString()} psi`} />
            </Bar>
          </BarChart>
        </ChartContainer>
      )}

      {/* Method comparison cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {methods.map((m) => (
          <div key={m.name}
            className={`glass-panel p-5 rounded-2xl border ${m.recommended ? 'border-green-500/30' : 'border-white/5'} ${!m.available ? 'opacity-40' : ''}`}
          >
            <div className="flex justify-between items-start mb-3">
              <h4 className="font-bold text-sm" style={{ color: METHOD_COLORS[m.name] }}>{m.name}</h4>
              <div className="flex gap-2">
                {m.recommended && (
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-green-500/20 text-green-400">
                    RECOMMENDED
                  </span>
                )}
                {m.available ? (
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-white/10 text-white/50">
                    CALCULATED
                  </span>
                ) : (
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-white/5 text-white/20">
                    NOT CALCULATED
                  </span>
                )}
              </div>
            </div>

            {/* Quick metrics */}
            <div className="grid grid-cols-3 gap-2 mb-3">
              <div className="text-center">
                <p className="text-[10px] text-white/30">Circulations</p>
                <p className="text-lg font-bold text-white/80">{m.circulations}</p>
              </div>
              <div className="text-center">
                <p className="text-[10px] text-white/30">Complexity</p>
                <div className="flex justify-center gap-0.5 mt-1">
                  {[1, 2, 3, 4, 5].map(n => (
                    <div key={n} className={`w-2 h-2 rounded-full ${n <= m.complexity ? 'bg-industrial-500' : 'bg-white/10'}`} />
                  ))}
                </div>
              </div>
              <div className="text-center">
                <p className="text-[10px] text-white/30">Max P</p>
                <p className="text-sm font-bold text-white/80">
                  {m.available ? `${m.maxPressure.toLocaleString()}` : '—'}
                </p>
              </div>
            </div>

            {/* Pros and cons */}
            <div className="space-y-1 text-xs">
              {m.pros.map((p, i) => (
                <p key={`pro-${i}`} className="text-green-400/80">+ {p}</p>
              ))}
              {m.cons.map((c, i) => (
                <p key={`con-${i}`} className="text-red-400/60">- {c}</p>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default KillMethodCompare;
