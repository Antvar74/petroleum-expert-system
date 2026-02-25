import { useState, useCallback } from 'react';
import api from '../lib/api';
import { motion, AnimatePresence } from 'framer-motion';
import { Cylinder, Play, RefreshCw } from 'lucide-react';
import DisplacementScheduleChart from './charts/cem/DisplacementScheduleChart';
import ECDDuringCementChart from './charts/cem/ECDDuringCementChart';
import BHPScheduleChart from './charts/cem/BHPScheduleChart';
import FluidColumnDiagram from './charts/cem/FluidColumnDiagram';
import FreeFallIndicator from './charts/cem/FreeFallIndicator';
import AIAnalysisPanel from './AIAnalysisPanel';
import { useLanguage } from '../hooks/useLanguage';
import { useAIAnalysis } from '../hooks/useAIAnalysis';
import { useTranslation } from 'react-i18next';
import { useToast } from './ui/Toast';
import type { APIError } from '../types/api';

interface CementingModuleProps {
  wellId?: number;
  wellName?: string;
}

const CementingModule: React.FC<CementingModuleProps> = ({ wellId, wellName = '' }) => {
  const [activeTab, setActiveTab] = useState('input');
  const [loading, setLoading] = useState(false);

  const [params, setParams] = useState({
    casing_od_in: 9.625, casing_id_in: 8.681, hole_id_in: 12.25,
    casing_shoe_md_ft: 10000, casing_shoe_tvd_ft: 9500,
    toc_md_ft: 5000, toc_tvd_ft: 4750,
    float_collar_md_ft: 9900,
    mud_weight_ppg: 10.5, spacer_density_ppg: 11.5,
    lead_cement_density_ppg: 13.5, tail_cement_density_ppg: 16.0,
    tail_length_ft: 500, spacer_volume_bbl: 25, excess_pct: 50,
    rat_hole_ft: 50, pump_rate_bbl_min: 5.0,
    pv_mud: 15, yp_mud: 10,
    fracture_gradient_ppg: 16.5, pore_pressure_ppg: 9.0,
  });

  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const { language } = useLanguage();
  const { t } = useTranslation();
  const { addToast } = useToast();

  const { aiAnalysis, isAnalyzing, runAnalysis, provider, setProvider, availableProviders, setAiAnalysis } = useAIAnalysis({
    module: 'cementing',
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
        ? `/wells/${wellId}/cementing`
        : `/calculate/cementing`;
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

  const statusColor = (status: string) => {
    if (status?.includes('CRITICAL')) return 'text-red-400 bg-red-500/10';
    if (status?.includes('WARNING') || status?.includes('CAUTION')) return 'text-yellow-400 bg-yellow-500/10';
    return 'text-green-400 bg-green-500/10';
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Cylinder className="text-teal-400" size={28} />
        <h2 className="text-2xl font-bold">{t('cementing.title')}</h2>
        <span className="text-sm text-gray-500">{t('cementing.subtitle')}</span>
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
            <div className="glass-panel p-6 rounded-2xl border border-white/5 space-y-6">
              <div>
                <h3 className="text-lg font-bold mb-3">{t('cementing.sections.geometry')}</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {[
                    { key: 'casing_od_in', label: 'OD Casing (in)', step: '0.125' },
                    { key: 'casing_id_in', label: 'ID Casing (in)', step: '0.001' },
                    { key: 'hole_id_in', label: 'ID Hoyo (in)', step: '0.25' },
                    { key: 'casing_shoe_md_ft', label: 'Zapata MD (ft)', step: '100' },
                    { key: 'casing_shoe_tvd_ft', label: 'Zapata TVD (ft)', step: '100' },
                    { key: 'toc_md_ft', label: 'TOC MD (ft)', step: '100' },
                    { key: 'toc_tvd_ft', label: 'TOC TVD (ft)', step: '100' },
                    { key: 'float_collar_md_ft', label: 'Float Collar MD (ft)', step: '10' },
                  ].map(({ key, label, step }) => (
                    <div key={key} className="space-y-1">
                      <label className="text-xs text-gray-400">{label}</label>
                      <input type="number" step={step} value={(params as Record<string, number>)[key]}
                        onChange={e => updateParam(key, e.target.value)}
                        className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:border-teal-500 focus:outline-none" />
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <h3 className="text-lg font-bold mb-3">{t('cementing.sections.fluids')}</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {[
                    { key: 'mud_weight_ppg', label: 'Peso Lodo (ppg)', step: '0.1' },
                    { key: 'spacer_density_ppg', label: 'Densidad Spacer (ppg)', step: '0.1' },
                    { key: 'lead_cement_density_ppg', label: 'Lead Cement (ppg)', step: '0.1' },
                    { key: 'tail_cement_density_ppg', label: 'Tail Cement (ppg)', step: '0.1' },
                    { key: 'tail_length_ft', label: 'Long. Tail (ft)', step: '50' },
                    { key: 'spacer_volume_bbl', label: 'Vol. Spacer (bbl)', step: '5' },
                    { key: 'excess_pct', label: 'Exceso (%)', step: '5' },
                    { key: 'rat_hole_ft', label: 'Rat Hole (ft)', step: '10' },
                  ].map(({ key, label, step }) => (
                    <div key={key} className="space-y-1">
                      <label className="text-xs text-gray-400">{label}</label>
                      <input type="number" step={step} value={(params as Record<string, number>)[key]}
                        onChange={e => updateParam(key, e.target.value)}
                        className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:border-teal-500 focus:outline-none" />
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <h3 className="text-lg font-bold mb-3">{t('cementing.sections.operations')}</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {[
                    { key: 'pump_rate_bbl_min', label: 'Pump Rate (bbl/min)', step: '0.5' },
                    { key: 'pv_mud', label: 'PV Lodo (cP)', step: '1' },
                    { key: 'yp_mud', label: 'YP Lodo (lb/100ft²)', step: '1' },
                    { key: 'fracture_gradient_ppg', label: 'Grad. Fractura (ppg)', step: '0.1' },
                    { key: 'pore_pressure_ppg', label: 'Presión Poro (ppg)', step: '0.1' },
                  ].map(({ key, label, step }) => (
                    <div key={key} className="space-y-1">
                      <label className="text-xs text-gray-400">{label}</label>
                      <input type="number" step={step} value={(params as Record<string, number>)[key]}
                        onChange={e => updateParam(key, e.target.value)}
                        className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:border-teal-500 focus:outline-none" />
                    </div>
                  ))}
                </div>
              </div>

              <button onClick={calculate} disabled={loading}
                className="mt-4 flex items-center gap-2 px-6 py-3 bg-teal-600 hover:bg-teal-700 rounded-lg font-medium transition-colors disabled:opacity-50">
                {loading ? <RefreshCw size={16} className="animate-spin" /> : <Play size={16} />}
                {loading ? t('cementing.simulating') : t('cementing.simulate')}
              </button>
            </div>
          </motion.div>
        )}

        {activeTab === 'results' && result && (
          <motion.div key="results" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-6">
            {/* Summary Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { label: t('cementing.totalCement'), value: `${result.summary?.total_cement_bbl} bbl`, sub: `${result.summary?.total_cement_sacks} ${t('cementing.sacks')}`, color: 'text-teal-400' },
                { label: t('cementing.jobTime'), value: `${result.summary?.job_time_hrs} hrs`, color: 'text-blue-400' },
                { label: t('cementing.maxECD'), value: `${result.summary?.max_ecd_ppg} ppg`, sub: `${t('cementing.margin')}: ${result.summary?.fracture_margin_ppg} ppg`, color: result.summary?.fracture_margin_ppg < 0 ? 'text-red-400' : 'text-green-400' },
                { label: t('cementing.maxBHP'), value: `${result.summary?.max_bhp_psi} psi`, color: 'text-orange-400' },
              ].map((item, i) => (
                <div key={i} className="glass-panel p-4 rounded-xl border border-white/5 text-center">
                  <div className="text-xs text-gray-500 mb-1">{item.label}</div>
                  <div className={`text-xl font-bold ${item.color}`}>{item.value}</div>
                  {item.sub && <div className="text-xs text-gray-500 mt-1">{item.sub}</div>}
                </div>
              ))}
            </div>

            {/* Status Banner */}
            <div className={`glass-panel p-4 rounded-xl border ${result.summary?.ecd_status?.includes('CRITICAL') ? 'border-red-500/30' : result.summary?.ecd_status?.includes('WARNING') ? 'border-yellow-500/30' : 'border-green-500/30'}`}>
              <div className={`text-sm font-bold ${statusColor(result.summary?.ecd_status)}`}>
                {result.summary?.ecd_status}
              </div>
            </div>

            {/* Volumes Detail */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="glass-panel p-6 rounded-2xl border border-white/5">
                <h3 className="text-lg font-bold mb-3">{t('cementing.volumes')}</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between"><span className="text-gray-400">Lead Cement:</span><span className="font-mono">{result.volumes?.lead_cement_bbl} bbl ({result.volumes?.lead_cement_sacks} sacos)</span></div>
                  <div className="flex justify-between"><span className="text-gray-400">Tail Cement:</span><span className="font-mono">{result.volumes?.tail_cement_bbl} bbl ({result.volumes?.tail_cement_sacks} sacos)</span></div>
                  <div className="flex justify-between"><span className="text-gray-400">Spacer:</span><span className="font-mono">{result.volumes?.spacer_volume_bbl} bbl</span></div>
                  <div className="flex justify-between"><span className="text-gray-400">Displacement:</span><span className="font-mono">{result.volumes?.displacement_volume_bbl} bbl</span></div>
                  <div className="flex justify-between border-t border-white/10 pt-2"><span className="text-gray-300 font-bold">Total Bombeo:</span><span className="font-mono font-bold text-teal-400">{result.volumes?.total_pump_volume_bbl} bbl</span></div>
                </div>
              </div>
              <div className="glass-panel p-6 rounded-2xl border border-white/5">
                <h3 className="text-lg font-bold mb-3">{t('cementing.freeFallUtube')}</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between"><span className="text-gray-400">Free-Fall:</span><span className={`font-mono ${result.free_fall?.free_fall_occurs ? 'text-yellow-400' : 'text-green-400'}`}>{result.free_fall?.free_fall_height_ft} ft</span></div>
                  <div><span className="text-gray-500 text-xs">{result.free_fall?.explanation}</span></div>
                  <div className="border-t border-white/10 pt-2"></div>
                  <div className="flex justify-between"><span className="text-gray-400">U-Tube:</span><span className={`font-mono ${result.utube?.utube_occurs ? 'text-yellow-400' : 'text-green-400'}`}>{result.utube?.pressure_imbalance_psi} psi</span></div>
                  <div><span className="text-gray-500 text-xs">{result.utube?.explanation}</span></div>
                  <div className="flex justify-between"><span className="text-gray-400">Lift Pressure:</span><span className="font-mono">{result.lift_pressure?.lift_pressure_psi} psi</span></div>
                </div>
              </div>
            </div>

            {/* Alerts */}
            {result.summary?.alerts?.length > 0 && (
              <div className="glass-panel p-6 rounded-2xl border border-yellow-500/20">
                <h3 className="text-lg font-bold text-yellow-400 mb-3">&#9888; {t('common.alerts')}</h3>
                <ul className="space-y-2">
                  {result.summary.alerts.map((alert: string, i: number) => (
                    <li key={i} className="text-sm text-yellow-300 flex items-start gap-2">
                      <span className="mt-1">&bull;</span>{alert}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <DisplacementScheduleChart displacement={result.displacement} />
              <ECDDuringCementChart ecd={result.ecd_during_job} />
              <BHPScheduleChart bhp={result.bhp_schedule} />
              <FluidColumnDiagram volumes={result.volumes} />
              <FreeFallIndicator freeFall={result.free_fall} utube={result.utube} />
            </div>

            {/* AI Analysis */}
            <AIAnalysisPanel
              moduleName="Cementing"
              moduleIcon={Cylinder}
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
          <motion.div key="no-results" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <div className="glass-panel p-12 rounded-2xl border border-white/5 text-center text-gray-500">
              <Cylinder size={48} className="mx-auto mb-4 opacity-30" />
              <p>{t('cementing.noResults')}</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default CementingModule;
