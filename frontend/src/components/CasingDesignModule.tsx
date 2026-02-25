import { useState, useCallback } from 'react';
import api from '../lib/api';
import { motion, AnimatePresence } from 'framer-motion';
import { Shield, Play, RefreshCw, CheckCircle, XCircle } from 'lucide-react';
import BurstCollapseEnvelope from './charts/csg/BurstCollapseEnvelope';
import TensionProfile from './charts/csg/TensionProfile';
import SafetyFactorTrack from './charts/csg/SafetyFactorTrack';
import BiaxialEllipse from './charts/csg/BiaxialEllipse';
import CasingProgramSchematic from './charts/csg/CasingProgramSchematic';
import GradeSelectionTable from './charts/csg/GradeSelectionTable';
import AIAnalysisPanel from './AIAnalysisPanel';
import { useLanguage } from '../hooks/useLanguage';
import { useAIAnalysis } from '../hooks/useAIAnalysis';
import { useTranslation } from 'react-i18next';
import { useToast } from './ui/Toast';
import type { APIError } from '../types/api';

interface CasingDesignModuleProps {
  wellId?: number;
  wellName?: string;
}

const CasingDesignModule: React.FC<CasingDesignModuleProps> = ({ wellId, wellName = '' }) => {
  const [activeTab, setActiveTab] = useState('input');
  const [loading, setLoading] = useState(false);

  const [params, setParams] = useState({
    casing_od_in: 9.625, casing_id_in: 8.681, wall_thickness_in: 0.472,
    casing_weight_ppf: 47.0, casing_length_ft: 10000,
    tvd_ft: 9500, mud_weight_ppg: 10.5,
    pore_pressure_ppg: 9.0, fracture_gradient_ppg: 16.5,
    gas_gradient_psi_ft: 0.1,
    cement_top_tvd_ft: 5000, cement_density_ppg: 16.0,
    bending_dls: 3.0, overpull_lbs: 50000,
    sf_burst: 1.10, sf_collapse: 1.00, sf_tension: 1.60,
  });

  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const { language } = useLanguage();
  const { t } = useTranslation();
  const { addToast } = useToast();

  const { aiAnalysis, isAnalyzing, runAnalysis, provider, setProvider, availableProviders, setAiAnalysis } = useAIAnalysis({
    module: 'casing-design',
    wellId,
    wellName,
  });

  const updateParam = (key: string, value: string) => {
    setParams(prev => ({ ...prev, [key]: parseFloat(value) || 0 }));
  };

  const calculate = useCallback(async () => {
    setLoading(true);
    try {
      const url = wellId
        ? `/wells/${wellId}/casing-design`
        : `/calculate/casing-design`;
      const res = await api.post(url, params);
      setResult(res.data);
      setActiveTab('results');
    } catch (e: unknown) {
      addToast('Error: ' + ((e as APIError).response?.data?.detail || (e as APIError).message), 'error');
    }
    setLoading(false);
  }, [wellId, params, addToast]);

  const handleRunAnalysis = () => {
    runAnalysis(result || {}, params);
  };

  const tabs = [
    { id: 'input', label: t('common.parameters') },
    { id: 'results', label: t('common.results') },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Shield className="text-indigo-400" size={28} />
        <h2 className="text-2xl font-bold">{t('casingDesign.title')}</h2>
        <span className="text-sm text-gray-500">{t('casingDesign.subtitle')}</span>
      </div>

      <div className="flex gap-2 border-b border-white/10 pb-2">
        {tabs.map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              activeTab === tab.id ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30' : 'text-gray-400 hover:text-gray-200'
            }`}>{tab.label}</button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        {activeTab === 'input' && (
          <motion.div key="input" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="glass-panel p-6 rounded-2xl border border-white/5 space-y-6">
              <div>
                <h3 className="text-lg font-bold mb-3">{t('casingDesign.sections.casing')}</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {[
                    { key: 'casing_od_in', label: 'OD (in)', step: '0.125' },
                    { key: 'casing_id_in', label: 'ID (in)', step: '0.001' },
                    { key: 'wall_thickness_in', label: 'Espesor Pared (in)', step: '0.001' },
                    { key: 'casing_weight_ppf', label: 'Peso (lb/ft)', step: '1' },
                    { key: 'casing_length_ft', label: 'Longitud (ft)', step: '100' },
                    { key: 'tvd_ft', label: 'TVD (ft)', step: '100' },
                    { key: 'bending_dls', label: 'DLS Flexión (°/100ft)', step: '0.5' },
                    { key: 'overpull_lbs', label: 'Overpull (lbs)', step: '5000' },
                  ].map(({ key, label, step }) => (
                    <div key={key} className="space-y-1">
                      <label className="text-xs text-gray-400">{label}</label>
                      <input type="number" step={step} value={(params as Record<string, number>)[key]}
                        onChange={e => updateParam(key, e.target.value)}
                        className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none" />
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <h3 className="text-lg font-bold mb-3">{t('casingDesign.sections.wellConditions')}</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {[
                    { key: 'mud_weight_ppg', label: 'Peso Lodo (ppg)', step: '0.1' },
                    { key: 'pore_pressure_ppg', label: 'P. Poro (ppg)', step: '0.1' },
                    { key: 'fracture_gradient_ppg', label: 'Grad. Fractura (ppg)', step: '0.1' },
                    { key: 'gas_gradient_psi_ft', label: 'Grad. Gas (psi/ft)', step: '0.01' },
                    { key: 'cement_top_tvd_ft', label: 'TOC TVD (ft)', step: '100' },
                    { key: 'cement_density_ppg', label: 'Densidad Cemento (ppg)', step: '0.1' },
                  ].map(({ key, label, step }) => (
                    <div key={key} className="space-y-1">
                      <label className="text-xs text-gray-400">{label}</label>
                      <input type="number" step={step} value={(params as Record<string, number>)[key]}
                        onChange={e => updateParam(key, e.target.value)}
                        className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none" />
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <h3 className="text-lg font-bold mb-3">{t('casingDesign.sections.safetyFactors')}</h3>
                <div className="grid grid-cols-3 gap-4">
                  {[
                    { key: 'sf_burst', label: 'SF Burst', step: '0.05' },
                    { key: 'sf_collapse', label: 'SF Collapse', step: '0.05' },
                    { key: 'sf_tension', label: 'SF Tension', step: '0.1' },
                  ].map(({ key, label, step }) => (
                    <div key={key} className="space-y-1">
                      <label className="text-xs text-gray-400">{label}</label>
                      <input type="number" step={step} value={(params as Record<string, number>)[key]}
                        onChange={e => updateParam(key, e.target.value)}
                        className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none" />
                    </div>
                  ))}
                </div>
              </div>

              <button onClick={calculate} disabled={loading}
                className="mt-4 flex items-center gap-2 px-6 py-3 bg-indigo-600 hover:bg-indigo-700 rounded-lg font-medium transition-colors disabled:opacity-50">
                {loading ? <RefreshCw size={16} className="animate-spin" /> : <Play size={16} />}
                {loading ? t('common.calculating') : t('casingDesign.designCasing')}
              </button>
            </div>
          </motion.div>
        )}

        {activeTab === 'results' && result && (
          <motion.div key="results" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-6">
            {/* Overall Status */}
            <div className={`glass-panel p-5 rounded-2xl border flex items-center gap-4 ${
              result.summary?.overall_status === 'ALL PASS' ? 'border-green-500/30' : 'border-red-500/30'
            }`}>
              {result.summary?.overall_status === 'ALL PASS' ? (
                <CheckCircle size={32} className="text-green-400" />
              ) : (
                <XCircle size={32} className="text-red-400" />
              )}
              <div>
                <div className={`text-xl font-bold ${result.summary?.overall_status === 'ALL PASS' ? 'text-green-400' : 'text-red-400'}`}>
                  {result.summary?.overall_status}
                </div>
                <div className="text-sm text-gray-400">
                  {t('casingDesign.selectedGrade')}: <span className="font-bold text-indigo-400">{result.summary?.selected_grade}</span>
                  {' | '}Triaxial VME: <span className={result.summary?.triaxial_status === 'PASS' ? 'text-green-400' : 'text-red-400'}>{result.summary?.triaxial_status}</span>
                </div>
              </div>
            </div>

            {/* Safety Factor Cards */}
            <div className="grid grid-cols-3 gap-4">
              {['burst', 'collapse', 'tension'].map(criterion => {
                const sf = result.safety_factors?.results?.[criterion];
                if (!sf) return null;
                return (
                  <div key={criterion} className={`glass-panel p-4 rounded-xl border ${sf.passes ? 'border-green-500/20' : 'border-red-500/20'}`}>
                    <div className="text-xs text-gray-500 mb-1 uppercase">{criterion}</div>
                    <div className={`text-2xl font-bold ${sf.passes ? 'text-green-400' : 'text-red-400'}`}>
                      SF = {sf.safety_factor}
                    </div>
                    <div className="text-xs text-gray-500">
                      Load: {sf.load_psi || sf.load_lbs} | Rating: {sf.rating_psi || sf.rating_lbs} | Min: {sf.minimum_sf}
                    </div>
                    <div className={`text-xs mt-1 ${sf.passes ? 'text-green-500' : 'text-red-500'}`}>{sf.status}</div>
                  </div>
                );
              })}
            </div>

            {/* Load Details */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="glass-panel p-6 rounded-2xl border border-white/5">
                <h3 className="text-lg font-bold mb-3">{t('casingDesign.designLoads')}</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between"><span className="text-gray-400">Max Burst:</span><span className="font-mono">{result.summary?.max_burst_load_psi} psi @ {result.burst_load?.max_burst_depth_ft} ft</span></div>
                  <div className="flex justify-between"><span className="text-gray-400">Max Collapse:</span><span className="font-mono">{result.summary?.max_collapse_load_psi} psi @ {result.collapse_load?.max_collapse_depth_ft} ft</span></div>
                  <div className="flex justify-between"><span className="text-gray-400">Tensión Total:</span><span className="font-mono">{result.summary?.total_tension_lbs?.toLocaleString()} lbs</span></div>
                  <div className="flex justify-between"><span className="text-gray-400">Collapse Zone:</span><span className="font-mono text-indigo-400">{result.summary?.collapse_zone}</span></div>
                </div>
              </div>
              <div className="glass-panel p-6 rounded-2xl border border-white/5">
                <h3 className="text-lg font-bold mb-3">{t('casingDesign.tensionComponents')}</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between"><span className="text-gray-400">Peso Aire:</span><span className="font-mono">{result.tension_load?.air_weight_lbs?.toLocaleString()} lbs</span></div>
                  <div className="flex justify-between"><span className="text-gray-400">BF:</span><span className="font-mono">{result.tension_load?.buoyancy_factor}</span></div>
                  <div className="flex justify-between"><span className="text-gray-400">Peso Flotado:</span><span className="font-mono">{result.tension_load?.buoyant_weight_lbs?.toLocaleString()} lbs</span></div>
                  <div className="flex justify-between"><span className="text-gray-400">Shock Load:</span><span className="font-mono">{result.tension_load?.shock_load_lbs?.toLocaleString()} lbs</span></div>
                  <div className="flex justify-between"><span className="text-gray-400">Bending:</span><span className="font-mono">{result.tension_load?.bending_load_lbs?.toLocaleString()} lbs</span></div>
                  <div className="flex justify-between"><span className="text-gray-400">Overpull:</span><span className="font-mono">{result.tension_load?.overpull_lbs?.toLocaleString()} lbs</span></div>
                </div>
              </div>
            </div>

            {/* Biaxial & Triaxial */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="glass-panel p-6 rounded-2xl border border-white/5">
                <h3 className="text-lg font-bold mb-3">{t('casingDesign.biaxialCorrection')}</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between"><span className="text-gray-400">Collapse Original:</span><span className="font-mono">{result.biaxial_correction?.original_collapse_psi} psi</span></div>
                  <div className="flex justify-between"><span className="text-gray-400">Collapse Corregido:</span><span className="font-mono text-yellow-400">{result.biaxial_correction?.corrected_collapse_psi} psi</span></div>
                  <div className="flex justify-between"><span className="text-gray-400">Factor Reducción:</span><span className="font-mono">{result.biaxial_correction?.reduction_factor}</span></div>
                </div>
              </div>
              <div className="glass-panel p-6 rounded-2xl border border-white/5">
                <h3 className="text-lg font-bold mb-3">{t('casingDesign.triaxialTitle')}</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between"><span className="text-gray-400">VME Stress:</span><span className="font-mono">{result.triaxial_vme?.vme_stress_psi} psi</span></div>
                  <div className="flex justify-between"><span className="text-gray-400">Admisible:</span><span className="font-mono">{result.triaxial_vme?.allowable_psi} psi</span></div>
                  <div className="flex justify-between"><span className="text-gray-400">Utilización:</span><span className={`font-mono font-bold ${result.triaxial_vme?.utilization_pct > 90 ? 'text-red-400' : 'text-green-400'}`}>{result.triaxial_vme?.utilization_pct}%</span></div>
                  <div className="flex justify-between"><span className="text-gray-400">Status:</span><span className={`font-mono font-bold ${result.triaxial_vme?.status === 'PASS' ? 'text-green-400' : 'text-red-400'}`}>{result.triaxial_vme?.status}</span></div>
                </div>
              </div>
            </div>

            {/* Alerts */}
            {result.summary?.alerts?.length > 0 && (
              <div className="glass-panel p-6 rounded-2xl border border-red-500/20">
                <h3 className="text-lg font-bold text-red-400 mb-3">&#9888; {t('casingDesign.designAlerts')}</h3>
                <ul className="space-y-2">
                  {result.summary.alerts.map((alert: string, i: number) => (
                    <li key={i} className="text-sm text-red-300 flex items-start gap-2">
                      <span className="mt-1">&bull;</span>{alert}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <BurstCollapseEnvelope burstLoad={result.burst_load} collapseLoad={result.collapse_load}
                burstRating={result.burst_rating?.burst_rating_psi} collapseRating={result.biaxial_correction?.corrected_collapse_psi} />
              <SafetyFactorTrack safetyFactors={result.safety_factors} />
              <TensionProfile tensionLoad={result.tension_load} />
              <BiaxialEllipse biaxial={result.biaxial_correction} />
              <CasingProgramSchematic summary={result.summary} params={params} />
              <GradeSelectionTable gradeSelection={result.grade_selection} />
            </div>

            {/* AI Analysis */}
            <AIAnalysisPanel
              moduleName="Casing Design"
              moduleIcon={Shield}
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
              <Shield size={48} className="mx-auto mb-4 opacity-30" />
              <p>{t('casingDesign.noResults')}</p>
            </div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default CasingDesignModule;
