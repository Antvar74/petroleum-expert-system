import { useState, useEffect } from 'react';
import api from '../lib/api';
import { motion, AnimatePresence } from 'framer-motion';
import { Filter, Play, RefreshCw } from 'lucide-react';
import GrainDistributionChart from './charts/sc/GrainDistributionChart';
import CompletionComparisonRadar from './charts/sc/CompletionComparisonRadar';
import DrawdownLimitGauge from './charts/sc/DrawdownLimitGauge';
import GravelPackSchematic from './charts/sc/GravelPackSchematic';
import AIAnalysisPanel from './AIAnalysisPanel';
import { useLanguage } from '../hooks/useLanguage';
import { useTranslation } from 'react-i18next';
import { useToast } from './ui/Toast';
import type { Provider, ProviderOption } from '../types/ai';
import type { AIAnalysisResponse, APIError } from '../types/api';

interface SandControlModuleProps {
  wellId?: number;
  wellName?: string;
}

const SandControlModule: React.FC<SandControlModuleProps> = ({ wellId, wellName = '' }) => {
  const [activeTab, setActiveTab] = useState('input');
  const [loading, setLoading] = useState(false);

  const [params, setParams] = useState({
    sieve_sizes_mm: '2.0, 0.85, 0.425, 0.25, 0.15, 0.075',
    cumulative_passing_pct: '100, 95, 70, 40, 15, 2',
    hole_id: 8.5,
    screen_od: 5.5,
    interval_length: 50,
    ucs_psi: 500,
    friction_angle_deg: 30,
    reservoir_pressure_psi: 4500,
    overburden_stress_psi: 10000,
    formation_permeability_md: 500,
    wellbore_radius_ft: 0.354,
    wellbore_type: 'cased',
    gravel_permeability_md: 80000,
    pack_factor: 1.4,
    washout_factor: 1.1,
  });

  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [aiAnalysis, setAiAnalysis] = useState<AIAnalysisResponse | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const { language } = useLanguage();
  const { t } = useTranslation();
  const { addToast } = useToast();
  const [provider, setProvider] = useState<Provider>('auto');
  const [availableProviders, setAvailableProviders] = useState<ProviderOption[]>([
    { id: 'auto', name: 'Auto (Best Available)', name_es: 'Auto (Mejor Disponible)' }
  ]);

  useEffect(() => {
    api.get(`/providers`).then(res => setAvailableProviders(res.data)).catch(() => {});
  }, []);

  const updateParam = (key: string, value: string) => {
    setParams(prev => ({ ...prev, [key]: key.includes('sieve') || key.includes('cumulative') ? value : (parseFloat(value) || 0) }));
  };

  const calculate = async () => {
    setLoading(true);
    try {
      const payload = {
        ...params,
        sieve_sizes_mm: params.sieve_sizes_mm.split(',').map(s => parseFloat(s.trim())),
        cumulative_passing_pct: params.cumulative_passing_pct.split(',').map(s => parseFloat(s.trim())),
      };
      const url = wellId
        ? `/wells/${wellId}/sand-control`
        : `/calculate/sand-control`;
      const res = await api.post(url, payload);
      setResult(res.data);
      setActiveTab('results');
    } catch (e: unknown) {
      addToast('Error: ' + (e as APIError).response?.data?.detail || (e as APIError).message, 'error');
    }
    setLoading(false);
  };

  const runAIAnalysis = async () => {
    if (!result) return;
    setIsAnalyzing(true);
    try {
      const analyzeUrl = wellId
        ? `/wells/${wellId}/sand-control/analyze`
        : `/analyze/module`;
      const analyzeBody = wellId
        ? { result_data: result, params, language, provider }
        : { module: 'sand-control', well_name: wellName || 'General Analysis', result_data: result, params, language, provider };
      const res = await api.post(analyzeUrl, analyzeBody);
      setAiAnalysis(res.data);
    } catch (e: unknown) {
      setAiAnalysis({ analysis: `Error: ${(e as APIError)?.response?.data?.detail || (e as APIError)?.message}`, confidence: 'LOW', agent_role: 'Error', key_metrics: [] });
    }
    setIsAnalyzing(false);
  };

  const tabs = [
    { id: 'input', label: t('common.parameters') },
    { id: 'results', label: t('common.results') },
  ];

  const riskColor = (risk: string) => {
    if (risk?.includes('Very High') || risk?.includes('High')) return 'text-red-400 bg-red-500/10';
    if (risk?.includes('Moderate')) return 'text-yellow-400 bg-yellow-500/10';
    return 'text-green-400 bg-green-500/10';
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Filter className="text-amber-400" size={28} />
        <h2 className="text-2xl font-bold">{t('sandControl.title')}</h2>
        <span className="text-sm text-gray-500">{t('sandControl.subtitle')}</span>
      </div>

      <div className="flex gap-2 border-b border-white/10 pb-2">
        {tabs.map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              activeTab === tab.id ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' : 'text-gray-400 hover:text-gray-200'
            }`}>{tab.label}</button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        {activeTab === 'input' && (
          <motion.div key="input" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="glass-panel p-6 rounded-2xl border border-white/5 space-y-6">
              {/* Sieve Data */}
              <div>
                <h3 className="text-lg font-bold mb-3">{t('sandControl.sections.psd')}</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <label className="text-xs text-gray-400">Tamaños Tamiz (mm, separados por coma)</label>
                    <input type="text" value={params.sieve_sizes_mm}
                      onChange={e => updateParam('sieve_sizes_mm', e.target.value)}
                      className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:border-amber-500 focus:outline-none"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs text-gray-400">% Pasante Acumulado (separados por coma)</label>
                    <input type="text" value={params.cumulative_passing_pct}
                      onChange={e => updateParam('cumulative_passing_pct', e.target.value)}
                      className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:border-amber-500 focus:outline-none"
                    />
                  </div>
                </div>
              </div>

              {/* Completion & Formation */}
              <div>
                <h3 className="text-lg font-bold mb-3">{t('sandControl.sections.formation')}</h3>
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                  {[
                    { key: 'hole_id', label: 'Diámetro Hoyo (in)', step: '0.125' },
                    { key: 'screen_od', label: 'OD Screen (in)', step: '0.125' },
                    { key: 'interval_length', label: 'Intervalo (ft)', step: '10' },
                    { key: 'ucs_psi', label: 'UCS (psi)', step: '50' },
                    { key: 'friction_angle_deg', label: 'Ángulo Fricción (°)', step: '1' },
                    { key: 'reservoir_pressure_psi', label: 'P Reservorio (psi)', step: '100' },
                    { key: 'overburden_stress_psi', label: 'Esfuerzo Sobrecarga (psi)', step: '500' },
                    { key: 'formation_permeability_md', label: 'Permeabilidad (mD)', step: '50' },
                    { key: 'gravel_permeability_md', label: 'Perm. Grava (mD)', step: '10000' },
                    { key: 'pack_factor', label: 'Factor Empaque', step: '0.1' },
                    { key: 'washout_factor', label: 'Factor Lavado', step: '0.05' },
                    { key: 'wellbore_radius_ft', label: 'Radio Pozo (ft)', step: '0.01' },
                  ].map(({ key, label, step }) => (
                    <div key={key} className="space-y-1">
                      <label className="text-xs text-gray-400">{label}</label>
                      <input type="number" step={step}
                        value={(params as Record<string, unknown>)[key]}
                        onChange={e => updateParam(key, e.target.value)}
                        className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:border-amber-500 focus:outline-none"
                      />
                    </div>
                  ))}
                  <div className="space-y-1">
                    <label className="text-xs text-gray-400">Tipo Completación</label>
                    <select value={params.wellbore_type}
                      onChange={e => setParams(prev => ({ ...prev, wellbore_type: e.target.value }))}
                      className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:border-amber-500 focus:outline-none">
                      <option value="cased">Entubado</option>
                      <option value="openhole">Hoyo Abierto</option>
                    </select>
                  </div>
                </div>
              </div>

              <button onClick={calculate} disabled={loading}
                className="mt-4 flex items-center gap-2 px-6 py-3 bg-amber-600 hover:bg-amber-700 rounded-lg font-medium transition-colors disabled:opacity-50">
                {loading ? <RefreshCw size={16} className="animate-spin" /> : <Play size={16} />}
                {loading ? t('common.calculating') : t('common.calculate')}
              </button>
            </div>
          </motion.div>
        )}

        {activeTab === 'results' && result && (
          <motion.div key="results" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-6">
            {/* Summary Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { label: 'D50', value: `${result.summary?.d50_mm} mm`, color: 'text-amber-400' },
                { label: 'Riesgo Arena', value: result.summary?.sanding_risk, color: '' },
                { label: 'Grava', value: result.summary?.recommended_gravel, color: 'text-cyan-400' },
                { label: 'Skin Total', value: result.summary?.skin_total, color: result.summary?.skin_total < 5 ? 'text-green-400' : 'text-red-400' },
              ].map((item, i) => (
                <div key={i} className="glass-panel p-4 rounded-xl border border-white/5 text-center">
                  <div className="text-xs text-gray-500 mb-1">{item.label}</div>
                  <div className={`text-xl font-bold ${item.color || riskColor(String(item.value))}`}>{item.value}</div>
                </div>
              ))}
            </div>

            {/* PSD Details */}
            <div className="glass-panel p-6 rounded-2xl border border-white/5">
              <h3 className="text-lg font-bold mb-4">{t('sandControl.grainSize')}</h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                <div><span className="text-gray-400">D10:</span> <span className="font-mono">{result.psd?.d10_mm} mm</span></div>
                <div><span className="text-gray-400">D50:</span> <span className="font-mono">{result.psd?.d50_mm} mm</span></div>
                <div><span className="text-gray-400">D90:</span> <span className="font-mono">{result.psd?.d90_mm} mm</span></div>
                <div><span className="text-gray-400">Cu:</span> <span className="font-mono">{result.psd?.uniformity_coefficient}</span></div>
                <div><span className="text-gray-400">Sorting:</span> <span className="font-mono">{result.psd?.sorting}</span></div>
              </div>
            </div>

            {/* Gravel & Screen */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="glass-panel p-6 rounded-2xl border border-white/5">
                <h3 className="text-lg font-bold mb-3">{t('sandControl.gravelSelection')}</h3>
                <div className="space-y-2 text-sm">
                  <div><span className="text-gray-400">Pack Recomendado:</span> <span className="font-bold text-cyan-400">{result.gravel?.recommended_pack}</span></div>
                  <div><span className="text-gray-400">Rango:</span> <span className="font-mono">{result.gravel?.gravel_min_mm}-{result.gravel?.gravel_max_mm} mm</span></div>
                  <div><span className="text-gray-400">Volumen Grava:</span> <span className="font-mono">{result.volume?.gravel_volume_bbl} bbl</span></div>
                  <div><span className="text-gray-400">Peso Grava:</span> <span className="font-mono">{result.volume?.gravel_weight_lb} lb</span></div>
                </div>
              </div>
              <div className="glass-panel p-6 rounded-2xl border border-white/5">
                <h3 className="text-lg font-bold mb-3">Screen Selection</h3>
                <div className="space-y-2 text-sm">
                  <div><span className="text-gray-400">Tipo:</span> <span className="font-mono">{result.screen?.screen_type}</span></div>
                  <div><span className="text-gray-400">Slot Recomendado:</span> <span className="font-bold text-cyan-400">{result.screen?.recommended_standard_slot_in}"</span></div>
                  <div><span className="text-gray-400">Retención Est.:</span> <span className="font-mono">{result.screen?.estimated_retention_pct}%</span></div>
                </div>
              </div>
            </div>

            {/* Drawdown & Completion */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="glass-panel p-6 rounded-2xl border border-white/5">
                <h3 className="text-lg font-bold mb-3">{t('sandControl.sandingAnalysis')}</h3>
                <div className="space-y-2 text-sm">
                  <div><span className="text-gray-400">Drawdown Crítico:</span> <span className="font-mono">{result.drawdown?.critical_drawdown_psi} psi</span></div>
                  <div><span className="text-gray-400">Riesgo:</span> <span className={`font-bold ${riskColor(result.drawdown?.sanding_risk)}`}>{result.drawdown?.sanding_risk}</span></div>
                  <div><span className="text-gray-400">Recomendación:</span> <span className="text-xs">{result.drawdown?.recommendation}</span></div>
                </div>
              </div>
              <div className="glass-panel p-6 rounded-2xl border border-white/5">
                <h3 className="text-lg font-bold mb-3">Completion Type</h3>
                <div className="space-y-2 text-sm">
                  <div><span className="text-gray-400">Recomendado:</span> <span className="font-bold text-green-400">{result.completion?.recommended}</span></div>
                  {result.completion?.methods?.slice(0, 3).map((m: { method: string; score: number }, i: number) => (
                    <div key={i} className="flex justify-between items-center py-1 border-t border-white/5">
                      <span className="text-gray-300">{m.method}</span>
                      <span className="text-xs text-gray-500">Score: {m.score}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

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
              <GrainDistributionChart psd={result.psd} sieveData={result.parameters} />
              <CompletionComparisonRadar completion={result.completion} />
              <DrawdownLimitGauge drawdown={result.drawdown} />
              <GravelPackSchematic gravel={result.gravel} screen={result.screen} volume={result.volume} />
            </div>

            {/* AI Analysis */}
            <AIAnalysisPanel
              moduleName="Sand Control"
              moduleIcon={Filter}
              wellName={wellName}
              analysis={aiAnalysis?.analysis || null}
              confidence={aiAnalysis?.confidence || 'MEDIUM'}
              agentRole={aiAnalysis?.agent_role || ''}
              isLoading={isAnalyzing}
              keyMetrics={aiAnalysis?.key_metrics || []}
              onAnalyze={runAIAnalysis}
              provider={provider}
              onProviderChange={setProvider}
              availableProviders={availableProviders}
            />
          </motion.div>
        )}

        {activeTab === 'results' && !result && (
          <motion.div key="no-results" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <div className="glass-panel p-12 rounded-2xl border border-white/5 text-center text-gray-500">
              <Filter size={48} className="mx-auto mb-4 opacity-30" />
              <p>{t('sandControl.noResults')}</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default SandControlModule;
