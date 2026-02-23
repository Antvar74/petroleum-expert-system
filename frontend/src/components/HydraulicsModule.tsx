import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { Droplets, Plus, Trash2, Play, Waves, BrainCircuit, Upload } from 'lucide-react';
import { API_BASE_URL } from '../config';
import PressureWaterfallChart from './charts/hyd/PressureWaterfallChart';
import ECDProfileChart from './charts/hyd/ECDProfileChart';
import FlowRegimeTrack from './charts/hyd/FlowRegimeTrack';
import BitHydraulicsGauges from './charts/hyd/BitHydraulicsGauges';
import SurgeSwabWindow from './charts/hyd/SurgeSwabWindow';
import AIAnalysisPanel from './AIAnalysisPanel';
import { useTranslation } from 'react-i18next';
import { useLanguage } from '../hooks/useLanguage';
import { useToast } from './ui/Toast';
import type { Provider, ProviderOption } from '../types/ai';
import * as XLSX from 'xlsx';

interface HydraulicsModuleProps {
  wellId?: number;
  wellName?: string;
}

const HydraulicsModule: React.FC<HydraulicsModuleProps> = ({ wellId, wellName = '' }) => {
  const [activeTab, setActiveTab] = useState('circuit');
  const [loading, setLoading] = useState(false);

  // Circuit sections
  const [sections, setSections] = useState<any[]>([
    { section_type: 'drill_pipe', length: 9500, od: 5.0, id_inner: 4.276 },
    { section_type: 'hwdp', length: 300, od: 5.0, id_inner: 3.0 },
    { section_type: 'collar', length: 200, od: 6.5, id_inner: 2.813 },
    { section_type: 'annulus_dc', length: 200, od: 8.5, id_inner: 6.5 },
    { section_type: 'annulus_dp', length: 9800, od: 8.5, id_inner: 5.0 },
  ]);

  // Nozzles
  const [nozzles, setNozzles] = useState({ sizes: '12,12,12', bit_diameter: 8.5 });

  // Hydraulics params
  const [hydParams, setHydParams] = useState({
    flow_rate: 400, mud_weight: 10.0, pv: 15, yp: 10,
    tvd: 10000, rheology_model: 'bingham_plastic',
    n: 0.5, k: 300, surface_equipment_loss: 80,
  });
  const [hydResult, setHydResult] = useState<any>(null);

  // Surge/Swab
  const [surgeParams, setSurgeParams] = useState({
    mud_weight: 10.0, pv: 15, yp: 10, tvd: 10000,
    pipe_od: 5.0, pipe_id: 4.276, hole_id: 8.5,
    pipe_velocity_fpm: 90, pipe_open: true,
  });
  const [surgeResult, setSurgeResult] = useState<any>(null);

  // AI Analysis state
  const [aiAnalysis, setAiAnalysis] = useState<any>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const { t } = useTranslation();
  const { language, setLanguage } = useLanguage();
  const { addToast } = useToast();
  const circuitFileRef = useRef<HTMLInputElement>(null);
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
    if (!hydResult && !surgeResult) return;
    setIsAnalyzing(true);
    try {
      const analyzeUrl = wellId
        ? `${API_BASE_URL}/wells/${wellId}/hydraulics/analyze`
        : `${API_BASE_URL}/analyze/module`;
      const res = await axios.post(analyzeUrl, {
        ...(wellId ? {} : { module: 'hydraulics', well_name: wellName || 'General Analysis' }),
        result_data: { hydraulics: hydResult || {}, surge: surgeResult || {} },
        params: hydParams,
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
    { id: 'circuit', label: t('hydraulics.tabs.circuit') },
    { id: 'hydraulics', label: t('hydraulics.tabs.hydraulics') },
    { id: 'bit', label: t('hydraulics.tabs.bit') },
    { id: 'surge', label: t('hydraulics.tabs.surge') },
  ];

  // ── Circuit file upload (CSV / Excel) ──
  const CIRCUIT_COL_MAP: Record<string, string> = {
    'type': 'section_type', 'section type': 'section_type', 'section_type': 'section_type',
    'tipo': 'section_type', 'seccion': 'section_type', 'sección': 'section_type',
    'section': 'section_type', 'component': 'section_type', 'componente': 'section_type',
    'name': 'section_type', 'nombre': 'section_type',
    'length': 'length', 'length (ft)': 'length', 'length(ft)': 'length',
    'longitud': 'length', 'longitud (ft)': 'length', 'largo': 'length', 'long': 'length',
    'od': 'od', 'od (in)': 'od', 'od(in)': 'od', 'de': 'od', 'de (in)': 'od',
    'outer diameter': 'od', 'diametro externo': 'od',
    'id': 'id_inner', 'id (in)': 'id_inner', 'id(in)': 'id_inner', 'id_inner': 'id_inner',
    'di': 'id_inner', 'di (in)': 'id_inner', 'inner diameter': 'id_inner', 'diametro interno': 'id_inner',
  };

  const VALID_SECTION_TYPES = ['drill_pipe', 'hwdp', 'collar', 'annulus_dp', 'annulus_dc', 'annulus_hwdp', 'surface_equip'];

  const handleCircuitFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (evt) => {
      try {
        const data = new Uint8Array(evt.target?.result as ArrayBuffer);
        const wb = XLSX.read(data, { type: 'array' });
        const sheet = wb.Sheets[wb.SheetNames[0]];
        if (!sheet) { addToast(t('hydraulics.circuit.uploadEmpty'), 'error'); return; }
        const rows: any[] = XLSX.utils.sheet_to_json(sheet, { defval: '' });
        if (rows.length === 0) { addToast(t('hydraulics.circuit.uploadEmpty'), 'error'); return; }

        const hdrMap: Record<string, string> = {};
        for (const fh of Object.keys(rows[0])) {
          const mapped = CIRCUIT_COL_MAP[fh.trim().toLowerCase()];
          if (mapped) hdrMap[fh] = mapped;
        }
        if (!Object.values(hdrMap).includes('section_type')) {
          addToast(t('hydraulics.circuit.uploadNoColumns'), 'error'); return;
        }

        const parsed = rows
          .map(row => {
            const sec: any = { section_type: 'drill_pipe', length: 1000, od: 5.0, id_inner: 4.276 };
            for (const [fc, sf] of Object.entries(hdrMap)) {
              const v = row[fc];
              if (sf === 'section_type') {
                const val = String(v || '').trim().toLowerCase().replace(/\s+/g, '_');
                sec[sf] = VALID_SECTION_TYPES.includes(val) ? val : String(v || '').trim();
              } else {
                sec[sf] = parseFloat(v) || sec[sf];
              }
            }
            return sec;
          })
          .filter((s: any) => String(s.section_type).trim() !== '');

        if (parsed.length === 0) { addToast(t('hydraulics.circuit.uploadEmpty'), 'error'); return; }
        setSections(parsed);
        addToast(t('hydraulics.circuit.uploadSuccess', { count: parsed.length }), 'success');
      } catch (err) {
        console.error('Circuit file parse error:', err);
        addToast(t('hydraulics.circuit.uploadError'), 'error');
      }
    };
    reader.readAsArrayBuffer(file);
    e.target.value = '';
  };

  const saveSections = async () => {
    if (!wellId) return;
    setLoading(true);
    try {
      await axios.post(`${API_BASE_URL}/wells/${wellId}/hydraulic-sections`, sections);
      const nozSizes = nozzles.sizes.split(',').map(Number).filter(n => n > 0);
      await axios.post(`${API_BASE_URL}/wells/${wellId}/bit-nozzles`, { nozzle_sizes: nozSizes, bit_diameter: nozzles.bit_diameter });
      addToast(t('hydraulics.circuit.circuitSaved'), 'success');
    } catch (e: any) { addToast('Error: ' + (e.response?.data?.detail || e.message), 'error'); }
    setLoading(false);
  };

  const runHydraulics = async () => {
    setLoading(true);
    try {
      const nozSizes = nozzles.sizes.split(',').map(Number).filter(n => n > 0);
      const url = wellId
        ? `${API_BASE_URL}/wells/${wellId}/hydraulics/calculate`
        : `${API_BASE_URL}/calculate/hydraulics`;
      const body = wellId
        ? { ...hydParams, nozzle_sizes: nozSizes }
        : { ...hydParams, nozzle_sizes: nozSizes, sections };
      const res = await axios.post(url, body);
      setHydResult(res.data);
    } catch (e: any) { addToast('Error: ' + (e.response?.data?.detail || e.message), 'error'); }
    setLoading(false);
  };

  const runSurgeSwab = async () => {
    setLoading(true);
    try {
      const url = wellId
        ? `${API_BASE_URL}/wells/${wellId}/hydraulics/surge-swab`
        : `${API_BASE_URL}/calculate/hydraulics/surge-swab`;
      const res = await axios.post(url, surgeParams);
      setSurgeResult(res.data);
    } catch (e: any) { addToast('Error: ' + (e.response?.data?.detail || e.message), 'error'); }
    setLoading(false);
  };

  // (Pressure bar replaced by PressureWaterfallChart component)

  return (
    <div className="space-y-6 py-8">
      <div className="flex items-center gap-3 mb-8">
        <Droplets className="text-industrial-500" size={28} />
        <h2 className="text-2xl font-bold">{t('hydraulics.title')}</h2>
      </div>

      <div className="flex gap-2 mb-8">
        {tabs.map((tab) => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={`px-5 py-2.5 rounded-xl text-sm font-bold transition-all ${activeTab === tab.id ? 'bg-industrial-600 text-white shadow-lg' : 'bg-white/5 text-white/40 hover:text-white hover:bg-white/10'}`}>
            {tab.label}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        {/* Circuit Setup */}
        {activeTab === 'circuit' && (
          <motion.div key="circuit" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="space-y-6">
            <div className="glass-panel p-6 rounded-2xl border border-white/5">
              <div className="flex justify-between items-center mb-4">
                <h3 className="font-bold text-lg">Hydraulic Circuit Sections</h3>
                <div className="flex gap-2">
                  <button onClick={() => setSections([...sections, { section_type: 'drill_pipe', length: 1000, od: 5.0, id_inner: 4.276 }])} className="flex items-center gap-1 px-3 py-1.5 bg-white/5 hover:bg-white/10 rounded-lg text-sm"><Plus size={14} /> {t('common.add')}</button>
                  <button onClick={() => circuitFileRef.current?.click()} className="flex items-center gap-1 px-3 py-1.5 bg-white/5 hover:bg-white/10 rounded-lg text-sm"><Upload size={14} /> {t('hydraulics.circuit.uploadFile')}</button>
                  <input ref={circuitFileRef} type="file" accept=".csv,.xlsx,.xls" className="hidden" onChange={handleCircuitFileUpload} />
                  <button onClick={saveSections} disabled={loading} className="px-4 py-1.5 bg-industrial-600 hover:bg-industrial-700 rounded-lg text-sm font-bold disabled:opacity-50">{loading ? t('common.saving') : t('hydraulics.circuit.saveAll')}</button>
                </div>
              </div>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-white/40 border-b border-white/5">
                    <th className="text-left py-2 px-2">{t('hydraulics.circuit.type')}</th>
                    <th className="text-left py-2 px-2">{t('hydraulics.circuit.length')}</th>
                    <th className="text-left py-2 px-2">{t('hydraulics.circuit.od')}</th>
                    <th className="text-left py-2 px-2">{t('hydraulics.circuit.id')}</th>
                    <th className="w-10"></th>
                  </tr>
                </thead>
                <tbody>
                  {sections.map((s, i) => (
                    <tr key={i} className="border-b border-white/5">
                      <td className="py-1 px-2">
                        <select value={s.section_type} onChange={(e) => { const u = [...sections]; u[i] = { ...u[i], section_type: e.target.value }; setSections(u); }} className="input-field py-1 px-2 text-sm">
                          {['drill_pipe', 'hwdp', 'collar', 'annulus_dp', 'annulus_dc', 'annulus_hwdp', 'surface_equip'].map(t => <option key={t} value={t}>{t}</option>)}
                        </select>
                      </td>
                      <td className="py-1 px-2"><input type="number" value={s.length} onChange={(e) => { const u = [...sections]; u[i] = { ...u[i], length: +e.target.value }; setSections(u); }} className="input-field w-24 py-1 px-2 text-sm" /></td>
                      <td className="py-1 px-2"><input type="number" step="0.1" value={s.od} onChange={(e) => { const u = [...sections]; u[i] = { ...u[i], od: +e.target.value }; setSections(u); }} className="input-field w-20 py-1 px-2 text-sm" /></td>
                      <td className="py-1 px-2"><input type="number" step="0.001" value={s.id_inner} onChange={(e) => { const u = [...sections]; u[i] = { ...u[i], id_inner: +e.target.value }; setSections(u); }} className="input-field w-20 py-1 px-2 text-sm" /></td>
                      <td><button onClick={() => setSections(sections.filter((_, j) => j !== i))} className="text-red-400/50 hover:text-red-400 p-1"><Trash2 size={14} /></button></td>
                    </tr>
                  ))}
                </tbody>
              </table>

              <div className="mt-6 pt-4 border-t border-white/5">
                <h4 className="font-bold text-sm mb-3">{t('hydraulics.nozzles.title')}</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs text-white/40 block mb-1">{t('hydraulics.nozzles.sizes')}</label>
                    <input type="text" value={nozzles.sizes} onChange={(e) => setNozzles({ ...nozzles, sizes: e.target.value })} className="input-field w-full py-2 px-3 text-sm" placeholder="12,12,12" />
                  </div>
                  <div>
                    <label className="text-xs text-white/40 block mb-1">{t('hydraulics.nozzles.bitDiameter')}</label>
                    <input type="number" step="0.125" value={nozzles.bit_diameter} onChange={(e) => setNozzles({ ...nozzles, bit_diameter: +e.target.value })} className="input-field w-full py-2 px-3 text-sm" />
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {/* Full Hydraulics */}
        {activeTab === 'hydraulics' && (
          <motion.div key="hydraulics" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="space-y-6">
            <div className="glass-panel p-6 rounded-2xl border border-white/5">
              <h3 className="font-bold text-lg mb-4">{t('hydraulics.params.title')}</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                <div><label className="text-xs text-white/40 block mb-1">{t('hydraulics.params.flowRate')}</label><input type="number" value={hydParams.flow_rate} onChange={(e) => setHydParams({ ...hydParams, flow_rate: +e.target.value })} className="input-field w-full py-2 px-3 text-sm" /></div>
                <div><label className="text-xs text-white/40 block mb-1">{t('hydraulics.params.mudWeight')}</label><input type="number" step="0.1" value={hydParams.mud_weight} onChange={(e) => setHydParams({ ...hydParams, mud_weight: +e.target.value })} className="input-field w-full py-2 px-3 text-sm" /></div>
                <div><label className="text-xs text-white/40 block mb-1">{t('hydraulics.params.pv')}</label><input type="number" value={hydParams.pv} onChange={(e) => setHydParams({ ...hydParams, pv: +e.target.value })} className="input-field w-full py-2 px-3 text-sm" /></div>
                <div><label className="text-xs text-white/40 block mb-1">{t('hydraulics.params.yp')}</label><input type="number" value={hydParams.yp} onChange={(e) => setHydParams({ ...hydParams, yp: +e.target.value })} className="input-field w-full py-2 px-3 text-sm" /></div>
                <div><label className="text-xs text-white/40 block mb-1">{t('hydraulics.params.tvd')}</label><input type="number" value={hydParams.tvd} onChange={(e) => setHydParams({ ...hydParams, tvd: +e.target.value })} className="input-field w-full py-2 px-3 text-sm" /></div>
                <div>
                  <label className="text-xs text-white/40 block mb-1">{t('hydraulics.params.rheologyModel')}</label>
                  <select value={hydParams.rheology_model} onChange={(e) => setHydParams({ ...hydParams, rheology_model: e.target.value })} className="input-field w-full py-2 px-3 text-sm">
                    <option value="bingham_plastic">{t('hydraulics.params.bingham')}</option>
                    <option value="power_law">{t('hydraulics.params.powerLaw')}</option>
                  </select>
                </div>
                {hydParams.rheology_model === 'power_law' && <>
                  <div><label className="text-xs text-white/40 block mb-1">{t('hydraulics.params.flowIndex')}</label><input type="number" step="0.01" value={hydParams.n} onChange={(e) => setHydParams({ ...hydParams, n: +e.target.value })} className="input-field w-full py-2 px-3 text-sm" /></div>
                  <div><label className="text-xs text-white/40 block mb-1">{t('hydraulics.params.consistency')}</label><input type="number" value={hydParams.k} onChange={(e) => setHydParams({ ...hydParams, k: +e.target.value })} className="input-field w-full py-2 px-3 text-sm" /></div>
                </>}
              </div>
              <button onClick={runHydraulics} disabled={loading} className="btn-primary flex items-center gap-2 disabled:opacity-50">
                <Play size={16} /> {loading ? t('common.calculating') : t('hydraulics.params.calculateCircuit')}
              </button>
            </div>

            {hydResult && (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
                {/* ECD status badge */}
                <div className="flex justify-end">
                  <span className={`px-3 py-1 rounded-full text-xs font-bold ${hydResult.ecd?.status?.includes('HIGH') ? 'bg-red-500/20 text-red-400' : hydResult.ecd?.status?.includes('LOW') ? 'bg-yellow-500/20 text-yellow-400' : 'bg-green-500/20 text-green-400'}`}>
                    ECD: {hydResult.ecd?.ecd_ppg} ppg — {hydResult.ecd?.status}
                  </span>
                </div>

                {/* Pressure Waterfall Chart */}
                <PressureWaterfallChart summary={hydResult.summary} height={280} />

                {/* ECD Profile (if data available) */}
                {hydResult.ecd && (
                  <ECDProfileChart
                    data={(() => {
                      const backendProfile = hydResult.ecd_profile || [];
                      const mw = hydParams.mud_weight;
                      const ecdAtTd = hydResult.ecd.ecd_ppg;
                      const td = hydParams.tvd;
                      // Use backend data if it has enough points, otherwise generate synthetic profile
                      if (backendProfile.length >= 5) return backendProfile;
                      const steps = 11;
                      return Array.from({ length: steps }, (_, i) => {
                        const tvd = Math.round((i / (steps - 1)) * td);
                        // ECD increases linearly from MW at surface to ecdAtTd at TD
                        const ecd = tvd === 0 ? mw : +(mw + (ecdAtTd - mw) * (tvd / td)).toFixed(2);
                        return { tvd, ecd };
                      });
                    })()}
                    mudWeight={hydParams.mud_weight}
                    lotEmw={14.0}
                    height={300}
                  />
                )}

                {/* Flow Regime Track */}
                <FlowRegimeTrack
                  data={hydResult.section_results || []}
                  height={250}
                />

                {/* Section details table */}
                <div className="glass-panel p-6 rounded-2xl border border-white/5">
                  <h4 className="font-bold mb-4">{t('hydraulics.results.sectionResults')}</h4>
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-white/40 border-b border-white/5">
                        <th className="text-left py-2 px-2">{t('hydraulics.results.section')}</th>
                        <th className="text-right py-2 px-2">{t('hydraulics.results.dp')}</th>
                        <th className="text-right py-2 px-2">{t('hydraulics.results.velocity')}</th>
                        <th className="text-center py-2 px-2">{t('hydraulics.results.flowRegime')}</th>
                        <th className="text-right py-2 px-2">{t('hydraulics.results.re')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {hydResult.section_results?.map((sr: any, i: number) => (
                        <tr key={i} className="border-b border-white/5 hover:bg-white/5">
                          <td className="py-1 px-2">{sr.section_type}</td>
                          <td className="py-1 px-2 text-right font-mono">{sr.pressure_loss_psi}</td>
                          <td className="py-1 px-2 text-right font-mono">{sr.velocity_ft_min}</td>
                          <td className={`py-1 px-2 text-center text-xs font-bold ${sr.flow_regime === 'turbulent' ? 'text-orange-400' : 'text-green-400'}`}>{sr.flow_regime}</td>
                          <td className="py-1 px-2 text-right font-mono text-white/50">{Math.round(sr.reynolds)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </motion.div>
            )}
          </motion.div>
        )}

        {/* Bit Optimization */}
        {activeTab === 'bit' && (
          <motion.div key="bit" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="space-y-6">
            {hydResult?.bit_hydraulics ? (
              <BitHydraulicsGauges bitData={hydResult.bit_hydraulics} />
            ) : (
              <div className="glass-panel p-12 rounded-2xl border border-white/5 text-center">
                <p className="text-white/40">{t('hydraulics.bit.runFirst')}</p>
              </div>
            )}
          </motion.div>
        )}

        {/* Surge/Swab */}
        {activeTab === 'surge' && (
          <motion.div key="surge" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="space-y-6">
            <div className="glass-panel p-6 rounded-2xl border border-white/5">
              <h3 className="font-bold text-lg mb-4">{t('hydraulics.surge.title')}</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                <div><label className="text-xs text-white/40 block mb-1">{t('hydraulics.surge.mudWeight')}</label><input type="number" step="0.1" value={surgeParams.mud_weight} onChange={(e) => setSurgeParams({ ...surgeParams, mud_weight: +e.target.value })} className="input-field w-full py-2 px-3 text-sm" /></div>
                <div><label className="text-xs text-white/40 block mb-1">{t('hydraulics.surge.pv')}</label><input type="number" value={surgeParams.pv} onChange={(e) => setSurgeParams({ ...surgeParams, pv: +e.target.value })} className="input-field w-full py-2 px-3 text-sm" /></div>
                <div><label className="text-xs text-white/40 block mb-1">{t('hydraulics.surge.yp')}</label><input type="number" value={surgeParams.yp} onChange={(e) => setSurgeParams({ ...surgeParams, yp: +e.target.value })} className="input-field w-full py-2 px-3 text-sm" /></div>
                <div><label className="text-xs text-white/40 block mb-1">{t('hydraulics.surge.tvd')}</label><input type="number" value={surgeParams.tvd} onChange={(e) => setSurgeParams({ ...surgeParams, tvd: +e.target.value })} className="input-field w-full py-2 px-3 text-sm" /></div>
                <div><label className="text-xs text-white/40 block mb-1">{t('hydraulics.surge.pipeOD')}</label><input type="number" step="0.1" value={surgeParams.pipe_od} onChange={(e) => setSurgeParams({ ...surgeParams, pipe_od: +e.target.value })} className="input-field w-full py-2 px-3 text-sm" /></div>
                <div><label className="text-xs text-white/40 block mb-1">{t('hydraulics.surge.holeID')}</label><input type="number" step="0.1" value={surgeParams.hole_id} onChange={(e) => setSurgeParams({ ...surgeParams, hole_id: +e.target.value })} className="input-field w-full py-2 px-3 text-sm" /></div>
                <div><label className="text-xs text-white/40 block mb-1">{t('hydraulics.surge.tripSpeed')}</label><input type="number" value={surgeParams.pipe_velocity_fpm} onChange={(e) => setSurgeParams({ ...surgeParams, pipe_velocity_fpm: +e.target.value })} className="input-field w-full py-2 px-3 text-sm" /></div>
                <div className="flex items-end pb-1">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" checked={surgeParams.pipe_open} onChange={(e) => setSurgeParams({ ...surgeParams, pipe_open: e.target.checked })} className="accent-industrial-500" />
                    <span className="text-sm">{t('hydraulics.surge.openEnded')}</span>
                  </label>
                </div>
              </div>
              <button onClick={runSurgeSwab} disabled={loading} className="btn-primary flex items-center gap-2 disabled:opacity-50">
                <Waves size={16} /> {loading ? t('common.calculating') : t('hydraulics.surge.calculate')}
              </button>
            </div>

            {surgeResult && (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
                {/* Surge/Swab Window visualization */}
                <SurgeSwabWindow
                  mudWeight={surgeParams.mud_weight}
                  surgeEcd={surgeResult.surge_ecd_ppg}
                  swabEcd={surgeResult.swab_ecd_ppg}
                  lotEmw={14.0}
                  porePressure={surgeParams.mud_weight - 0.5}
                  surgeMargin={surgeResult.surge_margin || 'OK'}
                  swabMargin={surgeResult.swab_margin || 'OK'}
                  height={280}
                />

                {/* Value cards */}
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <div className="glass-panel p-5 rounded-xl border border-white/5 text-center">
                    <p className="text-xs text-white/40 mb-2">{t('hydraulics.surge.surgeECD')}</p>
                    <p className="text-2xl font-bold text-red-400">{surgeResult.surge_ecd_ppg} ppg</p>
                    <p className="text-xs text-white/30">+{surgeResult.surge_emw_ppg} ppg</p>
                  </div>
                  <div className="glass-panel p-5 rounded-xl border border-white/5 text-center">
                    <p className="text-xs text-white/40 mb-2">{t('hydraulics.surge.swabECD')}</p>
                    <p className="text-2xl font-bold text-blue-400">{surgeResult.swab_ecd_ppg} ppg</p>
                    <p className="text-xs text-white/30">-{surgeResult.swab_emw_ppg} ppg</p>
                  </div>
                  <div className="glass-panel p-5 rounded-xl border border-white/5 text-center">
                    <p className="text-xs text-white/40 mb-2">{t('hydraulics.surge.effectiveVelocity')}</p>
                    <p className="text-2xl font-bold text-white">{surgeResult.effective_velocity_fpm} ft/min</p>
                  </div>
                  <div className={`glass-panel p-5 rounded-xl border text-center ${surgeResult.surge_margin?.includes('CRITICAL') ? 'border-red-500/30 bg-red-500/5' : surgeResult.surge_margin?.includes('WARNING') ? 'border-yellow-500/30 bg-yellow-500/5' : 'border-green-500/30 bg-green-500/5'}`}>
                    <p className="text-xs text-white/40 mb-2">{t('hydraulics.surge.surgeMargin')}</p>
                    <p className={`text-sm font-bold ${surgeResult.surge_margin?.includes('CRITICAL') ? 'text-red-400' : surgeResult.surge_margin?.includes('WARNING') ? 'text-yellow-400' : 'text-green-400'}`}>{surgeResult.surge_margin}</p>
                  </div>
                  <div className={`glass-panel p-5 rounded-xl border text-center ${surgeResult.swab_margin?.includes('CRITICAL') ? 'border-red-500/30 bg-red-500/5' : surgeResult.swab_margin?.includes('WARNING') ? 'border-yellow-500/30 bg-yellow-500/5' : 'border-green-500/30 bg-green-500/5'}`}>
                    <p className="text-xs text-white/40 mb-2">{t('hydraulics.surge.swabMargin')}</p>
                    <p className={`text-sm font-bold ${surgeResult.swab_margin?.includes('CRITICAL') ? 'text-red-400' : surgeResult.swab_margin?.includes('WARNING') ? 'text-yellow-400' : 'text-green-400'}`}>{surgeResult.swab_margin}</p>
                  </div>
                  <div className="glass-panel p-5 rounded-xl border border-white/5 text-center">
                    <p className="text-xs text-white/40 mb-2">{t('hydraulics.surge.pressure')}</p>
                    <p className="text-2xl font-bold text-industrial-400">{surgeResult.surge_pressure_psi}</p>
                  </div>
                </div>
              </motion.div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* AI Executive Analysis Button & Panel */}
      {(hydResult || surgeResult) && (
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
              moduleName={t('modules.hydraulicsECD')}
              moduleIcon={Droplets}
              wellName={wellName}
              analysis={aiAnalysis?.analysis || null}
              confidence={aiAnalysis?.confidence || 'MEDIUM'}
              agentRole={aiAnalysis?.agent_role || 'Mud Engineer'}
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

export default HydraulicsModule;
