import { useState, useCallback } from 'react';
import api from '../lib/api';
import { motion, AnimatePresence } from 'framer-motion';
import { Layers, Play, RefreshCw } from 'lucide-react';
import PenetrationDepthChart from './charts/cd/PenetrationDepthChart';
import ProductivityRatioGauge from './charts/cd/ProductivityRatioGauge';
import FractureGradientProfile from './charts/cd/FractureGradientProfile';
import PhasingPolarChart from './charts/cd/PhasingPolarChart';
import UnderbalanceWindowChart from './charts/cd/UnderbalanceWindowChart';
import IPRCurveChart from './charts/cd/IPRCurveChart';
import NodalAnalysisChart from './charts/cd/NodalAnalysisChart';
import AIAnalysisPanel from './AIAnalysisPanel';
import { useLanguage } from '../hooks/useLanguage';
import { useAIAnalysis } from '../hooks/useAIAnalysis';
import { useTranslation } from 'react-i18next';
import { useToast } from './ui/Toast';
import type { APIError } from '../types/api';

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
    // VLP / Production tubing (Beggs & Brill 1973)
    tubing_id_in: 2.992,
    wellhead_pressure_psi: 200,
    gor_scf_stb: 500,
    water_cut: 0.10,
    oil_api: 35,
    gas_sg: 0.70,
    water_sg: 1.07,
    surface_temp_f: 80,
  });

  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const { language } = useLanguage();
  const { t } = useTranslation();
  const { addToast } = useToast();

  const { aiAnalysis, isAnalyzing, runAnalysis, provider, setProvider, availableProviders, setAiAnalysis } = useAIAnalysis({
    module: 'completion-design',
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
        ? `/wells/${wellId}/completion-design`
        : `/calculate/completion-design`;
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
                    { key: 'casing_id_in',               label: t('completionDesign.fieldCasingId'),       step: '0.125' },
                    { key: 'formation_permeability_md',  label: t('completionDesign.fieldPermeability'),   step: '10' },
                    { key: 'formation_thickness_ft',     label: t('completionDesign.fieldNetThickness'),   step: '5' },
                    { key: 'depth_tvd_ft',               label: t('completionDesign.fieldTvd') || 'TVD (ft)', step: '500' },
                    { key: 'wellbore_radius_ft',         label: t('completionDesign.fieldWellboreRadius'), step: '0.01' },
                    { key: 'kv_kh_ratio',                label: t('completionDesign.fieldKvKh'),           step: '0.1' },
                    { key: 'tubing_od_in',               label: t('completionDesign.fieldTubingOd'),       step: '0.125' },
                    { key: 'temperature_f',              label: t('completionDesign.fieldBHT'),            step: '10' },
                  ].map(({ key, label, step }) => (
                    <div key={key} className="space-y-1">
                      <label className="text-xs text-gray-400">{label}</label>
                      <input type="number" step={step}
                        value={(params as Record<string, number>)[key]}
                        onChange={e => updateParam(key, e.target.value)}
                        className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:border-violet-500 focus:outline-none"
                      />
                    </div>
                  ))}
                  <div className="space-y-1">
                    <label className="text-xs text-gray-400">{t('completionDesign.fieldFormationType')}</label>
                    <select value={params.formation_type}
                      onChange={e => setParams(prev => ({ ...prev, formation_type: e.target.value }))}
                      className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:border-violet-500 focus:outline-none">
                      <option value="sandstone">{t('completionDesign.fmtSandstone')}</option>
                      <option value="carbonate">{t('completionDesign.fmtCarbonate')}</option>
                      <option value="shale">{t('completionDesign.fmtShale')}</option>
                    </select>
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs text-gray-400">{t('completionDesign.fieldCompletionFluid')}</label>
                    <select value={params.completion_fluid}
                      onChange={e => setParams(prev => ({ ...prev, completion_fluid: e.target.value }))}
                      className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:border-violet-500 focus:outline-none">
                      <option value="brine">{t('completionDesign.fluidBrine')}</option>
                      <option value="acid">{t('completionDesign.fluidAcid')}</option>
                      <option value="oil_based">{t('completionDesign.fluidOilBased')}</option>
                      <option value="completion">{t('completionDesign.fluidCompletion')}</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* Pressures & Stresses */}
              <div>
                <h3 className="text-lg font-bold mb-3">{t('completionDesign.sections.pressuresStresses')}</h3>
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                  {[
                    { key: 'reservoir_pressure_psi', label: t('completionDesign.fieldReservoirPressure'), step: '100' },
                    { key: 'wellbore_pressure_psi',  label: t('completionDesign.fieldWellborePressure'),  step: '100' },
                    { key: 'pore_pressure_psi',      label: t('completionDesign.fieldPorePressure'),      step: '100' },
                    { key: 'overburden_stress_psi',  label: t('completionDesign.fieldOverburdenStress'),  step: '500' },
                    { key: 'sigma_min_psi',          label: t('completionDesign.fieldSigmaMin'),          step: '100' },
                    { key: 'sigma_max_psi',          label: t('completionDesign.fieldSigmaMax'),          step: '100' },
                    { key: 'tensile_strength_psi',   label: t('completionDesign.fieldTensileStrength'),   step: '50' },
                    { key: 'poisson_ratio',          label: t('completionDesign.fieldPoissonRatio'),      step: '0.01' },
                  ].map(({ key, label, step }) => (
                    <div key={key} className="space-y-1">
                      <label className="text-xs text-gray-400">{label}</label>
                      <input type="number" step={step}
                        value={(params as Record<string, number>)[key]}
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
                    { key: 'penetration_berea_in',   label: t('completionDesign.fieldPenetrationBerea'),   step: '1' },
                    { key: 'effective_stress_psi',   label: t('completionDesign.fieldEffectiveStress'),    step: '500' },
                    { key: 'damage_radius_ft',       label: t('completionDesign.fieldDamageRadius'),       step: '0.1' },
                    { key: 'damage_permeability_md', label: t('completionDesign.fieldDamagePermeability'), step: '10' },
                  ].map(({ key, label, step }) => (
                    <div key={key} className="space-y-1">
                      <label className="text-xs text-gray-400">{label}</label>
                      <input type="number" step={step}
                        value={(params as Record<string, number>)[key]}
                        onChange={e => updateParam(key, e.target.value)}
                        className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:border-violet-500 focus:outline-none"
                      />
                    </div>
                  ))}
                </div>
              </div>

              {/* Production & Tubing (VLP — Beggs & Brill 1973) */}
              <div>
                <h3 className="text-lg font-bold mb-3">
                  {t('completionDesign.sections.productionTubing')}
                  <span className="text-xs text-gray-500 font-normal ml-2">{t('completionDesign.sections.beggsBrill')}</span>
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                  {[
                    { key: 'tubing_id_in',          label: t('completionDesign.fieldTubingId'),         step: '0.125' },
                    { key: 'wellhead_pressure_psi', label: t('completionDesign.fieldWellheadPressure'), step: '50' },
                    { key: 'gor_scf_stb',           label: t('completionDesign.fieldGOR'),              step: '50' },
                    { key: 'water_cut',             label: t('completionDesign.fieldWaterCut'),         step: '0.05' },
                    { key: 'oil_api',               label: t('completionDesign.fieldOilAPI'),           step: '1' },
                    { key: 'gas_sg',                label: t('completionDesign.fieldGasSg'),            step: '0.01' },
                    { key: 'water_sg',              label: t('completionDesign.fieldWaterSg'),          step: '0.01' },
                    { key: 'surface_temp_f',        label: t('completionDesign.fieldSurfaceTemp'),      step: '5' },
                  ].map(({ key, label, step }) => (
                    <div key={key} className="space-y-1">
                      <label className="text-xs text-gray-400">{label}</label>
                      <input type="number" step={step}
                        value={(params as Record<string, number>)[key]}
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
                { label: t('completionDesign.summaryProductivity'),  value: `${(result.summary?.productivity_ratio * 100)?.toFixed(1)}%`, color: qualityColor(result.optimization?.optimal_configuration?.quality || '') },
                { label: t('completionDesign.summaryPenetration'),   value: `${result.summary?.penetration_corrected_in}" (${result.summary?.penetration_efficiency_pct}%)`, color: result.summary?.penetration_efficiency_pct > 80 ? 'text-green-400' : 'text-yellow-400' },
                { label: t('completionDesign.summaryOptimalConfig'), value: `${result.summary?.optimal_spf} SPF @ ${result.summary?.optimal_phasing_deg}°`, color: 'text-violet-400' },
                { label: t('completionDesign.summaryFracGradient'),  value: `${result.summary?.fracture_gradient_ppg} ppg`, color: 'text-cyan-400' },
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
                  <div><span className="text-gray-400">{t('completionDesign.labelBerea')}:</span> <span className="font-mono">{result.penetration?.penetration_berea_in}"</span></div>
                  <div><span className="text-gray-400">{t('completionDesign.labelCorrected')}:</span> <span className="font-bold text-violet-400">{result.penetration?.penetration_corrected_in}"</span></div>
                  <div><span className="text-gray-400">{t('completionDesign.labelEfficiency')}:</span> <span className="font-mono">{result.penetration?.efficiency_pct}%</span></div>
                  <div className="pt-2 border-t border-white/5 text-xs text-gray-500">
                    {t('completionDesign.correctionFactors', {
                      stress:  result.penetration?.correction_factors?.cf_stress,
                      temp:    result.penetration?.correction_factors?.cf_temperature,
                      fluid:   result.penetration?.correction_factors?.cf_fluid,
                      cement:  result.penetration?.correction_factors?.cf_cement,
                      casing:  result.penetration?.correction_factors?.cf_casing,
                    })}
                  </div>
                </div>
              </div>
              <div className="glass-panel p-6 rounded-2xl border border-white/5">
                <h3 className="text-lg font-bold mb-3">{t('completionDesign.gunSelection')}</h3>
                <div className="space-y-2 text-sm">
                  {result.gun_selection?.recommended ? (
                    <>
                      <div><span className="text-gray-400">{t('completionDesign.labelRecommended')}:</span> <span className="font-bold text-cyan-400">{result.gun_selection.recommended.gun_size}"</span></div>
                      <div><span className="text-gray-400">{t('completionDesign.labelTypicalSpf')}:</span> <span className="font-mono">{result.gun_selection.recommended.typical_spf}</span></div>
                      <div><span className="text-gray-400">{t('completionDesign.labelClearance')}:</span> <span className="font-mono">{result.gun_selection.recommended.clearance_in}"</span></div>
                      <div><span className="text-gray-400">{t('completionDesign.labelAvailablePhasing')}:</span> <span className="font-mono">{result.gun_selection.recommended.available_phasing?.join(', ')}°</span></div>
                      <div><span className="text-gray-400">{t('completionDesign.labelConveyance')}:</span> <span className="text-xs">{result.gun_selection.conveyance_notes}</span></div>
                      {result.gun_selection.recommended.pt_check && (() => {
                        const pt = result.gun_selection.recommended.pt_check as Record<string, number | boolean>;
                        return (
                          <div className="mt-3 pt-3 border-t border-white/10 space-y-1.5">
                            <div className="text-xs text-gray-500 font-semibold uppercase tracking-wide mb-2">{t('completionDesign.gunRatingTitle')}</div>
                            <div className="flex items-center justify-between">
                              <span className="text-gray-400">BHP {(pt.bhp_psi as number).toLocaleString()} / {(pt.gun_max_pressure_psi as number).toLocaleString()} psi</span>
                              <span className={`px-2 py-0.5 rounded text-xs font-bold ${pt.pressure_pass ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                                {pt.pressure_pass ? t('completionDesign.gunPass') : t('completionDesign.gunFail')}
                              </span>
                            </div>
                            <div className="flex items-center justify-between">
                              <span className="text-gray-400">BHT {pt.bht_f as number}°F / {pt.gun_max_temp_f as number}°F máx</span>
                              <span className={`px-2 py-0.5 rounded text-xs font-bold ${pt.temp_pass ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                                {pt.temp_pass ? t('completionDesign.gunPass') : t('completionDesign.gunFail')}
                              </span>
                            </div>
                          </div>
                        );
                      })()}
                    </>
                  ) : (
                    <div className="text-red-400">{t('completionDesign.noCompatibleGuns')}</div>
                  )}
                </div>
              </div>
            </div>

            {/* Underbalance & Fracture */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="glass-panel p-6 rounded-2xl border border-white/5">
                <h3 className="text-lg font-bold mb-3">{t('completionDesign.underbalanceAnalysis')}</h3>
                <div className="space-y-2 text-sm">
                  <div><span className="text-gray-400">{t('completionDesign.labelDeltaP')}:</span> <span className="font-bold text-lg">{result.underbalance?.underbalance_psi} psi</span></div>
                  <div>
                    <span className="text-gray-400">{t('completionDesign.labelStatus')}:</span>{' '}
                    <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                      result.underbalance?.status === 'Optimal' ? 'bg-green-500/20 text-green-400' :
                      result.underbalance?.status === 'Insufficient Underbalance' ? 'bg-yellow-500/20 text-yellow-400' :
                      'bg-red-500/20 text-red-400'
                    }`}>{result.underbalance?.status}</span>
                  </div>
                  <div><span className="text-gray-400">{t('completionDesign.labelRecommendedRange')}:</span> <span className="font-mono">{result.underbalance?.recommended_range_psi?.join(' - ')} psi</span></div>
                  <div><span className="text-gray-400">{t('completionDesign.labelPermClass')}:</span> <span className="font-mono">{result.underbalance?.permeability_class}</span></div>
                </div>
              </div>
              <div className="glass-panel p-6 rounded-2xl border border-white/5">
                <h3 className="text-lg font-bold mb-3">{t('completionDesign.hydraulicFracture')}</h3>
                <div className="space-y-2 text-sm">
                  <div><span className="text-gray-400">{t('completionDesign.labelBreakdownPressure')}:</span> <span className="font-bold text-orange-400">{result.fracture_initiation?.breakdown_pressure_psi} psi</span></div>
                  <div><span className="text-gray-400">{t('completionDesign.labelReopeningPressure')}:</span> <span className="font-mono">{result.fracture_initiation?.reopening_pressure_psi} psi</span></div>
                  <div><span className="text-gray-400">{t('completionDesign.labelClosurePressure')}:</span> <span className="font-mono">{result.fracture_initiation?.closure_pressure_psi} psi</span></div>
                  <div><span className="text-gray-400">{t('completionDesign.labelISIP')}:</span> <span className="font-mono">{result.fracture_initiation?.isip_estimate_psi} psi</span></div>
                  <div><span className="text-gray-400">{t('completionDesign.labelStressRatio')}:</span> <span className="font-mono">{result.fracture_initiation?.stress_ratio}</span></div>
                  <div className="flex items-center gap-2 mt-1">
                    {result.fracture_initiation?.stress_regime && (
                      <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                        result.fracture_initiation.stress_regime === 'Normal' ? 'bg-blue-500/20 text-blue-400' :
                        result.fracture_initiation.stress_regime === 'Strike-Slip' ? 'bg-yellow-500/20 text-yellow-400' :
                        result.fracture_initiation.stress_regime === 'Reverse' ? 'bg-red-500/20 text-red-400' :
                        'bg-gray-500/20 text-gray-400'
                      }`}>{result.fracture_initiation.stress_regime}</span>
                    )}
                    <span className="text-xs text-gray-500">{result.fracture_initiation?.fracture_orientation}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Optimization Results */}
            <div className="glass-panel p-6 rounded-2xl border border-white/5">
              <h3 className="text-lg font-bold mb-4">{t('completionDesign.optimizationTitle')}</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-white/10 text-gray-400">
                      <th className="text-left py-2 px-3">{t('completionDesign.colRank')}</th>
                      <th className="text-left py-2 px-3">{t('completionDesign.colSpf')}</th>
                      <th className="text-left py-2 px-3">{t('completionDesign.colPhasing')}</th>
                      <th className="text-left py-2 px-3">{t('completionDesign.colPR')}</th>
                      <th className="text-left py-2 px-3">{t('completionDesign.colSkinTotal')}</th>
                      <th className="text-left py-2 px-3">{t('completionDesign.colQuality')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.optimization?.top_5_configurations?.map((cfg: Record<string, string | number>, i: number) => (
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

            {/* Skin Component Breakdown (K&T 1991) */}
            {result.optimization?.optimal_configuration?.skin_components && (
              <div className="glass-panel p-6 rounded-2xl border border-white/5">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-bold">{t('completionDesign.skinBreakdownTitle')}</h3>
                  <span className="text-xs text-gray-500">{t('completionDesign.skinReference')}</span>
                </div>
                {(() => {
                  const sc = result.optimization.optimal_configuration.skin_components as Record<string, number>;
                  const opt = result.optimization.optimal_configuration as Record<string, number | string>;
                  const components = [
                    { key: 's_perforation', label: t('completionDesign.skinSperf'),  value: sc.s_perforation, color: '#818cf8', desc: t('completionDesign.skinSperfDesc') },
                    { key: 's_vertical',    label: t('completionDesign.skinSvert'),  value: sc.s_vertical,    color: '#f97316', desc: t('completionDesign.skinSvertDesc') },
                    { key: 's_wellbore',    label: t('completionDesign.skinSwb'),    value: sc.s_wellbore,    color: '#eab308', desc: t('completionDesign.skinSwbDesc') },
                    { key: 's_damage',      label: t('completionDesign.skinSdamage'),value: sc.s_damage,      color: '#ef4444', desc: t('completionDesign.skinSdamageDesc') },
                  ];
                  const maxAbs = Math.max(1, ...components.map(c => Math.abs(c.value ?? 0)));
                  return (
                    <div className="space-y-4">
                      {components.map(comp => (
                        <div key={comp.key}>
                          <div className="flex justify-between items-center mb-1">
                            <span className="text-sm font-mono font-semibold">{comp.label}</span>
                            <span className={`font-mono font-bold text-sm ${(comp.value ?? 0) < 0 ? 'text-green-400' : (comp.value ?? 0) > 0 ? 'text-orange-300' : 'text-gray-400'}`}>
                              {(comp.value ?? 0) > 0 ? '+' : ''}{(comp.value ?? 0).toFixed(3)}
                            </span>
                          </div>
                          <div className="w-full bg-white/5 rounded-full h-3 overflow-hidden">
                            <div
                              className="h-full rounded-full transition-all duration-700"
                              style={{
                                width: `${Math.max(2, Math.abs(comp.value ?? 0) / maxAbs * 100)}%`,
                                backgroundColor: comp.color,
                                opacity: (comp.value ?? 0) === 0 ? 0.2 : 0.8,
                              }}
                            />
                          </div>
                          <p className="text-xs text-gray-500 mt-0.5">{comp.desc}</p>
                        </div>
                      ))}
                      <div className="border-t border-white/10 pt-3 flex justify-between items-center">
                        <span className="text-sm text-gray-400">{t('completionDesign.labelSkinTotal')}:</span>
                        <span className={`font-mono font-bold text-xl ${(opt.skin_total as number) < 0 ? 'text-green-400' : 'text-orange-400'}`}>
                          {(opt.skin_total as number) > 0 ? '+' : ''}{(opt.skin_total as number)?.toFixed(3)}
                        </span>
                      </div>
                    </div>
                  );
                })()}
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

            {/* Nodal Analysis — full width (IPR + VLP + operating point) */}
            <NodalAnalysisChart
              ipr={result.ipr as Parameters<typeof NodalAnalysisChart>[0]['ipr']}
              vlp={result.vlp as Parameters<typeof NodalAnalysisChart>[0]['vlp']}
              nodal={result.nodal as Parameters<typeof NodalAnalysisChart>[0]['nodal']}
            />

            {/* Flow Efficiency */}
            {result.ipr?.flow_efficiency != null && (
              <div className="glass-panel p-6 rounded-2xl border border-white/5">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-bold">{t('completionDesign.flowEfficiencyTitle')}</h3>
                  <span className="text-xs text-gray-500">{t('completionDesign.flowEfficiencySubtitle')}</span>
                </div>
                {(() => {
                  const fe = result.ipr.flow_efficiency as number;
                  const aofActual = result.ipr.AOF_stbd as number;
                  const aofIdeal = result.ipr.AOF_ideal_stbd as number;
                  const piActual = result.ipr.PI_stbd_psi as number;
                  const piIdeal = result.ipr.PI_ideal_stbd_psi as number;
                  const isPositive = fe >= 1.0;
                  return (
                    <div className="space-y-4">
                      <div className="flex items-center gap-4">
                        <span className={`font-mono font-bold text-4xl ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
                          {fe.toFixed(2)}
                        </span>
                        <span className={`text-lg font-semibold ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
                          ({(fe * 100).toFixed(0)}%)
                        </span>
                      </div>
                      <p className={`text-sm ${isPositive ? 'text-green-300' : 'text-red-300'}`}>
                        {isPositive
                          ? t('completionDesign.fePositive', { pct: ((fe - 1) * 100).toFixed(0) })
                          : t('completionDesign.feNegative')}
                      </p>
                      <div className="grid grid-cols-2 gap-3 pt-2 border-t border-white/10">
                        <div>
                          <div className="text-xs text-gray-500 mb-1">{t('completionDesign.piWithCompletion')}</div>
                          <div className="font-mono text-violet-400 font-semibold">{piActual?.toFixed(4)} <span className="text-xs text-gray-500">STB/d/psi</span></div>
                        </div>
                        <div>
                          <div className="text-xs text-gray-500 mb-1">{t('completionDesign.piIdeal')}</div>
                          <div className="font-mono text-gray-300 font-semibold">{piIdeal?.toFixed(4)} <span className="text-xs text-gray-500">STB/d/psi</span></div>
                        </div>
                        <div>
                          <div className="text-xs text-gray-500 mb-1">{t('completionDesign.aofWithCompletion')}</div>
                          <div className="font-mono text-violet-400 font-semibold">{aofActual?.toFixed(0)} <span className="text-xs text-gray-500">STB/d</span></div>
                        </div>
                        <div>
                          <div className="text-xs text-gray-500 mb-1">{t('completionDesign.aofNoSkin')}</div>
                          <div className="font-mono text-gray-300 font-semibold">{aofIdeal?.toFixed(0)} <span className="text-xs text-gray-500">STB/d</span></div>
                        </div>
                      </div>
                    </div>
                  );
                })()}
              </div>
            )}

            {/* Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <PenetrationDepthChart penetration={result.penetration} />
              <ProductivityRatioGauge optimization={result.optimization} />
              <IPRCurveChart ipr={result.ipr as Parameters<typeof IPRCurveChart>[0]['ipr']} />
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
              <Layers size={48} className="mx-auto mb-4 opacity-30" />
              <p>{t('completionDesign.noResults')}</p>
            </div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default CompletionDesignModule;
