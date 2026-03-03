/**
 * IPR Curve Chart — Darcy straight-line inflow performance relationship.
 *
 * Shows Pwf (Y) vs q (X) with AOF and PI badges.
 * Reference: Darcy (1856), Vogel (1968).
 */
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ReferenceLine, ResponsiveContainer, Label,
} from 'recharts';

interface IPRData {
  Pwf_psi?: number[];
  q_oil_stbd?: number[];
  AOF_stbd?: number;
  PI_stbd_psi?: number;
  reservoir_pressure_psi?: number;
  skin?: number;
  method?: string;
  error?: string;
}

interface Props {
  ipr?: IPRData | null;
}

const IPRCurveChart: React.FC<Props> = ({ ipr }) => {
  if (!ipr || ipr.error || !ipr.Pwf_psi?.length || !ipr.q_oil_stbd?.length) {
    return (
      <div className="glass-panel p-6 rounded-2xl border border-white/5 flex items-center justify-center h-64">
        <p className="text-gray-500 text-sm">IPR no disponible</p>
      </div>
    );
  }

  // Build chart data: [{q, Pwf}] sorted by q ascending
  const data = ipr.q_oil_stbd.map((q, i) => ({
    q: Math.round(q),
    Pwf: Math.round(ipr.Pwf_psi![i]),
  })).sort((a, b) => a.q - b.q);

  const AOF = ipr.AOF_stbd ?? 0;
  const PI  = ipr.PI_stbd_psi ?? 0;
  const Pr  = ipr.reservoir_pressure_psi ?? 0;

  const formatQ = (v: number) => v >= 1000 ? `${(v / 1000).toFixed(1)}k` : `${v}`;

  return (
    <div className="glass-panel p-6 rounded-2xl border border-white/5">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-bold">Curva IPR — Inflow Performance</h3>
        <span className="text-xs text-gray-500">Darcy, steady-state</span>
      </div>

      {/* KPI badges */}
      <div className="flex gap-4 mb-4">
        <div className="flex-1 bg-white/5 rounded-xl p-3 text-center">
          <div className="text-xs text-gray-400 mb-0.5">AOF (Pwf=0)</div>
          <div className="font-mono font-bold text-violet-400 text-lg">{AOF.toFixed(0)} <span className="text-xs font-normal text-gray-400">STB/d</span></div>
        </div>
        <div className="flex-1 bg-white/5 rounded-xl p-3 text-center">
          <div className="text-xs text-gray-400 mb-0.5">PI</div>
          <div className="font-mono font-bold text-cyan-400 text-lg">{PI.toFixed(3)} <span className="text-xs font-normal text-gray-400">STB/d/psi</span></div>
        </div>
        <div className="flex-1 bg-white/5 rounded-xl p-3 text-center">
          <div className="text-xs text-gray-400 mb-0.5">Pr</div>
          <div className="font-mono font-bold text-green-400 text-lg">{Pr.toFixed(0)} <span className="text-xs font-normal text-gray-400">psi</span></div>
        </div>
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data} margin={{ top: 8, right: 24, left: 8, bottom: 24 }}>
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
            dataKey="Pwf"
            type="number"
            tick={{ fill: '#9ca3af', fontSize: 11 }}
            domain={[0, 'dataMax']}
            width={52}
          >
            <Label value="Pwf (psi)" angle={-90} position="insideLeft" fill="#6b7280" fontSize={11} dx={8} />
          </YAxis>
          <Tooltip
            contentStyle={{ background: 'rgba(15,15,25,0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8 }}
            formatter={(v: number, name: string) => [
              name === 'Pwf' ? `${v.toLocaleString()} psi` : `${v.toLocaleString()} STB/d`,
              name === 'Pwf' ? 'BHP Fluyente' : 'Caudal',
            ]}
          />
          {/* Static reservoir pressure line */}
          <ReferenceLine y={Pr} stroke="#4ade80" strokeDasharray="6 3" strokeWidth={1.5} label={{ value: `Pr=${Pr}`, fill: '#4ade80', fontSize: 10, position: 'right' }} />
          {/* IPR curve */}
          <Line
            type="monotone"
            dataKey="Pwf"
            stroke="#818cf8"
            strokeWidth={2.5}
            dot={false}
            activeDot={{ r: 4, fill: '#818cf8' }}
          />
        </LineChart>
      </ResponsiveContainer>

      <p className="text-xs text-gray-600 text-center mt-1">Skin = {ipr.skin?.toFixed(2)} (óptimo K&T)</p>
    </div>
  );
};

export default IPRCurveChart;
