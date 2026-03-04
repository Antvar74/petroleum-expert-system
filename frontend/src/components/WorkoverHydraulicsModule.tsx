import { useState, useCallback } from 'react';
import api from '../lib/api';
import { motion, AnimatePresence } from 'framer-motion';
import { Wrench, Play, RefreshCw } from 'lucide-react';
import CTPressureProfile from './charts/wh/CTPressureProfile';
import SnubbingForceChart from './charts/wh/SnubbingForceChart';
import WeightDragOverlay from './charts/wh/WeightDragOverlay';
import MaxReachIndicator from './charts/wh/MaxReachIndicator';
import AIAnalysisPanel from './AIAnalysisPanel';
import { useLanguage } from '../hooks/useLanguage';
import { useAIAnalysis } from '../hooks/useAIAnalysis';
import { useTranslation } from 'react-i18next';
import { useToast } from './ui/Toast';
import type { APIError } from '../types/api';

interface WorkoverHydraulicsModuleProps {
  wellId?: number;
  wellName?: string;
}

const WorkoverHydraulicsModule: React.FC<WorkoverHydraulicsModuleProps> = ({ wellId, wellName = '' }) => {
  const [activeTab, setActiveTab] = useState('input');
  const [loading, setLoading] = useState(false);

  const [params, setParams] = useState({
    flow_rate: 80,
    mud_weight: 8.6,
    pv: 12,
    yp: 8,
    ct_od: 2.0,
    wall_thickness: 0.156,
    ct_length: 10000,
    hole_id: 4.892,
    tvd: 10000,
    inclination: 0,
    friction_factor: 0.25,
    wellhead_pressure: 0,
    reservoir_pressure: 5200,
    yield_strength_psi: 80000,
    bht_f: 0,
    t_surface_f: 80,
  });

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [result, setResult] = useState<any>(null);
  useLanguage();
  const { t } = useTranslation();
  const { addToast } = useToast();

  const { aiAnalysis, isAnalyzing, runAnalysis, provider, setProvider, availableProviders } = useAIAnalysis({
    module: 'workover-hydraulics',
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
        ? `/wells/${wellId}/workover-hydraulics`
        : `/calculate/workover-hydraulics`;
      const res = await api.post(url, params);
      setResult(res.data);
      setActiveTab('results');
    } catch (e: unknown) {
      addToast('Error: ' + ((e as APIError).response?.data?.detail ?? (e as APIError).message ?? 'Unknown error'), 'error');
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
        <Wrench className="text-teal-400" size={28} />
        <h2 className="text-2xl font-bold">{t('workoverHyd.title')}</h2>
        <span className="text-sm text-gray-500">{t('workoverHyd.subtitle')}</span>
      </div>

      <div className="flex gap-2 border-b border-white/10 pb-2">
        {tabs.map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              activeTab === tab.id ? 'bg-teal-500/20 text-teal-400 border border-teal-500/30' : 'text-gray-400 hover:text-gray-200'
            }`}>{tab.label}</button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        {activeTab === 'input' && (
          <motion.div key="input" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="glass-panel p-6 rounded-2xl border border-white/5">
              <h3 className="text-lg font-bold mb-4">{t('workoverHyd.sections.ctProps')}</h3>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                {[
                  { key: 'ct_od', label: t('workoverHyd.ctOD'), step: '0.125' },
                  { key: 'wall_thickness', label: 'Wall Thickness (in)', step: '0.01' },
                  { key: 'ct_length', label: t('workoverHyd.ctLength'), step: '500' },
                  { key: 'hole_id', label: t('workoverHyd.casingID'), step: '0.125' },
                  { key: 'flow_rate', label: t('workoverHyd.flowRate'), step: '10' },
                  { key: 'mud_weight', label: t('workoverHyd.mudWeight'), step: '0.1' },
                  { key: 'pv', label: t('workoverHyd.pv'), step: '1' },
                  { key: 'yp', label: t('workoverHyd.yp'), step: '1' },
                  { key: 'tvd', label: 'TVD (ft)', step: '500' },
                  { key: 'inclination', label: t('workoverHyd.inclination'), step: '5' },
                  { key: 'friction_factor', label: 'Friction Factor', step: '0.05' },
                  { key: 'wellhead_pressure', label: 'Wellhead Pressure (psi)', step: '100' },
                  { key: 'reservoir_pressure', label: 'Reservoir Pressure (psi)', step: '100' },
                  { key: 'yield_strength_psi', label: 'Yield CT (psi)', step: '5000' },
                  { key: 'bht_f', label: 'BHT (°F) — 0 = not provided', step: '10' },
                  { key: 't_surface_f', label: 'T Surface (°F)', step: '5' },
                ].map(({ key, label, step }) => (
                  <div key={key} className="space-y-1">
                    <label className="text-xs text-gray-400">{label}</label>
                    <input type="number" step={step}
                      value={(params as Record<string, number>)[key]}
                      onChange={e => updateParam(key, e.target.value)}
                      className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:border-teal-500 focus:outline-none"
                    />
                  </div>
                ))}
              </div>
              <button onClick={calculate} disabled={loading}
                className="mt-6 flex items-center gap-2 px-6 py-3 bg-teal-600 hover:bg-teal-700 rounded-lg font-medium transition-colors disabled:opacity-50">
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
                { label: t('workoverHyd.pressureLoss'), value: `${result.summary?.total_pressure_loss_psi} psi`, color: 'text-teal-400' },
                { label: t('workoverHyd.buoyedWeight'), value: `${result.summary?.buoyed_weight_lb} lb`, color: 'text-cyan-400' },
                { label: t('workoverHyd.snubbingForce'), value: `${Math.abs(result.summary?.snubbing_force_lb ?? 0)} lb ${result.summary?.pipe_light ? '(Push)' : '(Heavy)'}`, color: result.summary?.pipe_light ? 'text-red-400' : 'text-green-400' },
                { label: t('workoverHyd.maxReach'), value: `${result.summary?.max_reach_ft} ft`, color: 'text-purple-400' },
              ].map((item, i) => (
                <div key={i} className="glass-panel p-4 rounded-xl border border-white/5 text-center">
                  <div className="text-xs text-gray-500 mb-1">{item.label}</div>
                  <div className={`text-xl font-bold ${item.color}`}>{item.value}</div>
                </div>
              ))}
            </div>

            {/* Hydraulics Detail */}
            <div className="glass-panel p-6 rounded-2xl border border-white/5">
              <h3 className="text-lg font-bold mb-4">{t('workoverHyd.ctHydraulics')}</h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                <div><span className="text-gray-400">Pérd. Tubería:</span> <span className="font-mono">{result.hydraulics?.pipe_loss_psi} psi</span></div>
                <div><span className="text-gray-400">Pérd. Anular:</span> <span className="font-mono">{result.hydraulics?.annular_loss_psi} psi</span></div>
                <div><span className="text-gray-400">Vel. Tubería:</span> <span className="font-mono">{result.hydraulics?.pipe_velocity_ftmin} ft/min</span></div>
                <div><span className="text-gray-400">Vel. Anular:</span> <span className="font-mono">{result.hydraulics?.annular_velocity_ftmin} ft/min</span></div>
                <div><span className="text-gray-400">Régimen Pipe:</span> <span className="font-mono">{result.hydraulics?.pipe_regime}</span></div>
                <div><span className="text-gray-400">Régimen Anular:</span> <span className="font-mono">{result.hydraulics?.annular_regime}</span></div>
              </div>
            </div>

            {/* Force Analysis */}
            <div className="glass-panel p-6 rounded-2xl border border-white/5">
              <h3 className="text-lg font-bold mb-4">{t('workoverHyd.forceAnalysis')}</h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                <div><span className="text-gray-400">Peso Aire:</span> <span className="font-mono">{result.weight_analysis?.air_weight_lb} lb</span></div>
                <div><span className="text-gray-400">Factor Flotación:</span> <span className="font-mono">{result.weight_analysis?.buoyancy_factor}</span></div>
                <div><span className="text-gray-400">Drag:</span> <span className="font-mono">{result.drag_analysis?.drag_force_lb} lb</span></div>
                <div><span className="text-gray-400">Pipe Light:</span> <span className={`font-bold ${result.snubbing?.pipe_light ? 'text-red-400' : 'text-green-400'}`}>{result.snubbing?.pipe_light ? 'Sí' : 'No'}</span></div>
                <div><span className="text-gray-400">Punto Light/Heavy:</span> <span className="font-mono">{result.snubbing?.light_heavy_depth_ft} ft</span></div>
                <div><span className="text-gray-400">Factor Limitante:</span> <span className="font-mono">{result.max_reach?.limiting_factor}</span></div>
              </div>
            </div>

            {/* Kill Data */}
            <div className="glass-panel p-6 rounded-2xl border border-white/5">
              <h3 className="text-lg font-bold mb-4">{t('workoverHyd.controlData')}</h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                <div><span className="text-gray-400">Peso Control:</span> <span className="font-mono">{result.kill_data?.kill_weight_ppg} ppg</span></div>
                <div><span className="text-gray-400">BHP Requerido:</span> <span className="font-mono">{result.kill_data?.required_bhp_psi} psi</span></div>
                <div><span className="text-gray-400">BHP Actual:</span> <span className="font-mono">{result.kill_data?.current_bhp_psi} psi</span></div>
                <div><span className="text-gray-400">Sobrebalance:</span> <span className="font-mono">{result.kill_data?.overbalance_psi} psi</span></div>
                <div><span className="text-gray-400">Estado:</span> <span className={`font-bold ${result.kill_data?.status?.includes('UNDER') ? 'text-red-400' : 'text-green-400'}`}>{result.kill_data?.status}</span></div>
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

            {/* CT Elongation Breakdown — FIX-WH-003 */}
            {result.elongation && (
              <div className="glass-panel p-6 rounded-2xl border border-white/5">
                <h3 className="text-lg font-bold mb-4">CT Elongation Breakdown</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm mb-3">
                  {[
                    { label: 'Peso (Weight)', value: result.elongation?.dL_weight_ft },
                    { label: 'Temperatura', value: result.elongation?.dL_temperature_ft },
                    { label: 'Ballooning', value: result.elongation?.dL_ballooning_ft },
                    { label: 'Bourdon', value: result.elongation?.dL_bourdon_ft },
                  ].map(({ label, value }) => (
                    <div key={label} className="glass-card p-3 rounded-lg text-center">
                      <div className="text-xs text-gray-400 mb-1">{label}</div>
                      <div className={`text-base font-mono font-bold ${Number(value) >= 0 ? 'text-cyan-400' : 'text-orange-400'}`}>
                        {Number(value) >= 0 ? '+' : ''}{Number(value)?.toFixed(3)} ft
                      </div>
                    </div>
                  ))}
                </div>
                <div className="flex gap-6 text-sm border-t border-white/10 pt-3">
                  <div><span className="text-gray-400">Total: </span><span className="font-mono font-bold text-white">{Number(result.elongation?.dL_total_ft)?.toFixed(3)} ft</span></div>
                  <div><span className="text-gray-400">Depth Correction: </span><span className="font-mono font-bold text-yellow-400">{Number(result.elongation?.depth_correction_ft)?.toFixed(3)} ft</span></div>
                  {result.elongation?.dL_temperature_ft === 0 && (
                    <div className="text-xs text-gray-500 italic">* BHT not provided — thermal elongation = 0</div>
                  )}
                </div>
              </div>
            )}

            {/* CT Fatigue — FIX-WH-004 */}
            {result.fatigue && (
              <div className="glass-panel p-6 rounded-2xl border border-white/5">
                <h3 className="text-lg font-bold mb-4">CT Fatigue Life</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm mb-3">
                  <div className="glass-card p-3 rounded-lg text-center">
                    <div className="text-xs text-gray-400 mb-1">Cycles to Failure (N_f)</div>
                    <div className="text-base font-mono font-bold text-white">{Number(result.fatigue?.cycles_to_failure)?.toLocaleString()}</div>
                  </div>
                  <div className="glass-card p-3 rounded-lg text-center">
                    <div className="text-xs text-gray-400 mb-1">Remaining Life</div>
                    <div className={`text-base font-mono font-bold ${Number(result.fatigue?.remaining_life_pct) > 50 ? 'text-green-400' : Number(result.fatigue?.remaining_life_pct) > 20 ? 'text-yellow-400' : 'text-red-400'}`}>
                      {result.fatigue?.remaining_life_pct}%
                    </div>
                  </div>
                  <div className="glass-card p-3 rounded-lg text-center">
                    <div className="text-xs text-gray-400 mb-1">Grade</div>
                    <div className="text-base font-mono font-bold text-purple-400">{result.fatigue?.sn_parameters?.grade_class}</div>
                  </div>
                  <div className="glass-card p-3 rounded-lg text-center">
                    <div className="text-xs text-gray-400 mb-1">Total Strain</div>
                    <div className="text-base font-mono font-bold text-teal-400">{Number(result.fatigue?.strain_total_pct)?.toFixed(3)}%</div>
                  </div>
                </div>
                <div className="text-xs text-gray-500">
                  Reel diameter: {result.fatigue?.reel_diameter_in}" ({result.fatigue?.reel_source}) — No trip history provided (D = 0)
                </div>
              </div>
            )}

            {/* CT Burst Rating — FIX-WH-005 */}
            {result.burst_rating && (
              <div className="glass-panel p-6 rounded-2xl border border-white/5">
                <h3 className="text-lg font-bold mb-4">CT Pressure Rating</h3>
                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div><span className="text-gray-400">Burst Rating (API 5C7):</span> <span className="font-mono font-bold text-green-400">{Number(result.burst_rating?.burst_rating_psi)?.toLocaleString()} psi</span></div>
                  <div><span className="text-gray-400">Max Operating:</span> <span className="font-mono">{result.burst_rating?.max_operating_psi} psi</span></div>
                  <div>
                    <span className="text-gray-400">Utilización:</span>{' '}
                    <span className={`font-mono font-bold ${Number(result.burst_rating?.burst_utilization_pct) < 50 ? 'text-green-400' : Number(result.burst_rating?.burst_utilization_pct) < 80 ? 'text-yellow-400' : 'text-red-400'}`}>
                      {result.burst_rating?.burst_utilization_pct}%
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <CTPressureProfile hydraulics={result.hydraulics} ctDims={result.ct_dimensions} />
              <SnubbingForceChart snubbing={result.snubbing} weightAnalysis={result.weight_analysis} />
              <WeightDragOverlay weightAnalysis={result.weight_analysis} dragAnalysis={result.drag_analysis} params={params} />
              <MaxReachIndicator maxReach={result.max_reach} ctLength={params.ct_length} />
            </div>

            {/* AI Analysis */}
            <AIAnalysisPanel
              moduleName="Workover Hydraulics"
              moduleIcon={Wrench}
              wellName={wellName}
              analysis={aiAnalysis?.analysis || null}
              confidence={aiAnalysis?.confidence || 'MEDIUM'}
              agentRole={aiAnalysis?.role || ''}
              isLoading={isAnalyzing}
              keyMetrics={[]}
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
              <Wrench size={48} className="mx-auto mb-4 opacity-30" />
              <p>{t('workoverHyd.noResults')}</p>
            </div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default WorkoverHydraulicsModule;
