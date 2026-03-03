/**
 * NodalAnalysisChart.tsx — Combined IPR + VLP curves with operating point.
 *
 * Shows:
 *  - IPR (Darcy) line: reservoir deliverability
 *  - VLP (Beggs & Brill): tubing lift performance
 *  - Intersection = well operating point (q_op, Pwf_op)
 *
 * Reference: Brown (1984) "The Technology of Artificial Lift Methods"
 */
import {
  ComposedChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ReferenceLine, ResponsiveContainer, Label,
} from 'recharts';

interface IPRData {
  Pwf_psi?: number[];
  q_oil_stbd?: number[];
  AOF_stbd?: number;
  PI_stbd_psi?: number;
  reservoir_pressure_psi?: number;
  flow_efficiency?: number;
  PI_ideal_stbd_psi?: number;
  AOF_ideal_stbd?: number;
}

interface VLPData {
  q_stbd?: number[];
  Pwf_psi?: number[];
  static_bhp_psi?: number;
  method?: string;
}

interface NodalData {
  operating_point_q?: number;
  operating_point_Pwf_psi?: number;
  intersection_error_psi?: number;
  stable?: boolean;
  no_natural_flow?: boolean;
  message?: string;
  drawdown_psi?: number;
  pct_aof_utilized?: number;
}

interface Props {
  ipr?: IPRData | null;
  vlp?: VLPData | null;
  nodal?: NodalData | null;
}

const NodalAnalysisChart: React.FC<Props> = ({ ipr, vlp, nodal }) => {
  const hasIPR = ipr?.Pwf_psi?.length && ipr?.q_oil_stbd?.length;
  const hasVLP = vlp?.q_stbd?.length && vlp?.Pwf_psi?.length;

  if (!hasIPR && !hasVLP) {
    return (
      <div className="glass-panel p-6 rounded-2xl border border-white/5 flex items-center justify-center h-64">
        <p className="text-gray-500 text-sm">Análisis Nodal no disponible</p>
      </div>
    );
  }

  // Build unified q axis — union of all q values
  const allQ = new Set<number>();
  if (hasIPR) ipr!.q_oil_stbd!.forEach(q => allQ.add(Math.round(q)));
  if (hasVLP) vlp!.q_stbd!.forEach(q => allQ.add(Math.round(q)));
  const sortedQ = Array.from(allQ).sort((a, b) => a - b);

  // Linear interpolation helper
  const interp = (xs: number[], ys: number[], xq: number): number | null => {
    if (!xs.length) return null;
    if (xq <= xs[0]) return ys[0];
    if (xq >= xs[xs.length - 1]) return ys[ys.length - 1];
    for (let i = 0; i < xs.length - 1; i++) {
      if (xs[i] <= xq && xq <= xs[i + 1]) {
        const t = (xq - xs[i]) / (xs[i + 1] - xs[i]);
        return ys[i] + t * (ys[i + 1] - ys[i]);
      }
    }
    return null;
  };

  const iprXs = ipr?.q_oil_stbd?.map(Math.round) ?? [];
  const iprYs = ipr?.Pwf_psi ?? [];
  const vlpXs = vlp?.q_stbd?.map(Math.round) ?? [];
  const vlpYs = vlp?.Pwf_psi ?? [];

  const data = sortedQ.map(q => ({
    q,
    ipr: hasIPR ? (interp(iprXs, iprYs, q) ?? undefined) : undefined,
    vlp: hasVLP ? (interp(vlpXs, vlpYs, q) ?? undefined) : undefined,
  }));

  const q_op = nodal?.operating_point_q ?? 0;
  const pwf_op = nodal?.operating_point_Pwf_psi ?? 0;
  const noFlow = nodal?.no_natural_flow;
  const AOF = ipr?.AOF_stbd ?? 0;
  const Pr = ipr?.reservoir_pressure_psi ?? 0;

  const formatQ = (v: number) => v >= 1000 ? `${(v / 1000).toFixed(1)}k` : `${v}`;

  return (
    <div className="glass-panel p-6 rounded-2xl border border-white/5">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-bold">Análisis Nodal — IPR × VLP</h3>
        <span className="text-xs text-gray-500">Beggs &amp; Brill (1973)</span>
      </div>

      {/* No natural flow alert */}
      {noFlow && (
        <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-300">
          ⚠ {nodal?.message ?? 'No hay flujo natural — considerar levantamiento artificial'}
        </div>
      )}

      {/* KPI badges */}
      {!noFlow && q_op > 0 && (
        <div className="grid grid-cols-4 gap-2 mb-4">
          <div className="bg-white/5 rounded-xl p-3 text-center">
            <div className="text-xs text-gray-400 mb-0.5">q Operación</div>
            <div className="font-mono font-bold text-violet-400">{q_op.toFixed(0)}</div>
            <div className="text-xs text-gray-500">STB/d</div>
          </div>
          <div className="bg-white/5 rounded-xl p-3 text-center">
            <div className="text-xs text-gray-400 mb-0.5">Pwf Operación</div>
            <div className="font-mono font-bold text-cyan-400">{pwf_op.toFixed(0)}</div>
            <div className="text-xs text-gray-500">psi</div>
          </div>
          <div className="bg-white/5 rounded-xl p-3 text-center">
            <div className="text-xs text-gray-400 mb-0.5">Drawdown</div>
            <div className="font-mono font-bold text-orange-400">{nodal?.drawdown_psi?.toFixed(0) ?? '-'}</div>
            <div className="text-xs text-gray-500">psi</div>
          </div>
          <div className="bg-white/5 rounded-xl p-3 text-center">
            <div className="text-xs text-gray-400 mb-0.5">% AOF</div>
            <div className="font-mono font-bold text-green-400">{nodal?.pct_aof_utilized?.toFixed(1) ?? '-'}%</div>
            <div className="text-xs text-gray-500">utilizado</div>
          </div>
        </div>
      )}

      {/* Chart */}
      <ResponsiveContainer width="100%" height={240}>
        <ComposedChart data={data} margin={{ top: 8, right: 24, left: 8, bottom: 24 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
          <XAxis
            dataKey="q"
            type="number"
            tickFormatter={formatQ}
            tick={{ fill: '#9ca3af', fontSize: 11 }}
            domain={[0, 'dataMax']}
          >
            <Label value="Caudal (STB/d)" offset={-12} position="insideBottom" fill="#6b7280" fontSize={11} />
          </XAxis>
          <YAxis
            tick={{ fill: '#9ca3af', fontSize: 11 }}
            domain={[0, Math.ceil((Pr * 1.05) / 500) * 500]}
            width={55}
          >
            <Label value="Pwf (psi)" angle={-90} position="insideLeft" fill="#6b7280" fontSize={11} dx={10} />
          </YAxis>
          <Tooltip
            contentStyle={{ background: 'rgba(15,15,25,0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8 }}
            formatter={(v: number, name: string) => [`${v?.toFixed(0)} psi`, name === 'ipr' ? 'IPR (Darcy)' : 'VLP (B&B)']}
          />
          <Legend verticalAlign="top" height={24} wrapperStyle={{ fontSize: 11, color: 'rgba(255,255,255,0.6)' }} />
          {/* Reservoir pressure reference */}
          {Pr > 0 && (
            <ReferenceLine y={Pr} stroke="#4ade80" strokeDasharray="4 3" strokeWidth={1}
              label={{ value: `Pr=${Pr}`, fill: '#4ade80', fontSize: 9, position: 'right' }} />
          )}
          {/* AOF reference */}
          {AOF > 0 && (
            <ReferenceLine x={AOF} stroke="#f97316" strokeDasharray="4 3" strokeWidth={1}
              label={{ value: `AOF`, fill: '#f97316', fontSize: 9, position: 'top' }} />
          )}
          {/* Operating point vertical line */}
          {!noFlow && q_op > 0 && (
            <ReferenceLine x={q_op} stroke="#c084fc" strokeWidth={2}
              label={{ value: `q_op=${q_op.toFixed(0)}`, fill: '#c084fc', fontSize: 9, position: 'top' }} />
          )}
          {/* Operating point horizontal line */}
          {!noFlow && pwf_op > 0 && (
            <ReferenceLine y={pwf_op} stroke="#c084fc" strokeWidth={2} strokeDasharray="2 2" />
          )}
          {/* IPR curve */}
          <Line type="monotone" dataKey="ipr" stroke="#818cf8" strokeWidth={2.5}
            dot={false} name="IPR" connectNulls />
          {/* VLP curve */}
          <Line type="monotone" dataKey="vlp" stroke="#f97316" strokeWidth={2.5}
            dot={false} name="VLP" connectNulls />
        </ComposedChart>
      </ResponsiveContainer>

      {!noFlow && q_op > 0 && (
        <p className="text-xs text-center text-gray-600 mt-1">
          Punto de operación: ({q_op.toFixed(0)} STB/d, {pwf_op.toFixed(0)} psi) — intersección IPR×VLP
        </p>
      )}
    </div>
  );
};

export default NodalAnalysisChart;
