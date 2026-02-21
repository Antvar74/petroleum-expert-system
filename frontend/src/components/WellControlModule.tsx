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
import AIAnalysisPanel from './AIAnalysisPanel';
import { useTranslation } from 'react-i18next';
import { useLanguage } from '../hooks/useLanguage';
import type { Provider, ProviderOption } from '../types/ai';

interface WellControlModuleProps {
  wellId: number;
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

  // AI Analysis state
  const [aiAnalysis, setAiAnalysis] = useState<any>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const { t } = useTranslation();
  const { language, setLanguage } = useLanguage();
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
      const res = await axios.post(`${API_BASE_URL}/wells/${wellId}/well-control/analyze`, {
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
    { id: 'prerecord', label: 'Pre-Record Kill Sheet' },
    { id: 'active', label: 'Active Kill' },
    { id: 'schedule', label: 'Pressure Schedule' },
    { id: 'pressure-profile', label: 'Pressure Profile' },
    { id: 'methods', label: 'Kill Methods' },
  ];

  const savePreRecord = async () => {
    setLoading(true);
    try {
      const res = await axios.post(`${API_BASE_URL}/wells/${wellId}/kill-sheet/pre-record`, preRecord);
      setPreRecordResult(res.data);
    } catch (e: any) { alert('Error: ' + (e.response?.data?.detail || e.message)); }
    setLoading(false);
  };

  const runKillCalc = async () => {
    setLoading(true);
    try {
      const res = await axios.post(`${API_BASE_URL}/wells/${wellId}/kill-sheet/calculate`, kickData);
      setKillResult(res.data);
    } catch (e: any) { alert('Error: ' + (e.response?.data?.detail || e.message)); }
    setLoading(false);
  };

  const runVolumetric = async () => {
    setLoading(true);
    try {
      const res = await axios.post(`${API_BASE_URL}/kill-sheet/volumetric`, volParams);
      setVolResult(res.data);
    } catch (e: any) { alert('Error: ' + (e.response?.data?.detail || e.message)); }
    setLoading(false);
  };

  const runBullhead = async () => {
    setLoading(true);
    try {
      const res = await axios.post(`${API_BASE_URL}/kill-sheet/bullhead`, bullheadParams);
      setBullheadResult(res.data);
    } catch (e: any) { alert('Error: ' + (e.response?.data?.detail || e.message)); }
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
        <h2 className="text-2xl font-bold">Well Control / Kill Sheet</h2>
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
              <h3 className="font-bold text-lg mb-4">Pre-Record Kill Sheet Data</h3>
              <p className="text-white/40 text-sm mb-6">Enter static well data before any kick occurs. This is your reference kill sheet.</p>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                <InputField label="Depth MD (ft)" value={preRecord.depth_md} onChange={(v) => setPreRecord({ ...preRecord, depth_md: v })} />
                <InputField label="Depth TVD (ft)" value={preRecord.depth_tvd} onChange={(v) => setPreRecord({ ...preRecord, depth_tvd: v })} />
                <InputField label="Mud Weight (ppg)" value={preRecord.original_mud_weight} onChange={(v) => setPreRecord({ ...preRecord, original_mud_weight: v })} step="0.1" />
                <InputField label="Casing Shoe TVD (ft)" value={preRecord.casing_shoe_tvd} onChange={(v) => setPreRecord({ ...preRecord, casing_shoe_tvd: v })} />
                <InputField label="Casing ID (in)" value={preRecord.casing_id} onChange={(v) => setPreRecord({ ...preRecord, casing_id: v })} step="0.001" />
                <InputField label="Hole Size (in)" value={preRecord.hole_size} onChange={(v) => setPreRecord({ ...preRecord, hole_size: v })} step="0.125" />
                <InputField label="DP OD (in)" value={preRecord.dp_od} onChange={(v) => setPreRecord({ ...preRecord, dp_od: v })} step="0.1" />
                <InputField label="DP ID (in)" value={preRecord.dp_id} onChange={(v) => setPreRecord({ ...preRecord, dp_id: v })} step="0.001" />
                <InputField label="DP Length (ft)" value={preRecord.dp_length} onChange={(v) => setPreRecord({ ...preRecord, dp_length: v })} />
                <InputField label="DC OD (in)" value={preRecord.dc_od} onChange={(v) => setPreRecord({ ...preRecord, dc_od: v })} step="0.1" />
                <InputField label="DC ID (in)" value={preRecord.dc_id} onChange={(v) => setPreRecord({ ...preRecord, dc_id: v })} step="0.001" />
                <InputField label="DC Length (ft)" value={preRecord.dc_length} onChange={(v) => setPreRecord({ ...preRecord, dc_length: v })} />
                <InputField label="SCR Pressure (psi)" value={preRecord.scr_pressure} onChange={(v) => setPreRecord({ ...preRecord, scr_pressure: v })} />
                <InputField label="SCR Rate (spm)" value={preRecord.scr_rate} onChange={(v) => setPreRecord({ ...preRecord, scr_rate: v })} />
                <InputField label="LOT EMW (ppg)" value={preRecord.lot_emw} onChange={(v) => setPreRecord({ ...preRecord, lot_emw: v })} step="0.1" />
                <InputField label="Pump Output (bbl/stk)" value={preRecord.pump_output} onChange={(v) => setPreRecord({ ...preRecord, pump_output: v })} step="0.01" />
              </div>

              <button onClick={savePreRecord} disabled={loading} className="btn-primary flex items-center gap-2 disabled:opacity-50">
                <Save size={16} /> {loading ? 'Saving...' : 'Save Kill Sheet'}
              </button>
            </div>

            {preRecordResult && (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="glass-panel p-4 rounded-xl border border-white/5 text-center">
                    <p className="text-xs text-white/40 mb-1">Hydrostatic</p>
                    <p className="text-xl font-bold text-industrial-400">{preRecordResult.reference_values?.hydrostatic_psi}</p>
                    <p className="text-xs text-white/30">psi</p>
                  </div>
                  <div className="glass-panel p-4 rounded-xl border border-white/5 text-center">
                    <p className="text-xs text-white/40 mb-1">MAASP</p>
                    <p className="text-xl font-bold text-industrial-400">{preRecordResult.reference_values?.maasp_psi}</p>
                    <p className="text-xs text-white/30">psi</p>
                  </div>
                  <div className="glass-panel p-4 rounded-xl border border-white/5 text-center">
                    <p className="text-xs text-white/40 mb-1">Strokes to Bit</p>
                    <p className="text-xl font-bold text-white">{preRecordResult.strokes?.strokes_surface_to_bit}</p>
                  </div>
                  <div className="glass-panel p-4 rounded-xl border border-white/5 text-center">
                    <p className="text-xs text-white/40 mb-1">Total Volume</p>
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
              <h3 className="font-bold text-lg mb-4">Kick Data</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                <InputField label="SIDPP (psi)" value={kickData.sidpp} onChange={(v) => setKickData({ ...kickData, sidpp: v })} />
                <InputField label="SICP (psi)" value={kickData.sicp} onChange={(v) => setKickData({ ...kickData, sicp: v })} />
                <InputField label="Pit Gain (bbl)" value={kickData.pit_gain} onChange={(v) => setKickData({ ...kickData, pit_gain: v })} />
                <div>
                  <label className="text-xs text-white/40 block mb-1">Kill Method</label>
                  <select value={kickData.kill_method} onChange={(e) => setKickData({ ...kickData, kill_method: e.target.value })} className="input-field w-full py-2 px-3 text-sm">
                    <option value="wait_weight">Wait & Weight</option>
                    <option value="drillers">Driller's Method</option>
                  </select>
                </div>
              </div>
              <button onClick={runKillCalc} disabled={loading} className="btn-primary flex items-center gap-2 disabled:opacity-50">
                <AlertTriangle size={16} /> {loading ? 'Calculating...' : 'Calculate Kill Sheet'}
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
                      { label: 'Formation Pressure', value: killResult.formation_pressure_psi, unit: 'psi', color: 'text-red-400' },
                      { label: 'Kill Mud Weight', value: killResult.kill_mud_weight_ppg, unit: 'ppg', color: 'text-industrial-400' },
                      { label: 'ICP', value: killResult.icp_psi, unit: 'psi', color: 'text-orange-400' },
                      { label: 'FCP', value: killResult.fcp_psi, unit: 'psi', color: 'text-green-400' },
                      { label: 'MAASP', value: killResult.maasp_psi, unit: 'psi', color: 'text-yellow-400' },
                      { label: 'MW Increase', value: killResult.mud_weight_increase_ppg, unit: 'ppg', color: 'text-white' },
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
                  <h4 className="font-bold mb-4">Schedule Table</h4>
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-white/40 border-b border-white/5">
                        <th className="text-left py-2 px-2">Step</th>
                        <th className="text-right py-2 px-2">Strokes</th>
                        <th className="text-right py-2 px-2">Pressure (psi)</th>
                        <th className="text-right py-2 px-2">Complete (%)</th>
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
                <h3 className="text-xl font-bold mb-2">No Pressure Schedule</h3>
                <p className="text-white/40">Calculate kill sheet in "Active Kill" tab first.</p>
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
                <h4 className="font-bold text-lg mb-2">Volumetric Method</h4>
                <p className="text-white/40 text-sm mb-4">No circulation needed — for stuck pipe or pump failure.</p>
                <div className="grid grid-cols-2 gap-3 mb-4">
                  <InputField label="MW (ppg)" value={volParams.mud_weight} onChange={(v) => setVolParams({ ...volParams, mud_weight: v })} step="0.1" />
                  <InputField label="SICP (psi)" value={volParams.sicp} onChange={(v) => setVolParams({ ...volParams, sicp: v })} />
                  <InputField label="TVD (ft)" value={volParams.tvd} onChange={(v) => setVolParams({ ...volParams, tvd: v })} />
                  <InputField label="Ann Cap (bbl/ft)" value={volParams.annular_capacity} onChange={(v) => setVolParams({ ...volParams, annular_capacity: v })} step="0.001" />
                </div>
                <button onClick={runVolumetric} disabled={loading} className="btn-primary w-full text-sm disabled:opacity-50">{loading ? 'Calculating...' : 'Calculate Volumetric'}</button>
                {volResult && (
                  <div className="mt-4 p-3 bg-white/5 rounded-lg text-xs space-y-1">
                    <p className="text-white/60">Vol/cycle: <span className="text-industrial-400 font-bold">{volResult.parameters?.volume_per_cycle_bbl} bbl</span></p>
                    <p className="text-white/60">Est. cycles: <span className="text-industrial-400 font-bold">{volResult.parameters?.estimated_cycles}</span></p>
                    <p className="text-white/60">Working P: <span className="text-industrial-400 font-bold">{volResult.initial_conditions?.working_pressure_psi} psi</span></p>
                  </div>
                )}
              </div>

              {/* Bullhead */}
              <div className="glass-panel p-6 rounded-2xl border border-white/5">
                <h4 className="font-bold text-lg mb-2">Bullhead</h4>
                <p className="text-white/40 text-sm mb-4">Force influx back — for H2S or off-bottom situations.</p>
                <div className="grid grid-cols-2 gap-3 mb-4">
                  <InputField label="MW (ppg)" value={bullheadParams.mud_weight} onChange={(v) => setBullheadParams({ ...bullheadParams, mud_weight: v })} step="0.1" />
                  <InputField label="KMW (ppg)" value={bullheadParams.kill_mud_weight} onChange={(v) => setBullheadParams({ ...bullheadParams, kill_mud_weight: v })} step="0.1" />
                  <InputField label="TVD (ft)" value={bullheadParams.depth_tvd} onChange={(v) => setBullheadParams({ ...bullheadParams, depth_tvd: v })} />
                  <InputField label="Fm Pressure (psi)" value={bullheadParams.formation_pressure} onChange={(v) => setBullheadParams({ ...bullheadParams, formation_pressure: v })} />
                </div>
                <button onClick={runBullhead} disabled={loading} className="btn-primary w-full text-sm disabled:opacity-50">{loading ? 'Calculating...' : 'Calculate Bullhead'}</button>
                {bullheadResult && (
                  <div className="mt-4 p-3 bg-white/5 rounded-lg text-xs space-y-1">
                    <p className="text-white/60">Pump P: <span className="text-industrial-400 font-bold">{bullheadResult.calculations?.required_pump_pressure_psi} psi</span></p>
                    <p className="text-white/60">Displace: <span className="text-industrial-400 font-bold">{bullheadResult.calculations?.displacement_volume_bbl} bbl</span></p>
                    <p className={`font-bold ${bullheadResult.shoe_integrity?.safe ? 'text-green-400' : 'text-red-400'}`}>
                      Shoe: {bullheadResult.shoe_integrity?.safe ? 'SAFE' : 'AT RISK'} (margin: {bullheadResult.shoe_integrity?.margin_psi} psi)
                    </p>
                  </div>
                )}
              </div>
            </div>
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
