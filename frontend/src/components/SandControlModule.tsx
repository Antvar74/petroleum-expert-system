import { useState, useCallback } from 'react';
import api from '../lib/api';
import { motion, AnimatePresence } from 'framer-motion';
import { Filter, Play, RefreshCw } from 'lucide-react';
import GrainDistributionChart from './charts/sc/GrainDistributionChart';
import CompletionComparisonRadar from './charts/sc/CompletionComparisonRadar';
import DrawdownLimitGauge from './charts/sc/DrawdownLimitGauge';
import GravelPackSchematic from './charts/sc/GravelPackSchematic';
import AIAnalysisPanel from './AIAnalysisPanel';
import { useLanguage } from '../hooks/useLanguage';
import { useAIAnalysis } from '../hooks/useAIAnalysis';
import { useTranslation } from 'react-i18next';
import { useToast } from './ui/Toast';
import type { APIError } from '../types/api';

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
    casing_id_in: '' as string | number,
    drainage_radius_ft: 660,
    productivity_index_stbd_psi: '' as string | number,
  });

  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const { language } = useLanguage();
  const { t } = useTranslation();
  const { addToast } = useToast();

  const { aiAnalysis, isAnalyzing, runAnalysis, provider, setProvider, availableProviders } = useAIAnalysis({
    module: 'sand-control',
    wellId,
    wellName,
  });

  const updateParam = (key: string, value: string) => {
    if (key.includes('sieve') || key.includes('cumulative')) {
      setParams(prev => ({ ...prev, [key]: value }));
    } else {
      setParams(prev => ({ ...prev, [key]: value === '' ? '' : (parseFloat(value) || 0) }));
    }
  };

  const calculate = useCallback(async () => {
    setLoading(true);
    try {
      const payload: Record<string, unknown> = {
        ...params,
        sieve_sizes_mm: String(params.sieve_sizes_mm).split(',').map(s => parseFloat(s.trim())),
        cumulative_passing_pct: String(params.cumulative_passing_pct).split(',').map(s => parseFloat(s.trim())),
      };
      if (!params.casing_id_in || params.casing_id_in === '') delete payload.casing_id_in;
      if (!params.productivity_index_stbd_psi || params.productivity_index_stbd_psi === '') delete payload.productivity_index_stbd_psi;

      const url = wellId ? `/wells/${wellId}/sand-control` : `/calculate/sand-control`;
      const res = await api.post(url, payload);
      setResult(res.data);
      setActiveTab('results');
    } catch (e: unknown) {
      addToast('Error: ' + ((e as APIError).response?.data?.detail || (e as APIError).message), 'error');
    }
    setLoading(false);
  }, [wellId, params, addToast]);

  const handleRunAnalysis = () => runAnalysis(result || {}, params);

  const tabs = [
    { id: 'input', label: t('common.parameters') },
    { id: 'results', label: t('common.results') },
  ];

  const riskColor = (risk: string) => {
    if (risk?.includes('Very High') || risk?.includes('High')) return 'text-red-400 bg-red-500/10';
    if (risk?.includes('Moderate')) return 'text-yellow-400 bg-yellow-500/10';
    return 'text-green-400 bg-green-500/10';
  };

  const feColor = (cls: string) => {
    if (cls === 'NORMAL') return 'text-green-400';
    if (cls === 'CAUTION') return 'text-yellow-400';
    return 'text-red-400';
  };

  const skinBarColor = (val: number) => val < 0 ? 'bg-blue-500' : 'bg-orange-500';

  // Suppress unused warning — language used for future i18n consistency
  void language;

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
                    <label className="text-xs text-gray-400">{t('sandControl.labelSieveSizes')}</label>
                    <input type="text" value={params.sieve_sizes_mm}
                      onChange={e => updateParam('sieve_sizes_mm', e.target.value)}
                      className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:border-amber-500 focus:outline-none"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs text-gray-400">{t('sandControl.labelCumPassing')}</label>
                    <input type="text" value={params.cumulative_passing_pct}
                      onChange={e => updateParam('cumulative_passing_pct', e.target.value)}
                      className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:border-amber-500 focus:outline-none"
                    />
                  </div>
                </div>
              </div>

              {/* Formation & Completion */}
              <div>
                <h3 className="text-lg font-bold mb-3">{t('sandControl.sections.formation')}</h3>
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                  {[
                    { key: 'hole_id', label: t('sandControl.holeDiameter'), step: '0.125' },
                    { key: 'screen_od', label: t('sandControl.screenOD'), step: '0.125' },
                    { key: 'interval_length', label: 'Interval (ft)', step: '10' },
                    { key: 'ucs_psi', label: t('sandControl.ucs'), step: '50' },
                    { key: 'friction_angle_deg', label: 'Friction Angle (°)', step: '1' },
                    { key: 'reservoir_pressure_psi', label: t('sandControl.reservoirPressure'), step: '100' },
                    { key: 'overburden_stress_psi', label: 'Overburden Stress (psi)', step: '500' },
                    { key: 'formation_permeability_md', label: t('sandControl.permeability'), step: '50' },
                    { key: 'gravel_permeability_md', label: 'Gravel Perm. (mD)', step: '10000' },
                    { key: 'pack_factor', label: 'Pack Factor', step: '0.1' },
                    { key: 'washout_factor', label: 'Washout Factor', step: '0.05' },
                    { key: 'wellbore_radius_ft', label: 'Wellbore Radius (ft)', step: '0.01' },
                    { key: 'drainage_radius_ft', label: t('sandControl.drainageRadius'), step: '10' },
                  ].map(({ key, label, step }) => (
                    <div key={key} className="space-y-1">
                      <label className="text-xs text-gray-400">{label}</label>
                      <input type="number" step={step}
                        value={(params as Record<string, unknown>)[key] as number}
                        onChange={e => updateParam(key, e.target.value)}
                        className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:border-amber-500 focus:outline-none"
                      />
                    </div>
                  ))}

                  {/* Completion type */}
                  <div className="space-y-1">
                    <label className="text-xs text-gray-400">{t('sandControl.labelWellboreType')}</label>
                    <select value={params.wellbore_type}
                      onChange={e => setParams(prev => ({ ...prev, wellbore_type: e.target.value }))}
                      className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:border-amber-500 focus:outline-none">
                      <option value="cased">{t('sandControl.optCased')}</option>
                      <option value="openhole">{t('sandControl.optOpenhole')}</option>
                    </select>
                  </div>

                  {/* Casing ID — only for cased hole */}
                  {params.wellbore_type === 'cased' && (
                    <div className="space-y-1">
                      <label className="text-xs text-gray-400">{t('sandControl.casingId')}</label>
                      <input type="number" step="0.125" placeholder="e.g. 8.835"
                        value={params.casing_id_in === '' ? '' : params.casing_id_in as number}
                        onChange={e => updateParam('casing_id_in', e.target.value)}
                        className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:border-amber-500 focus:outline-none"
                      />
                    </div>
                  )}

                  {/* Optional PI */}
                  <div className="space-y-1">
                    <label className="text-xs text-gray-400">{t('sandControl.pi')}</label>
                    <input type="number" step="0.01" placeholder="e.g. 3.784"
                      value={params.productivity_index_stbd_psi === '' ? '' : params.productivity_index_stbd_psi as number}
                      onChange={e => updateParam('productivity_index_stbd_psi', e.target.value)}
                      className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:border-amber-500 focus:outline-none"
                    />
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
                { label: 'D50', value: `${(result.summary as Record<string, unknown>)?.d50_mm} mm`, color: 'text-amber-400' },
                { label: t('sandControl.labelRisk'), value: (result.summary as Record<string, unknown>)?.sanding_risk as string, color: '' },
                { label: t('sandControl.gravelSelection'), value: (result.summary as Record<string, unknown>)?.recommended_gravel as string, color: 'text-cyan-400' },
                { label: 'Skin Total', value: (result.summary as Record<string, unknown>)?.skin_total as number, color: ((result.summary as Record<string, unknown>)?.skin_total as number) < 5 ? 'text-green-400' : 'text-red-400' },
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
                <div><span className="text-gray-400">D10:</span> <span className="font-mono">{(result.psd as Record<string, unknown>)?.d10_mm} mm</span></div>
                <div><span className="text-gray-400">D50:</span> <span className="font-mono">{(result.psd as Record<string, unknown>)?.d50_mm} mm</span></div>
                <div><span className="text-gray-400">D90:</span> <span className="font-mono">{(result.psd as Record<string, unknown>)?.d90_mm} mm</span></div>
                <div><span className="text-gray-400">Cu:</span> <span className="font-mono">{(result.psd as Record<string, unknown>)?.uniformity_coefficient}</span></div>
                <div><span className="text-gray-400">Sorting:</span> <span className="font-mono">{(result.psd as Record<string, unknown>)?.sorting}</span></div>
              </div>
            </div>

            {/* Gravel & Screen */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="glass-panel p-6 rounded-2xl border border-white/5">
                <h3 className="text-lg font-bold mb-3">{t('sandControl.gravelSelection')}</h3>
                <div className="space-y-2 text-sm">
                  <div><span className="text-gray-400">{t('sandControl.labelRecommendedPack')}:</span> <span className="font-bold text-cyan-400">{(result.gravel as Record<string, unknown>)?.recommended_pack}</span></div>
                  <div><span className="text-gray-400">{t('sandControl.labelGravelRange')}:</span> <span className="font-mono">{(result.gravel as Record<string, unknown>)?.gravel_min_mm}–{(result.gravel as Record<string, unknown>)?.gravel_max_mm} mm</span></div>
                  <div><span className="text-gray-400">{t('sandControl.labelGravelVol')}:</span> <span className="font-mono">{(result.volume as Record<string, unknown>)?.gravel_volume_bbl} bbl</span></div>
                  <div><span className="text-gray-400">{t('sandControl.labelGravelWeight')}:</span> <span className="font-mono">{(result.volume as Record<string, unknown>)?.gravel_weight_lb} lb</span></div>
                </div>
              </div>
              <div className="glass-panel p-6 rounded-2xl border border-white/5">
                <h3 className="text-lg font-bold mb-3">{t('sandControl.screenSelection')}</h3>
                <div className="space-y-2 text-sm">
                  <div><span className="text-gray-400">{t('sandControl.labelScreenType')}:</span> <span className="font-mono">{(result.screen as Record<string, unknown>)?.screen_type}</span></div>
                  <div><span className="text-gray-400">{t('sandControl.labelSlot')}:</span> <span className="font-bold text-cyan-400">{(result.screen as Record<string, unknown>)?.recommended_standard_slot_in}"</span></div>
                  <div><span className="text-gray-400">{t('sandControl.labelRetention')}:</span> <span className="font-mono">{(result.screen as Record<string, unknown>)?.estimated_retention_pct}%</span></div>
                </div>
              </div>
            </div>

            {/* FIX-SAND-001: Sanding Analysis with dry + wet drawdown */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="glass-panel p-6 rounded-2xl border border-white/5">
                <h3 className="text-lg font-bold mb-3">{t('sandControl.sandingAnalysis')}</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between py-1 border-b border-white/5">
                    <span className="text-gray-400">{t('sandControl.labelCritDDDry')}:</span>
                    <span className="font-mono font-bold">{(result.drawdown as Record<string, unknown>)?.critical_drawdown_dry_psi} psi</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-white/5">
                    <span className="text-gray-400">{t('sandControl.labelCritDDWet')}:</span>
                    <span className="font-mono font-bold text-yellow-300">{(result.drawdown as Record<string, unknown>)?.critical_drawdown_wet_psi} psi</span>
                  </div>
                  <div className="text-xs text-gray-500 italic pb-1">{t('sandControl.labelWaterWeakening')}</div>
                  <div className="flex justify-between py-1 border-b border-white/5">
                    <span className="text-gray-400">{t('sandControl.labelRisk')}:</span>
                    <span className={`font-bold px-2 py-0.5 rounded text-xs ${riskColor((result.drawdown as Record<string, unknown>)?.sanding_risk as string)}`}>
                      {(result.drawdown as Record<string, unknown>)?.sanding_risk}
                    </span>
                  </div>
                  <div><span className="text-gray-400">{t('sandControl.labelRecommendation')}:</span> <span className="text-xs">{(result.drawdown as Record<string, unknown>)?.recommendation}</span></div>
                </div>
              </div>
              <div className="glass-panel p-6 rounded-2xl border border-white/5">
                <h3 className="text-lg font-bold mb-3">{t('sandControl.completionType')}</h3>
                <div className="space-y-2 text-sm">
                  <div><span className="text-gray-400">{t('sandControl.labelRecommended')}:</span> <span className="font-bold text-green-400">{(result.completion as Record<string, unknown>)?.recommended}</span></div>
                  {((result.completion as Record<string, unknown>)?.methods as Array<{ method: string; score: number }>)?.slice(0, 3).map((m, i) => (
                    <div key={i} className="flex justify-between items-center py-1 border-t border-white/5">
                      <span className="text-gray-300">{m.method}</span>
                      <span className="text-xs text-gray-500">Score: {m.score}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* FIX-SAND-002: Skin Breakdown + FIX-SAND-003/004: FE + q_max */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="glass-panel p-6 rounded-2xl border border-white/5">
                <h3 className="text-lg font-bold mb-4">{t('sandControl.skinBreakdown')}</h3>
                <div className="space-y-3 text-sm">
                  {([
                    { label: t('sandControl.labelSkinPerf'), val: (result.skin as Record<string, unknown>)?.skin_perforation as number },
                    { label: t('sandControl.labelSkinGravel'), val: (result.skin as Record<string, unknown>)?.skin_gravel as number },
                    { label: t('sandControl.labelSkinDamage'), val: (result.skin as Record<string, unknown>)?.skin_damage as number },
                  ]).map(({ label, val }) => (
                    <div key={label}>
                      <div className="flex justify-between mb-1">
                        <span className="text-gray-400">{label}</span>
                        <span className={`font-mono font-bold ${val < 0 ? 'text-blue-400' : 'text-orange-400'}`}>{val?.toFixed(2)}</span>
                      </div>
                      <div className="w-full bg-white/10 rounded-full h-1.5">
                        <div className={`h-1.5 rounded-full ${skinBarColor(val)}`}
                          style={{ width: `${Math.min(Math.abs(val ?? 0) * 8, 100)}%` }} />
                      </div>
                    </div>
                  ))}
                  <div className="flex justify-between pt-2 border-t border-white/10 font-bold">
                    <span className="text-gray-200">S_total</span>
                    <span className={`font-mono ${((result.skin as Record<string, unknown>)?.skin_total as number) < 0 ? 'text-blue-400' : 'text-orange-400'}`}>
                      {((result.skin as Record<string, unknown>)?.skin_total as number)?.toFixed(2)}
                    </span>
                  </div>
                </div>
              </div>

              <div className="glass-panel p-6 rounded-2xl border border-white/5">
                <h3 className="text-lg font-bold mb-4">{t('sandControl.flowEfficiency')}</h3>
                <div className="space-y-3 text-sm">
                  <div className="text-center py-2">
                    <div className={`text-3xl font-bold ${feColor(result.flow_efficiency_class as string)}`}>
                      {(((result.flow_efficiency as number) ?? 0) * 100).toFixed(1)}%
                    </div>
                    <div className={`text-xs mt-1 ${feColor(result.flow_efficiency_class as string)}`}>
                      {result.flow_efficiency_class === 'NORMAL'
                        ? t('sandControl.feNormal')
                        : result.flow_efficiency_class === 'CAUTION'
                        ? t('sandControl.feCaution')
                        : t('sandControl.feCritical')}
                    </div>
                  </div>
                  <div className="border-t border-white/10 pt-3">
                    <div className="font-semibold text-gray-300 mb-2">{t('sandControl.qMaxSafe')}</div>
                    {result.q_max_safe_stbd != null ? (
                      <div className="flex items-baseline gap-2">
                        <span className="text-2xl font-bold text-cyan-400">
                          {(result.q_max_safe_stbd as number).toLocaleString()}
                        </span>
                        <span className="text-gray-400">{t('sandControl.qMaxUnit')}</span>
                      </div>
                    ) : (
                      <div className="text-xs text-gray-500 italic">{t('sandControl.qMaxNoPi')}</div>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Alerts */}
            {((result.alerts as string[])?.length ?? 0) > 0 && (
              <div className="glass-panel p-6 rounded-2xl border border-yellow-500/20">
                <h3 className="text-lg font-bold text-yellow-400 mb-3">&#9888; {t('common.alerts')}</h3>
                <ul className="space-y-2">
                  {(result.alerts as string[]).map((alert, i) => (
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
              <Filter size={48} className="mx-auto mb-4 opacity-30" />
              <p>{t('sandControl.noResults')}</p>
            </div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default SandControlModule;
