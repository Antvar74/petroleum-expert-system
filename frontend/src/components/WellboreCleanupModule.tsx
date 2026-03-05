import { useState, useCallback } from 'react';
import api from '../lib/api';
import { motion, AnimatePresence } from 'framer-motion';
import { Droplets, Play, RefreshCw } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import FlowRateSensitivity from './charts/cu/FlowRateSensitivity';
import AnnularVelocityChart from './charts/cu/AnnularVelocityChart';
import CuttingsConcentrationGauge from './charts/cu/CuttingsConcentrationGauge';
import CleanupEfficiencyProfile from './charts/cu/CleanupEfficiencyProfile';
import AIAnalysisPanel from './AIAnalysisPanel';
import { useLanguage } from '../hooks/useLanguage';
import { useAIAnalysis } from '../hooks/useAIAnalysis';
import { useToast } from './ui/Toast';
import type { APIError } from '../types/api';

// ── Slip velocity helpers (matching engine slip_velocity.py) ────────────
/** Moore correlation — vertical wells (Stokes / Intermediate regimes) */
const mooreSlipVelocity = (mw: number, pv: number, yp: number, cs: number, cd: number): number => {
  if (cs <= 0 || mw <= 0) return 0;
  const muA = Math.max(pv + 5.0 * yp, 1.0);
  const dRho = cd - mw;
  if (dRho <= 0) return 0;
  const reP = 15.47 * mw * cs * Math.sqrt(dRho * cs / mw) / muA;
  if (reP < 1) return 113.4 * cs * cs * dRho / muA;        // Stokes
  return 175.0 * cs * Math.sqrt(dRho / mw);                 // Intermediate / Newton
};

/** Larsen (SPE 36383) — deviated wells, inc ≥ 30° */
const larsenSlipVelocity = (vsVert: number, inc: number, rpm: number): number => {
  const r = inc * Math.PI / 180;
  // Inclination factor
  const fInc = inc < 10 ? 1.0
    : inc <= 60 ? 1.0 + 0.3 * Math.sin(2.0 * r)
    : 1.0 + 0.2 * (1.0 - Math.cos(r));
  // Vertical component corrected
  let vsInc = vsVert * Math.abs(Math.cos(r)) * fInc;
  if (inc > 80) vsInc = Math.max(vsInc, vsVert * 0.1);
  // RPM factor
  let fRpm = inc > 30
    ? (inc >= 75 ? 1.0 - Math.min(rpm / 150, 0.5) : 1.0 - Math.min(rpm / 200, 0.4))
    : 1.0;
  fRpm = Math.max(fRpm, 0.3);
  return vsInc * fRpm;
};

interface WellboreCleanupModuleProps {
  wellId?: number;
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
  const [result, setResult] = useState<Record<string, unknown> | null>(null);

  // AI Analysis
  const { language } = useLanguage();
  const { t } = useTranslation();
  const { addToast } = useToast();

  const { aiAnalysis, isAnalyzing, runAnalysis, provider, setProvider, availableProviders, setAiAnalysis } = useAIAnalysis({
    module: 'wellbore-cleanup',
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
        ? `/wells/${wellId}/wellbore-cleanup`
        : `/calculate/wellbore-cleanup`;
      const res = await api.post(url, params);
      setResult(res.data);
      setActiveTab('results');
    } catch (e: unknown) {
      addToast('Error: ' + (e as APIError).response?.data?.detail || (e as APIError).message, 'error');
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
    if (q === 'Good') return 'text-emerald-400 bg-emerald-500/10';
    if (q === 'Fair') return 'text-yellow-400 bg-yellow-500/10';
    return 'text-red-400 bg-red-500/10';
  };

  // Sensitivity data for FlowRateSensitivity chart — Luo (1992) 4-factor HCI
  const sensitivityData = result ? (() => {
    const va_min = params.inclination > 60 ? 150 : params.inclination >= 30 ? 130 : 120;
    const rpmF = 0.7 + 0.3 * Math.min(params.rpm / 120, 1);
    const rheoF = 0.6 + 0.4 * Math.min(params.yp / 15, 1);
    const densF = 0.8 + 0.2 * Math.min(params.mud_weight / 10, 1);
    const vsMoore = mooreSlipVelocity(params.mud_weight, params.pv, params.yp, params.cutting_size, params.cutting_density);
    const vs = params.inclination >= 30
      ? larsenSlipVelocity(vsMoore, params.inclination, params.rpm)
      : vsMoore;
    return Array.from({ length: 13 }, (_, i) => {
      const q = 200 + i * 50;
      const va = 24.51 * q / (params.hole_id ** 2 - params.pipe_od ** 2);
      const velRatio = Math.min(va / va_min, 1.5);
      const hci = velRatio * rpmF * rheoF * densF;
      const ctr = va > 0 ? Math.max((va - vs) / va, 0) : 0;
      return { flow_rate: q, hci: Math.round(hci * 100) / 100, ctr: Math.round(ctr * 100) / 100 };
    });
  })() : [];

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
                      value={(params as Record<string, unknown>)[key]}
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
                { label: t('wellboreCleanup.hci'), value: result.summary?.hole_cleaning_index, color: (result.summary?.hole_cleaning_index >= 0.90) ? 'text-green-400' : (result.summary?.hole_cleaning_index >= 0.70) ? 'text-emerald-400' : (result.summary?.hole_cleaning_index >= 0.50) ? 'text-yellow-400' : 'text-red-400' },
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
                <div>
                  <span className="text-gray-400">{t('wellboreCleanup.ecdCuttings')}:</span>{' '}
                  <span className="font-mono">{result.summary?.effective_mud_weight_ppg} ppg</span>{' '}
                  <span className={`text-xs font-bold ${(result.summary?.cuttings_ecd_ppg || 0) > 0.5 ? 'text-red-400' : (result.summary?.cuttings_ecd_ppg || 0) > 0.2 ? 'text-yellow-400' : 'text-green-400'}`}>
                    (+{result.summary?.cuttings_ecd_ppg} ppg)
                  </span>
                </div>
                <div>
                  <span className="text-gray-400">{t('wellboreCleanup.bottomsUp')}:</span>{' '}
                  <span className="font-mono">{result.summary?.bottoms_up_min} min</span>{' '}
                  <span className="text-xs text-gray-500">({result.summary?.annular_volume_bbl} bbl)</span>
                </div>
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
                  const vsMoore = mooreSlipVelocity(params.mud_weight, params.pv, params.yp, params.cutting_size, params.cutting_density);
                  const rF = 0.7 + 0.3 * Math.min(params.rpm / 120, 1);
                  const rheF = 0.6 + 0.4 * Math.min(params.yp / 15, 1);
                  const dF = 0.8 + 0.2 * Math.min(params.mud_weight / 10, 1);
                  // Base HCI at 0° (Luo with cap) — engine KPI anchor
                  const hciBase = Math.min(va / 120, 1.5) * rF * rheF * dF;
                  return Array.from({ length: 19 }, (_, i) => {
                    const inc = i * 5; // 0° to 90°
                    const incRad = inc * Math.PI / 180;
                    // V_min continuous: sin(θ) ramps 120→180; sin(2θ) adds avalanche penalty 40-65°
                    const vaMinEff = 120 + 60 * Math.sin(incRad) + 25 * Math.sin(2 * incRad);
                    // HCI: normalized to engine KPI at 0°, smooth curve via continuous V_min
                    const hci = hciBase * 120 / vaMinEff;
                    // Slip: Moore <30°, Larsen F_inc ≥30° (SPE 36383 simplified)
                    const vsSlip = inc >= 30 ? vsMoore * (1 + 0.3 * Math.sin(incRad)) : vsMoore;
                    // Bed formation factor: sin²(θ) — max 30% efficiency loss at 90°
                    const bedFactor = 1.0 - 0.3 * Math.pow(Math.sin(incRad), 2);
                    // CTR: slip + bed formation penalty, clamped to [0, 1]
                    const ctr = Math.min(1.0, Math.max(0, (va - vsSlip) / va * bedFactor));
                    return {
                      inclination: inc,
                      hci: Math.round(hci * 1000) / 1000,
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
              <Droplets size={48} className="mx-auto mb-4 opacity-30" />
              <p>{t('wellboreCleanup.noResults')}</p>
            </div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default WellboreCleanupModule;
