import { useState, useEffect } from 'react';
import api from '../lib/api';
import { motion, AnimatePresence } from 'framer-motion';
import { Anchor, Play, RefreshCw } from 'lucide-react';
import ForceComponentsBar from './charts/pf/ForceComponentsBar';
import TubingMovementDiagram from './charts/pf/TubingMovementDiagram';
import PackerForceGaugeComponent from './charts/pf/PackerForceGauge';
import SensitivityHeatmap from './charts/pf/SensitivityHeatmap';
import AIAnalysisPanel from './AIAnalysisPanel';
import { useLanguage } from '../hooks/useLanguage';
import { useTranslation } from 'react-i18next';
import { useToast } from './ui/Toast';
import type { Provider, ProviderOption } from '../types/ai';
import type { AIAnalysisResponse, APIError } from '../types/api';

interface PackerForcesModuleProps {
  wellId?: number;
  wellName?: string;
}

const PackerForcesModule: React.FC<PackerForcesModuleProps> = ({ wellId, wellName = '' }) => {
  const [activeTab, setActiveTab] = useState('input');
  const [loading, setLoading] = useState(false);

  const [params, setParams] = useState({
    tubing_od: 2.875,
    tubing_id: 2.441,
    tubing_weight: 6.5,
    tubing_length: 10000,
    seal_bore_id: 3.25,
    initial_tubing_pressure: 0,
    final_tubing_pressure: 3000,
    initial_annulus_pressure: 0,
    final_annulus_pressure: 0,
    initial_temperature: 80,
    final_temperature: 250,
    packer_depth_tvd: 10000,
    mud_weight_tubing: 8.34,
    mud_weight_annulus: 8.34,
    poisson_ratio: 0.30,
    thermal_expansion: 6.9e-6,
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
    setParams(prev => ({ ...prev, [key]: parseFloat(value) || 0 }));
  };

  const calculate = async () => {
    setLoading(true);
    try {
      const url = wellId
        ? `/wells/${wellId}/packer-forces`
        : `/calculate/packer-forces`;
      const res = await api.post(url, params);
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
        ? `/wells/${wellId}/packer-forces/analyze`
        : `/analyze/module`;
      const analyzeBody = wellId
        ? { result_data: result, params, language, provider }
        : { module: 'packer-forces', well_name: wellName || 'General Analysis', result_data: result, params, language, provider };
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

  // Generate sensitivity data for heatmap
  const sensitivityData = result ? (() => {
    const data: { deltaP: number; deltaT: number; totalForce: number }[] = [];
    const pressures = [0, 1000, 2000, 3000, 5000];
    const temps = [0, 50, 100, 170, 250];
    // Simple linear approximation from the result
    const fc = result.force_components || {};
    const baseDP = params.final_tubing_pressure - params.initial_tubing_pressure;
    const baseDT = params.final_temperature - params.initial_temperature;
    for (const dp of pressures) {
      for (const dt of temps) {
        const pScale = baseDP > 0 ? dp / baseDP : 0;
        const tScale = baseDT > 0 ? dt / baseDT : 0;
        const approxForce = Math.round((fc.piston || 0) * pScale + (fc.ballooning || 0) * pScale + (fc.temperature || 0) * tScale);
        data.push({ deltaP: dp, deltaT: dt, totalForce: approxForce });
      }
    }
    return data;
  })() : [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Anchor className="text-purple-400" size={28} />
        <h2 className="text-2xl font-bold">{t('packerForces.title')}</h2>
        <span className="text-sm text-gray-500">{t('packerForces.subtitle')}</span>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-white/10 pb-2">
        {tabs.map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              activeTab === tab.id ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30' : 'text-gray-400 hover:text-gray-200'
            }`}>{tab.label}</button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        {/* INPUT TAB */}
        {activeTab === 'input' && (
          <motion.div key="input" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="glass-panel p-6 rounded-2xl border border-white/5 space-y-6">
              {/* Tubing Properties */}
              <div>
                <h3 className="text-md font-bold mb-3 text-purple-400">{t('packerForces.sections.tubing')}</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {[
                    { key: 'tubing_od', label: t('packerForces.tubingOD'), step: '0.125' },
                    { key: 'tubing_id', label: t('packerForces.tubingID'), step: '0.125' },
                    { key: 'tubing_weight', label: t('packerForces.tubingWeight'), step: '0.1' },
                    { key: 'tubing_length', label: t('packerForces.tubingLength'), step: '100' },
                    { key: 'seal_bore_id', label: 'ID Bore Seal (in)', step: '0.125' },
                    { key: 'packer_depth_tvd', label: t('packerForces.packerDepth'), step: '100' },
                    { key: 'mud_weight_tubing', label: 'MW Tubing (ppg)', step: '0.1' },
                    { key: 'mud_weight_annulus', label: 'MW Annulus (ppg)', step: '0.1' },
                  ].map(({ key, label, step }) => (
                    <div key={key} className="space-y-1">
                      <label className="text-xs text-gray-400">{label}</label>
                      <input type="number" step={step}
                        value={(params as Record<string, unknown>)[key]}
                        onChange={e => updateParam(key, e.target.value)}
                        className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:border-purple-500 focus:outline-none"
                      />
                    </div>
                  ))}
                </div>
              </div>

              {/* Pressure Conditions */}
              <div>
                <h3 className="text-md font-bold mb-3 text-blue-400">{t('packerForces.sections.pressure')}</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {[
                    { key: 'initial_tubing_pressure', label: t('packerForces.tubingPressInit') },
                    { key: 'final_tubing_pressure', label: t('packerForces.tubingPressFinal') },
                    { key: 'initial_annulus_pressure', label: t('packerForces.annPressInit') },
                    { key: 'final_annulus_pressure', label: t('packerForces.annPressFinal') },
                  ].map(({ key, label }) => (
                    <div key={key} className="space-y-1">
                      <label className="text-xs text-gray-400">{label}</label>
                      <input type="number" step="100"
                        value={(params as Record<string, unknown>)[key]}
                        onChange={e => updateParam(key, e.target.value)}
                        className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                      />
                    </div>
                  ))}
                </div>
              </div>

              {/* Temperature */}
              <div>
                <h3 className="text-md font-bold mb-3 text-amber-400">{t('packerForces.sections.temperature')}</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {[
                    { key: 'initial_temperature', label: t('packerForces.tempSurfInit') },
                    { key: 'final_temperature', label: t('packerForces.tempBotFinal') },
                    { key: 'poisson_ratio', label: 'Poisson Ratio', step: '0.01' },
                    { key: 'thermal_expansion', label: 'Thermal Coeff. (1/°F)', step: '0.0000001' },
                  ].map(({ key, label, step }) => (
                    <div key={key} className="space-y-1">
                      <label className="text-xs text-gray-400">{label}</label>
                      <input type="number" step={step || '1'}
                        value={(params as Record<string, unknown>)[key]}
                        onChange={e => updateParam(key, e.target.value)}
                        className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:border-amber-500 focus:outline-none"
                      />
                    </div>
                  ))}
                </div>
              </div>

              <button onClick={calculate} disabled={loading}
                className="flex items-center gap-2 px-6 py-3 bg-purple-600 hover:bg-purple-700 rounded-lg font-medium transition-colors disabled:opacity-50">
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
              <div className="glass-panel p-4 rounded-xl border border-white/5 text-center">
                <div className="text-xs text-gray-500 mb-1">{t('packerForces.totalForce')}</div>
                <div className={`text-xl font-bold ${result.summary?.force_direction === 'Tension' ? 'text-green-400' : 'text-red-400'}`}>
                  {Math.abs(result.summary?.total_force_lbs || 0).toLocaleString()} lbs
                </div>
                <div className="text-xs text-gray-500">{result.summary?.force_direction}</div>
              </div>
              <div className="glass-panel p-4 rounded-xl border border-white/5 text-center">
                <div className="text-xs text-gray-500 mb-1">{t('packerForces.totalMovement')}</div>
                <div className="text-xl font-bold text-blue-400">{result.summary?.total_movement_inches} in</div>
              </div>
              <div className="glass-panel p-4 rounded-xl border border-white/5 text-center">
                <div className="text-xs text-gray-500 mb-1">{t('packerForces.bucklingStatus')}</div>
                <div className={`text-xl font-bold ${result.summary?.buckling_status === 'OK' ? 'text-green-400' : 'text-red-400'}`}>
                  {result.summary?.buckling_status}
                </div>
              </div>
              <div className="glass-panel p-4 rounded-xl border border-white/5 text-center">
                <div className="text-xs text-gray-500 mb-1">{t('packerForces.forceBreakdown')}</div>
                <div className="text-xl font-bold text-amber-400">{(result.summary?.buckling_critical_load_lbs || 0).toLocaleString()} lbs</div>
              </div>
            </div>

            {/* Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {result.force_components && (
                <ForceComponentsBar forces={result.force_components} />
              )}
              {result.movements && (
                <TubingMovementDiagram movements={result.movements} />
              )}
              {result.summary && (
                <PackerForceGaugeComponent
                  totalForce={result.summary.total_force_lbs}
                  bucklingCritical={result.summary.buckling_critical_load_lbs}
                  bucklingStatus={result.summary.buckling_status}
                  forceDirection={result.summary.force_direction}
                />
              )}
              {sensitivityData.length > 0 && (
                <SensitivityHeatmap data={sensitivityData} />
              )}
            </div>

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

            {/* AI Analysis */}
            <AIAnalysisPanel
              moduleName="Packer Forces"
              moduleIcon={Anchor}
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
              <Anchor size={48} className="mx-auto mb-4 opacity-30" />
              <p>{t('packerForces.noResults')}</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default PackerForcesModule;
