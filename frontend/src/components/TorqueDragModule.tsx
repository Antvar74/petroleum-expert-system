import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowUpDown, Plus, Trash2, Play, RefreshCw, Upload, Layers, BrainCircuit } from 'lucide-react';
import { API_BASE_URL } from '../config';
import TDMultiSeriesChart from './charts/td/TDMultiSeriesChart';
import HookloadComparisonBar from './charts/td/HookloadComparisonBar';
import BucklingStatusTrack from './charts/td/BucklingStatusTrack';
import TorqueDragProfile from './charts/td/TorqueDragProfile';
import WellboreTrajectory from './charts/td/WellboreTrajectory';
import AIAnalysisPanel from './AIAnalysisPanel';
import { useTranslation } from 'react-i18next';
import { useLanguage } from '../hooks/useLanguage';
import { useToast } from './ui/Toast';
import type { Provider, ProviderOption } from '../types/ai';
import * as XLSX from 'xlsx';

interface TorqueDragModuleProps {
  wellId?: number;
  wellName?: string;
}

const OPERATIONS = ['rotating', 'sliding', 'trip_in', 'trip_out', 'back_ream'];

const TorqueDragModule: React.FC<TorqueDragModuleProps> = ({ wellId, wellName = '' }) => {
  const [activeTab, setActiveTab] = useState('survey');
  const [loading, setLoading] = useState(false);

  // Survey state — default: J-type well profile with build & hold sections
  const [surveyStations, setSurveyStations] = useState<any[]>([
    { md: 0, inclination: 0, azimuth: 135 },
    { md: 1000, inclination: 0, azimuth: 135 },
    { md: 2000, inclination: 0, azimuth: 135 },
    { md: 3000, inclination: 5, azimuth: 135 },
    { md: 4000, inclination: 15, azimuth: 135 },
    { md: 5000, inclination: 30, azimuth: 135 },
    { md: 6000, inclination: 45, azimuth: 135 },
    { md: 7000, inclination: 45, azimuth: 135 },
    { md: 8000, inclination: 45, azimuth: 135 },
    { md: 9000, inclination: 45, azimuth: 135 },
    { md: 10000, inclination: 45, azimuth: 135 },
  ]);
  const [computedSurvey, setComputedSurvey] = useState<any[]>([]);

  // Drillstring state
  const [drillstring, setDrillstring] = useState<any[]>([
    { section_name: 'Drill Pipe', od: 5.0, id_inner: 4.276, weight: 19.5, length: 9500, order_from_bit: 3 },
    { section_name: 'HWDP', od: 5.0, id_inner: 3.0, weight: 49.3, length: 300, order_from_bit: 2 },
    { section_name: 'Drill Collar', od: 6.5, id_inner: 2.813, weight: 83.0, length: 200, order_from_bit: 1 },
  ]);

  // T&D Analysis state
  const [tdParams, setTdParams] = useState({
    operation: 'trip_out',
    friction_cased: 0.25,
    friction_open: 0.35,
    mud_weight: 10.0,
    wob: 0,
    rpm: 0,
    casing_shoe_md: 5000,
  });
  const [tdResult, setTdResult] = useState<any>(null);

  // Multi-operation compare state
  const [compareResult, setCompareResult] = useState<any>(null);
  const [compareLoading, setCompareLoading] = useState(false);

  // Back-calculate state
  const [backCalcParams, setBackCalcParams] = useState({
    measured_hookload: 200,
    operation: 'trip_out',
    mud_weight: 10.0,
    wob: 0,
    casing_shoe_md: 5000,
  });
  const [backCalcResult, setBackCalcResult] = useState<any>(null);

  // AI Analysis state
  const [aiAnalysis, setAiAnalysis] = useState<any>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const { t } = useTranslation();
  const { language, setLanguage } = useLanguage();
  const { addToast } = useToast();
  const surveyFileRef = useRef<HTMLInputElement>(null);
  const drillstringFileRef = useRef<HTMLInputElement>(null);
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
    if (!tdResult && !compareResult) return;
    setIsAnalyzing(true);
    try {
      const analyzeUrl = wellId
        ? `${API_BASE_URL}/wells/${wellId}/torque-drag/analyze`
        : `${API_BASE_URL}/analyze/module`;
      const res = await axios.post(analyzeUrl, {
        ...(wellId ? {} : { module: 'torque-drag', well_name: wellName || 'General Analysis' }),
        result_data: tdResult || {},
        params: tdParams,
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
    { id: 'survey', label: t('torqueDrag.tabs.survey') },
    { id: 'drillstring', label: t('torqueDrag.tabs.drillstring') },
    { id: 'analysis', label: t('torqueDrag.tabs.analysis') },
    { id: 'compare', label: t('torqueDrag.tabs.compare') },
  ];

  // --- Survey handlers ---
  const addSurveyStation = () => {
    const last = surveyStations[surveyStations.length - 1];
    setSurveyStations([...surveyStations, { md: (last?.md || 0) + 500, inclination: 0, azimuth: 0 }]);
  };

  const removeSurveyStation = (idx: number) => {
    setSurveyStations(surveyStations.filter((_, i) => i !== idx));
  };

  const updateStation = (idx: number, field: string, value: string) => {
    const updated = [...surveyStations];
    updated[idx] = { ...updated[idx], [field]: parseFloat(value) || 0 };
    setSurveyStations(updated);
  };

  // ── Survey file upload (CSV / Excel) ──
  const SURVEY_COL_MAP: Record<string, string> = {
    'md': 'md', 'md (ft)': 'md', 'md(ft)': 'md', 'measured depth': 'md',
    'pm': 'md', 'pm (ft)': 'md', 'profundidad medida': 'md', 'prof': 'md', 'depth': 'md',
    'inc': 'inclination', 'inc (°)': 'inclination', 'inclination': 'inclination',
    'inclinacion': 'inclination', 'inclinación': 'inclination', 'incl': 'inclination',
    'azi': 'azimuth', 'azi (°)': 'azimuth', 'azimuth': 'azimuth',
    'azimut': 'azimuth', 'az': 'azimuth',
  };

  const handleSurveyFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (evt) => {
      try {
        const data = new Uint8Array(evt.target?.result as ArrayBuffer);
        const wb = XLSX.read(data, { type: 'array' });
        const sheet = wb.Sheets[wb.SheetNames[0]];
        if (!sheet) { addToast(t('torqueDrag.survey.uploadEmpty'), 'error'); return; }
        const rows: any[] = XLSX.utils.sheet_to_json(sheet, { defval: '' });
        if (rows.length === 0) { addToast(t('torqueDrag.survey.uploadEmpty'), 'error'); return; }

        const hdrMap: Record<string, string> = {};
        for (const fh of Object.keys(rows[0])) {
          const mapped = SURVEY_COL_MAP[fh.trim().toLowerCase()];
          if (mapped) hdrMap[fh] = mapped;
        }
        if (!Object.values(hdrMap).includes('md')) {
          addToast(t('torqueDrag.survey.uploadNoColumns'), 'error'); return;
        }

        const parsed = rows
          .map(row => {
            const st = { md: 0, inclination: 0, azimuth: 0 };
            for (const [fc, sf] of Object.entries(hdrMap)) {
              (st as any)[sf] = parseFloat(row[fc]) || 0;
            }
            return st;
          })
          .filter(s => s.md > 0);

        if (parsed.length === 0) { addToast(t('torqueDrag.survey.uploadEmpty'), 'error'); return; }
        setSurveyStations(parsed);
        setComputedSurvey([]); // clear computed since data changed
        addToast(t('torqueDrag.survey.uploadSuccess', { count: parsed.length }), 'success');
      } catch (err) {
        console.error('Survey file parse error:', err);
        addToast(t('torqueDrag.survey.uploadError'), 'error');
      }
    };
    reader.readAsArrayBuffer(file);
    e.target.value = '';
  };

  const uploadSurvey = async () => {
    if (!wellId) return;
    setLoading(true);
    try {
      const res = await axios.post(`${API_BASE_URL}/wells/${wellId}/survey`, surveyStations);
      setComputedSurvey(res.data.stations);
    } catch (e: any) {
      addToast(t('torqueDrag.errorUploadSurvey') + ': ' + (e.response?.data?.detail || e.message), 'error');
    }
    setLoading(false);
  };

  // --- Drillstring handlers ---
  const addSection = () => {
    setDrillstring([...drillstring, { section_name: 'New Section', od: 5.0, id_inner: 4.276, weight: 19.5, length: 500, order_from_bit: drillstring.length + 1 }]);
  };

  const removeSection = (idx: number) => {
    setDrillstring(drillstring.filter((_, i) => i !== idx));
  };

  const updateSection = (idx: number, field: string, value: string) => {
    const updated = [...drillstring];
    if (field === 'section_name') {
      updated[idx] = { ...updated[idx], [field]: value };
    } else {
      updated[idx] = { ...updated[idx], [field]: parseFloat(value) || 0 };
    }
    setDrillstring(updated);
  };

  // ── Drillstring file upload (CSV / Excel) ──
  const DS_COL_MAP: Record<string, string> = {
    'section': 'section_name', 'section name': 'section_name', 'section_name': 'section_name',
    'seccion': 'section_name', 'sección': 'section_name', 'component': 'section_name',
    'componente': 'section_name', 'name': 'section_name', 'nombre': 'section_name',
    'description': 'section_name', 'descripcion': 'section_name', 'type': 'section_name',
    'od': 'od', 'od (in)': 'od', 'od(in)': 'od', 'de': 'od', 'de (in)': 'od',
    'outer diameter': 'od', 'diametro externo': 'od',
    'id': 'id_inner', 'id (in)': 'id_inner', 'id(in)': 'id_inner', 'id_inner': 'id_inner',
    'di': 'id_inner', 'di (in)': 'id_inner', 'inner diameter': 'id_inner', 'diametro interno': 'id_inner',
    'weight': 'weight', 'weight (lb/ft)': 'weight', 'weight(lb/ft)': 'weight',
    'peso': 'weight', 'peso (lb/ft)': 'weight', 'lb/ft': 'weight',
    'length': 'length', 'length (ft)': 'length', 'length(ft)': 'length',
    'longitud': 'length', 'longitud (ft)': 'length', 'largo': 'length', 'long': 'length',
    'order': 'order_from_bit', 'order_from_bit': 'order_from_bit', 'orden': 'order_from_bit',
  };

  const handleDrillstringFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (evt) => {
      try {
        const data = new Uint8Array(evt.target?.result as ArrayBuffer);
        const wb = XLSX.read(data, { type: 'array' });
        const sheet = wb.Sheets[wb.SheetNames[0]];
        if (!sheet) { addToast(t('torqueDrag.drillstring.uploadEmpty'), 'error'); return; }
        const rows: any[] = XLSX.utils.sheet_to_json(sheet, { defval: '' });
        if (rows.length === 0) { addToast(t('torqueDrag.drillstring.uploadEmpty'), 'error'); return; }

        const hdrMap: Record<string, string> = {};
        for (const fh of Object.keys(rows[0])) {
          const mapped = DS_COL_MAP[fh.trim().toLowerCase()];
          if (mapped) hdrMap[fh] = mapped;
        }
        if (!Object.values(hdrMap).includes('section_name')) {
          addToast(t('torqueDrag.drillstring.uploadNoColumns'), 'error'); return;
        }

        const parsed = rows
          .map((row, idx) => {
            const sec: any = { section_name: '', od: 5.0, id_inner: 4.276, weight: 19.5, length: 500, order_from_bit: idx + 1 };
            for (const [fc, sf] of Object.entries(hdrMap)) {
              const v = row[fc];
              if (sf === 'section_name') sec[sf] = String(v || '').trim();
              else sec[sf] = parseFloat(v) || sec[sf];
            }
            return sec;
          })
          .filter((s: any) => s.section_name.trim() !== '');

        if (parsed.length === 0) { addToast(t('torqueDrag.drillstring.uploadEmpty'), 'error'); return; }
        setDrillstring(parsed);
        addToast(t('torqueDrag.drillstring.uploadSuccess', { count: parsed.length }), 'success');
      } catch (err) {
        console.error('Drillstring file parse error:', err);
        addToast(t('torqueDrag.drillstring.uploadError'), 'error');
      }
    };
    reader.readAsArrayBuffer(file);
    e.target.value = '';
  };

  const uploadDrillstring = async () => {
    if (!wellId) return;
    setLoading(true);
    try {
      await axios.post(`${API_BASE_URL}/wells/${wellId}/drillstring`, drillstring);
      addToast(t('torqueDrag.drillstring.savedSuccess'), 'success');
    } catch (e: any) {
      addToast(t('common.error') + ': ' + (e.response?.data?.detail || e.message), 'error');
    }
    setLoading(false);
  };

  // --- T&D calculation ---
  const runTorqueDrag = async () => {
    setLoading(true);
    try {
      const url = wellId
        ? `${API_BASE_URL}/wells/${wellId}/torque-drag`
        : `${API_BASE_URL}/calculate/torque-drag`;
      const body = wellId
        ? tdParams
        : { ...tdParams, survey: surveyStations, drillstring };
      const res = await axios.post(url, body);
      setTdResult(res.data);
    } catch (e: any) {
      addToast(t('common.error') + ': ' + (e.response?.data?.detail || e.message), 'error');
    }
    setLoading(false);
  };

  // --- Multi-operation compare ---
  const runCompare = async () => {
    setCompareLoading(true);
    try {
      const url = wellId
        ? `${API_BASE_URL}/wells/${wellId}/torque-drag/compare`
        : `${API_BASE_URL}/calculate/torque-drag/compare`;
      const body = wellId
        ? {
            friction_cased: tdParams.friction_cased,
            friction_open: tdParams.friction_open,
            mud_weight: tdParams.mud_weight,
            wob: tdParams.wob,
            rpm: tdParams.rpm,
            casing_shoe_md: tdParams.casing_shoe_md,
            operations: ['trip_out', 'trip_in', 'rotating', 'sliding'],
          }
        : {
            survey: surveyStations,
            drillstring,
            friction_cased: tdParams.friction_cased,
            friction_open: tdParams.friction_open,
            mud_weight: tdParams.mud_weight,
            wob: tdParams.wob,
            rpm: tdParams.rpm,
            casing_shoe_md: tdParams.casing_shoe_md,
            operations: ['trip_out', 'trip_in', 'rotating', 'sliding'],
          };
      const res = await axios.post(url, body);
      setCompareResult(res.data);
    } catch (e: any) {
      addToast(t('common.error') + ': ' + (e.response?.data?.detail || e.message), 'error');
    }
    setCompareLoading(false);
  };

  // Compute buoyed weight from drillstring + buoyancy factor
  const computeBuoyedWeight = (): number | undefined => {
    if (!tdResult?.summary?.buoyancy_factor) return undefined;
    const totalWeight = drillstring.reduce((sum, s) => sum + (s.weight * s.length) / 1000, 0); // klb
    return Math.round(totalWeight * tdResult.summary.buoyancy_factor * 10) / 10;
  };

  // --- Back-calculate friction ---
  const runBackCalc = async () => {
    setLoading(true);
    try {
      const url = wellId
        ? `${API_BASE_URL}/torque-drag/back-calculate`
        : `${API_BASE_URL}/calculate/torque-drag/back-calculate`;
      const body = wellId
        ? { well_id: wellId, ...backCalcParams }
        : { survey: surveyStations, drillstring, ...backCalcParams };
      const res = await axios.post(url, body);
      setBackCalcResult(res.data);
    } catch (e: any) {
      addToast(t('common.error') + ': ' + (e.response?.data?.detail || e.message), 'error');
    }
    setLoading(false);
  };

  // Sub-tab state for analysis results
  const [analysisSubTab, setAnalysisSubTab] = useState('force');

  return (
    <div className="space-y-6 py-8">
      <div className="flex items-center gap-3 mb-8">
        <ArrowUpDown className="text-industrial-500" size={28} />
        <h2 className="text-2xl font-bold">{t('torqueDrag.title')}</h2>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-8">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-5 py-2.5 rounded-xl text-sm font-bold transition-all ${activeTab === tab.id
              ? 'bg-industrial-600 text-white shadow-lg'
              : 'bg-white/5 text-white/40 hover:text-white hover:bg-white/10'
              }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        {/* === Survey Input Tab === */}
        {activeTab === 'survey' && (
          <motion.div key="survey" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="space-y-6">
            <div className="glass-panel p-6 rounded-2xl border border-white/5">
              <div className="flex justify-between items-center mb-4">
                <h3 className="font-bold text-lg">{t('torqueDrag.survey.title')}</h3>
                <div className="flex gap-2">
                  <button onClick={addSurveyStation} className="flex items-center gap-1 px-3 py-1.5 bg-white/5 hover:bg-white/10 rounded-lg text-sm transition-colors">
                    <Plus size={14} /> {t('torqueDrag.survey.addStation')}
                  </button>
                  <button onClick={() => surveyFileRef.current?.click()} className="flex items-center gap-1 px-3 py-1.5 bg-white/5 hover:bg-white/10 rounded-lg text-sm transition-colors">
                    <Upload size={14} /> {t('torqueDrag.survey.uploadFile')}
                  </button>
                  <input ref={surveyFileRef} type="file" accept=".csv,.xlsx,.xls" className="hidden" onChange={handleSurveyFileUpload} />
                  <button onClick={uploadSurvey} disabled={loading} className="flex items-center gap-1 px-4 py-1.5 bg-industrial-600 hover:bg-industrial-700 rounded-lg text-sm font-bold transition-colors disabled:opacity-50">
                    <Upload size={14} /> {loading ? t('common.computing') : t('torqueDrag.survey.uploadCompute')}
                  </button>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-white/40 border-b border-white/5">
                      <th className="text-left py-2 px-2">{t('torqueDrag.survey.md')}</th>
                      <th className="text-left py-2 px-2">{t('torqueDrag.survey.inc')}</th>
                      <th className="text-left py-2 px-2">{t('torqueDrag.survey.azi')}</th>
                      {computedSurvey.length > 0 && <>
                        <th className="text-left py-2 px-2">{t('torqueDrag.survey.tvd')}</th>
                        <th className="text-left py-2 px-2">{t('torqueDrag.survey.north')}</th>
                        <th className="text-left py-2 px-2">{t('torqueDrag.survey.east')}</th>
                        <th className="text-left py-2 px-2">{t('torqueDrag.survey.dls')}</th>
                      </>}
                      <th className="w-10"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {surveyStations.map((s, i) => (
                      <tr key={i} className="border-b border-white/5">
                        <td className="py-1 px-2"><input type="number" value={s.md} onChange={(e) => updateStation(i, 'md', e.target.value)} className="input-field w-24 py-1 px-2 text-sm" /></td>
                        <td className="py-1 px-2"><input type="number" value={s.inclination} onChange={(e) => updateStation(i, 'inclination', e.target.value)} className="input-field w-20 py-1 px-2 text-sm" /></td>
                        <td className="py-1 px-2"><input type="number" value={s.azimuth} onChange={(e) => updateStation(i, 'azimuth', e.target.value)} className="input-field w-20 py-1 px-2 text-sm" /></td>
                        {computedSurvey.length > 0 && computedSurvey[i] && <>
                          <td className="py-1 px-2 text-industrial-400">{computedSurvey[i].tvd}</td>
                          <td className="py-1 px-2 text-industrial-400">{computedSurvey[i].north}</td>
                          <td className="py-1 px-2 text-industrial-400">{computedSurvey[i].east}</td>
                          <td className="py-1 px-2 text-industrial-400">{computedSurvey[i].dls}</td>
                        </>}
                        <td className="py-1">
                          <button onClick={() => removeSurveyStation(i)} className="text-red-400/50 hover:text-red-400 p-1"><Trash2 size={14} /></button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </motion.div>
        )}

        {/* === Drillstring Tab === */}
        {activeTab === 'drillstring' && (
          <motion.div key="drillstring" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="space-y-6">
            <div className="glass-panel p-6 rounded-2xl border border-white/5">
              <div className="flex justify-between items-center mb-4">
                <h3 className="font-bold text-lg">{t('torqueDrag.drillstring.title')}</h3>
                <div className="flex gap-2">
                  <button onClick={addSection} className="flex items-center gap-1 px-3 py-1.5 bg-white/5 hover:bg-white/10 rounded-lg text-sm transition-colors">
                    <Plus size={14} /> {t('torqueDrag.drillstring.addSection')}
                  </button>
                  <button onClick={() => drillstringFileRef.current?.click()} className="flex items-center gap-1 px-3 py-1.5 bg-white/5 hover:bg-white/10 rounded-lg text-sm transition-colors">
                    <Upload size={14} /> {t('torqueDrag.drillstring.uploadFile')}
                  </button>
                  <input ref={drillstringFileRef} type="file" accept=".csv,.xlsx,.xls" className="hidden" onChange={handleDrillstringFileUpload} />
                  <button onClick={uploadDrillstring} disabled={loading} className="flex items-center gap-1 px-4 py-1.5 bg-industrial-600 hover:bg-industrial-700 rounded-lg text-sm font-bold transition-colors disabled:opacity-50">
                    <Upload size={14} /> {t('common.save')}
                  </button>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-white/40 border-b border-white/5">
                      <th className="text-left py-2 px-2">{t('torqueDrag.drillstring.section')}</th>
                      <th className="text-left py-2 px-2">{t('torqueDrag.drillstring.od')}</th>
                      <th className="text-left py-2 px-2">{t('torqueDrag.drillstring.id')}</th>
                      <th className="text-left py-2 px-2">{t('torqueDrag.drillstring.weight')}</th>
                      <th className="text-left py-2 px-2">{t('torqueDrag.drillstring.length')}</th>
                      <th className="text-left py-2 px-2">{t('torqueDrag.drillstring.order')}</th>
                      <th className="w-10"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {drillstring.map((s, i) => (
                      <tr key={i} className="border-b border-white/5">
                        <td className="py-1 px-2"><input type="text" value={s.section_name} onChange={(e) => updateSection(i, 'section_name', e.target.value)} className="input-field w-32 py-1 px-2 text-sm" /></td>
                        <td className="py-1 px-2"><input type="number" step="0.1" value={s.od} onChange={(e) => updateSection(i, 'od', e.target.value)} className="input-field w-20 py-1 px-2 text-sm" /></td>
                        <td className="py-1 px-2"><input type="number" step="0.001" value={s.id_inner} onChange={(e) => updateSection(i, 'id_inner', e.target.value)} className="input-field w-20 py-1 px-2 text-sm" /></td>
                        <td className="py-1 px-2"><input type="number" step="0.1" value={s.weight} onChange={(e) => updateSection(i, 'weight', e.target.value)} className="input-field w-20 py-1 px-2 text-sm" /></td>
                        <td className="py-1 px-2"><input type="number" value={s.length} onChange={(e) => updateSection(i, 'length', e.target.value)} className="input-field w-24 py-1 px-2 text-sm" /></td>
                        <td className="py-1 px-2"><input type="number" value={s.order_from_bit} onChange={(e) => updateSection(i, 'order_from_bit', e.target.value)} className="input-field w-16 py-1 px-2 text-sm" /></td>
                        <td className="py-1"><button onClick={() => removeSection(i)} className="text-red-400/50 hover:text-red-400 p-1"><Trash2 size={14} /></button></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </motion.div>
        )}

        {/* === T&D Analysis Tab === */}
        {activeTab === 'analysis' && (
          <motion.div key="analysis" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="space-y-6">
            <div className="glass-panel p-6 rounded-2xl border border-white/5">
              <h3 className="font-bold text-lg mb-4">{t('torqueDrag.analysis.title')}</h3>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                <div>
                  <label className="text-xs text-white/40 block mb-1">{t('torqueDrag.analysis.operation')}</label>
                  <select value={tdParams.operation} onChange={(e) => setTdParams({ ...tdParams, operation: e.target.value })} className="input-field w-full py-2 px-3 text-sm">
                    {OPERATIONS.map((op) => <option key={op} value={op}>{op.replace('_', ' ').toUpperCase()}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-white/40 block mb-1">{t('torqueDrag.analysis.frictionCased')}</label>
                  <input type="number" step="0.01" value={tdParams.friction_cased} onChange={(e) => setTdParams({ ...tdParams, friction_cased: parseFloat(e.target.value) || 0 })} className="input-field w-full py-2 px-3 text-sm" />
                </div>
                <div>
                  <label className="text-xs text-white/40 block mb-1">{t('torqueDrag.analysis.frictionOpen')}</label>
                  <input type="number" step="0.01" value={tdParams.friction_open} onChange={(e) => setTdParams({ ...tdParams, friction_open: parseFloat(e.target.value) || 0 })} className="input-field w-full py-2 px-3 text-sm" />
                </div>
                <div>
                  <label className="text-xs text-white/40 block mb-1">{t('torqueDrag.analysis.mudWeight')}</label>
                  <input type="number" step="0.1" value={tdParams.mud_weight} onChange={(e) => setTdParams({ ...tdParams, mud_weight: parseFloat(e.target.value) || 0 })} className="input-field w-full py-2 px-3 text-sm" />
                </div>
                <div>
                  <label className="text-xs text-white/40 block mb-1">{t('torqueDrag.analysis.wob')}</label>
                  <input type="number" value={tdParams.wob} onChange={(e) => setTdParams({ ...tdParams, wob: parseFloat(e.target.value) || 0 })} className="input-field w-full py-2 px-3 text-sm" />
                </div>
                <div>
                  <label className="text-xs text-white/40 block mb-1">{t('torqueDrag.analysis.rpm')}</label>
                  <input type="number" value={tdParams.rpm} onChange={(e) => setTdParams({ ...tdParams, rpm: parseFloat(e.target.value) || 0 })} className="input-field w-full py-2 px-3 text-sm" />
                </div>
                <div>
                  <label className="text-xs text-white/40 block mb-1">{t('torqueDrag.analysis.casingShoe')}</label>
                  <input type="number" value={tdParams.casing_shoe_md} onChange={(e) => setTdParams({ ...tdParams, casing_shoe_md: parseFloat(e.target.value) || 0 })} className="input-field w-full py-2 px-3 text-sm" />
                </div>
              </div>

              <button onClick={runTorqueDrag} disabled={loading} className="btn-primary flex items-center gap-2 disabled:opacity-50">
                <Play size={16} /> {loading ? t('common.calculating') : t('torqueDrag.analysis.runCalculation')}
              </button>
            </div>

            {/* Results */}
            {tdResult && (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
                {/* Summary cards */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="glass-panel p-4 rounded-xl border border-white/5 text-center">
                    <p className="text-xs text-white/40 mb-1">{t('torqueDrag.analysis.surfaceHookload')}</p>
                    <p className="text-2xl font-bold text-industrial-400">{tdResult.summary?.surface_hookload_klb}</p>
                    <p className="text-xs text-white/30">klb</p>
                  </div>
                  <div className="glass-panel p-4 rounded-xl border border-white/5 text-center">
                    <p className="text-xs text-white/40 mb-1">{t('torqueDrag.analysis.surfaceTorque')}</p>
                    <p className="text-2xl font-bold text-industrial-400">{tdResult.summary?.surface_torque_ftlb}</p>
                    <p className="text-xs text-white/30">ft-lb</p>
                  </div>
                  <div className="glass-panel p-4 rounded-xl border border-white/5 text-center">
                    <p className="text-xs text-white/40 mb-1">{t('torqueDrag.analysis.maxSideForce')}</p>
                    <p className="text-2xl font-bold text-industrial-400">{tdResult.summary?.max_side_force_lb}</p>
                    <p className="text-xs text-white/30">lb</p>
                  </div>
                  <div className="glass-panel p-4 rounded-xl border border-white/5 text-center">
                    <p className="text-xs text-white/40 mb-1">{t('torqueDrag.analysis.buoyancyFactor')}</p>
                    <p className="text-2xl font-bold text-white">{tdResult.summary?.buoyancy_factor}</p>
                  </div>
                </div>

                {/* Alerts */}
                {tdResult.summary?.alerts?.length > 0 && (
                  <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4">
                    <p className="text-red-400 font-bold text-sm mb-2">{t('common.alerts')}</p>
                    {tdResult.summary.alerts.map((a: string, i: number) => (
                      <p key={i} className="text-red-300 text-sm">- {a}</p>
                    ))}
                  </div>
                )}

                {/* Analysis sub-tabs */}
                <div className="flex gap-2">
                  {[
                    { id: 'force', label: t('torqueDrag.subtabs.force') },
                    { id: 'torque', label: t('torqueDrag.subtabs.torque') },
                    { id: 'wellpath', label: t('torqueDrag.subtabs.wellpath') },
                    { id: 'table', label: t('torqueDrag.subtabs.table') },
                  ].map(st => (
                    <button key={st.id} onClick={() => setAnalysisSubTab(st.id)}
                      className={`px-4 py-2 rounded-lg text-xs font-bold transition-all ${analysisSubTab === st.id ? 'bg-industrial-600/50 text-white' : 'bg-white/5 text-white/40 hover:text-white'}`}>
                      {st.label}
                    </button>
                  ))}
                </div>

                {/* Force Analysis — DepthTrack + Buckling + Hookload */}
                {analysisSubTab === 'force' && (
                  <div className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                      <div className="md:col-span-3">
                        <TDMultiSeriesChart
                          data={tdResult.station_results?.map((sr: any) => ({
                            md: sr.md,
                            [tdParams.operation]: sr.axial_force,
                          })) || []}
                          operations={[tdParams.operation]}
                          casingShoe={tdParams.casing_shoe_md}
                          height={380}
                        />
                      </div>
                      <div>
                        <BucklingStatusTrack
                          data={tdResult.station_results || []}
                          height={380}
                        />
                      </div>
                    </div>
                    <HookloadComparisonBar
                      data={[{
                        operation: tdParams.operation.replace('_', ' ').toUpperCase(),
                        hookload_klb: tdResult.summary?.surface_hookload_klb || 0,
                        label: tdParams.operation.replace('_', ' ').toUpperCase(),
                      }]}
                      buoyedWeight={computeBuoyedWeight()}
                      height={200}
                    />
                  </div>
                )}

                {/* Torque Profile */}
                {analysisSubTab === 'torque' && (
                  <TorqueDragProfile
                    data={tdResult.station_results || []}
                    height={400}
                  />
                )}

                {/* Well Path */}
                {analysisSubTab === 'wellpath' && computedSurvey.length > 0 && (
                  <WellboreTrajectory
                    data={computedSurvey}
                    height={400}
                  />
                )}
                {analysisSubTab === 'wellpath' && computedSurvey.length === 0 && (
                  <div className="glass-panel p-12 rounded-2xl border border-white/5 text-center">
                    <p className="text-white/40">{t('torqueDrag.uploadSurveyHint')}</p>
                  </div>
                )}

                {/* Station results table */}
                {analysisSubTab === 'table' && (
                  <div className="glass-panel p-6 rounded-2xl border border-white/5">
                    <h4 className="font-bold mb-4">{t('torqueDrag.stationResults')}</h4>
                    <div className="overflow-x-auto max-h-96 overflow-y-auto">
                      <table className="w-full text-sm">
                        <thead className="sticky top-0 bg-black/80">
                          <tr className="text-white/40 border-b border-white/5">
                            <th className="text-left py-2 px-2">MD</th>
                            <th className="text-left py-2 px-2">Inc</th>
                            <th className="text-right py-2 px-2">{t('torqueDrag.axial')}</th>
                            <th className="text-right py-2 px-2">{t('torqueDrag.normal')}</th>
                            <th className="text-right py-2 px-2">{t('torqueDrag.drag')}</th>
                            <th className="text-right py-2 px-2">{t('torqueDrag.torqueCol')}</th>
                            <th className="text-center py-2 px-2">{t('torqueDrag.buckling')}</th>
                          </tr>
                        </thead>
                        <tbody>
                          {tdResult.station_results?.map((sr: any, i: number) => (
                            <tr key={i} className="border-b border-white/5 hover:bg-white/5">
                              <td className="py-1 px-2">{sr.md}</td>
                              <td className="py-1 px-2">{sr.inclination}°</td>
                              <td className="py-1 px-2 text-right font-mono">{sr.axial_force?.toLocaleString()}</td>
                              <td className="py-1 px-2 text-right font-mono">{sr.normal_force?.toLocaleString()}</td>
                              <td className="py-1 px-2 text-right font-mono">{sr.drag?.toLocaleString()}</td>
                              <td className="py-1 px-2 text-right font-mono">{sr.torque?.toLocaleString()}</td>
                              <td className={`py-1 px-2 text-center font-bold text-xs ${sr.buckling_status === 'OK' ? 'text-green-400' : sr.buckling_status === 'SINUSOIDAL' ? 'text-yellow-400' : 'text-red-400'}`}>{sr.buckling_status}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </motion.div>
            )}
          </motion.div>
        )}

        {/* === Real-Time Compare Tab === */}
        {activeTab === 'compare' && (
          <motion.div key="compare" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="space-y-6">
            {/* Multi-Operation Compare */}
            <div className="glass-panel p-6 rounded-2xl border border-white/5">
              <div className="flex items-center gap-2 mb-2">
                <Layers size={18} className="text-industrial-400" />
                <h3 className="font-bold text-lg">{t('torqueDrag.compare.title')}</h3>
              </div>
              <p className="text-white/40 text-sm mb-4">
                {t('torqueDrag.compare.description')}
              </p>
              <button onClick={runCompare} disabled={compareLoading} className="btn-primary flex items-center gap-2 disabled:opacity-50">
                <Play size={16} /> {compareLoading ? t('torqueDrag.compare.computingAll') : t('torqueDrag.compare.run')}
              </button>
            </div>

            {compareResult && (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
                {/* Multi-series chart using compare endpoint data */}
                <TDMultiSeriesChart
                  data={compareResult.combined || []}
                  operations={Object.keys(compareResult.operations || {})}
                  casingShoe={tdParams.casing_shoe_md}
                  height={450}
                />

                {/* Hookload comparison bars for all operations */}
                <HookloadComparisonBar
                  data={(compareResult.summary_comparison || []).map((sc: any) => ({
                    operation: sc.operation,
                    hookload_klb: sc.hookload_klb,
                    label: sc.operation.replace(/_/g, ' ').toUpperCase(),
                  }))}
                  buoyedWeight={computeBuoyedWeight()}
                  height={250}
                />
              </motion.div>
            )}

            {/* Back-Calculate Friction */}
            <div className="glass-panel p-6 rounded-2xl border border-white/5">
              <h3 className="font-bold text-lg mb-4">{t('torqueDrag.backCalc.title')}</h3>
              <p className="text-white/40 text-sm mb-4">{t('torqueDrag.backCalc.description')}</p>

              <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
                <div>
                  <label className="text-xs text-white/40 block mb-1">{t('torqueDrag.backCalc.measuredHL')}</label>
                  <input type="number" value={backCalcParams.measured_hookload} onChange={(e) => setBackCalcParams({ ...backCalcParams, measured_hookload: parseFloat(e.target.value) || 0 })} className="input-field w-full py-2 px-3 text-sm" />
                </div>
                <div>
                  <label className="text-xs text-white/40 block mb-1">{t('torqueDrag.analysis.operation')}</label>
                  <select value={backCalcParams.operation} onChange={(e) => setBackCalcParams({ ...backCalcParams, operation: e.target.value })} className="input-field w-full py-2 px-3 text-sm">
                    {OPERATIONS.map((op) => <option key={op} value={op}>{op.replace('_', ' ').toUpperCase()}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-white/40 block mb-1">{t('torqueDrag.analysis.mudWeight')}</label>
                  <input type="number" step="0.1" value={backCalcParams.mud_weight} onChange={(e) => setBackCalcParams({ ...backCalcParams, mud_weight: parseFloat(e.target.value) || 0 })} className="input-field w-full py-2 px-3 text-sm" />
                </div>
              </div>

              <button onClick={runBackCalc} disabled={loading} className="btn-primary flex items-center gap-2 disabled:opacity-50">
                <RefreshCw size={16} /> {loading ? t('common.calculating') : t('torqueDrag.backCalc.run')}
              </button>
            </div>

            {backCalcResult && (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="glass-panel p-4 rounded-xl border border-white/5 text-center">
                  <p className="text-xs text-white/40 mb-1">{t('torqueDrag.backCalc.frictionFactor')}</p>
                  <p className="text-3xl font-bold text-industrial-400">{backCalcResult.friction_factor}</p>
                </div>
                <div className="glass-panel p-4 rounded-xl border border-white/5 text-center">
                  <p className="text-xs text-white/40 mb-1">{t('torqueDrag.backCalc.calculatedHL')}</p>
                  <p className="text-2xl font-bold text-white">{backCalcResult.calculated_hookload_klb} klb</p>
                </div>
                <div className="glass-panel p-4 rounded-xl border border-white/5 text-center">
                  <p className="text-xs text-white/40 mb-1">{t('torqueDrag.backCalc.error')}</p>
                  <p className="text-2xl font-bold text-white">{backCalcResult.error_klb} klb</p>
                </div>
                <div className="glass-panel p-4 rounded-xl border border-white/5 text-center">
                  <p className="text-xs text-white/40 mb-1">{t('torqueDrag.backCalc.converged')}</p>
                  <p className={`text-2xl font-bold ${backCalcResult.converged ? 'text-green-400' : 'text-red-400'}`}>
                    {backCalcResult.converged ? t('common.yes') : t('common.no')}
                  </p>
                  <p className="text-xs text-white/30">{backCalcResult.iterations} {t('common.iterations')}</p>
                </div>
              </motion.div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* AI Executive Analysis Button & Panel */}
      {(tdResult || compareResult) && (
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
              moduleName={t('modules.torqueDrag')}
              moduleIcon={ArrowUpDown}
              wellName={wellName}
              analysis={aiAnalysis?.analysis || null}
              confidence={aiAnalysis?.confidence || 'MEDIUM'}
              agentRole={aiAnalysis?.agent_role || 'Well Engineer'}
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

export default TorqueDragModule;
