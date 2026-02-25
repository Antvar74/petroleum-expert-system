import { useState, useCallback } from 'react';
import api from '../lib/api';
import { motion, AnimatePresence } from 'framer-motion';
import { FileBarChart, Play, Upload, RefreshCw } from 'lucide-react';
import AdvancedLogTrack from './charts/petro/AdvancedLogTrack';
import PickettPlotChart from './charts/petro/PickettPlotChart';
import CrossplotChart from './charts/petro/CrossplotChart';
import AIAnalysisPanel from './AIAnalysisPanel';
import { useLanguage } from '../hooks/useLanguage';
import { useAIAnalysis } from '../hooks/useAIAnalysis';
import { useToast } from './ui/Toast';
import type { Provider } from '../types/ai';
import type { APIError } from '../types/api';

/* ── Local response types (mirror backend Pydantic models) ────────── */

interface EvalPoint {
  md: number; gr: number; rhob: number; nphi: number; rt: number;
  vsh: number; phi_total: number; phi_effective: number; sw: number;
  k_md: number; is_pay: boolean; hc_saturation: number; sw_model: string;
}

interface EvalInterval {
  top_md: number;
  base_md: number;
  thickness_ft: number;
  avg_phi: number;
  avg_sw: number;
  avg_perm_md: number;
}

interface EvalSummary {
  total_points: number;
  net_pay_ft: number;
  avg_phi_pay: number;
  avg_sw_pay: number;
  avg_perm_pay: number;
}

interface EvalResult {
  evaluated_data: EvalPoint[];
  summary: EvalSummary;
  intervals: EvalInterval[];
}

interface PickettPlotResult {
  points: { log_phi: number; log_rt: number; sw?: number }[];
  iso_sw_lines: Record<string, { log_phi: number; log_rt: number }[]>;
  regression?: { slope: number; intercept: number; estimated_m: number };
}

interface CrossplotResult {
  points: { rhob: number; nphi: number; gas_flag: boolean; md?: number }[];
  gas_count: number;
  total_points: number;
}

interface PetroParams {
  a: number; m: number; n: number; rw: number;
  rho_matrix: number; rho_fluid: number; gr_clean: number; gr_shale: number;
  phi_min: number; sw_max: number; vsh_max: number;
}

interface PetrophysicsModuleProps {
  wellId?: number;
  wellName?: string;
}

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

const PetrophysicsModule: React.FC<PetrophysicsModuleProps> = ({ wellId, wellName = '' }) => {
  const [activeTab, setActiveTab] = useState('input');
  const [loading, setLoading] = useState(false);
  const [logData, setLogData] = useState(JSON.stringify(SAMPLE_LOG_DATA, null, 2));
  const [params, setParams] = useState<PetroParams>({
    a: 1.0, m: 2.0, n: 2.0, rw: 0.05,
    rho_matrix: 2.65, rho_fluid: 1.0, gr_clean: 20, gr_shale: 120,
    phi_min: 0.08, sw_max: 0.60, vsh_max: 0.40,
  });
  const [evalResult, setEvalResult] = useState<EvalResult | null>(null);
  const [pickettResult, setPickettResult] = useState<PickettPlotResult | null>(null);
  const [crossplotResult, setCrossplotResult] = useState<CrossplotResult | null>(null);
  const { language } = useLanguage();
  const { addToast } = useToast();

  const { aiAnalysis, isAnalyzing, runAnalysis, provider, setProvider, availableProviders, setAiAnalysis } = useAIAnalysis({
    module: 'petrophysics',
    wellId,
    wellName,
  });

  const updateParam = (key: string, value: string) => {
    setParams(prev => ({ ...prev, [key]: parseFloat(value) || 0 }));
  };

  // ── LAS file upload ──
  const handleLASUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async (evt) => {
      try {
        const content = evt.target?.result as string;
        // If .las file, parse via API
        if (file.name.toLowerCase().endsWith('.las')) {
          const res = await api.post(`/calculate/petrophysics/parse-las`, {
            las_content: content,
          });
          if (res.data?.data) {
            setLogData(JSON.stringify(res.data.data, null, 2));
            addToast(
              language === 'es'
                ? `LAS cargado: ${res.data.depth_range?.points || 0} puntos`
                : `LAS loaded: ${res.data.depth_range?.points || 0} points`,
              'success',
            );
          }
        } else {
          // CSV fallback
          const lines = content.trim().split('\n');
          const headers = lines[0].split(',').map(h => h.trim().toLowerCase());
          const entries: Record<string, number>[] = [];
          for (let i = 1; i < lines.length; i++) {
            const vals = lines[i].split(',');
            if (vals.length < headers.length) continue;
            const entry: Record<string, number> = {};
            headers.forEach((h, j) => { entry[h] = parseFloat(vals[j]?.trim()) || 0; });
            entries.push(entry);
          }
          setLogData(JSON.stringify(entries, null, 2));
          addToast(`CSV: ${entries.length} rows`, 'success');
        }
      } catch (err: unknown) {
        const e = err as APIError;
        addToast('Error: ' + (e.response?.data?.detail || e.message), 'error');
      }
    };
    reader.readAsText(file);
  };

  // ── Run full evaluation ──
  const runEvaluation = useCallback(async () => {
    setLoading(true);
    try {
      let entries;
      try { entries = JSON.parse(logData); } catch {
        addToast(language === 'es' ? 'JSON inválido' : 'Invalid JSON', 'error');
        setLoading(false);
        return;
      }

      const payload = {
        log_data: entries,
        archie_params: { a: params.a, m: params.m, n: params.n, rw: params.rw },
        matrix_params: {
          rho_matrix: params.rho_matrix, rho_fluid: params.rho_fluid,
          gr_clean: params.gr_clean, gr_shale: params.gr_shale,
        },
        cutoffs: { phi_min: params.phi_min, sw_max: params.sw_max, vsh_max: params.vsh_max },
      };

      const res = await api.post(`/calculate/petrophysics/evaluate`, payload);
      setEvalResult(res.data);

      // Also run Pickett and crossplot
      if (res.data?.evaluated_data?.length) {
        const evalData = res.data.evaluated_data;
        const pickettData = evalData
          .filter((d: EvalPoint) => d.phi_effective > 0.01 && d.rt > 0.1)
          .map((d: EvalPoint) => ({ phi: d.phi_effective, rt: d.rt, sw: d.sw }));

        const [pickettRes, crossRes] = await Promise.all([
          api.post(`/calculate/petrophysics/pickett-plot`, {
            log_data: pickettData, rw: params.rw, a: params.a, m: params.m, n: params.n,
          }),
          api.post(`/calculate/petrophysics/crossplot`, {
            log_data: evalData.map((d: EvalPoint) => ({ rhob: d.rhob, nphi: d.nphi, md: d.md })),
            rho_fluid: params.rho_fluid,
          }),
        ]);
        setPickettResult(pickettRes.data);
        setCrossplotResult(crossRes.data);
      }

      setActiveTab('log-tracks');
    } catch (e: unknown) {
      addToast('Error: ' + ((e as APIError).response?.data?.detail || (e as APIError).message), 'error');
    }
    setLoading(false);
  }, [logData, params, language, addToast]);

  const handleRunAnalysis = () => {
    runAnalysis(
      { evaluation: evalResult, pickett: pickettResult, crossplot: crossplotResult },
      params as unknown as Record<string, unknown>
    );
  };

  const tabs = [
    { id: 'input', label: language === 'es' ? 'Datos' : 'Input' },
    { id: 'log-tracks', label: 'Log Tracks' },
    { id: 'crossplots', label: 'Crossplots' },
    { id: 'results', label: language === 'es' ? 'Resultados' : 'Results' },
  ];

  return (
    <div className="animate-fadeIn space-y-4">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-violet-500/10 border border-violet-500/20">
          <FileBarChart className="w-5 h-5 text-violet-400" />
        </div>
        <div>
          <h2 className="text-lg font-semibold text-white">
            {language === 'es' ? 'Petrofísica Avanzada' : 'Advanced Petrophysics'}
          </h2>
          <p className="text-xs text-slate-400">
            LAS Import · Waxman-Smits · Dual-Water · Pickett Plot · Crossplots
          </p>
        </div>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 bg-slate-800/50 p-1 rounded-lg border border-slate-700/50">
        {tabs.map(tab => (
          <button key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex-1 px-3 py-1.5 text-xs font-medium rounded-md transition-all
              ${activeTab === tab.id
                ? 'bg-violet-500/20 text-violet-300 border border-violet-500/30'
                : 'text-slate-400 hover:text-slate-200 border border-transparent'
              }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        {activeTab === 'input' && (
          <motion.div key="input" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="space-y-4">
            {/* Upload */}
            <div className="bg-slate-800/40 rounded-xl border border-slate-700/50 p-4">
              <h3 className="text-sm font-medium text-white mb-3">
                {language === 'es' ? 'Cargar Datos de Registros' : 'Load Log Data'}
              </h3>
              <div className="flex gap-3">
                <label className="flex items-center gap-2 px-4 py-2 bg-violet-600/20 border border-violet-500/30 rounded-lg cursor-pointer hover:bg-violet-600/30 transition-colors">
                  <Upload className="w-4 h-4 text-violet-400" />
                  <span className="text-xs text-violet-300">
                    {language === 'es' ? 'Subir LAS / CSV' : 'Upload LAS / CSV'}
                  </span>
                  <input type="file" accept=".las,.csv,.LAS,.CSV" onChange={handleLASUpload} className="hidden" />
                </label>
              </div>
            </div>

            {/* Parameters */}
            <div className="bg-slate-800/40 rounded-xl border border-slate-700/50 p-4">
              <h3 className="text-sm font-medium text-white mb-3">
                {language === 'es' ? 'Parámetros Petrofísicos' : 'Petrophysical Parameters'}
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {[
                  { key: 'a', label: 'a (Archie)', step: 0.1 },
                  { key: 'm', label: 'm (Cementation)', step: 0.1 },
                  { key: 'n', label: 'n (Saturation)', step: 0.1 },
                  { key: 'rw', label: 'Rw (Ω·m)', step: 0.01 },
                  { key: 'rho_matrix', label: 'ρ matrix (g/cc)', step: 0.01 },
                  { key: 'rho_fluid', label: 'ρ fluid (g/cc)', step: 0.1 },
                  { key: 'gr_clean', label: 'GR clean (API)', step: 5 },
                  { key: 'gr_shale', label: 'GR shale (API)', step: 5 },
                  { key: 'phi_min', label: 'φ min cutoff', step: 0.01 },
                  { key: 'sw_max', label: 'Sw max cutoff', step: 0.05 },
                  { key: 'vsh_max', label: 'Vsh max cutoff', step: 0.05 },
                ].map(p => (
                  <div key={p.key}>
                    <label className="block text-[10px] text-slate-400 mb-1">{p.label}</label>
                    <input type="number" step={p.step}
                      value={params[p.key as keyof PetroParams]}
                      onChange={e => updateParam(p.key, e.target.value)}
                      className="w-full px-2 py-1.5 bg-slate-700/50 border border-slate-600/50 rounded text-xs text-white"
                    />
                  </div>
                ))}
              </div>
            </div>

            {/* Log data textarea */}
            <div className="bg-slate-800/40 rounded-xl border border-slate-700/50 p-4">
              <h3 className="text-sm font-medium text-white mb-2">
                {language === 'es' ? 'Datos de Registros (JSON)' : 'Log Data (JSON)'}
              </h3>
              <textarea
                value={logData}
                onChange={e => setLogData(e.target.value)}
                rows={8}
                className="w-full bg-slate-900/50 border border-slate-600/50 rounded-lg p-3 text-xs text-slate-300 font-mono"
              />
            </div>

            {/* Run button */}
            <button onClick={runEvaluation} disabled={loading}
              className="w-full flex items-center justify-center gap-2 py-3 bg-gradient-to-r from-violet-600 to-purple-600 rounded-xl text-white font-medium text-sm hover:from-violet-500 hover:to-purple-500 disabled:opacity-50 transition-all">
              {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              {loading
                ? (language === 'es' ? 'Evaluando...' : 'Evaluating...')
                : (language === 'es' ? 'Ejecutar Evaluación Petrofísica' : 'Run Petrophysical Evaluation')
              }
            </button>
          </motion.div>
        )}

        {activeTab === 'log-tracks' && evalResult && (
          <motion.div key="tracks" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            <AdvancedLogTrack
              data={evalResult.evaluated_data}
              cutoffs={params}
            />
          </motion.div>
        )}

        {activeTab === 'crossplots' && (
          <motion.div key="crossplots" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {pickettResult && (
              <PickettPlotChart
                points={pickettResult.points}
                isoSwLines={pickettResult.iso_sw_lines}
                regression={pickettResult.regression}
              />
            )}
            {crossplotResult && (
              <CrossplotChart
                points={crossplotResult.points}
                gasCount={crossplotResult.gas_count}
                totalPoints={crossplotResult.total_points}
              />
            )}
          </motion.div>
        )}

        {activeTab === 'results' && evalResult && (
          <motion.div key="results" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className="space-y-4">
            {/* Summary cards */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              {[
                { label: language === 'es' ? 'Puntos' : 'Points', value: evalResult.summary.total_points, color: 'text-slate-300' },
                { label: 'Net Pay', value: `${evalResult.summary.net_pay_ft} ft`, color: 'text-green-400' },
                { label: 'φ avg', value: `${(evalResult.summary.avg_phi_pay * 100).toFixed(1)}%`, color: 'text-cyan-400' },
                { label: 'Sw avg', value: `${(evalResult.summary.avg_sw_pay * 100).toFixed(1)}%`, color: 'text-blue-400' },
                { label: 'k avg', value: `${evalResult.summary.avg_perm_pay.toFixed(0)} mD`, color: 'text-yellow-400' },
              ].map((card, i) => (
                <div key={i} className="bg-slate-800/40 rounded-lg border border-slate-700/50 p-3 text-center">
                  <div className={`text-lg font-bold ${card.color}`}>{card.value}</div>
                  <div className="text-[10px] text-slate-500">{card.label}</div>
                </div>
              ))}
            </div>

            {/* Intervals table */}
            {evalResult.intervals?.length > 0 && (
              <div className="bg-slate-800/40 rounded-xl border border-slate-700/50 p-4">
                <h3 className="text-sm font-medium text-white mb-3">
                  {language === 'es' ? 'Intervalos Net Pay' : 'Net Pay Intervals'}
                </h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="text-slate-400 border-b border-slate-700">
                        <th className="p-2 text-left">Top (ft)</th>
                        <th className="p-2 text-left">Base (ft)</th>
                        <th className="p-2 text-left">{language === 'es' ? 'Espesor' : 'Thickness'} (ft)</th>
                        <th className="p-2 text-left">φe avg</th>
                        <th className="p-2 text-left">Sw avg</th>
                        <th className="p-2 text-left">k avg (mD)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {evalResult.intervals.map((iv: EvalInterval, i: number) => (
                        <tr key={i} className="border-b border-slate-700/50 text-slate-300">
                          <td className="p-2">{iv.top_md}</td>
                          <td className="p-2">{iv.base_md}</td>
                          <td className="p-2 text-green-400">{iv.thickness_ft}</td>
                          <td className="p-2">{(iv.avg_phi * 100).toFixed(1)}%</td>
                          <td className="p-2">{(iv.avg_sw * 100).toFixed(1)}%</td>
                          <td className="p-2">{iv.avg_perm_md.toFixed(0)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* AI Analysis */}
            <AIAnalysisPanel
              moduleName={language === 'es' ? 'Petrofísica Avanzada' : 'Advanced Petrophysics'}
              moduleIcon={FileBarChart}
              wellName={wellName || 'General Analysis'}
              analysis={aiAnalysis?.analysis || null}
              confidence={aiAnalysis?.confidence || 'MEDIUM'}
              agentRole="Petrophysics Specialist"
              isLoading={isAnalyzing}
              keyMetrics={evalResult ? [
                { label: 'Net Pay', value: `${evalResult.summary.net_pay_ft} ft` },
                { label: 'φ avg', value: `${(evalResult.summary.avg_phi_pay * 100).toFixed(1)}%` },
                { label: 'Sw avg', value: `${(evalResult.summary.avg_sw_pay * 100).toFixed(1)}%` },
                { label: 'k avg', value: `${evalResult.summary.avg_perm_pay.toFixed(0)} mD` },
              ] : []}
              onAnalyze={handleRunAnalysis}
              provider={provider}
              onProviderChange={setProvider}
              availableProviders={availableProviders}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default PetrophysicsModule;
