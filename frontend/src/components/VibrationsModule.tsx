import { useState, useCallback } from 'react';
import api from '../lib/api';
import { motion, AnimatePresence } from 'framer-motion';
import { Vibrate, Play, RefreshCw, Wrench, Layers } from 'lucide-react';
import StabilityGauge from './charts/vb/StabilityGauge';
import VibrationMapHeatmap from './charts/vb/VibrationMapHeatmap';
import CriticalRPMChart from './charts/vb/CriticalRPMChart';
import MSEBreakdownChart from './charts/vb/MSEBreakdownChart';
import StickSlipIndicator from './charts/vb/StickSlipIndicator';
import BHAEditor, { type BHAComponent } from './charts/vb/BHAEditor';
import WellboreSectionEditor, { type WellboreSection } from './charts/vb/WellboreSectionEditor';
import ModeShapePlot from './charts/vb/ModeShapePlot';
import CampbellDiagram from './charts/vb/CampbellDiagram';
import AIAnalysisPanel from './AIAnalysisPanel';
import { useLanguage } from '../hooks/useLanguage';
import { useAIAnalysis } from '../hooks/useAIAnalysis';
import { useTranslation } from 'react-i18next';
import { useToast } from './ui/Toast';
import type { APIError } from '../types/api';

interface VibrationsModuleProps {
  wellId?: number;
  wellName?: string;
}

const VibrationsModule: React.FC<VibrationsModuleProps> = ({ wellId, wellName = '' }) => {
  const [activeTab, setActiveTab] = useState('input');
  const [loading, setLoading] = useState(false);

  const [params, setParams] = useState<Record<string, number | undefined>>({
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
    pv_cp: undefined,
    yp_lbf_100ft2: undefined,
    flow_rate_gpm: undefined,
    hole_diameter_in: 8.5,
    inclination_deg: 15,
    friction_factor: 0.25,
    stabilizer_spacing_ft: undefined,
    ucs_psi: undefined,
    n_blades: undefined,
  });

  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [bhaComponents, setBhaComponents] = useState<BHAComponent[]>([]);
  const [feaResult, setFeaResult] = useState<Record<string, any> | null>(null);
  const [feaLoading, setFeaLoading] = useState(false);
  const [showBhaEditor, setShowBhaEditor] = useState(false);
  const [wellboreSections, setWellboreSections] = useState<WellboreSection[]>([]);
  const { language } = useLanguage();
  const { t } = useTranslation();
  const { addToast } = useToast();

  const { aiAnalysis, isAnalyzing, runAnalysis, provider, setProvider, availableProviders, setAiAnalysis } = useAIAnalysis({
    module: 'vibrations',
    wellId,
    wellName,
  });

  const optionalFields = new Set(['stabilizer_spacing_ft', 'ucs_psi', 'n_blades', 'pv_cp', 'yp_lbf_100ft2', 'flow_rate_gpm']);

  const lithologyPresets = [
    { label: 'Shale', value: 8000 },
    { label: 'Sandstone', value: 20000 },
    { label: 'Limestone', value: 35000 },
    { label: 'Dolomite', value: 50000 },
  ];

  const updateParam = (key: string, value: string) => {
    if (optionalFields.has(key)) {
      setParams(prev => ({ ...prev, [key]: value === '' ? undefined : parseFloat(value) || 0 }));
    } else {
      setParams(prev => ({ ...prev, [key]: parseFloat(value) || 0 }));
    }
  };

  const calculate = useCallback(async () => {
    setLoading(true);
    try {
      const url = wellId
        ? `/wells/${wellId}/vibrations`
        : `/calculate/vibrations`;
      const cleanParams: Record<string, unknown> = Object.fromEntries(Object.entries(params).filter(([, v]) => v !== undefined));
      // Derive total depth from wellbore sections (max bottom_md_ft)
      if (wellboreSections.length > 0) {
        const totalDepth = Math.max(...wellboreSections.map(s => s.bottom_md_ft));
        if (totalDepth > 0) cleanParams.total_depth_ft = totalDepth;
        cleanParams.wellbore_sections = wellboreSections;
      }
      // Pass BHA components for multi-component stick-slip calculation
      if (bhaComponents.length > 0) {
        cleanParams.bha_components = bhaComponents;
      }
      const res = await api.post(url, cleanParams);
      setResult(res.data);
      setActiveTab('results');
    } catch (e: unknown) {
      addToast('Error: ' + ((e as APIError).response?.data?.detail || (e as APIError).message), 'error');
    }
    setLoading(false);
  }, [wellId, params, wellboreSections, bhaComponents, addToast]);

  const calculateFEA = useCallback(async () => {
    if (bhaComponents.length < 2) {
      addToast('Add at least 2 BHA components for FEA analysis', 'error');
      return;
    }
    setFeaLoading(true);
    try {
      const res = await api.post('/vibrations/fea', {
        bha_components: bhaComponents,
        wob_klb: params.wob_klb || 20,
        rpm: params.rpm || 120,
        mud_weight_ppg: params.mud_weight_ppg || 10,
        pv_cp: params.pv_cp || undefined,
        yp_lbf_100ft2: params.yp_lbf_100ft2 || undefined,
        hole_diameter_in: params.hole_diameter_in || 8.5,
        boundary_conditions: 'pinned-pinned',
        n_modes: 5,
        include_forced_response: true,
        include_campbell: true,
        n_blades: params.n_blades || undefined,
      });
      setFeaResult(res.data);
      setActiveTab('results');
    } catch (e: unknown) {
      addToast('FEA Error: ' + ((e as APIError).response?.data?.detail || (e as APIError).message), 'error');
    }
    setFeaLoading(false);
    // Also recalculate main vibrations so stick-slip updates with BHA data
    calculate();
  }, [bhaComponents, params, addToast, calculate]);

  const handleRunAnalysis = () => {
    runAnalysis(result || {}, params);
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
                    { key: 'pv_cp', label: t('vibrations.pvCp'), step: '1', placeholder: 'Opcional' },
                    { key: 'yp_lbf_100ft2', label: t('vibrations.ypLbf'), step: '1', placeholder: 'Opcional' },
                    { key: 'flow_rate_gpm', label: t('vibrations.flowRate'), step: '50', placeholder: 'Opcional' },
                    { key: 'hole_diameter_in', label: t('vibrations.holeDiameter'), step: '0.125' },
                    { key: 'inclination_deg', label: t('vibrations.inclination'), step: '5' },
                    { key: 'friction_factor', label: t('vibrations.frictionCoeff'), step: '0.05' },
                    { key: 'dp_od_in', label: t('vibrations.dpOD'), step: '0.125' },
                    { key: 'dp_id_in', label: t('vibrations.dpID'), step: '0.125' },
                    { key: 'dp_weight_lbft', label: t('vibrations.dpWeight'), step: '1' },
                    { key: 'stabilizer_spacing_ft', label: 'Estabilizador (ft)', step: '5', placeholder: 'Auto (max 90 ft)' },
                    { key: 'n_blades', label: 'Blades PDC', step: '1', placeholder: 'Opcional' },
                  ].map(({ key, label, step, placeholder }) => (
                    <div key={key} className="space-y-1">
                      <label className="text-xs text-gray-400">{label}</label>
                      <input type="number" step={step}
                        value={params[key] ?? ''}
                        placeholder={placeholder}
                        onChange={e => updateParam(key, e.target.value)}
                        className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:border-rose-500 focus:outline-none"
                      />
                    </div>
                  ))}
                  {/* UCS with lithology quick-select */}
                  <div className="space-y-1 col-span-2 md:col-span-2">
                    <label className="text-xs text-gray-400">UCS (psi)</label>
                    <div className="flex gap-2">
                      <input type="number" step="1000"
                        value={params.ucs_psi ?? ''}
                        placeholder="Opcional"
                        onChange={e => updateParam('ucs_psi', e.target.value)}
                        className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:border-rose-500 focus:outline-none"
                      />
                      <div className="flex gap-1">
                        {lithologyPresets.map(lith => (
                          <button key={lith.label} type="button"
                            onClick={() => setParams(prev => ({ ...prev, ucs_psi: lith.value }))}
                            className={`px-2 py-1 text-xs rounded-md border transition-colors ${
                              params.ucs_psi === lith.value
                                ? 'bg-rose-500/20 border-rose-500/40 text-rose-300'
                                : 'bg-white/5 border-white/10 text-gray-400 hover:border-white/20 hover:text-gray-300'
                            }`}
                            title={`${lith.label}: ${lith.value.toLocaleString()} psi`}
                          >
                            {lith.label}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Wellbore Configuration */}
              <div>
                <h3 className="text-lg font-bold mb-3 flex items-center gap-2">
                  <Layers size={18} />
                  {t('vibrations.sections.wellbore')}
                </h3>
                <div className="glass-panel p-4 rounded-xl border border-white/5">
                  <WellboreSectionEditor sections={wellboreSections} onChange={setWellboreSections} />
                </div>
              </div>

              {/* FEA — BHA Detailed Editor */}
              <div>
                <button
                  type="button"
                  onClick={() => setShowBhaEditor(!showBhaEditor)}
                  className="flex items-center gap-2 text-lg font-bold mb-3 hover:text-rose-400 transition-colors"
                >
                  <Wrench size={18} />
                  BHA Detallado (FEA)
                  <span className="text-xs font-normal text-gray-500 ml-2">
                    {showBhaEditor ? '▼' : '▶'} {bhaComponents.length > 0 ? `${bhaComponents.reduce((s, c) => s + (c.quantity ?? 1), 0)} joints · ${bhaComponents.reduce((s, c) => s + c.length_ft, 0).toFixed(0)} ft` : 'Click to expand'}
                  </span>
                </button>
                {showBhaEditor && (
                  <div className="glass-panel p-4 rounded-xl border border-white/5">
                    <BHAEditor components={bhaComponents} onChange={setBhaComponents} />
                    {bhaComponents.length >= 2 && (
                      <button onClick={calculateFEA} disabled={feaLoading}
                        className="mt-4 flex items-center gap-2 px-5 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-lg text-sm font-medium transition-colors disabled:opacity-50">
                        {feaLoading ? <RefreshCw size={14} className="animate-spin" /> : <Wrench size={14} />}
                        {feaLoading ? 'Running FEA...' : 'Run FEA Analysis'}
                      </button>
                    )}
                  </div>
                )}
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
                { label: t('vibrations.criticalRpmLateral'), value: `${result.summary?.critical_rpm_lateral?.toFixed(0)}${(result.lateral_vibrations as Record<string, unknown>)?.span_source === 'estimated' ? ' (est)' : ''}`, color: 'text-cyan-400' },
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
                  {result.mse?.efficiency_pct != null ? (
                    <div><span className="text-gray-400">Eficiencia:</span> <span className="font-mono">{result.mse.efficiency_pct}%</span>
                      <span className="text-xs text-gray-500 ml-1">({result.mse?.classification_basis === 'ucs_based' ? 'UCS-based' : 'estimada'})</span>
                    </div>
                  ) : (
                    <div><span className="text-gray-400">Eficiencia:</span> <span className="text-gray-500 italic text-xs">Proporcione UCS para calculo</span></div>
                  )}
                  <div>
                    <span className="text-gray-400">Estado:</span>{' '}
                    <span className={`px-2 py-0.5 rounded text-xs font-bold ${statusColor(result.mse?.classification === 'Efficient' ? 'Stable' : result.mse?.classification === 'Normal' ? 'Marginal' : 'Critical')}`}>
                      {result.mse?.classification}
                    </span>
                  </div>
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

            {/* Bit Excitation & Resonance */}
            {result.bit_excitation && (
              <div className="glass-panel p-6 rounded-2xl border border-white/5">
                <h3 className="text-lg font-bold mb-3">Bit Excitation</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div><span className="text-gray-400">Frecuencia:</span> <span className="font-mono">{result.bit_excitation.excitation_freq_hz} Hz</span></div>
                  <div><span className="text-gray-400">Corte/rev:</span> <span className="font-mono">{result.bit_excitation.depth_of_cut_in} in</span></div>
                  <div><span className="text-gray-400">Fuerza corte:</span> <span className="font-mono">{result.bit_excitation.cutting_force_lbs?.toLocaleString()} lbs</span></div>
                  {result.resonance_check && (
                    <div>
                      <span className="text-gray-400">Resonancia:</span>{' '}
                      <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                        result.resonance_check.resonance_risk === 'low' ? 'text-green-400 bg-green-500/10' :
                        result.resonance_check.resonance_risk === 'moderate' ? 'text-yellow-400 bg-yellow-500/10' :
                        'text-red-400 bg-red-500/10'
                      }`}>
                        {result.resonance_check.resonance_risk}
                      </span>
                    </div>
                  )}
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
              <StabilityGauge stability={result.stability} />
              <CriticalRPMChart axial={result.axial_vibrations} lateral={result.lateral_vibrations} operatingRpm={params.rpm} />
              <VibrationMapHeatmap vibrationMap={result.vibration_map} />
              <MSEBreakdownChart mse={result.mse} />
              <StickSlipIndicator stickSlip={result.stick_slip} />
            </div>

            {/* FEA Results */}
            {feaResult && (
              <>
                {/* FEA Summary */}
                <div className="glass-panel p-6 rounded-2xl border border-indigo-500/20">
                  <h3 className="text-lg font-bold text-indigo-400 mb-3">FEA Analysis (Euler-Bernoulli FEM)</h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    {feaResult.eigenvalue?.frequencies_hz?.slice(0, 4).map((freq: number, i: number) => (
                      <div key={i} className="text-center">
                        <div className="text-xs text-gray-500">Mode {i + 1}</div>
                        <div className="font-bold text-indigo-300">{freq.toFixed(2)} Hz</div>
                        <div className="text-xs text-gray-500">{(freq * 60).toFixed(0)} RPM</div>
                      </div>
                    ))}
                  </div>
                  {feaResult.summary?.resonance_warnings?.length > 0 && (
                    <div className="mt-3 space-y-1">
                      {feaResult.summary.resonance_warnings.map((w: string, i: number) => (
                        <p key={i} className="text-xs text-red-400">&#9888; {w}</p>
                      ))}
                    </div>
                  )}
                </div>

                {/* FEA Charts */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <ModeShapePlot
                    nodePositions={feaResult.node_positions_ft || []}
                    modeShapes={feaResult.eigenvalue?.mode_shapes || []}
                    frequenciesHz={feaResult.eigenvalue?.frequencies_hz || []}
                  />
                  {feaResult.campbell && (
                    <CampbellDiagram
                      rpmValues={feaResult.campbell.rpm_values || []}
                      naturalFreqCurves={feaResult.campbell.natural_freq_curves || {}}
                      excitationLines={feaResult.campbell.excitation_lines || {}}
                      crossings={feaResult.campbell.crossings || []}
                      operatingRpm={params.rpm as number}
                    />
                  )}
                </div>
              </>
            )}

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
              <Vibrate size={48} className="mx-auto mb-4 opacity-30" />
              <p>{t('vibrations.noResults')}</p>
            </div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default VibrationsModule;
