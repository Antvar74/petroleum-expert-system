import { useState, useEffect } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { Shield, Save, AlertTriangle, TrendingDown, BrainCircuit } from 'lucide-react';
import { API_BASE_URL } from '../config';
import PressureScheduleChart from './charts/wc/PressureScheduleChart';
import KillMethodCompare from './charts/wc/KillMethodCompare';
import WellborePressureProfile from './charts/wc/WellborePressureProfile';
import VolumetricCyclesChart from './charts/wc/VolumetricCyclesChart';
import InfluxAnalysisGauge from './charts/wc/InfluxAnalysisGauge';
import KickMigrationChart from './charts/wc/KickMigrationChart';
import KillCirculationChart from './charts/wc/KillCirculationChart';
import AIAnalysisPanel from './AIAnalysisPanel';
import { useTranslation } from 'react-i18next';
import { useLanguage } from '../hooks/useLanguage';
import { useToast } from './ui/Toast';
import type { Provider, ProviderOption } from '../types/ai';

interface WellControlModuleProps {
  wellId?: number;
  wellName?: string;
}

const WellControlModule: React.FC<WellControlModuleProps> = ({ wellId, wellName = '' }) => {
  const [activeTab, setActiveTab] = useState('prerecord');
  const [loading, setLoading] = useState(false);

  // Pre-record state
  const [preRecord, setPreRecord] = useState({
    depth_md: 10000, depth_tvd: 9500, original_mud_weight: 10.0,
    casing_shoe_tvd: 5000, casing_id: 8.681, hole_size: 8.5,
    dp_od: 5.0, dp_id: 4.276, dp_length: 9500,
    dc_od: 6.5, dc_id: 2.813, dc_length: 500,
    scr_pressure: 800, scr_rate: 30, lot_emw: 14.0, pump_output: 0.1,
  });
  const [preRecordResult, setPreRecordResult] = useState<any>(null);

  // Active Kill state
  const [kickData, setKickData] = useState({
    sidpp: 350, sicp: 500, pit_gain: 15, kill_method: 'wait_weight',
  });
  const [killResult, setKillResult] = useState<any>(null);

  // Volumetric state
  const [volParams, setVolParams] = useState({
    mud_weight: 10.0, sicp: 500, tvd: 9500, annular_capacity: 0.05,
    lot_emw: 14.0, casing_shoe_tvd: 5000, safety_margin_psi: 50, pressure_increment_psi: 100,
  });
  const [volResult, setVolResult] = useState<any>(null);

  // Bullhead state
  const [bullheadParams, setBullheadParams] = useState({
    mud_weight: 10.0, kill_mud_weight: 11.0, depth_tvd: 9500,
    casing_shoe_tvd: 5000, lot_emw: 14.0, dp_capacity: 0.018,
    depth_md: 10000, formation_pressure: 5720,
  });
  const [bullheadResult, setBullheadResult] = useState<any>(null);

  // Simulation state
  const [simParams, setSimParams] = useState({
    well_depth_tvd: 10000, mud_weight: 10.0, kick_volume_bbl: 20,
    kick_gradient: 0.1, sidpp: 200, sicp: 350,
    annular_capacity_bbl_ft: 0.0459, time_steps_min: 120,
    kill_mud_weight: 11.0, scr: 400,
    strokes_to_bit: 1000, strokes_bit_to_surface: 2000,
    kill_method: 'drillers',
  });
  const [kickMigrationResult, setKickMigrationResult] = useState<any>(null);
  const [killSimResult, setKillSimResult] = useState<any>(null);

  // AI Analysis state
  const [aiAnalysis, setAiAnalysis] = useState<any>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const { t } = useTranslation();
  const { language, setLanguage } = useLanguage();
  const { addToast } = useToast();
  const [provider, setProvider] = useState<Provider>('auto');
  const [availableProviders, setAvailableProviders] = useState<ProviderOption[]>([
    { id: 'auto', name: 'Auto (Best Available)', name_es: 'Auto (Mejor Disponible)' }
  ]);

  // Fetch available providers on mount
  useEffect(() => {
    axios.get(`${API_BASE_URL}/providers`)
      .then(res => setAvailableProviders(res.data))
      .catch(() => { });
  }, []);

  const runAIAnalysis = async () => {
    if (!killResult && !volResult && !bullheadResult) return;
    setIsAnalyzing(true);
    try {
      const analyzeUrl = wellId
        ? `${API_BASE_URL}/wells/${wellId}/well-control/analyze`
        : `${API_BASE_URL}/analyze/module`;
      const res = await axios.post(analyzeUrl, {
        ...(wellId ? {} : { module: 'well-control', well_name: wellName || 'General Analysis' }),
        result_data: {
          kill: killResult || {},
          volumetric: volResult || {},
          bullhead: bullheadResult || {},
        },
        params: preRecord,
        language,
        provider,
      });
      setAiAnalysis(res.data);
    } catch (e: any) {
      console.error('AI analysis error:', e);
      const errMsg = e?.response?.data?.detail || e?.message || 'Connection error. Please try again.';
      setAiAnalysis({ analysis: `Error: ${errMsg}`, confidence: 'LOW', agent_role: 'Error', key_metrics: [] });
    }
    setIsAnalyzing(false);
  };

  const tabs = [
    { id: 'prerecord', label: t('wellControl.tabs.prerecord') },
    { id: 'active', label: t('wellControl.tabs.active') },
    { id: 'schedule', label: t('wellControl.tabs.schedule') },
    { id: 'pressure-profile', label: t('wellControl.tabs.pressureProfile') },
    { id: 'methods', label: t('wellControl.tabs.methods') },
    { id: 'simulation', label: t('wellControl.tabs.simulation') },
  ];

  const savePreRecord = async () => {
    setLoading(true);
    try {
      const url = wellId
        ? `${API_BASE_URL}/wells/${wellId}/kill-sheet/pre-record`
        : `${API_BASE_URL}/calculate/kill-sheet/pre-record`;
      const res = await axios.post(url, preRecord);
      setPreRecordResult(res.data);
    } catch (e: any) { addToast('Error: ' + (e.response?.data?.detail || e.message), 'error'); }
    setLoading(false);
  };

  const runKillCalc = async () => {
    setLoading(true);
    try {
      const url = wellId
        ? `${API_BASE_URL}/wells/${wellId}/kill-sheet/calculate`
        : `${API_BASE_URL}/calculate/kill-sheet/calculate`;
      // Well-scoped route pulls pre-record from DB; standalone needs it in body
      const body = wellId
        ? kickData
        : {
            ...kickData,
            depth_md: preRecord.depth_md,
            depth_tvd: preRecord.depth_tvd,
            original_mud_weight: preRecord.original_mud_weight,
            casing_shoe_tvd: preRecord.casing_shoe_tvd,
            casing_id: preRecord.casing_id,
            scr_pressure: preRecord.scr_pressure,
            scr_rate: preRecord.scr_rate,
            lot_emw: preRecord.lot_emw,
            dp_capacity: preRecordResult?.capacities_bbl_ft?.dp_capacity ?? 0,
            annular_capacity: preRecordResult?.capacities_bbl_ft?.annular_oh_dp ?? 0,
            strokes_surface_to_bit: preRecordResult?.strokes?.strokes_surface_to_bit ?? 0,
            strokes_bit_to_surface: preRecordResult?.strokes?.strokes_bit_to_surface ?? 0,
            total_strokes: preRecordResult?.strokes?.total_strokes ?? 0,
          };
      const res = await axios.post(url, body);
      setKillResult(res.data);
    } catch (e: any) { addToast('Error: ' + (e.response?.data?.detail || e.message), 'error'); }
    setLoading(false);
  };

  const runVolumetric = async () => {
    setLoading(true);
    try {
      const res = await axios.post(`${API_BASE_URL}/kill-sheet/volumetric`, volParams);
      setVolResult(res.data);
    } catch (e: any) { addToast('Error: ' + (e.response?.data?.detail || e.message), 'error'); }
    setLoading(false);
  };

  const runBullhead = async () => {
    setLoading(true);
    try {
      const res = await axios.post(`${API_BASE_URL}/kill-sheet/bullhead`, bullheadParams);
      setBullheadResult(res.data);
    } catch (e: any) { addToast('Error: ' + (e.response?.data?.detail || e.message), 'error'); }
    setLoading(false);
  };

  const runKickMigration = async () => {
    setLoading(true);
    try {
      const res = await axios.post(`${API_BASE_URL}/calculate/well-control/kick-migration`, {
        well_depth_tvd: simParams.well_depth_tvd, mud_weight: simParams.mud_weight,
        kick_volume_bbl: simParams.kick_volume_bbl, kick_gradient: simParams.kick_gradient,
        sidpp: simParams.sidpp, sicp: simParams.sicp,
        annular_capacity_bbl_ft: simParams.annular_capacity_bbl_ft,
        time_steps_min: simParams.time_steps_min,
      });
      setKickMigrationResult(res.data);
    } catch (e: any) { addToast('Error: ' + (e.response?.data?.detail || e.message), 'error'); }
    setLoading(false);
  };

  const runKillSimulation = async () => {
    setLoading(true);
    try {
      const res = await axios.post(`${API_BASE_URL}/calculate/well-control/kill-simulation`, {
        well_depth_tvd: simParams.well_depth_tvd, mud_weight: simParams.mud_weight,
        kill_mud_weight: simParams.kill_mud_weight, sidpp: simParams.sidpp,
        scr: simParams.scr, strokes_to_bit: simParams.strokes_to_bit,
        strokes_bit_to_surface: simParams.strokes_bit_to_surface,
        method: simParams.kill_method,
      });
      setKillSimResult(res.data);
    } catch (e: any) { addToast('Error: ' + (e.response?.data?.detail || e.message), 'error'); }
    setLoading(false);
  };

  const InputField = ({ label, value, onChange, step }: { label: string; value: number; onChange: (v: number) => void; step?: string }) => (
    <div>
      <label className="text-xs text-white/40 block mb-1">{label}</label>
      <input type="number" step={step || '1'} value={value} onChange={(e) => onChange(+e.target.value)} className="input-field w-full py-2 px-3 text-sm" />
    </div>
  );

  return (
    <div className="space-y-6 py-8">
      <div className="flex items-center gap-3 mb-8">
        <Shield className="text-industrial-500" size={28} />
        <h2 className="text-2xl font-bold">{t('wellControl.title')}</h2>
      </div>

      <div className="flex gap-2 mb-8 flex-wrap">
        {tabs.map((tab) => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={`px-5 py-2.5 rounded-xl text-sm font-bold transition-all ${activeTab === tab.id ? 'bg-industrial-600 text-white shadow-lg' : 'bg-white/5 text-white/40 hover:text-white hover:bg-white/10'}`}>
            {tab.label}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        {/* Pre-Record Kill Sheet */}
        {activeTab === 'prerecord' && (
          <motion.div key="prerecord" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="space-y-6">
            <div className="glass-panel p-6 rounded-2xl border border-white/5">
              <h3 className="font-bold text-lg mb-4">{t('wellControl.prerecord.title')}</h3>
              <p className="text-white/40 text-sm mb-6">{t('wellControl.prerecord.description')}</p>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                <InputField label={t('wellControl.prerecord.depthMD')} value={preRecord.depth_md} onChange={(v) => setPreRecord({ ...preRecord, depth_md: v })} />
                <InputField label={t('wellControl.prerecord.depthTVD')} value={preRecord.depth_tvd} onChange={(v) => setPreRecord({ ...preRecord, depth_tvd: v })} />
                <InputField label={t('wellControl.prerecord.mudWeight')} value={preRecord.original_mud_weight} onChange={(v) => setPreRecord({ ...preRecord, original_mud_weight: v })} step="0.1" />
                <InputField label={t('wellControl.prerecord.casingShoe')} value={preRecord.casing_shoe_tvd} onChange={(v) => setPreRecord({ ...preRecord, casing_shoe_tvd: v })} />
                <InputField label={t('wellControl.prerecord.casingID')} value={preRecord.casing_id} onChange={(v) => setPreRecord({ ...preRecord, casing_id: v })} step="0.001" />
                <InputField label={t('wellControl.prerecord.holeSize')} value={preRecord.hole_size} onChange={(v) => setPreRecord({ ...preRecord, hole_size: v })} step="0.125" />
                <InputField label={t('wellControl.prerecord.dpOD')} value={preRecord.dp_od} onChange={(v) => setPreRecord({ ...preRecord, dp_od: v })} step="0.1" />
                <InputField label={t('wellControl.prerecord.dpID')} value={preRecord.dp_id} onChange={(v) => setPreRecord({ ...preRecord, dp_id: v })} step="0.001" />
                <InputField label={t('wellControl.prerecord.dpLength')} value={preRecord.dp_length} onChange={(v) => setPreRecord({ ...preRecord, dp_length: v })} />
                <InputField label={t('wellControl.prerecord.dcOD')} value={preRecord.dc_od} onChange={(v) => setPreRecord({ ...preRecord, dc_od: v })} step="0.1" />
                <InputField label={t('wellControl.prerecord.dcID')} value={preRecord.dc_id} onChange={(v) => setPreRecord({ ...preRecord, dc_id: v })} step="0.001" />
                <InputField label={t('wellControl.prerecord.dcLength')} value={preRecord.dc_length} onChange={(v) => setPreRecord({ ...preRecord, dc_length: v })} />
                <InputField label={t('wellControl.prerecord.scrPressure')} value={preRecord.scr_pressure} onChange={(v) => setPreRecord({ ...preRecord, scr_pressure: v })} />
                <InputField label={t('wellControl.prerecord.scrRate')} value={preRecord.scr_rate} onChange={(v) => setPreRecord({ ...preRecord, scr_rate: v })} />
                <InputField label={t('wellControl.prerecord.lotEmw')} value={preRecord.lot_emw} onChange={(v) => setPreRecord({ ...preRecord, lot_emw: v })} step="0.1" />
                <InputField label={t('wellControl.prerecord.pumpOutput')} value={preRecord.pump_output} onChange={(v) => setPreRecord({ ...preRecord, pump_output: v })} step="0.01" />
              </div>

              <button onClick={savePreRecord} disabled={loading} className="btn-primary flex items-center gap-2 disabled:opacity-50">
                <Save size={16} /> {loading ? t('common.saving') : t('wellControl.prerecord.saveKillSheet')}
              </button>
            </div>

            {preRecordResult && (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="glass-panel p-4 rounded-xl border border-white/5 text-center">
                    <p className="text-xs text-white/40 mb-1">{t('wellControl.prerecord.hydrostatic')}</p>
                    <p className="text-xl font-bold text-industrial-400">{preRecordResult.reference_values?.hydrostatic_psi}</p>
                    <p className="text-xs text-white/30">psi</p>
                  </div>
                  <div className="glass-panel p-4 rounded-xl border border-white/5 text-center">
                    <p className="text-xs text-white/40 mb-1">{t('wellControl.prerecord.maasp')}</p>
                    <p className="text-xl font-bold text-industrial-400">{preRecordResult.reference_values?.maasp_psi}</p>
                    <p className="text-xs text-white/30">psi</p>
                  </div>
                  <div className="glass-panel p-4 rounded-xl border border-white/5 text-center">
                    <p className="text-xs text-white/40 mb-1">{t('wellControl.prerecord.strokesToBit')}</p>
                    <p className="text-xl font-bold text-white">{preRecordResult.strokes?.strokes_surface_to_bit}</p>
                  </div>
                  <div className="glass-panel p-4 rounded-xl border border-white/5 text-center">
                    <p className="text-xs text-white/40 mb-1">{t('wellControl.prerecord.totalVolume')}</p>
                    <p className="text-xl font-bold text-white">{preRecordResult.volumes_bbl?.total_well_volume}</p>
                    <p className="text-xs text-white/30">bbl</p>
                  </div>
                </div>
              </motion.div>
            )}
          </motion.div>
        )}

        {/* Active Kill */}
        {activeTab === 'active' && (
          <motion.div key="active" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="space-y-6">
            <div className="glass-panel p-6 rounded-2xl border border-white/5">
              <h3 className="font-bold text-lg mb-4">{t('wellControl.active.title')}</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                <InputField label={t('wellControl.active.sidpp')} value={kickData.sidpp} onChange={(v) => setKickData({ ...kickData, sidpp: v })} />
                <InputField label={t('wellControl.active.sicp')} value={kickData.sicp} onChange={(v) => setKickData({ ...kickData, sicp: v })} />
                <InputField label={t('wellControl.active.pitGain')} value={kickData.pit_gain} onChange={(v) => setKickData({ ...kickData, pit_gain: v })} />
                <div>
                  <label className="text-xs text-white/40 block mb-1">{t('wellControl.active.killMethod')}</label>
                  <select value={kickData.kill_method} onChange={(e) => setKickData({ ...kickData, kill_method: e.target.value })} className="input-field w-full py-2 px-3 text-sm">
                    <option value="wait_weight">{t('wellControl.active.waitWeight')}</option>
                    <option value="drillers">{t('wellControl.active.drillers')}</option>
                  </select>
                </div>
              </div>
              <button onClick={runKillCalc} disabled={loading} className="btn-primary flex items-center gap-2 disabled:opacity-50">
                <AlertTriangle size={16} /> {loading ? t('common.calculating') : t('wellControl.active.calculateKill')}
              </button>
            </div>

            {killResult && (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
                {/* Alerts */}
                {killResult.alerts?.length > 0 && (
                  <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4">
                    {killResult.alerts.map((a: string, i: number) => (
                      <p key={i} className="text-red-400 text-sm font-bold">- {a}</p>
                    ))}
                  </div>
                )}

                {/* Influx Analysis Gauge + Key values */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <InfluxAnalysisGauge
                    influxType={killResult.influx_type || 'Unknown'}
                    influxHeight={killResult.influx_height_ft || 0}
                    formationPressure={killResult.formation_pressure_psi || 0}
                    killMudWeight={killResult.kill_mud_weight_ppg || 0}
                    sidpp={kickData.sidpp}
                    sicp={kickData.sicp}
                  />
                  <div className="md:col-span-2 grid grid-cols-2 gap-4 content-start">
                    {[
                      { label: t('wellControl.active.formationPressure'), value: killResult.formation_pressure_psi, unit: 'psi', color: 'text-red-400' },
                      { label: t('wellControl.active.killMudWeight'), value: killResult.kill_mud_weight_ppg, unit: 'ppg', color: 'text-industrial-400' },
                      { label: t('wellControl.active.icp'), value: killResult.icp_psi, unit: 'psi', color: 'text-orange-400' },
                      { label: t('wellControl.active.fcp'), value: killResult.fcp_psi, unit: 'psi', color: 'text-green-400' },
                      { label: t('wellControl.active.maasp'), value: killResult.maasp_psi, unit: 'psi', color: 'text-yellow-400' },
                      { label: t('wellControl.active.mwIncrease'), value: killResult.mud_weight_increase_ppg, unit: 'ppg', color: 'text-white' },
                    ].map((card, i) => (
                      <div key={i} className="glass-panel p-4 rounded-xl border border-white/5 text-center">
                        <p className="text-xs text-white/40 mb-1">{card.label}</p>
                        <p className={`text-xl font-bold ${card.color}`}>{card.value}</p>
                        {card.unit && <p className="text-xs text-white/30">{card.unit}</p>}
                      </div>
                    ))}
                  </div>
                </div>
              </motion.div>
            )}
          </motion.div>
        )}

        {/* Pressure Schedule */}
        {activeTab === 'schedule' && (
          <motion.div key="schedule" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="space-y-6">
            {killResult?.pressure_schedule ? (
              <>
                {/* Chart */}
                <PressureScheduleChart
                  schedule={killResult.pressure_schedule}
                  icp={killResult.icp_psi}
                  fcp={killResult.fcp_psi}
                  maasp={killResult.maasp_psi}
                  height={320}
                />

                {/* Schedule Table */}
                <div className="glass-panel p-6 rounded-2xl border border-white/5">
                  <h4 className="font-bold mb-4">{t('wellControl.schedule.title')}</h4>
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-white/40 border-b border-white/5">
                        <th className="text-left py-2 px-2">{t('wellControl.schedule.step')}</th>
                        <th className="text-right py-2 px-2">{t('wellControl.schedule.strokes')}</th>
                        <th className="text-right py-2 px-2">{t('wellControl.schedule.pressure')}</th>
                        <th className="text-right py-2 px-2">{t('wellControl.schedule.complete')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {killResult.pressure_schedule.map((s: any, i: number) => (
                        <tr key={i} className="border-b border-white/5 hover:bg-white/5">
                          <td className="py-1 px-2">{s.step}</td>
                          <td className="py-1 px-2 text-right font-mono">{s.strokes}</td>
                          <td className="py-1 px-2 text-right font-mono text-industrial-400">{s.pressure_psi}</td>
                          <td className="py-1 px-2 text-right">{s.percent_complete}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            ) : (
              <div className="glass-panel p-12 rounded-2xl border border-white/5 text-center">
                <TrendingDown className="mx-auto mb-4 text-white/20" size={48} />
                <h3 className="text-xl font-bold mb-2">{t('wellControl.schedule.noSchedule')}</h3>
                <p className="text-white/40">{t('wellControl.schedule.noScheduleDesc')}</p>
              </div>
            )}
          </motion.div>
        )}

        {/* Pressure Profile */}
        {activeTab === 'pressure-profile' && (
          <motion.div key="pressure-profile" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="space-y-6">
            <WellborePressureProfile
              tvd={preRecord.depth_tvd}
              mudWeight={preRecord.original_mud_weight}
              killMudWeight={killResult?.kill_mud_weight_ppg}
              formationPressure={killResult?.formation_pressure_psi}
              lotEmw={preRecord.lot_emw}
              casingShoe={preRecord.casing_shoe_tvd}
              height={450}
            />
          </motion.div>
        )}

        {/* Kill Methods */}
        {activeTab === 'methods' && (
          <motion.div key="methods" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="space-y-6">
            {/* Kill Method Comparison */}
            <KillMethodCompare
              killResult={killResult}
              volResult={volResult}
              bullheadResult={bullheadResult}
              height={250}
            />

            {/* Volumetric Cycles Chart */}
            {volResult?.cycles?.length > 0 && (
              <VolumetricCyclesChart
                cycles={volResult.cycles}
                maasp={killResult?.maasp_psi}
                height={280}
              />
            )}

            {/* Calculation panels */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Volumetric */}
              <div className="glass-panel p-6 rounded-2xl border border-white/5">
                <h4 className="font-bold text-lg mb-2">{t('wellControl.methods.volumetric.title')}</h4>
                <p className="text-white/40 text-sm mb-4">{t('wellControl.methods.volumetric.description')}</p>
                <div className="grid grid-cols-2 gap-3 mb-4">
                  <InputField label={t('wellControl.methods.volumetric.mw')} value={volParams.mud_weight} onChange={(v) => setVolParams({ ...volParams, mud_weight: v })} step="0.1" />
                  <InputField label={t('wellControl.methods.volumetric.sicp')} value={volParams.sicp} onChange={(v) => setVolParams({ ...volParams, sicp: v })} />
                  <InputField label={t('wellControl.methods.volumetric.tvd')} value={volParams.tvd} onChange={(v) => setVolParams({ ...volParams, tvd: v })} />
                  <InputField label={t('wellControl.methods.volumetric.annCap')} value={volParams.annular_capacity} onChange={(v) => setVolParams({ ...volParams, annular_capacity: v })} step="0.001" />
                </div>
                <button onClick={runVolumetric} disabled={loading} className="btn-primary w-full text-sm disabled:opacity-50">{loading ? t('common.calculating') : t('wellControl.methods.volumetric.calculate')}</button>
                {volResult && (
                  <div className="mt-4 p-3 bg-white/5 rounded-lg text-xs space-y-1">
                    <p className="text-white/60">{t('wellControl.methods.volumetric.volPerCycle')} <span className="text-industrial-400 font-bold">{volResult.parameters?.volume_per_cycle_bbl} bbl</span></p>
                    <p className="text-white/60">{t('wellControl.methods.volumetric.estCycles')} <span className="text-industrial-400 font-bold">{volResult.parameters?.estimated_cycles}</span></p>
                    <p className="text-white/60">{t('wellControl.methods.volumetric.workingP')} <span className="text-industrial-400 font-bold">{volResult.initial_conditions?.working_pressure_psi} psi</span></p>
                  </div>
                )}
              </div>

              {/* Bullhead */}
              <div className="glass-panel p-6 rounded-2xl border border-white/5">
                <h4 className="font-bold text-lg mb-2">{t('wellControl.methods.bullhead.title')}</h4>
                <p className="text-white/40 text-sm mb-4">{t('wellControl.methods.bullhead.description')}</p>
                <div className="grid grid-cols-2 gap-3 mb-4">
                  <InputField label={t('wellControl.methods.bullhead.mw')} value={bullheadParams.mud_weight} onChange={(v) => setBullheadParams({ ...bullheadParams, mud_weight: v })} step="0.1" />
                  <InputField label={t('wellControl.methods.bullhead.kmw')} value={bullheadParams.kill_mud_weight} onChange={(v) => setBullheadParams({ ...bullheadParams, kill_mud_weight: v })} step="0.1" />
                  <InputField label={t('wellControl.methods.bullhead.tvd')} value={bullheadParams.depth_tvd} onChange={(v) => setBullheadParams({ ...bullheadParams, depth_tvd: v })} />
                  <InputField label={t('wellControl.methods.bullhead.fmPressure')} value={bullheadParams.formation_pressure} onChange={(v) => setBullheadParams({ ...bullheadParams, formation_pressure: v })} />
                </div>
                <button onClick={runBullhead} disabled={loading} className="btn-primary w-full text-sm disabled:opacity-50">{loading ? t('common.calculating') : t('wellControl.methods.bullhead.calculate')}</button>
                {bullheadResult && (
                  <div className="mt-4 p-3 bg-white/5 rounded-lg text-xs space-y-1">
                    <p className="text-white/60">{t('wellControl.methods.bullhead.pumpP')} <span className="text-industrial-400 font-bold">{bullheadResult.calculations?.required_pump_pressure_psi} psi</span></p>
                    <p className="text-white/60">{t('wellControl.methods.bullhead.displace')} <span className="text-industrial-400 font-bold">{bullheadResult.calculations?.displacement_volume_bbl} bbl</span></p>
                    <p className={`font-bold ${bullheadResult.shoe_integrity?.safe ? 'text-green-400' : 'text-red-400'}`}>
                      {t('wellControl.methods.bullhead.shoe')} {bullheadResult.shoe_integrity?.safe ? t('common.safe') : t('common.atRisk')} (margin: {bullheadResult.shoe_integrity?.margin_psi} psi)
                    </p>
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        )}

        {activeTab === 'simulation' && (
          <motion.div key="simulation" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="space-y-6">
            {/* Simulation Parameters */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Kick Migration */}
              <div className="glass-panel p-6 rounded-2xl border border-white/5">
                <h4 className="font-bold text-lg mb-2">{t('wellControl.simulation.kickMigration')}</h4>
                <p className="text-white/40 text-sm mb-4">{t('wellControl.simulation.kickMigrationDesc')}</p>
                <div className="grid grid-cols-2 gap-3 mb-4">
                  <InputField label="TVD (ft)" value={simParams.well_depth_tvd} onChange={(v) => setSimParams({ ...simParams, well_depth_tvd: v })} />
                  <InputField label={t('wellControl.simulation.mudWeight')} value={simParams.mud_weight} onChange={(v) => setSimParams({ ...simParams, mud_weight: v })} step="0.1" />
                  <InputField label={t('wellControl.simulation.kickVolume')} value={simParams.kick_volume_bbl} onChange={(v) => setSimParams({ ...simParams, kick_volume_bbl: v })} />
                  <InputField label="SIDPP (psi)" value={simParams.sidpp} onChange={(v) => setSimParams({ ...simParams, sidpp: v })} />
                  <InputField label="SICP (psi)" value={simParams.sicp} onChange={(v) => setSimParams({ ...simParams, sicp: v })} />
                  <InputField label={t('wellControl.simulation.timeSteps')} value={simParams.time_steps_min} onChange={(v) => setSimParams({ ...simParams, time_steps_min: v })} />
                </div>
                <button onClick={runKickMigration} disabled={loading} className="btn-primary w-full text-sm disabled:opacity-50">
                  {loading ? t('common.calculating') : t('wellControl.simulation.runKickSim')}
                </button>
                {kickMigrationResult && (
                  <div className="mt-4 p-3 bg-white/5 rounded-lg text-xs space-y-1">
                    <p className="text-white/60">{t('wellControl.simulation.maxCP')}: <span className="text-red-400 font-bold">{kickMigrationResult.max_casing_pressure} psi</span></p>
                    <p className="text-white/60">{t('wellControl.simulation.surfaceArrival')}: <span className="text-industrial-400 font-bold">{kickMigrationResult.surface_arrival_min ? `${kickMigrationResult.surface_arrival_min} min` : 'N/A'}</span></p>
                    <p className="text-white/60">{t('wellControl.simulation.dataPoints')}: <span className="text-white/80 font-bold">{kickMigrationResult.time_series?.length}</span></p>
                  </div>
                )}
              </div>

              {/* Kill Circulation */}
              <div className="glass-panel p-6 rounded-2xl border border-white/5">
                <h4 className="font-bold text-lg mb-2">{t('wellControl.simulation.killCirculation')}</h4>
                <p className="text-white/40 text-sm mb-4">{t('wellControl.simulation.killCirculationDesc')}</p>
                <div className="grid grid-cols-2 gap-3 mb-4">
                  <InputField label={t('wellControl.simulation.killMW')} value={simParams.kill_mud_weight} onChange={(v) => setSimParams({ ...simParams, kill_mud_weight: v })} step="0.1" />
                  <InputField label={t('wellControl.simulation.scr')} value={simParams.scr} onChange={(v) => setSimParams({ ...simParams, scr: v })} />
                  <InputField label={t('wellControl.simulation.strokesToBit')} value={simParams.strokes_to_bit} onChange={(v) => setSimParams({ ...simParams, strokes_to_bit: v })} />
                  <InputField label={t('wellControl.simulation.strokesBitToSurf')} value={simParams.strokes_bit_to_surface} onChange={(v) => setSimParams({ ...simParams, strokes_bit_to_surface: v })} />
                </div>
                <div className="mb-4">
                  <label className="text-xs text-white/40 block mb-1">{t('wellControl.simulation.method')}</label>
                  <select
                    value={simParams.kill_method}
                    onChange={(e) => setSimParams({ ...simParams, kill_method: e.target.value })}
                    className="input-field w-full py-2 px-3 text-sm"
                  >
                    <option value="drillers">{t('wellControl.simulation.drillers')}</option>
                    <option value="wait_weight">{t('wellControl.simulation.waitWeight')}</option>
                  </select>
                </div>
                <button onClick={runKillSimulation} disabled={loading} className="btn-primary w-full text-sm disabled:opacity-50">
                  {loading ? t('common.calculating') : t('wellControl.simulation.runKillSim')}
                </button>
                {killSimResult && (
                  <div className="mt-4 p-3 bg-white/5 rounded-lg text-xs space-y-1">
                    <p className="text-white/60">ICP: <span className="text-blue-400 font-bold">{killSimResult.icp} psi</span></p>
                    <p className="text-white/60">FCP: <span className="text-green-400 font-bold">{killSimResult.fcp} psi</span></p>
                    <p className="text-white/60">{t('wellControl.simulation.totalStrokes')}: <span className="text-white/80 font-bold">{killSimResult.total_strokes}</span></p>
                  </div>
                )}
              </div>
            </div>

            {/* Charts */}
            {kickMigrationResult?.time_series?.length > 0 && (
              <KickMigrationChart
                data={kickMigrationResult.time_series}
                maxCasingPressure={kickMigrationResult.max_casing_pressure}
                surfaceArrivalMin={kickMigrationResult.surface_arrival_min}
              />
            )}

            {killSimResult?.drill_pipe_pressure?.length > 0 && (
              <KillCirculationChart
                dpp={killSimResult.drill_pipe_pressure}
                cp={killSimResult.casing_pressure}
                icp={killSimResult.icp}
                fcp={killSimResult.fcp}
                method={killSimResult.method}
              />
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* AI Executive Analysis Button & Panel */}
      {(killResult || volResult || bullheadResult) && (
        <div className="mt-8">
          {!aiAnalysis && (
            <div className="flex flex-col items-center gap-3">
              <div className="flex items-center gap-2 bg-white/5 rounded-lg overflow-hidden border border-white/10">
                {(['en', 'es'] as const).map((lang) => (
                  <button
                    key={lang}
                    onClick={() => setLanguage(lang)}
                    className={`px-3 py-1.5 text-xs font-bold transition-all ${language === lang
                      ? 'bg-industrial-600 text-white'
                      : 'text-white/40 hover:text-white/70'
                      }`}
                  >
                    {lang.toUpperCase()}
                  </button>
                ))}
              </div>
              <button
                onClick={runAIAnalysis}
                disabled={isAnalyzing}
                className="btn-primary py-3 px-8 text-lg disabled:opacity-50"
              >
                <BrainCircuit size={22} />
                {isAnalyzing ? t('ai.analyzingWithAI') : t('ai.executiveAnalysis')}
              </button>
            </div>
          )}
          {(aiAnalysis || isAnalyzing) && (
            <AIAnalysisPanel
              moduleName={t('modules.wellControl')}
              moduleIcon={Shield}
              wellName={wellName}
              analysis={aiAnalysis?.analysis || null}
              confidence={aiAnalysis?.confidence || 'MEDIUM'}
              agentRole={aiAnalysis?.agent_role || 'Drilling Engineer'}
              isLoading={isAnalyzing}
              keyMetrics={aiAnalysis?.key_metrics || []}
              onAnalyze={runAIAnalysis}
              onClose={() => setAiAnalysis(null)}
              provider={provider}
              onProviderChange={setProvider}
              availableProviders={availableProviders}
            />
          )}
        </div>
      )}
    </div>
  );
};

export default WellControlModule;
