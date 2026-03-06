import { useState, useRef, useCallback } from 'react';
import api from '../lib/api';
import { motion, AnimatePresence } from 'framer-motion';
import { Droplets, Plus, Trash2, Play, Upload } from 'lucide-react';
import PressureWaterfallChart from './charts/hyd/PressureWaterfallChart';
import ECDProfileChart from './charts/hyd/ECDProfileChart';
import FlowRegimeTrack from './charts/hyd/FlowRegimeTrack';
import BitHydraulicsGauges from './charts/hyd/BitHydraulicsGauges';
import SurgeSwabWindow from './charts/hyd/SurgeSwabWindow';
import AIAnalysisPanel from './AIAnalysisPanel';
import { useTranslation } from 'react-i18next';
import { useAIAnalysis } from '../hooks/useAIAnalysis';
import { useToast } from './ui/Toast';
import type { APIError } from '../types/api';
import type { CircuitSection, HydResult, HydSectionResult, SurgeSwabResult } from '../types/modules/hydraulics';

interface HydraulicsModuleProps {
  wellId?: number;
  wellName?: string;
}

interface HydraulicsResult {
  hydraulics: HydResult;
  surge: SurgeSwabResult;
}

const HydraulicsModule: React.FC<HydraulicsModuleProps> = ({ wellId, wellName = '' }) => {
  const [activeTab, setActiveTab] = useState('input');
  const [loading, setLoading] = useState(false);

  // Circuit sections
  const [sections, setSections] = useState<CircuitSection[]>([
    { section_type: 'drill_pipe', length: 9500, od: 5.0, id_inner: 4.276 },
    { section_type: 'hwdp', length: 300, od: 5.0, id_inner: 3.0 },
    { section_type: 'collar', length: 200, od: 6.5, id_inner: 2.813 },
    { section_type: 'annulus_dc', length: 200, od: 8.5, id_inner: 6.5 },
    { section_type: 'annulus_dp', length: 9800, od: 8.5, id_inner: 5.0 },
  ]);

  // Nozzles
  const [nozzles, setNozzles] = useState({ sizes: '12,12,12', bit_diameter: 8.5 });

  // Unified parameters (hydraulics + surge shared fields + surge-only fields)
  const [params, setParams] = useState({
    flow_rate: 400, mud_weight: 10.0, pv: 15, yp: 10,
    tvd: 10000, rheology_model: 'bingham_plastic',
    n: 0.5, k: 300, surface_equipment_loss: 80,
    pipe_od: 5.0, pipe_id: 4.276, hole_id: 8.5,
    pipe_velocity_fpm: 90, pipe_open: true,
  });

  // Unified result
  const [result, setResult] = useState<HydraulicsResult | null>(null);

  const { t } = useTranslation();
  const { addToast } = useToast();
  const circuitFileRef = useRef<HTMLInputElement>(null);

  const { aiAnalysis, isAnalyzing, runAnalysis, provider, setProvider, availableProviders, setAiAnalysis } = useAIAnalysis({
    module: 'hydraulics',
    wellId,
    wellName,
  });

  const handleRunAnalysis = () => {
    runAnalysis(
      { hydraulics: result?.hydraulics || {}, surge: result?.surge || {} },
      params
    );
  };

  const tabs = [
    { id: 'input', label: t('common.parameters') },
    { id: 'results', label: t('common.results') },
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
    reader.onload = async (evt) => {
      try {
        const XLSX = await import('xlsx');
        const data = new Uint8Array(evt.target?.result as ArrayBuffer);
        const wb = XLSX.read(data, { type: 'array' });
        const sheet = wb.Sheets[wb.SheetNames[0]];
        if (!sheet) { addToast(t('hydraulics.circuit.uploadEmpty'), 'error'); return; }
        const rows: Record<string, string>[] = XLSX.utils.sheet_to_json(sheet, { defval: '' });
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
            const sec: CircuitSection = { section_type: 'drill_pipe', length: 1000, od: 5.0, id_inner: 4.276 };
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
          .filter((s: CircuitSection) => String(s.section_type).trim() !== '');

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

  const saveSections = useCallback(async () => {
    if (!wellId) return;
    setLoading(true);
    try {
      await api.post(`/wells/${wellId}/hydraulic-sections`, sections);
      const nozSizes = nozzles.sizes.split(',').map(Number).filter(n => n > 0);
      await api.post(`/wells/${wellId}/bit-nozzles`, { nozzle_sizes: nozSizes, bit_diameter: nozzles.bit_diameter });
      addToast(t('hydraulics.circuit.circuitSaved'), 'success');
    } catch (e: unknown) { const err = e as APIError; addToast('Error: ' + (err.response?.data?.detail || err.message), 'error'); }
    setLoading(false);
  }, [wellId, sections, nozzles, addToast, t]);

  const calculate = useCallback(async () => {
    setLoading(true);
    try {
      const nozSizes = nozzles.sizes.split(',').map(Number).filter(n => n > 0);
      const hydUrl = wellId
        ? `/wells/${wellId}/hydraulics/calculate`
        : `/calculate/hydraulics`;
      const surgeUrl = wellId
        ? `/wells/${wellId}/hydraulics/surge-swab`
        : `/calculate/hydraulics/surge-swab`;

      const hydBody = wellId
        ? { flow_rate: params.flow_rate, mud_weight: params.mud_weight, pv: params.pv, yp: params.yp, tvd: params.tvd, rheology_model: params.rheology_model, n: params.n, k: params.k, surface_equipment_loss: params.surface_equipment_loss, nozzle_sizes: nozSizes }
        : { flow_rate: params.flow_rate, mud_weight: params.mud_weight, pv: params.pv, yp: params.yp, tvd: params.tvd, rheology_model: params.rheology_model, n: params.n, k: params.k, surface_equipment_loss: params.surface_equipment_loss, nozzle_sizes: nozSizes, sections };

      const surgeBody = {
        mud_weight: params.mud_weight, pv: params.pv, yp: params.yp, tvd: params.tvd,
        pipe_od: params.pipe_od, pipe_id: params.pipe_id, hole_id: params.hole_id,
        pipe_velocity_fpm: params.pipe_velocity_fpm, pipe_open: params.pipe_open,
      };

      const [hydRes, surgeRes] = await Promise.all([
        api.post(hydUrl, hydBody),
        api.post(surgeUrl, surgeBody),
      ]);

      setResult({ hydraulics: hydRes.data, surge: surgeRes.data });
      setActiveTab('results');
    } catch (e: unknown) {
      const err = e as APIError;
      addToast('Error: ' + (err.response?.data?.detail || err.message), 'error');
    }
    setLoading(false);
  }, [wellId, params, nozzles, sections, addToast]);

  const hyd = result?.hydraulics;
  const surge = result?.surge;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Droplets className="text-industrial-500" size={28} />
        <h2 className="text-2xl font-bold">{t('hydraulics.title')}</h2>
      </div>

      <div className="flex gap-2 border-b border-white/10 pb-2">
        {tabs.map((tab) => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${activeTab === tab.id ? 'bg-industrial-600/20 text-industrial-400 border border-industrial-500/30' : 'text-gray-400 hover:text-gray-200'}`}>
            {tab.label}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        {/* ════ INPUT TAB ════ */}
        {activeTab === 'input' && (
          <motion.div key="input" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="glass-panel p-6 rounded-2xl border border-white/5 space-y-8">
              {/* ── Circuit Sections ── */}
              <div>
                <div className="flex justify-between items-center mb-4">
                  <h3 className="font-bold text-lg">{t('hydraulics.sections.circuit')}</h3>
                  <div className="flex gap-2">
                    <button onClick={() => setSections([...sections, { section_type: 'drill_pipe', length: 1000, od: 5.0, id_inner: 4.276 }])} className="flex items-center gap-1 px-3 py-1.5 bg-white/5 hover:bg-white/10 rounded-lg text-sm"><Plus size={14} /> {t('common.add')}</button>
                    <button onClick={() => circuitFileRef.current?.click()} className="flex items-center gap-1 px-3 py-1.5 bg-white/5 hover:bg-white/10 rounded-lg text-sm"><Upload size={14} /> {t('hydraulics.circuit.uploadFile')}</button>
                    <input ref={circuitFileRef} type="file" accept=".csv,.xlsx,.xls" className="hidden" onChange={handleCircuitFileUpload} />
                    {wellId && (
                      <button onClick={saveSections} disabled={loading} className="px-4 py-1.5 bg-industrial-600 hover:bg-industrial-700 rounded-lg text-sm font-bold disabled:opacity-50">{loading ? t('common.saving') : t('hydraulics.circuit.saveAll')}</button>
                    )}
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
                            {VALID_SECTION_TYPES.map(st => <option key={st} value={st}>{st}</option>)}
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
              </div>

              {/* ── Nozzles ── */}
              <div className="pt-4 border-t border-white/5">
                <h3 className="font-bold text-sm mb-3">{t('hydraulics.nozzles.title')}</h3>
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

              {/* ── Fluid & Hydraulic Parameters ── */}
              <div className="pt-4 border-t border-white/5">
                <h3 className="font-bold text-sm mb-3">{t('hydraulics.sections.fluidParams')}</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div><label className="text-xs text-white/40 block mb-1">{t('hydraulics.params.flowRate')}</label><input type="number" value={params.flow_rate} onChange={(e) => setParams({ ...params, flow_rate: +e.target.value })} className="input-field w-full py-2 px-3 text-sm" /></div>
                  <div><label className="text-xs text-white/40 block mb-1">{t('hydraulics.params.mudWeight')}</label><input type="number" step="0.1" value={params.mud_weight} onChange={(e) => setParams({ ...params, mud_weight: +e.target.value })} className="input-field w-full py-2 px-3 text-sm" /></div>
                  <div><label className="text-xs text-white/40 block mb-1">{t('hydraulics.params.pv')}</label><input type="number" value={params.pv} onChange={(e) => setParams({ ...params, pv: +e.target.value })} className="input-field w-full py-2 px-3 text-sm" /></div>
                  <div><label className="text-xs text-white/40 block mb-1">{t('hydraulics.params.yp')}</label><input type="number" value={params.yp} onChange={(e) => setParams({ ...params, yp: +e.target.value })} className="input-field w-full py-2 px-3 text-sm" /></div>
                  <div><label className="text-xs text-white/40 block mb-1">{t('hydraulics.params.tvd')}</label><input type="number" value={params.tvd} onChange={(e) => setParams({ ...params, tvd: +e.target.value })} className="input-field w-full py-2 px-3 text-sm" /></div>
                  <div>
                    <label className="text-xs text-white/40 block mb-1">{t('hydraulics.params.rheologyModel')}</label>
                    <select value={params.rheology_model} onChange={(e) => setParams({ ...params, rheology_model: e.target.value })} className="input-field w-full py-2 px-3 text-sm">
                      <option value="bingham_plastic">{t('hydraulics.params.bingham')}</option>
                      <option value="power_law">{t('hydraulics.params.powerLaw')}</option>
                    </select>
                  </div>
                  {params.rheology_model === 'power_law' && <>
                    <div><label className="text-xs text-white/40 block mb-1">{t('hydraulics.params.flowIndex')}</label><input type="number" step="0.01" value={params.n} onChange={(e) => setParams({ ...params, n: +e.target.value })} className="input-field w-full py-2 px-3 text-sm" /></div>
                    <div><label className="text-xs text-white/40 block mb-1">{t('hydraulics.params.consistency')}</label><input type="number" value={params.k} onChange={(e) => setParams({ ...params, k: +e.target.value })} className="input-field w-full py-2 px-3 text-sm" /></div>
                  </>}
                </div>
              </div>

              {/* ── Surge/Swab Parameters ── */}
              <div className="pt-4 border-t border-white/5">
                <h3 className="font-bold text-sm mb-3">{t('hydraulics.sections.surgeParams')}</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div><label className="text-xs text-white/40 block mb-1">{t('hydraulics.surge.pipeOD')}</label><input type="number" step="0.1" value={params.pipe_od} onChange={(e) => setParams({ ...params, pipe_od: +e.target.value })} className="input-field w-full py-2 px-3 text-sm" /></div>
                  <div><label className="text-xs text-white/40 block mb-1">{t('hydraulics.surge.holeID')}</label><input type="number" step="0.1" value={params.hole_id} onChange={(e) => setParams({ ...params, hole_id: +e.target.value })} className="input-field w-full py-2 px-3 text-sm" /></div>
                  <div><label className="text-xs text-white/40 block mb-1">{t('hydraulics.surge.tripSpeed')}</label><input type="number" value={params.pipe_velocity_fpm} onChange={(e) => setParams({ ...params, pipe_velocity_fpm: +e.target.value })} className="input-field w-full py-2 px-3 text-sm" /></div>
                  <div className="flex items-end pb-1">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input type="checkbox" checked={params.pipe_open} onChange={(e) => setParams({ ...params, pipe_open: e.target.checked })} className="accent-industrial-500" />
                      <span className="text-sm">{t('hydraulics.surge.openEnded')}</span>
                    </label>
                  </div>
                </div>
              </div>

              {/* ── Calculate Button ── */}
              <div className="pt-4 border-t border-white/5 flex justify-center">
                <button onClick={calculate} disabled={loading} className="btn-primary py-3 px-10 text-lg flex items-center gap-2 disabled:opacity-50">
                  <Play size={18} /> {loading ? t('common.calculating') : t('hydraulics.params.calculateCircuit')}
                </button>
              </div>
            </div>
          </motion.div>
        )}

        {/* ════ RESULTS TAB ════ */}
        {activeTab === 'results' && result && (
          <motion.div key="results" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-6">
            {/* Summary Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="glass-panel p-4 rounded-xl border border-white/5 text-center">
                <p className="text-xs text-white/40 mb-1">{t('hydraulics.summary.totalSPP')}</p>
                <p className="text-2xl font-bold text-industrial-400">{hyd?.summary.total_spp_psi?.toLocaleString()} psi</p>
              </div>
              <div className="glass-panel p-4 rounded-xl border border-white/5 text-center">
                <p className="text-xs text-white/40 mb-1">{t('hydraulics.summary.ecdAtTD')}</p>
                <p className="text-2xl font-bold text-emerald-400">{hyd?.ecd?.ecd_ppg} ppg</p>
                <span className={`text-xs px-2 py-0.5 rounded-full ${hyd?.ecd?.status?.includes('HIGH') ? 'bg-red-500/20 text-red-400' : hyd?.ecd?.status?.includes('LOW') ? 'bg-yellow-500/20 text-yellow-400' : 'bg-green-500/20 text-green-400'}`}>
                  {hyd?.ecd?.status}
                </span>
              </div>
              <div className="glass-panel p-4 rounded-xl border border-white/5 text-center">
                <p className="text-xs text-white/40 mb-1">{t('hydraulics.summary.bitHSI')}</p>
                <p className="text-2xl font-bold text-amber-400">{hyd?.bit_hydraulics?.hsi}</p>
              </div>
              <div className="glass-panel p-4 rounded-xl border border-white/5 text-center">
                <p className="text-xs text-white/40 mb-1">{t('hydraulics.summary.surgeEMW')}</p>
                <p className="text-2xl font-bold text-red-400">+{surge?.surge_emw_ppg} ppg</p>
                <span className={`text-xs px-2 py-0.5 rounded-full ${surge?.surge_margin?.includes('CRITICAL') ? 'bg-red-500/20 text-red-400' : surge?.surge_margin?.includes('WARNING') ? 'bg-yellow-500/20 text-yellow-400' : 'bg-green-500/20 text-green-400'}`}>
                  {surge?.surge_margin}
                </span>
              </div>
            </div>

            {/* Charts Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {hyd?.summary && (
                <PressureWaterfallChart summary={hyd.summary} height={280} />
              )}
              {hyd?.ecd && (
                <ECDProfileChart
                  data={(() => {
                    const backendProfile = hyd.ecd_profile || [];
                    const mw = params.mud_weight;
                    const ecdAtTd = hyd.ecd.ecd_ppg;
                    const td = params.tvd;
                    if (backendProfile.length >= 5) return backendProfile;
                    const steps = 11;
                    return Array.from({ length: steps }, (_, i) => {
                      const tvd = Math.round((i / (steps - 1)) * td);
                      const ecd = tvd === 0 ? mw : +(mw + (ecdAtTd - mw) * (tvd / td)).toFixed(2);
                      return { tvd, ecd };
                    });
                  })()}
                  mudWeight={params.mud_weight}
                  lotEmw={14.0}
                  height={300}
                />
              )}
              {hyd?.section_results && (
                <FlowRegimeTrack data={hyd.section_results} height={250} />
              )}
              {hyd?.bit_hydraulics && (
                <BitHydraulicsGauges bitData={hyd.bit_hydraulics} />
              )}
            </div>

            {/* Surge/Swab Window — full width */}
            {surge && (
              <SurgeSwabWindow
                mudWeight={params.mud_weight}
                surgeEcd={surge.surge_ecd_ppg}
                swabEcd={surge.swab_ecd_ppg}
                lotEmw={14.0}
                porePressure={params.mud_weight - 0.5}
                surgeMargin={surge.surge_margin || 'OK'}
                swabMargin={surge.swab_margin || 'OK'}
                height={280}
              />
            )}

            {/* Section Results Table */}
            {hyd?.section_results && (
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
                    {hyd.section_results.map((sr: HydSectionResult, i: number) => (
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
            )}

            {/* Surge/Swab Detail Cards */}
            {surge && (
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <div className="glass-panel p-5 rounded-xl border border-white/5 text-center">
                  <p className="text-xs text-white/40 mb-2">{t('hydraulics.surge.surgeECD')}</p>
                  <p className="text-2xl font-bold text-red-400">{surge.surge_ecd_ppg} ppg</p>
                  <p className="text-xs text-white/30">+{surge.surge_emw_ppg} ppg</p>
                </div>
                <div className="glass-panel p-5 rounded-xl border border-white/5 text-center">
                  <p className="text-xs text-white/40 mb-2">{t('hydraulics.surge.swabECD')}</p>
                  <p className="text-2xl font-bold text-blue-400">{surge.swab_ecd_ppg} ppg</p>
                  <p className="text-xs text-white/30">-{surge.swab_emw_ppg} ppg</p>
                </div>
                <div className="glass-panel p-5 rounded-xl border border-white/5 text-center">
                  <p className="text-xs text-white/40 mb-2">{t('hydraulics.surge.effectiveVelocity')}</p>
                  <p className="text-2xl font-bold text-white">{surge.effective_velocity_fpm} ft/min</p>
                </div>
                <div className={`glass-panel p-5 rounded-xl border text-center ${surge.surge_margin?.includes('CRITICAL') ? 'border-red-500/30 bg-red-500/5' : surge.surge_margin?.includes('WARNING') ? 'border-yellow-500/30 bg-yellow-500/5' : 'border-green-500/30 bg-green-500/5'}`}>
                  <p className="text-xs text-white/40 mb-2">{t('hydraulics.surge.surgeMargin')}</p>
                  <p className={`text-sm font-bold ${surge.surge_margin?.includes('CRITICAL') ? 'text-red-400' : surge.surge_margin?.includes('WARNING') ? 'text-yellow-400' : 'text-green-400'}`}>{surge.surge_margin}</p>
                </div>
                <div className={`glass-panel p-5 rounded-xl border text-center ${surge.swab_margin?.includes('CRITICAL') ? 'border-red-500/30 bg-red-500/5' : surge.swab_margin?.includes('WARNING') ? 'border-yellow-500/30 bg-yellow-500/5' : 'border-green-500/30 bg-green-500/5'}`}>
                  <p className="text-xs text-white/40 mb-2">{t('hydraulics.surge.swabMargin')}</p>
                  <p className={`text-sm font-bold ${surge.swab_margin?.includes('CRITICAL') ? 'text-red-400' : surge.swab_margin?.includes('WARNING') ? 'text-yellow-400' : 'text-green-400'}`}>{surge.swab_margin}</p>
                </div>
                <div className="glass-panel p-5 rounded-xl border border-white/5 text-center">
                  <p className="text-xs text-white/40 mb-2">{t('hydraulics.surge.pressure')}</p>
                  <p className="text-2xl font-bold text-industrial-400">{surge.surge_pressure_psi} psi</p>
                </div>
              </div>
            )}

            {/* AI Analysis */}
            <AIAnalysisPanel
              moduleName={t('modules.hydraulicsECD')}
              moduleIcon={Droplets}
              wellName={wellName}
              analysis={aiAnalysis?.analysis || null}
              confidence={aiAnalysis?.confidence || 'MEDIUM'}
              agentRole={aiAnalysis?.agent_role || 'Mud Engineer'}
              isLoading={isAnalyzing}
              keyMetrics={aiAnalysis?.key_metrics || []}
              onAnalyze={handleRunAnalysis}
              onClose={() => setAiAnalysis(null)}
              provider={provider}
              onProviderChange={setProvider}
              availableProviders={availableProviders}
            />
          </motion.div>
        )}

        {/* No results placeholder */}
        {activeTab === 'results' && !result && (
          <div className="animate-fadeIn">
            <div className="glass-panel p-12 rounded-2xl border border-white/5 text-center text-gray-500">
              <Droplets size={48} className="mx-auto mb-4 opacity-30" />
              <p>{t('hydraulics.noResults')}</p>
            </div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default HydraulicsModule;
