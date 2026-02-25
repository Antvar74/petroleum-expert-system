import { useState, useEffect } from 'react';
import api from '../lib/api';
import { motion, AnimatePresence } from 'framer-motion';
import { Vibrate, Play, RefreshCw } from 'lucide-react';
import StabilityGauge from './charts/vb/StabilityGauge';
import VibrationMapHeatmap from './charts/vb/VibrationMapHeatmap';
import CriticalRPMChart from './charts/vb/CriticalRPMChart';
import MSEBreakdownChart from './charts/vb/MSEBreakdownChart';
import StickSlipIndicator from './charts/vb/StickSlipIndicator';
import AIAnalysisPanel from './AIAnalysisPanel';
import { useLanguage } from '../hooks/useLanguage';
import { useTranslation } from 'react-i18next';
import { useToast } from './ui/Toast';
import type { Provider, ProviderOption } from '../types/ai';
import type { AIAnalysisResponse, APIError } from '../types/api';

interface VibrationsModuleProps {
  wellId?: number;
  wellName?: string;
}

const VibrationsModule: React.FC<VibrationsModuleProps> = ({ wellId, wellName = '' }) => {
  const [activeTab, setActiveTab] = useState('input');
  const [loading, setLoading] = useState(false);

  const [params, setParams] = useState({
    wob_klb: 20,
    rpm: 120,
    rop_fph: 60,
    torque_ftlb: 12000,
    bit_diameter_in: 8.5,
    dp_od_in: 5.0,
    dp_id_in: 4.276,
    dp_weight_lbft: 19.5,
    bha_length_ft: 300,
    bha_od_in: 6.75,
    bha_id_in: 2.813,
    bha_weight_lbft: 83.0,
    mud_weight_ppg: 10.0,
    hole_diameter_in: 8.5,
    inclination_deg: 15,
    friction_factor: 0.25,
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
        ? `/wells/${wellId}/vibrations`
        : `/calculate/vibrations`;
      const res = await api.post(url, params);
      setResult(res.data);
      setActiveTab('results');
    } catch (e: unknown) {
      addToast('Error: ' + ((e as APIError).response?.data?.detail || (e as APIError).message), 'error');
    }
    setLoading(false);
  };

  const runAIAnalysis = async () => {
    if (!result) return;
    setIsAnalyzing(true);
    try {
      const analyzeUrl = wellId
        ? `/wells/${wellId}/vibrations/analyze`
        : `/analyze/module`;
      const analyzeBody = {
        ...(wellId ? {} : { module: 'vibrations', well_name: wellName || 'General Analysis' }),
        result_data: result, params, language, provider,
      };
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

  const statusColor = (s: string) => {
    if (s === 'Stable') return 'text-green-400 bg-green-500/10';
    if (s === 'Marginal') return 'text-yellow-400 bg-yellow-500/10';
    if (s === 'Unstable') return 'text-orange-400 bg-orange-500/10';
    return 'text-red-400 bg-red-500/10';
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Vibrate className="text-rose-400" size={28} />
        <h2 className="text-2xl font-bold">{t('vibrations.title')}</h2>
        <span className="text-sm text-gray-500">{t('vibrations.subtitle')}</span>
      </div>

      <div className="flex gap-2 border-b border-white/10 pb-2">
        {tabs.map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              activeTab === tab.id ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30' : 'text-gray-400 hover:text-gray-200'
            }`}>{tab.label}</button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        {activeTab === 'input' && (
          <motion.div key="input" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="glass-panel p-6 rounded-2xl border border-white/5 space-y-6">
              {/* Operating Parameters */}
              <div>
                <h3 className="text-lg font-bold mb-3">{t('vibrations.sections.operating')}</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {[
                    { key: 'wob_klb', label: t('vibrations.wob'), step: '1' },
                    { key: 'rpm', label: t('vibrations.rpm'), step: '5' },
                    { key: 'rop_fph', label: t('vibrations.rop'), step: '5' },
                    { key: 'torque_ftlb', label: t('vibrations.torque'), step: '500' },
                    { key: 'bit_diameter_in', label: t('vibrations.bitDiameter'), step: '0.125' },
                    { key: 'mud_weight_ppg', label: t('vibrations.mudWeight'), step: '0.5' },
                    { key: 'hole_diameter_in', label: t('vibrations.holeDiameter'), step: '0.125' },
                    { key: 'inclination_deg', label: t('vibrations.inclination'), step: '5' },
                    { key: 'friction_factor', label: t('vibrations.frictionCoeff'), step: '0.05' },
                  ].map(({ key, label, step }) => (
                    <div key={key} className="space-y-1">
                      <label className="text-xs text-gray-400">{label}</label>
                      <input type="number" step={step}
                        value={(params as Record<string, number>)[key]}
                        onChange={e => updateParam(key, e.target.value)}
                        className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:border-rose-500 focus:outline-none"
                      />
                    </div>
                  ))}
                </div>
              </div>

              {/* BHA Configuration */}
              <div>
                <h3 className="text-lg font-bold mb-3">{t('vibrations.sections.bha')}</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {[
                    { key: 'bha_length_ft', label: t('vibrations.bhaLength'), step: '50' },
                    { key: 'bha_od_in', label: t('vibrations.bhaOD'), step: '0.25' },
                    { key: 'bha_id_in', label: t('vibrations.bhaID'), step: '0.125' },
                    { key: 'bha_weight_lbft', label: t('vibrations.bhaWeight'), step: '5' },
                    { key: 'dp_od_in', label: t('vibrations.dpOD'), step: '0.125' },
                    { key: 'dp_id_in', label: t('vibrations.dpID'), step: '0.125' },
                    { key: 'dp_weight_lbft', label: t('vibrations.dpWeight'), step: '1' },
                  ].map(({ key, label, step }) => (
                    <div key={key} className="space-y-1">
                      <label className="text-xs text-gray-400">{label}</label>
                      <input type="number" step={step}
                        value={(params as Record<string, number>)[key]}
                        onChange={e => updateParam(key, e.target.value)}
                        className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:border-rose-500 focus:outline-none"
                      />
                    </div>
                  ))}
                </div>
              </div>

              <button onClick={calculate} disabled={loading}
                className="mt-4 flex items-center gap-2 px-6 py-3 bg-rose-600 hover:bg-rose-700 rounded-lg font-medium transition-colors disabled:opacity-50">
                {loading ? <RefreshCw size={16} className="animate-spin" /> : <Play size={16} />}
                {loading ? t('shotEfficiency.analyzing') : t('vibrations.analyzeVibrations')}
              </button>
            </div>
          </motion.div>
        )}

        {activeTab === 'results' && result && (
          <motion.div key="results" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-6">
            {/* Summary Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { label: t('vibrations.stability'), value: `${result.summary?.stability_index?.toFixed(0)}/100`, color: statusColor(result.summary?.stability_status || '') },
                { label: t('vibrations.criticalRpmAxial'), value: `${result.summary?.critical_rpm_axial?.toFixed(0)}`, color: 'text-blue-400' },
                { label: t('vibrations.criticalRpmLateral'), value: `${result.summary?.critical_rpm_lateral?.toFixed(0)}`, color: 'text-cyan-400' },
                { label: 'Stick-Slip', value: `${result.summary?.stick_slip_severity?.toFixed(2)} (${result.summary?.stick_slip_class})`, color: statusColor(result.summary?.stick_slip_class === 'Mild' ? 'Stable' : result.summary?.stick_slip_class === 'Moderate' ? 'Marginal' : 'Critical') },
              ].map((item, i) => (
                <div key={i} className="glass-panel p-4 rounded-xl border border-white/5 text-center">
                  <div className="text-xs text-gray-500 mb-1">{item.label}</div>
                  <div className={`text-lg font-bold ${item.color}`}>{item.value}</div>
                </div>
              ))}
            </div>

            {/* MSE & Optimal Point */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="glass-panel p-6 rounded-2xl border border-white/5">
                <h3 className="text-lg font-bold mb-3">{t('vibrations.mseTitle')}</h3>
                <div className="space-y-2 text-sm">
                  <div><span className="text-gray-400">MSE Total:</span> <span className="font-bold text-lg">{result.mse?.mse_total_psi?.toLocaleString()} psi</span></div>
                  <div><span className="text-gray-400">Rotario:</span> <span className="font-mono">{result.mse?.mse_rotary_psi?.toLocaleString()} psi ({result.mse?.rotary_pct}%)</span></div>
                  <div><span className="text-gray-400">Empuje:</span> <span className="font-mono">{result.mse?.mse_thrust_psi?.toLocaleString()} psi ({result.mse?.thrust_pct}%)</span></div>
                  <div><span className="text-gray-400">Eficiencia:</span> <span className="font-mono">{result.mse?.efficiency_pct}%</span></div>
                  <div>
                    <span className="text-gray-400">Estado:</span>{' '}
                    <span className={`px-2 py-0.5 rounded text-xs font-bold ${statusColor(result.mse?.classification === 'Efficient' ? 'Stable' : result.mse?.classification === 'Normal' ? 'Marginal' : 'Critical')}`}>
                      {result.mse?.classification}
                    </span>
                  </div>
                  {result.mse?.is_founder_point && (
                    <div className="text-red-400 text-xs font-bold mt-2">&#9888; Founder Point Detected!</div>
                  )}
                </div>
              </div>
              <div className="glass-panel p-6 rounded-2xl border border-white/5">
                <h3 className="text-lg font-bold mb-3">{t('vibrations.optimalPoint')}</h3>
                <div className="space-y-2 text-sm">
                  <div><span className="text-gray-400">WOB Óptimo:</span> <span className="font-bold text-rose-400">{result.summary?.optimal_wob} klb</span></div>
                  <div><span className="text-gray-400">RPM Óptimo:</span> <span className="font-bold text-rose-400">{result.summary?.optimal_rpm} RPM</span></div>
                  <div><span className="text-gray-400">MSE:</span> <span className="font-mono">{result.summary?.mse_psi?.toLocaleString()} psi</span></div>
                  <div className="pt-3 border-t border-white/5">
                    <h4 className="text-gray-400 text-xs mb-2">Scores por Modo:</h4>
                    <div className="grid grid-cols-2 gap-1">
                      {result.stability?.mode_scores && Object.entries(result.stability.mode_scores).map(([k, v]: [string, any]) => (
                        <div key={k} className="flex justify-between text-xs">
                          <span className="text-gray-500 capitalize">{k}:</span>
                          <span className={v >= 70 ? 'text-green-400' : v >= 40 ? 'text-yellow-400' : 'text-red-400'}>{v.toFixed(0)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Stick-Slip Detail */}
            <div className="glass-panel p-6 rounded-2xl border border-white/5">
              <h3 className="text-lg font-bold mb-3">{t('vibrations.stickSlipAnalysis')}</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div><span className="text-gray-400">{t('vibrations.severity')}:</span> <span className="font-mono">{result.stick_slip?.severity_index}</span></div>
                <div><span className="text-gray-400">{t('vibrations.rpmMinBit')}:</span> <span className="font-mono">{result.stick_slip?.rpm_min_at_bit}</span></div>
                <div><span className="text-gray-400">{t('vibrations.rpmMaxBit')}:</span> <span className="font-mono">{result.stick_slip?.rpm_max_at_bit}</span></div>
                <div><span className="text-gray-400">{t('vibrations.frictionTorque')}:</span> <span className="font-mono">{result.stick_slip?.friction_torque_ftlb?.toLocaleString()} ft-lb</span></div>
              </div>
              {result.stick_slip?.recommendation && (
                <p className="text-xs text-gray-400 mt-3 italic">{result.stick_slip.recommendation}</p>
              )}
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
              <StabilityGauge stability={result.stability} />
              <CriticalRPMChart axial={result.axial_vibrations} lateral={result.lateral_vibrations} operatingRpm={params.rpm} />
              <VibrationMapHeatmap vibrationMap={result.vibration_map} />
              <MSEBreakdownChart mse={result.mse} />
              <StickSlipIndicator stickSlip={result.stick_slip} />
            </div>

            {/* AI Analysis */}
            <AIAnalysisPanel
              moduleName="Vibrations & Stability"
              moduleIcon={Vibrate}
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
              <Vibrate size={48} className="mx-auto mb-4 opacity-30" />
              <p>{t('vibrations.noResults')}</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default VibrationsModule;
