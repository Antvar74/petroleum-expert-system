import { useState, useEffect } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { Layers, Play, RefreshCw } from 'lucide-react';
import { API_BASE_URL } from '../config';
import PenetrationDepthChart from './charts/cd/PenetrationDepthChart';
import ProductivityRatioGauge from './charts/cd/ProductivityRatioGauge';
import FractureGradientProfile from './charts/cd/FractureGradientProfile';
import PhasingPolarChart from './charts/cd/PhasingPolarChart';
import UnderbalanceWindowChart from './charts/cd/UnderbalanceWindowChart';
import AIAnalysisPanel from './AIAnalysisPanel';
import { useLanguage } from '../hooks/useLanguage';
import { useTranslation } from 'react-i18next';
import { useToast } from './ui/Toast';
import type { Provider, ProviderOption } from '../types/ai';

interface CompletionDesignModuleProps {
  wellId?: number;
  wellName?: string;
}

const CompletionDesignModule: React.FC<CompletionDesignModuleProps> = ({ wellId, wellName = '' }) => {
  const [activeTab, setActiveTab] = useState('input');
  const [loading, setLoading] = useState(false);

  const [params, setParams] = useState({
    casing_id_in: 6.276,
    formation_permeability_md: 100,
    formation_thickness_ft: 30,
    reservoir_pressure_psi: 5000,
    wellbore_pressure_psi: 4500,
    depth_tvd_ft: 10000,
    overburden_stress_psi: 10000,
    pore_pressure_psi: 4700,
    sigma_min_psi: 6500,
    sigma_max_psi: 8000,
    tensile_strength_psi: 500,
    poisson_ratio: 0.25,
    penetration_berea_in: 12.0,
    effective_stress_psi: 3000,
    temperature_f: 200,
    completion_fluid: 'brine',
    wellbore_radius_ft: 0.354,
    kv_kh_ratio: 0.5,
    tubing_od_in: 0,
    damage_radius_ft: 0.5,
    damage_permeability_md: 50,
    formation_type: 'sandstone',
  });

  const [result, setResult] = useState<any>(null);
  const [aiAnalysis, setAiAnalysis] = useState<any>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const { language } = useLanguage();
  const { t } = useTranslation();
  const { addToast } = useToast();
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
      const url = wellId
        ? `${API_BASE_URL}/wells/${wellId}/completion-design`
        : `${API_BASE_URL}/calculate/completion-design`;
      const res = await axios.post(url, params);
      setResult(res.data);
      setActiveTab('results');
    } catch (e: any) {
      addToast('Error: ' + (e.response?.data?.detail || e.message), 'error');
    }
    setLoading(false);
  };

  const runAIAnalysis = async () => {
    if (!result) return;
    setIsAnalyzing(true);
    try {
      const analyzeUrl = wellId
        ? `${API_BASE_URL}/wells/${wellId}/completion-design/analyze`
        : `${API_BASE_URL}/analyze/module`;
      const analyzeBody = wellId
        ? { result_data: result, params, language, provider }
        : { module: 'completion-design', well_name: wellName || 'General Analysis', result_data: result, params, language, provider };
      const res = await axios.post(analyzeUrl, analyzeBody);
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
    if (q === 'Excellent') return 'text-green-400 bg-green-500/10';
    if (q === 'Good') return 'text-cyan-400 bg-cyan-500/10';
    if (q === 'Fair') return 'text-yellow-400 bg-yellow-500/10';
    return 'text-red-400 bg-red-500/10';
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Layers className="text-violet-400" size={28} />
        <h2 className="text-2xl font-bold">{t('completionDesign.title')}</h2>
        <span className="text-sm text-gray-500">{t('completionDesign.subtitle')}</span>
      </div>

      <div className="flex gap-2 border-b border-white/10 pb-2">
        {tabs.map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              activeTab === tab.id ? 'bg-violet-500/20 text-violet-400 border border-violet-500/30' : 'text-gray-400 hover:text-gray-200'
            }`}>{tab.label}</button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        {activeTab === 'input' && (
          <motion.div key="input" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="glass-panel p-6 rounded-2xl border border-white/5 space-y-6">
              {/* Casing & Formation */}
              <div>
                <h3 className="text-lg font-bold mb-3">{t('completionDesign.sections.casingFormation')}</h3>
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                  {[
                    { key: 'casing_id_in', label: 'ID Casing (in)', step: '0.125' },
                    { key: 'formation_permeability_md', label: 'Permeabilidad (mD)', step: '10' },
                    { key: 'formation_thickness_ft', label: 'Espesor Neto (ft)', step: '5' },
                    { key: 'depth_tvd_ft', label: 'TVD (ft)', step: '500' },
                    { key: 'wellbore_radius_ft', label: 'Radio Pozo (ft)', step: '0.01' },
                    { key: 'kv_kh_ratio', label: 'Kv/Kh', step: '0.1' },
                    { key: 'tubing_od_in', label: 'OD Tubing (in, 0=casing)', step: '0.125' },
                    { key: 'temperature_f', label: 'BHT (°F)', step: '10' },
                  ].map(({ key, label, step }) => (
                    <div key={key} className="space-y-1">
                      <label className="text-xs text-gray-400">{label}</label>
                      <input type="number" step={step}
                        value={(params as any)[key]}
                        onChange={e => updateParam(key, e.target.value)}
                        className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:border-violet-500 focus:outline-none"
                      />
                    </div>
                  ))}
                  <div className="space-y-1">
                    <label className="text-xs text-gray-400">Tipo Formación</label>
                    <select value={params.formation_type}
                      onChange={e => setParams(prev => ({ ...prev, formation_type: e.target.value }))}
                      className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:border-violet-500 focus:outline-none">
                      <option value="sandstone">Arenisca</option>
                      <option value="carbonate">Carbonato</option>
                      <option value="shale">Lutita</option>
                    </select>
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs text-gray-400">Fluido Completación</label>
                    <select value={params.completion_fluid}
                      onChange={e => setParams(prev => ({ ...prev, completion_fluid: e.target.value }))}
                      className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:border-violet-500 focus:outline-none">
                      <option value="brine">Salmuera</option>
                      <option value="acid">Ácido</option>
                      <option value="oil_based">Base Aceite</option>
                      <option value="completion">Completación</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* Pressures & Stresses */}
              <div>
                <h3 className="text-lg font-bold mb-3">{t('completionDesign.sections.pressuresStresses')}</h3>
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                  {[
                    { key: 'reservoir_pressure_psi', label: 'P Reservorio (psi)', step: '100' },
                    { key: 'wellbore_pressure_psi', label: 'P Pozo (psi)', step: '100' },
                    { key: 'pore_pressure_psi', label: 'P Poro (psi)', step: '100' },
                    { key: 'overburden_stress_psi', label: 'Sobrecarga (psi)', step: '500' },
                    { key: 'sigma_min_psi', label: 'σ_min (psi)', step: '100' },
                    { key: 'sigma_max_psi', label: 'σ_max (psi)', step: '100' },
                    { key: 'tensile_strength_psi', label: 'T. Tensión (psi)', step: '50' },
                    { key: 'poisson_ratio', label: 'Ratio Poisson', step: '0.01' },
                  ].map(({ key, label, step }) => (
                    <div key={key} className="space-y-1">
                      <label className="text-xs text-gray-400">{label}</label>
                      <input type="number" step={step}
                        value={(params as any)[key]}
                        onChange={e => updateParam(key, e.target.value)}
                        className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:border-violet-500 focus:outline-none"
                      />
                    </div>
                  ))}
                </div>
              </div>

              {/* Perforation & Damage */}
              <div>
                <h3 className="text-lg font-bold mb-3">{t('completionDesign.sections.perforationDamage')}</h3>
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                  {[
                    { key: 'penetration_berea_in', label: 'Penetración Berea (in)', step: '1' },
                    { key: 'effective_stress_psi', label: 'Esfuerzo Efectivo (psi)', step: '500' },
                    { key: 'damage_radius_ft', label: 'Radio Daño (ft)', step: '0.1' },
                    { key: 'damage_permeability_md', label: 'Perm. Daño (mD)', step: '10' },
                  ].map(({ key, label, step }) => (
                    <div key={key} className="space-y-1">
                      <label className="text-xs text-gray-400">{label}</label>
                      <input type="number" step={step}
                        value={(params as any)[key]}
                        onChange={e => updateParam(key, e.target.value)}
                        className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:border-violet-500 focus:outline-none"
                      />
                    </div>
                  ))}
                </div>
              </div>

              <button onClick={calculate} disabled={loading}
                className="mt-4 flex items-center gap-2 px-6 py-3 bg-violet-600 hover:bg-violet-700 rounded-lg font-medium transition-colors disabled:opacity-50">
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
                { label: 'Productividad', value: `${(result.summary?.productivity_ratio * 100)?.toFixed(1)}%`, color: qualityColor(result.optimization?.optimal_configuration?.quality || '') },
                { label: 'Penetración', value: `${result.summary?.penetration_corrected_in}" (${result.summary?.penetration_efficiency_pct}%)`, color: result.summary?.penetration_efficiency_pct > 80 ? 'text-green-400' : 'text-yellow-400' },
                { label: 'Óptimo SPF/Fase', value: `${result.summary?.optimal_spf} SPF @ ${result.summary?.optimal_phasing_deg}°`, color: 'text-violet-400' },
                { label: 'Frac Gradient', value: `${result.summary?.fracture_gradient_ppg} ppg`, color: 'text-cyan-400' },
              ].map((item, i) => (
                <div key={i} className="glass-panel p-4 rounded-xl border border-white/5 text-center">
                  <div className="text-xs text-gray-500 mb-1">{item.label}</div>
                  <div className={`text-lg font-bold ${item.color}`}>{item.value}</div>
                </div>
              ))}
            </div>

            {/* Penetration & Gun Selection */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="glass-panel p-6 rounded-2xl border border-white/5">
                <h3 className="text-lg font-bold mb-3">{t('completionDesign.penetration')}</h3>
                <div className="space-y-2 text-sm">
                  <div><span className="text-gray-400">Berea:</span> <span className="font-mono">{result.penetration?.penetration_berea_in}"</span></div>
                  <div><span className="text-gray-400">Corregida:</span> <span className="font-bold text-violet-400">{result.penetration?.penetration_corrected_in}"</span></div>
                  <div><span className="text-gray-400">Eficiencia:</span> <span className="font-mono">{result.penetration?.efficiency_pct}%</span></div>
                  <div className="pt-2 border-t border-white/5 text-xs text-gray-500">
                    CF: Stress {result.penetration?.correction_factors?.cf_stress} | Temp {result.penetration?.correction_factors?.cf_temperature} | Fluid {result.penetration?.correction_factors?.cf_fluid} | Cement {result.penetration?.correction_factors?.cf_cement} | Casing {result.penetration?.correction_factors?.cf_casing}
                  </div>
                </div>
              </div>
              <div className="glass-panel p-6 rounded-2xl border border-white/5">
                <h3 className="text-lg font-bold mb-3">{t('completionDesign.gunSelection')}</h3>
                <div className="space-y-2 text-sm">
                  {result.gun_selection?.recommended ? (
                    <>
                      <div><span className="text-gray-400">Recomendado:</span> <span className="font-bold text-cyan-400">{result.gun_selection.recommended.gun_size}"</span></div>
                      <div><span className="text-gray-400">SPF Típico:</span> <span className="font-mono">{result.gun_selection.recommended.typical_spf}</span></div>
                      <div><span className="text-gray-400">Clearance:</span> <span className="font-mono">{result.gun_selection.recommended.clearance_in}"</span></div>
                      <div><span className="text-gray-400">Fases Disp.:</span> <span className="font-mono">{result.gun_selection.recommended.available_phasing?.join(', ')}°</span></div>
                      <div><span className="text-gray-400">Conveyance:</span> <span className="text-xs">{result.gun_selection.conveyance_notes}</span></div>
                    </>
                  ) : (
                    <div className="text-red-400">No compatible guns found</div>
                  )}
                </div>
              </div>
            </div>

            {/* Underbalance & Fracture */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="glass-panel p-6 rounded-2xl border border-white/5">
                <h3 className="text-lg font-bold mb-3">{t('completionDesign.underbalanceAnalysis')}</h3>
                <div className="space-y-2 text-sm">
                  <div><span className="text-gray-400">ΔP:</span> <span className="font-bold text-lg">{result.underbalance?.underbalance_psi} psi</span></div>
                  <div>
                    <span className="text-gray-400">Estado:</span>{' '}
                    <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                      result.underbalance?.status === 'Optimal' ? 'bg-green-500/20 text-green-400' :
                      result.underbalance?.status === 'Insufficient Underbalance' ? 'bg-yellow-500/20 text-yellow-400' :
                      'bg-red-500/20 text-red-400'
                    }`}>{result.underbalance?.status}</span>
                  </div>
                  <div><span className="text-gray-400">Rango Recom.:</span> <span className="font-mono">{result.underbalance?.recommended_range_psi?.join(' - ')} psi</span></div>
                  <div><span className="text-gray-400">Clase Perm.:</span> <span className="font-mono">{result.underbalance?.permeability_class}</span></div>
                </div>
              </div>
              <div className="glass-panel p-6 rounded-2xl border border-white/5">
                <h3 className="text-lg font-bold mb-3">{t('completionDesign.hydraulicFracture')}</h3>
                <div className="space-y-2 text-sm">
                  <div><span className="text-gray-400">P Breakdown:</span> <span className="font-bold text-orange-400">{result.fracture_initiation?.breakdown_pressure_psi} psi</span></div>
                  <div><span className="text-gray-400">P Reapertura:</span> <span className="font-mono">{result.fracture_initiation?.reopening_pressure_psi} psi</span></div>
                  <div><span className="text-gray-400">P Cierre:</span> <span className="font-mono">{result.fracture_initiation?.closure_pressure_psi} psi</span></div>
                  <div><span className="text-gray-400">ISIP Est.:</span> <span className="font-mono">{result.fracture_initiation?.isip_estimate_psi} psi</span></div>
                  <div><span className="text-gray-400">Ratio Esfuerzos:</span> <span className="font-mono">{result.fracture_initiation?.stress_ratio}</span></div>
                  <div className="text-xs text-gray-500">{result.fracture_initiation?.fracture_orientation}</div>
                </div>
              </div>
            </div>

            {/* Optimization Results */}
            <div className="glass-panel p-6 rounded-2xl border border-white/5">
              <h3 className="text-lg font-bold mb-4">Top 5 Configuraciones (Optimización SPF × Phasing)</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-white/10 text-gray-400">
                      <th className="text-left py-2 px-3">#</th>
                      <th className="text-left py-2 px-3">SPF</th>
                      <th className="text-left py-2 px-3">Phasing</th>
                      <th className="text-left py-2 px-3">PR</th>
                      <th className="text-left py-2 px-3">Skin Total</th>
                      <th className="text-left py-2 px-3">Calidad</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.optimization?.top_5_configurations?.map((cfg: any, i: number) => (
                      <tr key={i} className={`border-b border-white/5 ${i === 0 ? 'bg-violet-500/10' : ''}`}>
                        <td className="py-2 px-3 font-bold">{i + 1}</td>
                        <td className="py-2 px-3 font-mono">{cfg.spf}</td>
                        <td className="py-2 px-3 font-mono">{cfg.phasing_deg}°</td>
                        <td className="py-2 px-3 font-bold text-violet-400">{(cfg.productivity_ratio * 100).toFixed(1)}%</td>
                        <td className="py-2 px-3 font-mono">{cfg.skin_total?.toFixed(2)}</td>
                        <td className="py-2 px-3"><span className={`px-2 py-0.5 rounded text-xs font-bold ${qualityColor(cfg.quality)}`}>{cfg.quality}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
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
              <PenetrationDepthChart penetration={result.penetration} />
              <ProductivityRatioGauge optimization={result.optimization} />
              <FractureGradientProfile fractureGradient={result.fracture_gradient} />
              <PhasingPolarChart optimization={result.optimization} />
              <UnderbalanceWindowChart underbalance={result.underbalance} />
            </div>

            {/* AI Analysis */}
            <AIAnalysisPanel
              moduleName="Completion Design"
              moduleIcon={Layers}
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
              <Layers size={48} className="mx-auto mb-4 opacity-30" />
              <p>{t('completionDesign.noResults')}</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default CompletionDesignModule;
