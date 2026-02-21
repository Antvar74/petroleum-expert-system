import { useState, useEffect } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { Droplets, Play, RefreshCw } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { API_BASE_URL } from '../config';
import FlowRateSensitivity from './charts/cu/FlowRateSensitivity';
import AnnularVelocityChart from './charts/cu/AnnularVelocityChart';
import CuttingsConcentrationGauge from './charts/cu/CuttingsConcentrationGauge';
import CleanupEfficiencyProfile from './charts/cu/CleanupEfficiencyProfile';
import AIAnalysisPanel from './AIAnalysisPanel';
import { useLanguage } from '../hooks/useLanguage';
import type { Provider, ProviderOption } from '../types/ai';

interface WellboreCleanupModuleProps {
  wellId: number;
  wellName?: string;
}

const WellboreCleanupModule: React.FC<WellboreCleanupModuleProps> = ({ wellId, wellName = '' }) => {
  const [activeTab, setActiveTab] = useState('input');
  const [loading, setLoading] = useState(false);

  // Input parameters
  const [params, setParams] = useState({
    flow_rate: 500,
    mud_weight: 10.0,
    pv: 15,
    yp: 10,
    hole_id: 8.5,
    pipe_od: 5.0,
    inclination: 0,
    rop: 60,
    cutting_size: 0.25,
    cutting_density: 21.0,
    rpm: 0,
    annular_length: 1000,
  });

  // Results
  const [result, setResult] = useState<any>(null);

  // AI Analysis
  const [aiAnalysis, setAiAnalysis] = useState<any>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const { language } = useLanguage();
  const { t } = useTranslation();
  const [provider, setProvider] = useState<Provider>('auto');
  const [availableProviders, setAvailableProviders] = useState<ProviderOption[]>([
    { id: 'auto', name: 'Auto (Best Available)', name_es: 'Auto (Mejor Disponible)' }
  ]);

  useEffect(() => {
    axios.get(`${API_BASE_URL}/providers`).then(res => setAvailableProviders(res.data)).catch(() => {});
  }, []);

  const updateParam = (key: string, value: string) => {
    setParams(prev => ({ ...prev, [key]: parseFloat(value) || 0 }));
  };

  const calculate = async () => {
    setLoading(true);
    try {
      const res = await axios.post(`${API_BASE_URL}/wells/${wellId}/wellbore-cleanup`, params);
      setResult(res.data);
      setActiveTab('results');
    } catch (e: any) {
      alert('Error: ' + (e.response?.data?.detail || e.message));
    }
    setLoading(false);
  };

  const runAIAnalysis = async () => {
    if (!result) return;
    setIsAnalyzing(true);
    try {
      const res = await axios.post(`${API_BASE_URL}/wells/${wellId}/wellbore-cleanup/analyze`, {
        result_data: result, params, language, provider,
      });
      setAiAnalysis(res.data);
    } catch (e: any) {
      setAiAnalysis({ analysis: `Error: ${e?.response?.data?.detail || e?.message}`, confidence: 'LOW', agent_role: 'Error', key_metrics: [] });
    }
    setIsAnalyzing(false);
  };

  const tabs = [
    { id: 'input', label: t('common.parameters') },
    { id: 'results', label: t('common.results') },
  ];

  const qualityColor = (q: string) => {
    if (q === 'Good') return 'text-green-400 bg-green-500/10';
    if (q === 'Marginal') return 'text-yellow-400 bg-yellow-500/10';
    return 'text-red-400 bg-red-500/10';
  };

  // Sensitivity data for chart
  const sensitivityData = result ? Array.from({ length: 13 }, (_, i) => {
    const q = 200 + i * 50;
    const va = 24.51 * q / (params.hole_id ** 2 - params.pipe_od ** 2);
    const va_min = params.inclination > 60 ? 150 : params.inclination > 30 ? 130 : 120;
    const hci = va / va_min;
    const vs = result.summary?.slip_velocity_ftmin || 30;
    const ctr = va > 0 ? Math.max((va - vs) / va, 0) : 0;
    return { flow_rate: q, hci: Math.round(hci * 100) / 100, ctr: Math.round(ctr * 100) / 100 };
  }) : [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Droplets className="text-blue-400" size={28} />
        <h2 className="text-2xl font-bold">{t('wellboreCleanup.title')}</h2>
        <span className="text-sm text-gray-500">{t('wellboreCleanup.subtitle')}</span>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-white/10 pb-2">
        {tabs.map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              activeTab === tab.id ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30' : 'text-gray-400 hover:text-gray-200'
            }`}>{tab.label}</button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        {/* INPUT TAB */}
        {activeTab === 'input' && (
          <motion.div key="input" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="glass-panel p-6 rounded-2xl border border-white/5">
              <h3 className="text-lg font-bold mb-4">{t('wellboreCleanup.sections.operating')}</h3>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                {[
                  { key: 'flow_rate', label: t('wellboreCleanup.flowRate'), step: '10' },
                  { key: 'mud_weight', label: t('wellboreCleanup.mudWeight'), step: '0.1' },
                  { key: 'pv', label: t('wellboreCleanup.pv'), step: '1' },
                  { key: 'yp', label: t('wellboreCleanup.yp'), step: '1' },
                  { key: 'hole_id', label: t('wellboreCleanup.holeSize'), step: '0.125' },
                  { key: 'pipe_od', label: t('wellboreCleanup.dpOD'), step: '0.125' },
                  { key: 'inclination', label: t('wellboreCleanup.inclination'), step: '5' },
                  { key: 'rop', label: t('wellboreCleanup.rop'), step: '5' },
                  { key: 'cutting_size', label: t('wellboreCleanup.cuttingSize'), step: '0.05' },
                  { key: 'cutting_density', label: t('wellboreCleanup.cuttingDensity'), step: '0.5' },
                  { key: 'rpm', label: t('wellboreCleanup.rpm'), step: '10' },
                  { key: 'annular_length', label: t('wellboreCleanup.annularLength'), step: '100' },
                ].map(({ key, label, step }) => (
                  <div key={key} className="space-y-1">
                    <label className="text-xs text-gray-400">{label}</label>
                    <input type="number" step={step}
                      value={(params as any)[key]}
                      onChange={e => updateParam(key, e.target.value)}
                      className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                    />
                  </div>
                ))}
              </div>
              <button onClick={calculate} disabled={loading}
                className="mt-6 flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium transition-colors disabled:opacity-50">
                {loading ? <RefreshCw size={16} className="animate-spin" /> : <Play size={16} />}
                {loading ? t('common.calculating') : t('common.calculate')}
              </button>
            </div>
          </motion.div>
        )}

        {/* RESULTS TAB */}
        {activeTab === 'results' && result && (
          <motion.div key="results" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-6">
            {/* Summary Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { label: t('wellboreCleanup.annularVelocity'), value: `${result.summary?.annular_velocity_ftmin} ft/min`, color: 'text-blue-400' },
                { label: t('wellboreCleanup.ctr'), value: result.summary?.cuttings_transport_ratio, color: (result.summary?.cuttings_transport_ratio >= 0.55) ? 'text-green-400' : 'text-red-400' },
                { label: t('wellboreCleanup.hci'), value: result.summary?.hole_cleaning_index, color: (result.summary?.hole_cleaning_index >= 1.0) ? 'text-green-400' : 'text-yellow-400' },
                { label: t('wellboreCleanup.quality'), value: result.summary?.cleaning_quality, color: '' },
              ].map((item, i) => (
                <div key={i} className="glass-panel p-4 rounded-xl border border-white/5 text-center">
                  <div className="text-xs text-gray-500 mb-1">{item.label}</div>
                  <div className={`text-xl font-bold ${item.color || qualityColor(String(item.value))}`}>{item.value}</div>
                </div>
              ))}
            </div>

            {/* Detailed Metrics */}
            <div className="glass-panel p-6 rounded-2xl border border-white/5">
              <h3 className="text-lg font-bold mb-4">{t('common.detailedMetrics')}</h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                <div><span className="text-gray-400">{t('wellboreCleanup.slipVelocity')}:</span> <span className="font-mono">{result.summary?.slip_velocity_ftmin} ft/min</span></div>
                <div><span className="text-gray-400">{t('wellboreCleanup.transportVelocity')}:</span> <span className="font-mono">{result.summary?.transport_velocity_ftmin} ft/min</span></div>
                <div><span className="text-gray-400">{t('wellboreCleanup.minFlowRate')}:</span> <span className="font-mono">{result.summary?.minimum_flow_rate_gpm} gpm</span></div>
                <div><span className="text-gray-400">{t('wellboreCleanup.cuttingsConcentration')}:</span> <span className="font-mono">{result.summary?.cuttings_concentration_pct}%</span></div>
                <div><span className="text-gray-400">{t('wellboreCleanup.flowRateAdequate')}:</span> <span className={`font-bold ${result.summary?.flow_rate_adequate ? 'text-green-400' : 'text-red-400'}`}>{result.summary?.flow_rate_adequate ? t('common.yes') : t('common.no')}</span></div>
              </div>
            </div>

            {/* Sweep Pill */}
            {result.sweep_pill && (
              <div className="glass-panel p-6 rounded-2xl border border-white/5">
                <h3 className="text-lg font-bold mb-4">{t('wellboreCleanup.sweepDesign')}</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div><span className="text-gray-400">{t('wellboreCleanup.pillVolume')}:</span> <span className="font-mono">{result.sweep_pill.pill_volume_bbl} bbl</span></div>
                  <div><span className="text-gray-400">{t('wellboreCleanup.pillWeight')}:</span> <span className="font-mono">{result.sweep_pill.pill_weight_ppg} ppg</span></div>
                  <div><span className="text-gray-400">{t('wellboreCleanup.pillLength')}:</span> <span className="font-mono">{result.sweep_pill.pill_length_ft} ft</span></div>
                  <div><span className="text-gray-400">{t('wellboreCleanup.annularVolume')}:</span> <span className="font-mono">{result.sweep_pill.annular_volume_bbl} bbl</span></div>
                </div>
              </div>
            )}

            {/* Alerts */}
            {result.alerts?.length > 0 && (
              <div className="glass-panel p-6 rounded-2xl border border-yellow-500/20">
                <h3 className="text-lg font-bold text-yellow-400 mb-3">⚠ {t('common.alerts')}</h3>
                <ul className="space-y-2">
                  {result.alerts.map((alert: string, i: number) => (
                    <li key={i} className="text-sm text-yellow-300 flex items-start gap-2">
                      <span className="mt-1">•</span>{alert}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <FlowRateSensitivity data={sensitivityData} currentFlowRate={params.flow_rate} />
              <AnnularVelocityChart
                actualVelocity={result.summary?.annular_velocity_ftmin || 0}
                minimumVelocity={result.summary?.minimum_flow_rate_gpm ? (24.51 * result.summary.minimum_flow_rate_gpm / (params.hole_id ** 2 - params.pipe_od ** 2)) : 120}
                slipVelocity={result.summary?.slip_velocity_ftmin || 0}
                transportVelocity={result.summary?.transport_velocity_ftmin || 0}
              />
              <CuttingsConcentrationGauge
                concentration={result.summary?.cuttings_concentration_pct || 0}
                hci={result.summary?.hole_cleaning_index || 0}
                ctr={result.summary?.cuttings_transport_ratio || 0}
                cleaningQuality={result.summary?.cleaning_quality || 'Poor'}
              />
              <CleanupEfficiencyProfile
                currentInclination={params.inclination}
                data={(() => {
                  const va = 24.51 * params.flow_rate / (params.hole_id ** 2 - params.pipe_od ** 2);
                  const vs_base = result.summary?.slip_velocity_ftmin || 1;
                  return Array.from({ length: 19 }, (_, i) => {
                    const inc = i * 5; // 0° to 90°
                    // va_min increases with inclination
                    const va_min = inc > 60 ? 150 : inc > 30 ? 130 : 120;
                    const hci = va / va_min;
                    // Slip velocity increases with inclination (bed formation effect)
                    const incRad = (inc * Math.PI) / 180;
                    const slipFactor = 1 + 2.5 * Math.sin(incRad) * Math.cos(incRad) + 1.5 * Math.pow(Math.sin(incRad), 2);
                    const vs_eff = vs_base * slipFactor;
                    const ctr = va > 0 ? Math.max((va - vs_eff) / va, 0) : 0;
                    return {
                      inclination: inc,
                      hci: Math.round(hci * 100) / 100,
                      ctr: Math.round(ctr * 1000) / 1000,
                    };
                  });
                })()}
              />
            </div>

            {/* AI Analysis */}
            <AIAnalysisPanel
              moduleName="Wellbore Cleanup"
              moduleIcon={Droplets}
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
              <Droplets size={48} className="mx-auto mb-4 opacity-30" />
              <p>{t('wellboreCleanup.noResults')}</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default WellboreCleanupModule;
