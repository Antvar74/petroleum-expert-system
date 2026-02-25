import { useState, useCallback } from 'react';
import api from '../lib/api';
import { motion, AnimatePresence } from 'framer-motion';
import { Target, Play, RefreshCw, Upload } from 'lucide-react';
import LogTrackChart from './charts/se/LogTrackChart';
import NetPayIntervalChart from './charts/se/NetPayIntervalChart';
import SkinComponentsBar from './charts/se/SkinComponentsBar';
import IntervalRankingChart from './charts/se/IntervalRankingChart';
import CutoffSensitivityChart from './charts/se/CutoffSensitivityChart';
import AIAnalysisPanel from './AIAnalysisPanel';
import { useLanguage } from '../hooks/useLanguage';
import { useAIAnalysis } from '../hooks/useAIAnalysis';
import { useTranslation } from 'react-i18next';
import { useToast } from './ui/Toast';
import type { APIError } from '../types/api';

interface ShotEfficiencyModuleProps {
  wellId?: number;
  wellName?: string;
}

// Sample log data for demo
const SAMPLE_LOG_DATA = [
  { md: 8000, gr: 25, rhob: 2.35, nphi: 0.22, rt: 45 },
  { md: 8005, gr: 30, rhob: 2.38, nphi: 0.20, rt: 40 },
  { md: 8010, gr: 28, rhob: 2.33, nphi: 0.24, rt: 50 },
  { md: 8015, gr: 35, rhob: 2.40, nphi: 0.18, rt: 30 },
  { md: 8020, gr: 22, rhob: 2.30, nphi: 0.26, rt: 65 },
  { md: 8025, gr: 20, rhob: 2.28, nphi: 0.28, rt: 80 },
  { md: 8030, gr: 24, rhob: 2.32, nphi: 0.25, rt: 55 },
  { md: 8035, gr: 90, rhob: 2.55, nphi: 0.12, rt: 5 },
  { md: 8040, gr: 95, rhob: 2.58, nphi: 0.10, rt: 3 },
  { md: 8045, gr: 85, rhob: 2.52, nphi: 0.14, rt: 8 },
  { md: 8050, gr: 26, rhob: 2.34, nphi: 0.23, rt: 48 },
  { md: 8055, gr: 23, rhob: 2.31, nphi: 0.25, rt: 60 },
  { md: 8060, gr: 21, rhob: 2.29, nphi: 0.27, rt: 72 },
  { md: 8065, gr: 27, rhob: 2.36, nphi: 0.21, rt: 42 },
  { md: 8070, gr: 32, rhob: 2.42, nphi: 0.17, rt: 25 },
  { md: 8075, gr: 80, rhob: 2.50, nphi: 0.15, rt: 10 },
  { md: 8080, gr: 18, rhob: 2.27, nphi: 0.29, rt: 90 },
  { md: 8085, gr: 19, rhob: 2.26, nphi: 0.30, rt: 100 },
  { md: 8090, gr: 22, rhob: 2.30, nphi: 0.26, rt: 70 },
  { md: 8095, gr: 24, rhob: 2.33, nphi: 0.24, rt: 55 },
];

const ShotEfficiencyModule: React.FC<ShotEfficiencyModuleProps> = ({ wellId, wellName = '' }) => {
  const [activeTab, setActiveTab] = useState('input');
  const [loading, setLoading] = useState(false);

  const [logData, setLogData] = useState(JSON.stringify(SAMPLE_LOG_DATA, null, 2));
  const [params, setParams] = useState({
    a: 1.0, m: 2.0, n: 2.0, rw: 0.05,
    rho_matrix: 2.65, rho_fluid: 1.0, gr_clean: 20, gr_shale: 120,
    phi_min: 0.08, sw_max: 0.60, vsh_max: 0.40, min_thickness_ft: 2.0,
    spf: 4, phasing_deg: 90, perf_length_in: 12.0, tunnel_radius_in: 0.20,
    kv_kh: 0.5, wellbore_radius_ft: 0.354,
  });

  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const { language } = useLanguage();
  const { t } = useTranslation();
  const { addToast } = useToast();

  const { aiAnalysis, isAnalyzing, runAnalysis, provider, setProvider, availableProviders, setAiAnalysis } = useAIAnalysis({
    module: 'shot-efficiency',
    wellId,
    wellName,
  });

  const updateParam = (key: string, value: string) => {
    setParams(prev => ({ ...prev, [key]: parseFloat(value) || 0 }));
  };

  const handleCSVUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (evt) => {
      try {
        const text = evt.target?.result as string;
        const lines = text.trim().split('\n');
        const headers = lines[0].split(',').map(h => h.trim().toLowerCase());
        const entries = [];
        for (let i = 1; i < lines.length; i++) {
          const vals = lines[i].split(',');
          if (vals.length < headers.length) continue;
          const entry: Record<string, number> = {};
          headers.forEach((h, j) => { entry[h] = parseFloat(vals[j]?.trim()) || 0; });
          entries.push(entry);
        }
        setLogData(JSON.stringify(entries, null, 2));
      } catch { addToast('Error parsing CSV', 'error'); }
    };
    reader.readAsText(file);
  };

  const calculate = useCallback(async () => {
    setLoading(true);
    try {
      let entries;
      try { entries = JSON.parse(logData); } catch { addToast('Invalid JSON log data', 'error'); setLoading(false); return; }

      const payload = {
        log_entries: entries,
        archie_params: { a: params.a, m: params.m, n: params.n, rw: params.rw },
        matrix_params: { rho_matrix: params.rho_matrix, rho_fluid: params.rho_fluid, gr_clean: params.gr_clean, gr_shale: params.gr_shale },
        cutoffs: { phi_min: params.phi_min, sw_max: params.sw_max, vsh_max: params.vsh_max, min_thickness_ft: params.min_thickness_ft },
        perf_params: { spf: params.spf, phasing_deg: params.phasing_deg, perf_length_in: params.perf_length_in, tunnel_radius_in: params.tunnel_radius_in },
        reservoir_params: { kv_kh: params.kv_kh, wellbore_radius_ft: params.wellbore_radius_ft },
      };
      const url = wellId
        ? `/wells/${wellId}/shot-efficiency`
        : `/calculate/shot-efficiency`;
      const res = await api.post(url, payload);
      setResult(res.data);
      setActiveTab('results');
    } catch (e: unknown) {
      addToast('Error: ' + (e as APIError).response?.data?.detail || (e as APIError).message, 'error');
    }
    setLoading(false);
  }, [wellId, params, logData, addToast]);

  const handleRunAnalysis = () => {
    runAnalysis(result || {}, params);
  };

  const tabs = [
    { id: 'input', label: t('shotEfficiency.sections.logs') + ' & ' + t('common.parameters') },
    { id: 'results', label: t('common.results') },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Target className="text-emerald-400" size={28} />
        <h2 className="text-2xl font-bold">{t('shotEfficiency.title')}</h2>
        <span className="text-sm text-gray-500">{t('shotEfficiency.subtitle')}</span>
      </div>

      <div className="flex gap-2 border-b border-white/10 pb-2">
        {tabs.map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              activeTab === tab.id ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'text-gray-400 hover:text-gray-200'
            }`}>{tab.label}</button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        {activeTab === 'input' && (
          <motion.div key="input" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="glass-panel p-6 rounded-2xl border border-white/5 space-y-6">
              {/* Log Data Input */}
              <div>
                <div className="flex justify-between items-center mb-3">
                  <h3 className="text-lg font-bold">{t('shotEfficiency.sections.logs')} (GR, RHOB, NPHI, Rt)</h3>
                  <label className="flex items-center gap-2 px-3 py-1.5 bg-emerald-600/20 hover:bg-emerald-600/30 border border-emerald-500/30 rounded-lg cursor-pointer text-sm text-emerald-400 transition-colors">
                    <Upload size={14} /> Cargar CSV
                    <input type="file" accept=".csv" className="hidden" onChange={handleCSVUpload} />
                  </label>
                </div>
                <textarea
                  value={logData}
                  onChange={e => setLogData(e.target.value)}
                  rows={8}
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-xs font-mono focus:border-emerald-500 focus:outline-none custom-scrollbar"
                  placeholder='[{"md": 8000, "gr": 25, "rhob": 2.35, "nphi": 0.22, "rt": 45}, ...]'
                />
                <p className="text-xs text-gray-500 mt-1">JSON array o pega desde CSV. Columnas: md, gr, rhob, nphi, rt, caliper (opc.)</p>
              </div>

              {/* Archie & Matrix */}
              <div>
                <h3 className="text-lg font-bold mb-3">{t('shotEfficiency.sections.petro')}</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {[
                    { key: 'a', label: 'a (Tortuosidad)', step: '0.1' },
                    { key: 'm', label: 'm (Cementación)', step: '0.1' },
                    { key: 'n', label: 'n (Saturación)', step: '0.1' },
                    { key: 'rw', label: 'Rw (ohm-m)', step: '0.01' },
                    { key: 'rho_matrix', label: 'ρ Matriz (g/cc)', step: '0.01' },
                    { key: 'rho_fluid', label: 'ρ Fluido (g/cc)', step: '0.01' },
                    { key: 'gr_clean', label: 'GR Clean (API)', step: '5' },
                    { key: 'gr_shale', label: 'GR Shale (API)', step: '5' },
                  ].map(({ key, label, step }) => (
                    <div key={key} className="space-y-1">
                      <label className="text-xs text-gray-400">{label}</label>
                      <input type="number" step={step}
                        value={(params as Record<string, unknown>)[key]}
                        onChange={e => updateParam(key, e.target.value)}
                        className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none"
                      />
                    </div>
                  ))}
                </div>
              </div>

              {/* Cutoffs & Perforation */}
              <div>
                <h3 className="text-lg font-bold mb-3">{t('shotEfficiency.sections.cutoffs')}</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {[
                    { key: 'phi_min', label: 'φ Mínimo (v/v)', step: '0.01' },
                    { key: 'sw_max', label: 'Sw Máximo (v/v)', step: '0.05' },
                    { key: 'vsh_max', label: 'Vsh Máximo (v/v)', step: '0.05' },
                    { key: 'min_thickness_ft', label: 'Espesor Mín. (ft)', step: '0.5' },
                    { key: 'spf', label: 'SPF', step: '1' },
                    { key: 'phasing_deg', label: 'Phasing (°)', step: '30' },
                    { key: 'perf_length_in', label: 'Long. Perf. (in)', step: '1' },
                    { key: 'tunnel_radius_in', label: 'Radio Túnel (in)', step: '0.02' },
                    { key: 'kv_kh', label: 'Kv/Kh', step: '0.1' },
                    { key: 'wellbore_radius_ft', label: 'Radio Pozo (ft)', step: '0.01' },
                  ].map(({ key, label, step }) => (
                    <div key={key} className="space-y-1">
                      <label className="text-xs text-gray-400">{label}</label>
                      <input type="number" step={step}
                        value={(params as Record<string, unknown>)[key]}
                        onChange={e => updateParam(key, e.target.value)}
                        className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none"
                      />
                    </div>
                  ))}
                </div>
              </div>

              <button onClick={calculate} disabled={loading}
                className="mt-4 flex items-center gap-2 px-6 py-3 bg-emerald-600 hover:bg-emerald-700 rounded-lg font-medium transition-colors disabled:opacity-50">
                {loading ? <RefreshCw size={16} className="animate-spin" /> : <Play size={16} />}
                {loading ? t('shotEfficiency.analyzing') : t('shotEfficiency.analyzeEfficiency')}
              </button>
            </div>
          </motion.div>
        )}

        {activeTab === 'results' && result && (
          <motion.div key="results" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-6">
            {/* Summary Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { label: 'Puntos Log', value: result.summary?.total_log_points || 0, color: 'text-blue-400' },
                { label: 'Intervalos Net Pay', value: result.summary?.net_pay_intervals_count || 0, color: 'text-emerald-400' },
                { label: 'Net Pay Total', value: `${result.summary?.total_net_pay_ft || 0} ft`, color: 'text-cyan-400' },
                { label: 'Mejor Score', value: result.summary?.best_interval?.score?.toFixed(3) || 'N/A', color: 'text-violet-400' },
              ].map((item, i) => (
                <div key={i} className="glass-panel p-4 rounded-xl border border-white/5 text-center">
                  <div className="text-xs text-gray-500 mb-1">{item.label}</div>
                  <div className={`text-xl font-bold ${item.color}`}>{item.value}</div>
                </div>
              ))}
            </div>

            {/* Best Interval Detail */}
            {result.summary?.best_interval && (
              <div className="glass-panel p-6 rounded-2xl border border-emerald-500/20">
                <h3 className="text-lg font-bold text-emerald-400 mb-3">&#127942; {t('shotEfficiency.bestInterval')}</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div><span className="text-gray-400">Tope:</span> <span className="font-mono">{result.summary.best_interval.top_md} ft</span></div>
                  <div><span className="text-gray-400">Base:</span> <span className="font-mono">{result.summary.best_interval.base_md} ft</span></div>
                  <div><span className="text-gray-400">Espesor:</span> <span className="font-mono">{result.summary.best_interval.thickness_ft} ft</span></div>
                  <div><span className="text-gray-400">φ avg:</span> <span className="font-mono">{(result.summary.best_interval.avg_phi * 100).toFixed(1)}%</span></div>
                  <div><span className="text-gray-400">Sw avg:</span> <span className="font-mono">{(result.summary.best_interval.avg_sw * 100).toFixed(1)}%</span></div>
                  <div><span className="text-gray-400">Score:</span> <span className="font-bold text-emerald-400">{result.summary.best_interval.score?.toFixed(3)}</span></div>
                  <div><span className="text-gray-400">Skin:</span> <span className="font-mono">{result.summary.best_interval.skin_total?.toFixed(2)}</span></div>
                </div>
              </div>
            )}

            {/* Average Petrophysics */}
            <div className="glass-panel p-6 rounded-2xl border border-white/5">
              <h3 className="text-lg font-bold mb-3">{t('shotEfficiency.petroAverages')}</h3>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div><span className="text-gray-400">φ Promedio:</span> <span className="font-mono">{((result.summary?.avg_porosity || 0) * 100).toFixed(1)}%</span></div>
                <div><span className="text-gray-400">Sw Promedio:</span> <span className="font-mono">{((result.summary?.avg_sw || 0) * 100).toFixed(1)}%</span></div>
                <div><span className="text-gray-400">Vsh Promedio:</span> <span className="font-mono">{((result.summary?.avg_vsh || 0) * 100).toFixed(1)}%</span></div>
              </div>
            </div>

            {/* Intervals Table */}
            {result.rankings?.ranked?.length > 0 && (
              <div className="glass-panel p-6 rounded-2xl border border-white/5">
                <h3 className="text-lg font-bold mb-4">{t('shotEfficiency.intervalRanking')}</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-white/10 text-gray-400">
                        <th className="text-left py-2 px-2">Rank</th>
                        <th className="text-left py-2 px-2">Tope (ft)</th>
                        <th className="text-left py-2 px-2">Base (ft)</th>
                        <th className="text-left py-2 px-2">h (ft)</th>
                        <th className="text-left py-2 px-2">φ (%)</th>
                        <th className="text-left py-2 px-2">Sw (%)</th>
                        <th className="text-left py-2 px-2">Vsh (%)</th>
                        <th className="text-left py-2 px-2">Skin</th>
                        <th className="text-left py-2 px-2">Score</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.rankings.ranked.map((iv: { rank: number; top_md: number; base_md: number; score: number }, i: number) => (
                        <tr key={i} className={`border-b border-white/5 ${i === 0 ? 'bg-emerald-500/10' : ''}`}>
                          <td className="py-2 px-2 font-bold text-emerald-400">{iv.rank}</td>
                          <td className="py-2 px-2 font-mono">{iv.top_md}</td>
                          <td className="py-2 px-2 font-mono">{iv.base_md}</td>
                          <td className="py-2 px-2 font-mono">{iv.thickness_ft}</td>
                          <td className="py-2 px-2 font-mono">{(iv.avg_phi * 100).toFixed(1)}</td>
                          <td className="py-2 px-2 font-mono">{(iv.avg_sw * 100).toFixed(1)}</td>
                          <td className="py-2 px-2 font-mono">{(iv.avg_vsh * 100).toFixed(1)}</td>
                          <td className="py-2 px-2 font-mono">{iv.skin_total?.toFixed(2)}</td>
                          <td className="py-2 px-2 font-bold">{iv.score?.toFixed(3)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Alerts */}
            {result.alerts?.length > 0 && (
              <div className="glass-panel p-6 rounded-2xl border border-yellow-500/20">
                <h3 className="text-lg font-bold text-yellow-400 mb-3">&#9888; {t('common.alerts')}</h3>
                <ul className="space-y-2">
                  {result.alerts.map((alert: string, i: number) => (
                    <li key={i} className="text-sm text-yellow-300 flex items-start gap-2">
                      <span className="mt-1">&bull;</span>{alert}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <LogTrackChart processedLogs={result.processed_logs} cutoffs={result.parameters?.cutoffs} />
              <NetPayIntervalChart intervals={result.intervals_with_skin} netPay={result.net_pay} />
              <SkinComponentsBar intervals={result.intervals_with_skin} />
              <IntervalRankingChart rankings={result.rankings} />
              <CutoffSensitivityChart summary={result.summary} parameters={result.parameters} />
            </div>

            {/* AI Analysis */}
            <AIAnalysisPanel
              moduleName="Shot Efficiency"
              moduleIcon={Target}
              wellName={wellName}
              analysis={aiAnalysis?.analysis || null}
              confidence={aiAnalysis?.confidence || 'MEDIUM'}
              agentRole={aiAnalysis?.agent_role || ''}
              isLoading={isAnalyzing}
              keyMetrics={aiAnalysis?.key_metrics || []}
              onAnalyze={handleRunAnalysis}
              provider={provider}
              onProviderChange={setProvider}
              availableProviders={availableProviders}
            />
          </motion.div>
        )}

        {activeTab === 'results' && !result && (
          <div className="animate-fadeIn">
            <div className="glass-panel p-12 rounded-2xl border border-white/5 text-center text-gray-500">
              <Target size={48} className="mx-auto mb-4 opacity-30" />
              <p>{t('shotEfficiency.noResults')}</p>
            </div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default ShotEfficiencyModule;
