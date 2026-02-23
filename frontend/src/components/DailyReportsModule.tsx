/**
 * DailyReportsModule.tsx — DDR / Operations Reports Module
 * Covers: Daily Drilling Reports, Completion Reports, Termination Reports
 * Features: CRUD, KPI dashboard, AI Analysis, PDF export
 */
import React, { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { useLanguage } from '../hooks/useLanguage';
import { useToast } from './ui/Toast';
import axios from 'axios';
import { API_BASE_URL } from '../config';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ClipboardList, Plus, ChevronDown, ChevronUp,
  Save, Send, CheckCircle, Trash2, Edit3, FileText,
  BarChart3, Activity, AlertTriangle, Clock, DollarSign,
  TrendingDown, Zap, Filter, Download, Database,
  Shield, Navigation, Layers, Gauge, Users, Package, Crosshair, Timer,
  Upload,
} from 'lucide-react';
import AIAnalysisPanel from './AIAnalysisPanel';
import DDRReportPDF from './DDRReportPDF';
// @ts-ignore — html2pdf has no types
import html2pdf from 'html2pdf.js';
import type { Provider } from '../types/ai';
import * as XLSX from 'xlsx';

// Charts
import TimeDepthChart from './charts/ddr/TimeDepthChart';
import CostTrackingChart from './charts/ddr/CostTrackingChart';
import NPTBreakdownChart from './charts/ddr/NPTBreakdownChart';
import DailyOperationsTimeline from './charts/ddr/DailyOperationsTimeline';
import ROPProgressChart from './charts/ddr/ROPProgressChart';

interface ReportListItem {
  id: number;
  report_type: string;
  report_date: string;
  report_number: number;
  depth_md_start: number | null;
  depth_md_end: number | null;
  status: string;
  summary: { footage_drilled: number; avg_rop: number; npt_hours: number; npt_percentage: number };
}

// Default empty operation row
const emptyOperation = () => ({
  from_time: 0, to_time: 0, hours: 0, iadc_code: '', category: '',
  description: '', depth_start: null as number | null, depth_end: null as number | null,
  is_npt: false, npt_code: '',
});

// Default empty BHA component
const emptyBHA = () => ({
  component_type: '', od: 0, length: 0, weight: 0, serial_number: '',
});

const DailyReportsModule: React.FC = () => {
  const { t } = useTranslation();
  const { language } = useLanguage();
  const { addToast } = useToast();

  // ── Internal well management (independent of Event Analysis) ──
  const [wells, setWells] = useState<{id: number; name: string; location?: string}[]>([]);
  const [selectedReportWell, setSelectedReportWell] = useState<{id: number; name: string} | null>(null);
  const [wellsLoading, setWellsLoading] = useState(true);
  const [isCreatingWell, setIsCreatingWell] = useState(false);
  const [newWellName, setNewWellName] = useState('');

  // Derive wellId and wellName from internal state (replaces props)
  const wellId = selectedReportWell?.id;
  const wellName = selectedReportWell?.name || '';

  useEffect(() => {
    const fetchWells = async () => {
      try {
        const res = await axios.get(`${API_BASE_URL}/wells`);
        setWells(res.data);
      } catch (e) {
        console.error('Error fetching wells:', e);
      } finally {
        setWellsLoading(false);
      }
    };
    fetchWells();
  }, []);

  const handleCreateWell = async () => {
    if (!newWellName.trim()) return;
    try {
      const res = await axios.post(`${API_BASE_URL}/wells?name=${encodeURIComponent(newWellName.trim())}`);
      const newWell = res.data;
      setWells(prev => [...prev, newWell]);
      setSelectedReportWell({ id: newWell.id, name: newWell.name });
      setNewWellName('');
      setIsCreatingWell(false);
      addToast(t('ddr.wellCreated'), 'success');
    } catch (e: any) {
      addToast('Error: ' + (e.response?.data?.detail || e.message), 'error');
    }
  };

  const [activeTab, setActiveTab] = useState('reports');
  const [loading, setLoading] = useState(false);

  // Reports list
  const [reports, setReports] = useState<ReportListItem[]>([]);
  const [filterType, setFilterType] = useState<string>('');

  // Form state — New DDR / Edit
  const [editingId, setEditingId] = useState<number | null>(null);
  const [reportType, setReportType] = useState('drilling');
  const [reportDate, setReportDate] = useState(new Date().toISOString().split('T')[0]);
  const [depthStart, setDepthStart] = useState(0);
  const [depthEnd, setDepthEnd] = useState(0);
  const [depthTvd, setDepthTvd] = useState(0);
  const [headerData, setHeaderData] = useState<any>({});
  const [operations, setOperations] = useState([emptyOperation()]);
  const [drillingParams, setDrillingParams] = useState<any>({});
  const [mudProps, setMudProps] = useState<any>({});
  const [mudInventory, setMudInventory] = useState<any>({});
  const [bhaData, setBhaData] = useState([emptyBHA()]);
  const [gasMonitoring, setGasMonitoring] = useState<any>({});
  const [nptEvents, setNptEvents] = useState<any[]>([]);
  const [hsseData, setHsseData] = useState<any>({});
  const [costSummary, setCostSummary] = useState<any>({});
  const [completionData, setCompletionData] = useState<any>({});
  const [terminationData, setTerminationData] = useState<any>({});
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['header', 'operations']));

  // KPI data
  const [timeDepthData, setTimeDepthData] = useState<any[]>([]);
  const [costData, setCostData] = useState<any[]>([]);
  const [nptBreakdown, setNptBreakdown] = useState<any>({});
  const [cumulativeStats, setCumulativeStats] = useState<any>({});

  // AI Analysis
  const [aiAnalysis, setAiAnalysis] = useState<any>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [provider, setProvider] = useState<Provider>('auto');
  const [availableProviders] = useState<any[]>([
    { value: 'auto', label: t('ai.providerAuto') },
    { value: 'google_gemini', label: t('ai.providerGemini') },
    { value: 'ollama', label: t('ai.providerOllama') },
  ]);

  // IADC codes
  const [iadcCodes, setIadcCodes] = useState<Record<string, string>>({});
  const [, setNptCodes] = useState<Record<string, string>>({});
  const [opCategories, setOpCategories] = useState<string[]>([]);

  // PDF
  const pdfRef = useRef<HTMLDivElement>(null);
  // BHA file upload
  const bhaFileRef = useRef<HTMLInputElement>(null);
  const [isGeneratingPDF, setIsGeneratingPDF] = useState(false);

  // ---------------------------------------------------------------
  // Fetch on mount
  // ---------------------------------------------------------------
  useEffect(() => {
    fetchReports();
    fetchReferenceData();
  }, [wellId]);

  useEffect(() => {
    if (activeTab === 'kpis') fetchKPIs();
  }, [activeTab, wellId]);

  const fetchReports = async () => {
    if (!wellId) return;
    try {
      const url = filterType
        ? `${API_BASE_URL}/wells/${wellId}/daily-reports?report_type=${filterType}`
        : `${API_BASE_URL}/wells/${wellId}/daily-reports`;
      const res = await axios.get(url);
      setReports(res.data);
    } catch (e) { console.error('Error fetching reports:', e); }
  };

  const fetchReferenceData = async () => {
    try {
      const [iadc, npt, cats] = await Promise.all([
        axios.get(`${API_BASE_URL}/ddr/iadc-codes`),
        axios.get(`${API_BASE_URL}/ddr/npt-codes`),
        axios.get(`${API_BASE_URL}/ddr/operation-categories`),
      ]);
      setIadcCodes(iadc.data);
      setNptCodes(npt.data);
      setOpCategories(cats.data);
    } catch (e) { console.error('Error fetching ref data:', e); }
  };

  const fetchKPIs = async () => {
    if (!wellId) return;
    try {
      const [td, cost, npt, stats] = await Promise.all([
        axios.get(`${API_BASE_URL}/wells/${wellId}/daily-reports/time-depth`),
        axios.get(`${API_BASE_URL}/wells/${wellId}/daily-reports/cost-tracking`),
        axios.get(`${API_BASE_URL}/wells/${wellId}/daily-reports/npt-breakdown`),
        axios.get(`${API_BASE_URL}/wells/${wellId}/daily-reports/stats`),
      ]);
      setTimeDepthData(td.data);
      setCostData(cost.data.daily_costs || []);
      setNptBreakdown(npt.data);
      setCumulativeStats(stats.data);
    } catch (e) { console.error('Error fetching KPIs:', e); }
  };

  // ---------------------------------------------------------------
  // Form helpers
  // ---------------------------------------------------------------
  const toggleSection = (s: string) => {
    const next = new Set(expandedSections);
    next.has(s) ? next.delete(s) : next.add(s);
    setExpandedSections(next);
  };

  const updateOp = (idx: number, field: string, value: any) => {
    const updated = [...operations];
    updated[idx] = { ...updated[idx], [field]: value };
    // Auto-calc hours
    if (field === 'from_time' || field === 'to_time') {
      const from = field === 'from_time' ? parseFloat(value) || 0 : updated[idx].from_time;
      const to = field === 'to_time' ? parseFloat(value) || 0 : updated[idx].to_time;
      updated[idx].hours = Math.max(0, to - from);
    }
    setOperations(updated);
  };

  const addOp = () => setOperations([...operations, emptyOperation()]);
  const removeOp = (idx: number) => setOperations(operations.filter((_, i) => i !== idx));

  const updateBHA = (idx: number, field: string, value: any) => {
    const updated = [...bhaData];
    updated[idx] = { ...updated[idx], [field]: value };
    setBhaData(updated);
  };
  const addBHA = () => setBhaData([...bhaData, emptyBHA()]);
  const removeBHA = (idx: number) => setBhaData(bhaData.filter((_, i) => i !== idx));

  // ── BHA file upload (CSV / Excel) ──
  const BHA_COL_MAP: Record<string, string> = {
    'component': 'component_type', 'component type': 'component_type', 'component_type': 'component_type',
    'componente': 'component_type', 'tipo': 'component_type', 'tipo componente': 'component_type',
    'type': 'component_type', 'description': 'component_type', 'descripcion': 'component_type',
    'od': 'od', 'od (in)': 'od', 'od(in)': 'od', 'de': 'od', 'de (in)': 'od',
    'outer diameter': 'od', 'diametro externo': 'od',
    'length': 'length', 'length (ft)': 'length', 'length(ft)': 'length',
    'longitud': 'length', 'longitud (ft)': 'length', 'long': 'length', 'largo': 'length',
    'weight': 'weight', 'weight (lb)': 'weight', 'weight(lb)': 'weight',
    'peso': 'weight', 'peso (lb)': 'weight',
    'serial': 'serial_number', 'serial #': 'serial_number', 'serial number': 'serial_number',
    'serial_number': 'serial_number', 'serie': 'serial_number', 'serie #': 'serial_number',
    'numero serie': 'serial_number', 'no. serie': 'serial_number',
  };

  const handleBHAFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (evt) => {
      try {
        const data = new Uint8Array(evt.target?.result as ArrayBuffer);
        const wb = XLSX.read(data, { type: 'array' });
        const sheet = wb.Sheets[wb.SheetNames[0]];
        if (!sheet) { addToast(t('ddr.bhaUploadEmpty'), 'error'); return; }
        const rows: any[] = XLSX.utils.sheet_to_json(sheet, { defval: '' });
        if (rows.length === 0) { addToast(t('ddr.bhaUploadEmpty'), 'error'); return; }

        // Map file columns → BHA fields
        const hdrMap: Record<string, string> = {};
        for (const fh of Object.keys(rows[0])) {
          const mapped = BHA_COL_MAP[fh.trim().toLowerCase()];
          if (mapped) hdrMap[fh] = mapped;
        }
        if (!Object.values(hdrMap).includes('component_type')) {
          addToast(t('ddr.bhaUploadNoColumns'), 'error'); return;
        }

        const parsed = rows
          .map(row => {
            const bha = emptyBHA();
            for (const [fc, bf] of Object.entries(hdrMap)) {
              const v = row[fc];
              if (bf === 'component_type' || bf === 'serial_number') (bha as any)[bf] = String(v || '').trim();
              else (bha as any)[bf] = parseFloat(v) || 0;
            }
            return bha;
          })
          .filter(b => b.component_type.trim() !== '');

        if (parsed.length === 0) { addToast(t('ddr.bhaUploadEmpty'), 'error'); return; }
        setBhaData(parsed);
        addToast(t('ddr.bhaUploadSuccess', { count: parsed.length }), 'success');
      } catch (err) {
        console.error('BHA file parse error:', err);
        addToast(t('ddr.bhaUploadError'), 'error');
      }
    };
    reader.readAsArrayBuffer(file);
    e.target.value = '';
  };

  // ── Survey helpers ──
  const updateSurvey = (idx: number, field: string, value: any) => {
    const surveys = [...(headerData.surveys || [])];
    surveys[idx] = { ...surveys[idx], [field]: value };
    setHeaderData({ ...headerData, surveys });
  };
  const addSurvey = () => setHeaderData({ ...headerData, surveys: [...(headerData.surveys || []), { md: 0, tvd: 0, inc: 0, azi: 0, dls: 0 }] });
  const removeSurvey = (idx: number) => setHeaderData({ ...headerData, surveys: (headerData.surveys || []).filter((_: any, i: number) => i !== idx) });

  // ── Personnel companies helpers ──
  const updateCompany = (idx: number, field: string, value: any) => {
    const companies = [...(hsseData.personnel_companies || [])];
    companies[idx] = { ...companies[idx], [field]: value };
    setHsseData({ ...hsseData, personnel_companies: companies });
  };
  const addCompany = () => setHsseData({ ...hsseData, personnel_companies: [...(hsseData.personnel_companies || []), { company: '', headcount: 0 }] });
  const removeCompany = (idx: number) => setHsseData({ ...hsseData, personnel_companies: (hsseData.personnel_companies || []).filter((_: any, i: number) => i !== idx) });

  // ── Materials helpers ──
  const updateMaterial = (idx: number, field: string, value: any) => {
    const materials = [...(mudInventory.materials || [])];
    materials[idx] = { ...materials[idx], [field]: value };
    setMudInventory({ ...mudInventory, materials });
  };
  const addMaterial = () => setMudInventory({ ...mudInventory, materials: [...(mudInventory.materials || []), { product: '', inventory: 0, used: 0, unit: '' }] });
  const removeMaterial = (idx: number) => setMudInventory({ ...mudInventory, materials: (mudInventory.materials || []).filter((_: any, i: number) => i !== idx) });

  const resetForm = () => {
    setEditingId(null);
    setReportDate(new Date().toISOString().split('T')[0]);
    setDepthStart(0); setDepthEnd(0); setDepthTvd(0);
    setHeaderData({}); setOperations([emptyOperation()]);
    setDrillingParams({}); setMudProps({});
    setMudInventory({}); setBhaData([emptyBHA()]);
    setGasMonitoring({}); setNptEvents([]); setHsseData({});
    setCostSummary({}); setCompletionData({}); setTerminationData({});
  };

  // ---------------------------------------------------------------
  // Save / Update report
  // ---------------------------------------------------------------
  const saveReport = async (status: string = 'draft') => {
    if (!wellId) return;
    setLoading(true);
    const payload: any = {
      report_type: reportType,
      report_date: reportDate,
      depth_md_start: depthStart || null,
      depth_md_end: depthEnd || null,
      depth_tvd: depthTvd || null,
      header_data: headerData,
      operations_log: operations.filter(o => o.description || o.iadc_code),
      drilling_params: drillingParams,
      mud_properties: mudProps,
      mud_inventory: mudInventory,
      bha_data: bhaData.filter(b => b.component_type),
      gas_monitoring: gasMonitoring,
      npt_events: nptEvents,
      hsse_data: hsseData,
      cost_summary: costSummary,
      completion_data: reportType === 'completion' ? completionData : null,
      termination_data: reportType === 'termination' ? terminationData : null,
      status,
    };

    try {
      if (editingId) {
        await axios.put(`${API_BASE_URL}/wells/${wellId}/daily-reports/${editingId}`, payload);
      } else {
        await axios.post(`${API_BASE_URL}/wells/${wellId}/daily-reports`, payload);
      }
      fetchReports();
      if (status !== 'draft') { resetForm(); setActiveTab('reports'); }
    } catch (e: any) {
      addToast('Error: ' + (e.response?.data?.detail || e.message), 'error');
    }
    setLoading(false);
  };

  const deleteReport = async (id: number) => {
    if (!wellId) return;
    if (!confirm(t('ddr.confirmDelete') || 'Delete this report?')) return;
    try {
      await axios.delete(`${API_BASE_URL}/wells/${wellId}/daily-reports/${id}`);
      fetchReports();
    } catch (e) { console.error(e); }
  };

  const loadReport = async (id: number) => {
    if (!wellId) return;
    try {
      const res = await axios.get(`${API_BASE_URL}/wells/${wellId}/daily-reports/${id}`);
      const r = res.data;
      setEditingId(r.id);
      setReportType(r.report_type);
      setReportDate(r.report_date);
      setDepthStart(r.depth_md_start || 0);
      setDepthEnd(r.depth_md_end || 0);
      setDepthTvd(r.depth_tvd || 0);
      setHeaderData(r.header_data || {});
      setOperations(r.operations_log?.length ? r.operations_log : [emptyOperation()]);
      setDrillingParams(r.drilling_params || {});
      setMudProps(r.mud_properties || {});
      setMudInventory(r.mud_inventory || {});
      setBhaData(r.bha_data?.length ? r.bha_data : [emptyBHA()]);
      setGasMonitoring(r.gas_monitoring || {});
      setNptEvents(r.npt_events || []);
      setHsseData(r.hsse_data || {});
      setCostSummary(r.cost_summary || {});
      setCompletionData(r.completion_data || {});
      setTerminationData(r.termination_data || {});
      setActiveTab('newDDR');
    } catch (e) { console.error(e); }
  };

  // ---------------------------------------------------------------
  // PDF Export
  // ---------------------------------------------------------------
  const handleExportPDF = async () => {
    const el = pdfRef.current;
    if (!el) return;
    setIsGeneratingPDF(true);
    try {
      el.style.display = 'block';
      const reportNum = editingId ? reports.find(r => r.id === editingId)?.report_number || 0 : 0;
      const opt = {
        margin: 10,
        filename: `DDR_${wellName || 'Well'}_Report-${reportNum}_${reportDate}.pdf`,
        image: { type: 'jpeg' as const, quality: 0.98 },
        html2canvas: { scale: 2, useCORS: true },
        jsPDF: { unit: 'mm' as const, format: 'a4' as const, orientation: 'portrait' as const },
      };
      await html2pdf().set(opt).from(el).save();
    } catch (err) {
      console.error('PDF generation error:', err);
    } finally {
      if (pdfRef.current) pdfRef.current.style.display = 'none';
      setIsGeneratingPDF(false);
    }
  };

  // ---------------------------------------------------------------
  // AI Analysis
  // ---------------------------------------------------------------
  const runAIAnalysis = async () => {
    if (!wellId || reports.length === 0) return;
    setIsAnalyzing(true);
    try {
      // Use the latest report data
      const latest = reports[0];
      const full = await axios.get(`${API_BASE_URL}/wells/${wellId}/daily-reports/${latest.id}`);
      const res = await axios.post(
        `${API_BASE_URL}/wells/${wellId}/daily-reports/analyze?language=${language}&provider=${provider}`,
        { result_data: full.data, params: { report_type: latest.report_type } }
      );
      setAiAnalysis(res.data);
    } catch (e: any) {
      setAiAnalysis({ analysis: `Error: ${e?.response?.data?.detail || e?.message}`, confidence: 'LOW', agent_role: 'Error', key_metrics: [] });
    }
    setIsAnalyzing(false);
  };

  // ---------------------------------------------------------------
  // Tabs definition
  // ---------------------------------------------------------------
  const tabs = [
    { id: 'reports', label: t('ddr.reports'), icon: ClipboardList },
    { id: 'newDDR', label: editingId ? t('ddr.editReport') || 'Edit Report' : t('ddr.newDDR'), icon: Plus },
    { id: 'kpis', label: t('ddr.kpis'), icon: BarChart3 },
    { id: 'analysis', label: t('ddr.aiAnalysis'), icon: Activity },
  ];

  // ---------------------------------------------------------------
  // Render: Collapsible Section
  // ---------------------------------------------------------------
  const Section = ({ id, title, icon: Icon, children }: { id: string; title: string; icon: any; children: React.ReactNode }) => (
    <div className="border border-white/5 rounded-xl overflow-hidden mb-4">
      <button
        onClick={() => toggleSection(id)}
        className="w-full flex items-center justify-between p-4 bg-white/5 hover:bg-white/8 transition-colors"
      >
        <div className="flex items-center gap-3">
          <Icon size={16} className="text-industrial-400" />
          <span className="font-bold text-sm">{title}</span>
        </div>
        {expandedSections.has(id) ? <ChevronUp size={16} className="text-white/30" /> : <ChevronDown size={16} className="text-white/30" />}
      </button>
      <AnimatePresence>
        {expandedSections.has(id) && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
            <div className="p-4 space-y-4">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );

  // Helper: simple input field
  const Field = ({ label, value, onChange, type = 'number', unit = '' }: any) => (
    <div>
      <label className="text-xs text-white/40 block mb-1">{label}{unit && ` (${unit})`}</label>
      <input type={type} value={value || ''} onChange={e => onChange(type === 'number' ? parseFloat(e.target.value) || 0 : e.target.value)} className="input-field w-full py-2 px-3 text-sm" />
    </div>
  );

  // Helper: textarea field
  const TextArea = ({ label, value, onChange, rows = 3 }: any) => (
    <div>
      <label className="text-xs text-white/40 block mb-1">{label}</label>
      <textarea value={value || ''} onChange={e => onChange(e.target.value)} rows={rows} className="input-field w-full py-2 px-3 text-sm resize-y min-h-[60px]" />
    </div>
  );

  // ---------------------------------------------------------------
  // Status badge
  // ---------------------------------------------------------------
  const StatusBadge = ({ status }: { status: string }) => {
    const colors: Record<string, string> = {
      draft: 'bg-yellow-500/20 text-yellow-400',
      submitted: 'bg-blue-500/20 text-blue-400',
      approved: 'bg-green-500/20 text-green-400',
    };
    return <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase ${colors[status] || colors.draft}`}>{t(`ddr.${status}`) || status}</span>;
  };

  // ---------------------------------------------------------------
  // RENDER
  // ---------------------------------------------------------------
  return (
    <div className="space-y-6">
      {/* ── Well Selector Bar ── */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-blue-500/10 rounded-xl border border-blue-500/20">
            <ClipboardList size={22} className="text-blue-400" />
          </div>
          <div>
            <h2 className="text-xl font-bold">{t('modules.dailyReports')}</h2>
            <p className="text-white/30 text-xs">{t('ddr.operationalReports')}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={selectedReportWell?.id ?? ''}
            onChange={(e) => {
              const id = parseInt(e.target.value);
              const well = wells.find(w => w.id === id);
              setSelectedReportWell(well ? { id: well.id, name: well.name } : null);
            }}
            className="bg-white/5 border border-white/10 rounded-xl px-4 py-2 text-sm text-white/70 focus:outline-none focus:border-blue-500 min-w-[220px]"
            disabled={wellsLoading}
          >
            <option value="">{wellsLoading ? t('common.loading') : t('ddr.selectAWell')}</option>
            {wells.map(w => (
              <option key={w.id} value={w.id}>{w.name}</option>
            ))}
          </select>
          <button
            onClick={() => setIsCreatingWell(!isCreatingWell)}
            className="flex items-center gap-1.5 px-3 py-2 bg-blue-600/20 hover:bg-blue-600/30 border border-blue-500/30 rounded-xl text-xs font-bold text-blue-400 transition-all"
          >
            <Plus size={14} /> {t('ddr.newWell')}
          </button>
        </div>
      </div>

      {/* Inline create-well form */}
      {isCreatingWell && (
        <div className="bg-white/5 p-4 rounded-xl border border-blue-500/20 flex items-center gap-3">
          <input
            type="text"
            value={newWellName}
            onChange={(e) => setNewWellName(e.target.value)}
            placeholder="e.g. WELL-X106-OFFSHORE"
            className="bg-white/5 border border-white/10 rounded-lg flex-1 py-2 px-3 text-sm text-white focus:outline-none focus:border-blue-500"
            autoFocus
            onKeyDown={(e) => e.key === 'Enter' && handleCreateWell()}
          />
          <button onClick={handleCreateWell} className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-xs font-bold text-white transition-colors">
            {t('well.createProject')}
          </button>
          <button onClick={() => { setIsCreatingWell(false); setNewWellName(''); }} className="px-3 py-2 bg-white/5 hover:bg-white/10 rounded-lg text-xs text-white/40">
            {t('common.cancel')}
          </button>
        </div>
      )}

      {!selectedReportWell ? (
        <div className="bg-white/5 p-16 text-center rounded-xl border border-white/5">
          <ClipboardList size={56} className="mx-auto text-white/10 mb-5" />
          <h3 className="text-lg font-bold text-white/60 mb-2">{t('ddr.selectWellPrompt')}</h3>
          <p className="text-white/30 text-sm max-w-md mx-auto">{t('ddr.selectWellDescription')}</p>
        </div>
      ) : (
        <>
          {/* Active well indicator */}
          <div className="flex items-center gap-2 text-xs text-white/40">
            <Database size={14} />
            <span>{t('ddr.activeWell')} <span className="text-white/70 font-bold">{wellName}</span></span>
          </div>

      {/* Tabs */}
      <div className="flex gap-2 flex-wrap">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => { if (tab.id === 'newDDR' && !editingId) resetForm(); setActiveTab(tab.id); }}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-bold transition-all ${activeTab === tab.id ? 'bg-blue-600 text-white shadow-lg' : 'bg-white/5 text-white/40 hover:bg-white/10 hover:text-white/60'}`}
          >
            <tab.icon size={16} />
            {tab.label}
          </button>
        ))}
      </div>

      {/* ============================================================ */}
      {/* TAB: Reports List */}
      {/* ============================================================ */}
      {activeTab === 'reports' && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
          {/* Filters */}
          <div className="flex gap-3 items-center">
            <Filter size={14} className="text-white/30" />
            {['', 'mobilization', 'drilling', 'completion', 'termination'].map(ft => (
              <button
                key={ft}
                onClick={() => { setFilterType(ft); setTimeout(fetchReports, 50); }}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${filterType === ft ? 'bg-blue-600 text-white' : 'bg-white/5 text-white/40 hover:bg-white/10'}`}
              >
                {ft ? t(`ddr.${ft}`) || ft.charAt(0).toUpperCase() + ft.slice(1) : t('ddr.allTypes') || 'All'}
              </button>
            ))}
          </div>

          {reports.length === 0 ? (
            <div className="glass-panel p-12 text-center">
              <ClipboardList size={48} className="mx-auto text-white/10 mb-4" />
              <p className="text-white/30 text-sm">{t('ddr.noReportsYet') || 'No reports yet. Create a new DDR to get started.'}</p>
            </div>
          ) : (
            <div className="space-y-3">
              {reports.map(r => (
                <div key={r.id} className="glass-panel p-5 rounded-xl border border-white/5 flex items-center justify-between hover:border-blue-500/30 transition-colors group">
                  <div className="flex items-center gap-4 flex-1 min-w-0">
                    <div className="w-10 h-10 bg-blue-500/10 border border-blue-500/20 rounded-lg flex items-center justify-center flex-shrink-0">
                      <FileText size={18} className="text-blue-400" />
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-sm">#{r.report_number}</span>
                        <StatusBadge status={r.status} />
                        <span className="text-[10px] text-white/20 uppercase font-bold">{r.report_type}</span>
                      </div>
                      <p className="text-xs text-white/40 mt-0.5">{r.report_date} — {r.summary.footage_drilled} ft drilled, ROP {r.summary.avg_rop} ft/hr, NPT {r.summary.npt_hours}h ({r.summary.npt_percentage}%)</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <button onClick={() => loadReport(r.id)} className="p-2 rounded-lg hover:bg-white/5 text-white/30 hover:text-white transition-colors" title={t('common.edit')}>
                      <Edit3 size={16} />
                    </button>
                    <button onClick={() => deleteReport(r.id)} className="p-2 rounded-lg hover:bg-red-500/10 text-white/20 hover:text-red-400 transition-colors" title={t('common.delete')}>
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </motion.div>
      )}

      {/* ============================================================ */}
      {/* TAB: New DDR / Edit Form */}
      {/* ============================================================ */}
      {activeTab === 'newDDR' && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
          {/* Report Type + Date */}
          <div className="glass-panel p-5 rounded-xl border border-white/5">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <label className="text-xs text-white/40 block mb-1">{t('ddr.reportType') || 'Report Type'}</label>
                <select value={reportType} onChange={e => setReportType(e.target.value)} className="input-field w-full py-2 px-3 text-sm">
                  <option value="mobilization">{t('ddr.mobilization')}</option>
                  <option value="drilling">{t('ddr.drilling') || 'Drilling'}</option>
                  <option value="completion">{t('ddr.completion')}</option>
                  <option value="termination">{t('ddr.termination')}</option>
                </select>
              </div>
              <Field label={t('ddr.reportDate')} value={reportDate} onChange={setReportDate} type="date" />
              <Field label={t('ddr.depthStart')} value={depthStart} onChange={setDepthStart} unit="ft" />
              <Field label={t('ddr.depthEnd')} value={depthEnd} onChange={setDepthEnd} unit="ft" />
            </div>
          </div>

          {/* Header — Expanded (#1) */}
          <Section id="header" title={t('ddr.headerSection')} icon={FileText}>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Field label={t('ddr.operator')} value={headerData.operator} onChange={(v: string) => setHeaderData({ ...headerData, operator: v })} type="text" />
              <Field label={t('ddr.contractor')} value={headerData.contractor} onChange={(v: string) => setHeaderData({ ...headerData, contractor: v })} type="text" />
              <Field label={t('ddr.rigName')} value={headerData.rig} onChange={(v: string) => setHeaderData({ ...headerData, rig: v })} type="text" />
              <Field label={t('ddr.fieldName')} value={headerData.field} onChange={(v: string) => setHeaderData({ ...headerData, field: v })} type="text" />
              <Field label={t('ddr.apiNumber')} value={headerData.api_number} onChange={(v: string) => setHeaderData({ ...headerData, api_number: v })} type="text" />
              <Field label={t('ddr.contractNumber')} value={headerData.contract_number} onChange={(v: string) => setHeaderData({ ...headerData, contract_number: v })} type="text" />
              <Field label="AFE #" value={headerData.afe_number} onChange={(v: string) => setHeaderData({ ...headerData, afe_number: v })} type="text" />
              <Field label="AFE Budget" value={headerData.afe_budget} onChange={(v: number) => setHeaderData({ ...headerData, afe_budget: v })} unit="USD" />
              <Field label={t('ddr.spudDate')} value={headerData.spud_date} onChange={(v: string) => setHeaderData({ ...headerData, spud_date: v })} type="date" />
              <Field label={t('ddr.plannedDepth')} value={headerData.planned_depth} onChange={(v: number) => setHeaderData({ ...headerData, planned_depth: v })} unit="ft" />
              <Field label={t('ddr.plannedDays')} value={headerData.planned_days} onChange={(v: number) => setHeaderData({ ...headerData, planned_days: v })} />
              <Field label="TVD" value={depthTvd} onChange={setDepthTvd} unit="ft" />
              <Field label={t('ddr.wellPhase')} value={headerData.phase} onChange={(v: string) => setHeaderData({ ...headerData, phase: v })} type="text" />
              <Field label={t('ddr.wellActivity')} value={headerData.activity} onChange={(v: string) => setHeaderData({ ...headerData, activity: v })} type="text" />
            </div>
          </Section>

          {/* HSEQ / Safety (#2) */}
          <Section id="hseq" title={t('ddr.hsseStructured')} icon={Shield}>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <Field label={t('ddr.dslti')} value={hsseData.dslti} onChange={(v: number) => setHsseData({ ...hsseData, dslti: v })} />
              <Field label={t('ddr.dslta')} value={hsseData.dslta} onChange={(v: number) => setHsseData({ ...hsseData, dslta: v })} />
              <Field label={t('ddr.daysNoSpills')} value={hsseData.days_no_spills} onChange={(v: number) => setHsseData({ ...hsseData, days_no_spills: v })} />
              <Field label={t('ddr.daysNoIncidents')} value={hsseData.days_no_incidents} onChange={(v: number) => setHsseData({ ...hsseData, days_no_incidents: v })} />
              <Field label={t('ddr.safetyCards')} value={hsseData.safety_cards} onChange={(v: number) => setHsseData({ ...hsseData, safety_cards: v })} />
            </div>
            <div className="grid grid-cols-2 gap-4 mt-4">
              <Field label={t('ddr.supervisorDrilling')} value={hsseData.supervisor_drilling} onChange={(v: string) => setHsseData({ ...hsseData, supervisor_drilling: v })} type="text" />
              <Field label={t('ddr.supervisorCompany')} value={hsseData.supervisor_company} onChange={(v: string) => setHsseData({ ...hsseData, supervisor_company: v })} type="text" />
            </div>
          </Section>

          {/* Operations Log */}
          <Section id="operations" title={`${t('ddr.operationsLog')} (${operations.length})`} icon={Clock}>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-white/40 border-b border-white/5 text-xs">
                    <th className="text-left py-2 px-1 w-16">From</th>
                    <th className="text-left py-2 px-1 w-16">To</th>
                    <th className="text-left py-2 px-1 w-14">Hrs</th>
                    <th className="text-left py-2 px-1 w-20">IADC</th>
                    <th className="text-left py-2 px-1 w-28">Category</th>
                    <th className="text-left py-2 px-1">Description</th>
                    <th className="text-left py-2 px-1 w-14">NPT</th>
                    <th className="w-8"></th>
                  </tr>
                </thead>
                <tbody>
                  {operations.map((op, i) => (
                    <tr key={i} className="border-b border-white/5">
                      <td className="py-1 px-1">
                        <input type="number" step="0.5" min="0" max="24" value={op.from_time || ''} onChange={e => updateOp(i, 'from_time', e.target.value)} className="input-field w-14 py-1 px-1.5 text-xs" />
                      </td>
                      <td className="py-1 px-1">
                        <input type="number" step="0.5" min="0" max="24" value={op.to_time || ''} onChange={e => updateOp(i, 'to_time', e.target.value)} className="input-field w-14 py-1 px-1.5 text-xs" />
                      </td>
                      <td className="py-1 px-1 text-white/30 text-xs">{op.hours?.toFixed(1)}</td>
                      <td className="py-1 px-1">
                        <select value={op.iadc_code} onChange={e => updateOp(i, 'iadc_code', e.target.value)} className="input-field w-18 py-1 px-1 text-xs">
                          <option value="">—</option>
                          {Object.entries(iadcCodes).map(([code]) => (
                            <option key={code} value={code}>{code}</option>
                          ))}
                        </select>
                      </td>
                      <td className="py-1 px-1">
                        <select value={op.category} onChange={e => updateOp(i, 'category', e.target.value)} className="input-field w-full py-1 px-1 text-xs">
                          <option value="">—</option>
                          {opCategories.map(c => <option key={c} value={c}>{c}</option>)}
                        </select>
                      </td>
                      <td className="py-1 px-1">
                        <input type="text" value={op.description} onChange={e => updateOp(i, 'description', e.target.value)} className="input-field w-full py-1 px-1.5 text-xs" placeholder={t('ddr.operationDescription')} />
                      </td>
                      <td className="py-1 px-1 text-center">
                        <input type="checkbox" checked={op.is_npt} onChange={e => updateOp(i, 'is_npt', e.target.checked)} className="accent-red-500" />
                      </td>
                      <td className="py-1 px-1">
                        <button onClick={() => removeOp(i)} className="text-white/20 hover:text-red-400"><Trash2 size={12} /></button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <button onClick={addOp} className="mt-3 px-3 py-1.5 bg-white/5 hover:bg-white/10 rounded-lg text-xs font-bold text-white/40 hover:text-white/60 transition-colors flex items-center gap-1.5">
              <Plus size={12} /> {t('ddr.addOperation') || 'Add Operation'}
            </button>
            <div className="mt-2 text-[10px] text-white/20">
              Total: {operations.reduce((s, o) => s + (o.hours || 0), 0).toFixed(1)} / 24.0 hrs
            </div>
          </Section>

          {/* Summary / Program (#10) — EASIEST */}
          <Section id="summary" title={t('ddr.summaryProgramSection')} icon={FileText}>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <TextArea label={t('ddr.prevDaySummary')} value={headerData.prev_day_summary} onChange={(v: string) => setHeaderData({ ...headerData, prev_day_summary: v })} rows={3} />
              <TextArea label={t('ddr.daySummary')} value={headerData.day_summary} onChange={(v: string) => setHeaderData({ ...headerData, day_summary: v })} rows={3} />
              <TextArea label={t('ddr.plannedProgram')} value={headerData.planned_program} onChange={(v: string) => setHeaderData({ ...headerData, planned_program: v })} rows={3} />
              <TextArea label={t('ddr.urgentItems')} value={headerData.urgent_items} onChange={(v: string) => setHeaderData({ ...headerData, urgent_items: v })} rows={3} />
            </div>
          </Section>

          {/* Time Classification (#6) */}
          <Section id="timeclass" title={t('ddr.timeClassification')} icon={Timer}>
            <div className="grid grid-cols-3 md:grid-cols-6 gap-4">
              <div className="col-span-3 md:col-span-6 flex gap-2 items-center">
                <span className="text-xs text-white/40 font-bold">{t('ddr.dailyHrs')}</span>
              </div>
              <Field label={t('ddr.productiveTime')} value={headerData.time_productive} onChange={(v: number) => setHeaderData({ ...headerData, time_productive: v })} unit="hrs" />
              <Field label={t('ddr.unproductiveTime')} value={headerData.time_unproductive} onChange={(v: number) => setHeaderData({ ...headerData, time_unproductive: v })} unit="hrs" />
              <Field label={t('ddr.downtimeHours')} value={headerData.time_downtime} onChange={(v: number) => setHeaderData({ ...headerData, time_downtime: v })} unit="hrs" />
              <Field label={`${t('ddr.productiveTime')} ${t('ddr.cumulativeHrs')}`} value={headerData.cum_productive} onChange={(v: number) => setHeaderData({ ...headerData, cum_productive: v })} unit="hrs" />
              <Field label={`${t('ddr.unproductiveTime')} ${t('ddr.cumulativeHrs')}`} value={headerData.cum_unproductive} onChange={(v: number) => setHeaderData({ ...headerData, cum_unproductive: v })} unit="hrs" />
              <Field label={`${t('ddr.downtimeHours')} ${t('ddr.cumulativeHrs')}`} value={headerData.cum_downtime} onChange={(v: number) => setHeaderData({ ...headerData, cum_downtime: v })} unit="hrs" />
            </div>
          </Section>

          {/* Drilling-specific sections (hidden for mobilization reports) */}
          {reportType !== 'mobilization' && (
            <>
              {/* Drilling Parameters */}
              <Section id="drilling" title={t('ddr.drillingParams')} icon={Activity}>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <Field label="WOB" value={drillingParams.wob} onChange={(v: number) => setDrillingParams({ ...drillingParams, wob: v })} unit="klb" />
                  <Field label="RPM" value={drillingParams.rpm} onChange={(v: number) => setDrillingParams({ ...drillingParams, rpm: v })} />
                  <Field label="SPM" value={drillingParams.spm} onChange={(v: number) => setDrillingParams({ ...drillingParams, spm: v })} />
                  <Field label={t('ddr.flowRate')} value={drillingParams.flow_rate} onChange={(v: number) => setDrillingParams({ ...drillingParams, flow_rate: v })} unit="gpm" />
                  <Field label="SPP" value={drillingParams.spp} onChange={(v: number) => setDrillingParams({ ...drillingParams, spp: v })} unit="psi" />
                  <Field label={t('ddr.torque')} value={drillingParams.torque} onChange={(v: number) => setDrillingParams({ ...drillingParams, torque: v })} unit="ft-lb" />
                  <Field label="ROP" value={drillingParams.rop} onChange={(v: number) => setDrillingParams({ ...drillingParams, rop: v })} unit="ft/hr" />
                  <Field label="ECD" value={drillingParams.ecd} onChange={(v: number) => setDrillingParams({ ...drillingParams, ecd: v })} unit="ppg" />
                  <Field label={t('ddr.hookLoad')} value={drillingParams.hook_load} onChange={(v: number) => setDrillingParams({ ...drillingParams, hook_load: v })} unit="klb" />
                  <Field label="ESD" value={drillingParams.esd} onChange={(v: number) => setDrillingParams({ ...drillingParams, esd: v })} unit="ppg" />
                </div>
              </Section>

              {/* Mud Properties */}
              <Section id="mud" title={t('ddr.mudProperties')} icon={TrendingDown}>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <Field label={t('ddr.mudWeight')} value={mudProps.density} onChange={(v: number) => setMudProps({ ...mudProps, density: v })} unit="ppg" />
                  <Field label="PV" value={mudProps.pv} onChange={(v: number) => setMudProps({ ...mudProps, pv: v })} unit="cP" />
                  <Field label="YP" value={mudProps.yp} onChange={(v: number) => setMudProps({ ...mudProps, yp: v })} unit="lb/100ft²" />
                  <Field label={t('ddr.gels10s')} value={mudProps.gels_10s} onChange={(v: number) => setMudProps({ ...mudProps, gels_10s: v })} unit="lb/100ft²" />
                  <Field label={t('ddr.gels10m')} value={mudProps.gels_10m} onChange={(v: number) => setMudProps({ ...mudProps, gels_10m: v })} unit="lb/100ft²" />
                  <Field label={t('ddr.filtrate')} value={mudProps.filtrate} onChange={(v: number) => setMudProps({ ...mudProps, filtrate: v })} unit="ml/30min" />
                  <Field label="pH" value={mudProps.ph} onChange={(v: number) => setMudProps({ ...mudProps, ph: v })} />
                  <Field label={t('ddr.chlorides')} value={mudProps.chlorides} onChange={(v: number) => setMudProps({ ...mudProps, chlorides: v })} unit="mg/L" />
                  <Field label="MBT" value={mudProps.mbt} onChange={(v: number) => setMudProps({ ...mudProps, mbt: v })} unit="lb/bbl" />
                  <Field label={t('ddr.solidsPct')} value={mudProps.solids_pct} onChange={(v: number) => setMudProps({ ...mudProps, solids_pct: v })} unit="%" />
                </div>
              </Section>

              {/* BHA */}
              <Section id="bha" title={`${t('ddr.bhaSection')} (${bhaData.length})`} icon={Zap}>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-white/40 border-b border-white/5 text-xs">
                        <th className="text-left py-2 px-1">Component</th>
                        <th className="text-left py-2 px-1">OD (in)</th>
                        <th className="text-left py-2 px-1">Length (ft)</th>
                        <th className="text-left py-2 px-1">Weight (lb)</th>
                        <th className="text-left py-2 px-1">Serial #</th>
                        <th className="w-8"></th>
                      </tr>
                    </thead>
                    <tbody>
                      {bhaData.map((b, i) => (
                        <tr key={i} className="border-b border-white/5">
                          <td className="py-1 px-1"><input type="text" value={b.component_type} onChange={e => updateBHA(i, 'component_type', e.target.value)} className="input-field w-full py-1 px-1.5 text-xs" placeholder="e.g. PDC Bit" /></td>
                          <td className="py-1 px-1"><input type="number" value={b.od || ''} onChange={e => updateBHA(i, 'od', parseFloat(e.target.value) || 0)} className="input-field w-16 py-1 px-1.5 text-xs" /></td>
                          <td className="py-1 px-1"><input type="number" value={b.length || ''} onChange={e => updateBHA(i, 'length', parseFloat(e.target.value) || 0)} className="input-field w-16 py-1 px-1.5 text-xs" /></td>
                          <td className="py-1 px-1"><input type="number" value={b.weight || ''} onChange={e => updateBHA(i, 'weight', parseFloat(e.target.value) || 0)} className="input-field w-16 py-1 px-1.5 text-xs" /></td>
                          <td className="py-1 px-1"><input type="text" value={b.serial_number} onChange={e => updateBHA(i, 'serial_number', e.target.value)} className="input-field w-full py-1 px-1.5 text-xs" /></td>
                          <td className="py-1 px-1"><button onClick={() => removeBHA(i)} className="text-white/20 hover:text-red-400"><Trash2 size={12} /></button></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="mt-3 flex items-center gap-2">
                  <button onClick={addBHA} className="px-3 py-1.5 bg-white/5 hover:bg-white/10 rounded-lg text-xs font-bold text-white/40 hover:text-white/60 transition-colors flex items-center gap-1.5">
                    <Plus size={12} /> {t('ddr.addBHAComponent')}
                  </button>
                  <button onClick={() => bhaFileRef.current?.click()} className="px-3 py-1.5 bg-white/5 hover:bg-white/10 rounded-lg text-xs font-bold text-white/40 hover:text-white/60 transition-colors flex items-center gap-1.5">
                    <Upload size={12} /> {t('ddr.uploadBHA')}
                  </button>
                  <input ref={bhaFileRef} type="file" accept=".csv,.xlsx,.xls" className="hidden" onChange={handleBHAFileUpload} />
                </div>
              </Section>

              {/* Gas Monitoring */}
              <Section id="gas" title={t('ddr.gasMonitoring')} icon={AlertTriangle}>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <Field label={t('ddr.backgroundGas')} value={gasMonitoring.background_gas} onChange={(v: number) => setGasMonitoring({ ...gasMonitoring, background_gas: v })} unit="%" />
                  <Field label={t('ddr.connectionGas')} value={gasMonitoring.connection_gas} onChange={(v: number) => setGasMonitoring({ ...gasMonitoring, connection_gas: v })} unit="%" />
                  <Field label={t('ddr.tripGas')} value={gasMonitoring.trip_gas} onChange={(v: number) => setGasMonitoring({ ...gasMonitoring, trip_gas: v })} unit="%" />
                  <Field label="C1 (Methane)" value={gasMonitoring.c1} onChange={(v: number) => setGasMonitoring({ ...gasMonitoring, c1: v })} unit="ppm" />
                  <Field label="C2 (Ethane)" value={gasMonitoring.c2} onChange={(v: number) => setGasMonitoring({ ...gasMonitoring, c2: v })} unit="ppm" />
                  <Field label="H2S" value={gasMonitoring.h2s} onChange={(v: number) => setGasMonitoring({ ...gasMonitoring, h2s: v })} unit="ppm" />
                  <Field label="CO2" value={gasMonitoring.co2} onChange={(v: number) => setGasMonitoring({ ...gasMonitoring, co2: v })} unit="%" />
                </div>
              </Section>

              {/* Bit Data (#3) */}
              <Section id="bitdata" title={t('ddr.bitDataSection')} icon={Crosshair}>
                <p className="text-[10px] text-white/30 font-bold uppercase mb-3">{t('ddr.currentBit')}</p>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <Field label={t('ddr.bitBrand')} value={drillingParams.bit_brand} onChange={(v: string) => setDrillingParams({ ...drillingParams, bit_brand: v })} type="text" />
                  <Field label={t('ddr.bitSerial')} value={drillingParams.bit_serial} onChange={(v: string) => setDrillingParams({ ...drillingParams, bit_serial: v })} type="text" />
                  <Field label={t('ddr.bitType')} value={drillingParams.bit_type} onChange={(v: string) => setDrillingParams({ ...drillingParams, bit_type: v })} type="text" />
                  <Field label={t('ddr.bitSize')} value={drillingParams.bit_size} onChange={(v: number) => setDrillingParams({ ...drillingParams, bit_size: v })} unit="in" />
                  <Field label={t('ddr.bitNozzles')} value={drillingParams.bit_nozzles} onChange={(v: string) => setDrillingParams({ ...drillingParams, bit_nozzles: v })} type="text" />
                  <Field label={t('ddr.bitDullIn')} value={drillingParams.bit_dull_in} onChange={(v: string) => setDrillingParams({ ...drillingParams, bit_dull_in: v })} type="text" />
                  <Field label={t('ddr.bitDullOut')} value={drillingParams.bit_dull_out} onChange={(v: string) => setDrillingParams({ ...drillingParams, bit_dull_out: v })} type="text" />
                  <Field label={t('ddr.bitFootage')} value={drillingParams.bit_footage} onChange={(v: number) => setDrillingParams({ ...drillingParams, bit_footage: v })} unit="ft" />
                </div>
                <p className="text-[10px] text-white/30 font-bold uppercase mb-3 mt-5">{t('ddr.previousBit')}</p>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <Field label={t('ddr.bitBrand')} value={drillingParams.prev_bit_brand} onChange={(v: string) => setDrillingParams({ ...drillingParams, prev_bit_brand: v })} type="text" />
                  <Field label={t('ddr.bitSerial')} value={drillingParams.prev_bit_serial} onChange={(v: string) => setDrillingParams({ ...drillingParams, prev_bit_serial: v })} type="text" />
                  <Field label={t('ddr.bitType')} value={drillingParams.prev_bit_type} onChange={(v: string) => setDrillingParams({ ...drillingParams, prev_bit_type: v })} type="text" />
                  <Field label={t('ddr.bitSize')} value={drillingParams.prev_bit_size} onChange={(v: number) => setDrillingParams({ ...drillingParams, prev_bit_size: v })} unit="in" />
                  <Field label={t('ddr.bitDullIn')} value={drillingParams.prev_bit_dull_in} onChange={(v: string) => setDrillingParams({ ...drillingParams, prev_bit_dull_in: v })} type="text" />
                  <Field label={t('ddr.bitDullOut')} value={drillingParams.prev_bit_dull_out} onChange={(v: string) => setDrillingParams({ ...drillingParams, prev_bit_dull_out: v })} type="text" />
                  <Field label={t('ddr.bitFootage')} value={drillingParams.prev_bit_footage} onChange={(v: number) => setDrillingParams({ ...drillingParams, prev_bit_footage: v })} unit="ft" />
                </div>
              </Section>

              {/* Survey / Deviation (#4) */}
              <Section id="survey" title={`${t('ddr.surveySection')} (${(headerData.surveys || []).length})`} icon={Navigation}>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-white/40 border-b border-white/5 text-xs">
                        <th className="text-left py-2 px-1 w-20">{t('ddr.surveyMD')}</th>
                        <th className="text-left py-2 px-1 w-20">{t('ddr.surveyTVD')}</th>
                        <th className="text-left py-2 px-1 w-16">{t('ddr.surveyInc')}</th>
                        <th className="text-left py-2 px-1 w-16">{t('ddr.surveyAzi')}</th>
                        <th className="text-left py-2 px-1 w-20">{t('ddr.surveyDLS')}</th>
                        <th className="w-8"></th>
                      </tr>
                    </thead>
                    <tbody>
                      {(headerData.surveys || []).map((s: any, i: number) => (
                        <tr key={i} className="border-b border-white/5">
                          <td className="py-1 px-1"><input type="number" value={s.md || ''} onChange={e => updateSurvey(i, 'md', parseFloat(e.target.value) || 0)} className="input-field w-18 py-1 px-1.5 text-xs" /></td>
                          <td className="py-1 px-1"><input type="number" value={s.tvd || ''} onChange={e => updateSurvey(i, 'tvd', parseFloat(e.target.value) || 0)} className="input-field w-18 py-1 px-1.5 text-xs" /></td>
                          <td className="py-1 px-1"><input type="number" step="0.1" value={s.inc || ''} onChange={e => updateSurvey(i, 'inc', parseFloat(e.target.value) || 0)} className="input-field w-16 py-1 px-1.5 text-xs" /></td>
                          <td className="py-1 px-1"><input type="number" step="0.1" value={s.azi || ''} onChange={e => updateSurvey(i, 'azi', parseFloat(e.target.value) || 0)} className="input-field w-16 py-1 px-1.5 text-xs" /></td>
                          <td className="py-1 px-1"><input type="number" step="0.01" value={s.dls || ''} onChange={e => updateSurvey(i, 'dls', parseFloat(e.target.value) || 0)} className="input-field w-18 py-1 px-1.5 text-xs" /></td>
                          <td className="py-1 px-1"><button onClick={() => removeSurvey(i)} className="text-white/20 hover:text-red-400"><Trash2 size={12} /></button></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <button onClick={addSurvey} className="mt-3 px-3 py-1.5 bg-white/5 hover:bg-white/10 rounded-lg text-xs font-bold text-white/40 hover:text-white/60 transition-colors flex items-center gap-1.5">
                  <Plus size={12} /> {t('ddr.addSurveyStation')}
                </button>
              </Section>

              {/* Casing Record (#5) */}
              <Section id="casing" title={t('ddr.casingRecord')} icon={Layers}>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <Field label={t('ddr.lastCasing')} value={headerData.last_casing} onChange={(v: string) => setHeaderData({ ...headerData, last_casing: v })} type="text" />
                  <Field label={t('ddr.lastCasingDepth')} value={headerData.last_casing_depth} onChange={(v: number) => setHeaderData({ ...headerData, last_casing_depth: v })} unit="ft" />
                  <Field label={t('ddr.nextCasing')} value={headerData.next_casing} onChange={(v: string) => setHeaderData({ ...headerData, next_casing: v })} type="text" />
                  <Field label={t('ddr.nextCasingDepth')} value={headerData.next_casing_depth} onChange={(v: number) => setHeaderData({ ...headerData, next_casing_depth: v })} unit="ft" />
                </div>
              </Section>

              {/* Surface Equipment Tests (#7) */}
              <Section id="surfacetests" title={t('ddr.surfaceEquipTests')} icon={Gauge}>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <Field label={t('ddr.bopTestDate')} value={headerData.bop_test_date} onChange={(v: string) => setHeaderData({ ...headerData, bop_test_date: v })} type="date" />
                  <Field label={t('ddr.bopTestPressure')} value={headerData.bop_test_pressure} onChange={(v: number) => setHeaderData({ ...headerData, bop_test_pressure: v })} unit="psi" />
                  <Field label={t('ddr.koomeyTime')} value={headerData.koomey_time} onChange={(v: number) => setHeaderData({ ...headerData, koomey_time: v })} unit="sec" />
                  <Field label={t('ddr.tonMiles')} value={headerData.ton_miles} onChange={(v: number) => setHeaderData({ ...headerData, ton_miles: v })} />
                  <Field label={t('ddr.standpipePressureSurf')} value={headerData.standpipe_pressure} onChange={(v: number) => setHeaderData({ ...headerData, standpipe_pressure: v })} unit="psi" />
                  <Field label={t('ddr.casingPressureSurf')} value={headerData.casing_pressure} onChange={(v: number) => setHeaderData({ ...headerData, casing_pressure: v })} unit="psi" />
                </div>
              </Section>

              {/* Pump Data (#8) */}
              <Section id="pumpdata" title={t('ddr.pumpDataSection')} icon={Gauge}>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <Field label={t('ddr.pump1Liner')} value={drillingParams.pump1_liner} onChange={(v: number) => setDrillingParams({ ...drillingParams, pump1_liner: v })} unit="in" />
                  <Field label={t('ddr.pump2Liner')} value={drillingParams.pump2_liner} onChange={(v: number) => setDrillingParams({ ...drillingParams, pump2_liner: v })} unit="in" />
                  <Field label={t('ddr.pump3Liner')} value={drillingParams.pump3_liner} onChange={(v: number) => setDrillingParams({ ...drillingParams, pump3_liner: v })} unit="in" />
                  <Field label={t('ddr.annularVelocity')} value={drillingParams.annular_velocity} onChange={(v: number) => setDrillingParams({ ...drillingParams, annular_velocity: v })} unit="ft/min" />
                  <Field label={t('ddr.stringWeightUp')} value={drillingParams.string_weight_up} onChange={(v: number) => setDrillingParams({ ...drillingParams, string_weight_up: v })} unit="klb" />
                  <Field label={t('ddr.stringWeightDown')} value={drillingParams.string_weight_down} onChange={(v: number) => setDrillingParams({ ...drillingParams, string_weight_down: v })} unit="klb" />
                </div>
              </Section>
            </>
          )}

          {/* Extended Mud Properties (#9) — shown for non-mobilization only */}
          {reportType !== 'mobilization' && (
            <Section id="mudext" title={`${t('ddr.mudProperties')} — ${t('ddr.mudType') || 'Extended'}`} icon={TrendingDown}>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                <Field label={t('ddr.mudType')} value={mudProps.mud_type} onChange={(v: string) => setMudProps({ ...mudProps, mud_type: v })} type="text" />
                <Field label={t('ddr.marshFunnel')} value={mudProps.marsh_funnel} onChange={(v: number) => setMudProps({ ...mudProps, marsh_funnel: v })} unit="sec" />
                <Field label={t('ddr.oilPct')} value={mudProps.oil_pct} onChange={(v: number) => setMudProps({ ...mudProps, oil_pct: v })} unit="%" />
                <Field label={t('ddr.waterPct')} value={mudProps.water_pct} onChange={(v: number) => setMudProps({ ...mudProps, water_pct: v })} unit="%" />
                <Field label={t('ddr.calcium')} value={mudProps.calcium} onChange={(v: number) => setMudProps({ ...mudProps, calcium: v })} unit="mg/L" />
                <Field label={t('ddr.alkalinity')} value={mudProps.alkalinity} onChange={(v: number) => setMudProps({ ...mudProps, alkalinity: v })} unit="mL" />
                <Field label={t('ddr.va')} value={mudProps.va} onChange={(v: number) => setMudProps({ ...mudProps, va: v })} unit="cP" />
                <Field label={t('ddr.es')} value={mudProps.es} onChange={(v: number) => setMudProps({ ...mudProps, es: v })} unit="V" />
                <Field label={t('ddr.mudTemperature')} value={mudProps.temperature} onChange={(v: number) => setMudProps({ ...mudProps, temperature: v })} unit="°F" />
              </div>
            </Section>
          )}

          {/* Cost Summary */}
          <Section id="cost" title={t('ddr.costSummary')} icon={DollarSign}>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Field label={t('ddr.rigCost')} value={costSummary.rig_cost} onChange={(v: number) => setCostSummary({ ...costSummary, rig_cost: v })} unit="USD" />
              <Field label={t('ddr.servicesCost')} value={costSummary.services} onChange={(v: number) => setCostSummary({ ...costSummary, services: v })} unit="USD" />
              <Field label={t('ddr.consumablesCost')} value={costSummary.consumables} onChange={(v: number) => setCostSummary({ ...costSummary, consumables: v })} unit="USD" />
              <Field label={t('ddr.mudChemicals')} value={costSummary.mud_chemicals} onChange={(v: number) => setCostSummary({ ...costSummary, mud_chemicals: v })} unit="USD" />
              <Field label={t('ddr.logistics')} value={costSummary.logistics} onChange={(v: number) => setCostSummary({ ...costSummary, logistics: v })} unit="USD" />
              <Field label={t('ddr.otherCost')} value={costSummary.other} onChange={(v: number) => setCostSummary({ ...costSummary, other: v })} unit="USD" />
              <Field label={t('ddr.totalDayCost')} value={costSummary.total_day} onChange={(v: number) => setCostSummary({ ...costSummary, total_day: v })} unit="USD" />
              <Field label={t('ddr.totalCumCost')} value={costSummary.total_cumulative} onChange={(v: number) => setCostSummary({ ...costSummary, total_cumulative: v })} unit="USD" />
            </div>
          </Section>

          {/* Personnel on Location (#11) */}
          <Section id="personnel" title={`${t('ddr.personnelSection')} (${(hsseData.personnel_companies || []).length})`} icon={Users}>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-white/40 border-b border-white/5 text-xs">
                    <th className="text-left py-2 px-1">{t('ddr.companyName')}</th>
                    <th className="text-left py-2 px-1 w-24">{t('ddr.headcount')}</th>
                    <th className="w-8"></th>
                  </tr>
                </thead>
                <tbody>
                  {(hsseData.personnel_companies || []).map((c: any, i: number) => (
                    <tr key={i} className="border-b border-white/5">
                      <td className="py-1 px-1"><input type="text" value={c.company || ''} onChange={e => updateCompany(i, 'company', e.target.value)} className="input-field w-full py-1 px-1.5 text-xs" placeholder="e.g. Halliburton" /></td>
                      <td className="py-1 px-1"><input type="number" value={c.headcount || ''} onChange={e => updateCompany(i, 'headcount', parseInt(e.target.value) || 0)} className="input-field w-20 py-1 px-1.5 text-xs" /></td>
                      <td className="py-1 px-1"><button onClick={() => removeCompany(i)} className="text-white/20 hover:text-red-400"><Trash2 size={12} /></button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <button onClick={addCompany} className="mt-3 px-3 py-1.5 bg-white/5 hover:bg-white/10 rounded-lg text-xs font-bold text-white/40 hover:text-white/60 transition-colors flex items-center gap-1.5">
              <Plus size={12} /> {t('ddr.addCompanyRow')}
            </button>
          </Section>

          {/* Materials / Inventory (#12) */}
          <Section id="materials" title={`${t('ddr.materialsSection')} (${(mudInventory.materials || []).length})`} icon={Package}>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-white/40 border-b border-white/5 text-xs">
                    <th className="text-left py-2 px-1">{t('ddr.productName')}</th>
                    <th className="text-left py-2 px-1 w-24">{t('ddr.materialInventory')}</th>
                    <th className="text-left py-2 px-1 w-24">{t('ddr.materialUsed')}</th>
                    <th className="text-left py-2 px-1 w-20">{t('ddr.materialUnit')}</th>
                    <th className="w-8"></th>
                  </tr>
                </thead>
                <tbody>
                  {(mudInventory.materials || []).map((m: any, i: number) => (
                    <tr key={i} className="border-b border-white/5">
                      <td className="py-1 px-1"><input type="text" value={m.product || ''} onChange={e => updateMaterial(i, 'product', e.target.value)} className="input-field w-full py-1 px-1.5 text-xs" placeholder="e.g. Barite" /></td>
                      <td className="py-1 px-1"><input type="number" value={m.inventory || ''} onChange={e => updateMaterial(i, 'inventory', parseFloat(e.target.value) || 0)} className="input-field w-20 py-1 px-1.5 text-xs" /></td>
                      <td className="py-1 px-1"><input type="number" value={m.used || ''} onChange={e => updateMaterial(i, 'used', parseFloat(e.target.value) || 0)} className="input-field w-20 py-1 px-1.5 text-xs" /></td>
                      <td className="py-1 px-1"><input type="text" value={m.unit || ''} onChange={e => updateMaterial(i, 'unit', e.target.value)} className="input-field w-18 py-1 px-1.5 text-xs" placeholder="sxs" /></td>
                      <td className="py-1 px-1"><button onClick={() => removeMaterial(i)} className="text-white/20 hover:text-red-400"><Trash2 size={12} /></button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <button onClick={addMaterial} className="mt-3 px-3 py-1.5 bg-white/5 hover:bg-white/10 rounded-lg text-xs font-bold text-white/40 hover:text-white/60 transition-colors flex items-center gap-1.5">
              <Plus size={12} /> {t('ddr.addMaterial')}
            </button>
          </Section>

          {/* Completion-specific */}
          {reportType === 'completion' && (
            <Section id="completion" title={t('ddr.fracParams')} icon={Zap}>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Field label={t('ddr.fracPressure')} value={completionData.frac_pressure} onChange={(v: number) => setCompletionData({ ...completionData, frac_pressure: v })} unit="psi" />
                <Field label={t('ddr.fracRate')} value={completionData.pump_rate} onChange={(v: number) => setCompletionData({ ...completionData, pump_rate: v })} unit="bpm" />
                <Field label={t('ddr.proppantType')} value={completionData.proppant_type} onChange={(v: string) => setCompletionData({ ...completionData, proppant_type: v })} type="text" />
                <Field label={t('ddr.proppantVolume')} value={completionData.proppant_volume} onChange={(v: number) => setCompletionData({ ...completionData, proppant_volume: v })} unit="lb" />
                <Field label={t('ddr.fluidVolume')} value={completionData.fluid_volume} onChange={(v: number) => setCompletionData({ ...completionData, fluid_volume: v })} unit="bbl" />
                <Field label="ISIP" value={completionData.isip} onChange={(v: number) => setCompletionData({ ...completionData, isip: v })} unit="psi" />
                <Field label={t('ddr.closurePressure')} value={completionData.closure_pressure} onChange={(v: number) => setCompletionData({ ...completionData, closure_pressure: v })} unit="psi" />
                <Field label={t('ddr.acidType')} value={completionData.acid_type} onChange={(v: string) => setCompletionData({ ...completionData, acid_type: v })} type="text" />
              </div>
            </Section>
          )}

          {/* Termination-specific */}
          {reportType === 'termination' && (
            <Section id="termination" title={t('ddr.wellSummary')} icon={CheckCircle}>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Field label={t('ddr.wellheadType')} value={terminationData.wellhead_type} onChange={(v: string) => setTerminationData({ ...terminationData, wellhead_type: v })} type="text" />
                <Field label="X-mas Tree Type" value={terminationData.xmas_tree_type} onChange={(v: string) => setTerminationData({ ...terminationData, xmas_tree_type: v })} type="text" />
                <Field label="P&A Barriers" value={terminationData.pa_barriers} onChange={(v: number) => setTerminationData({ ...terminationData, pa_barriers: v })} />
                <Field label={t('ddr.cementPlugs')} value={terminationData.cement_plugs} onChange={(v: number) => setTerminationData({ ...terminationData, cement_plugs: v })} />
                <Field label={t('ddr.totalWellDays')} value={terminationData.total_well_days} onChange={(v: number) => setTerminationData({ ...terminationData, total_well_days: v })} />
                <Field label={t('ddr.finalStatus')} value={terminationData.final_status} onChange={(v: string) => setTerminationData({ ...terminationData, final_status: v })} type="text" />
              </div>
            </Section>
          )}

          {/* Action buttons */}
          <div className="flex gap-3 sticky bottom-0 bg-gradient-to-t from-black/80 via-black/60 to-transparent pt-6 pb-2">
            <button onClick={() => saveReport('draft')} disabled={loading} className="flex items-center gap-2 px-5 py-2.5 bg-white/5 hover:bg-white/10 rounded-xl text-sm font-bold transition-all disabled:opacity-50">
              <Save size={16} /> {loading ? '...' : t('ddr.saveDraft')}
            </button>
            <button onClick={() => saveReport('submitted')} disabled={loading} className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 rounded-xl text-sm font-bold transition-all disabled:opacity-50 shadow-lg">
              <Send size={16} /> {t('ddr.submitReport')}
            </button>
            {editingId && (
              <>
                <button onClick={handleExportPDF} disabled={isGeneratingPDF} className="flex items-center gap-2 px-5 py-2.5 bg-green-600/20 hover:bg-green-600/30 border border-green-500/30 rounded-xl text-sm font-bold text-green-400 transition-all disabled:opacity-50">
                  <Download size={16} /> {isGeneratingPDF ? '...' : t('ddr.exportPDF')}
                </button>
                <button onClick={() => { resetForm(); setActiveTab('reports'); }} className="px-5 py-2.5 bg-white/5 hover:bg-white/10 rounded-xl text-sm font-bold text-white/40 transition-all">
                  {t('common.cancel')}
                </button>
              </>
            )}
          </div>
        </motion.div>
      )}

      {/* ============================================================ */}
      {/* TAB: KPIs Dashboard */}
      {/* ============================================================ */}
      {activeTab === 'kpis' && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
          {/* Cumulative Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: t('ddr.totalFootage'), value: `${cumulativeStats.total_footage || 0}`, unit: 'ft', color: 'text-green-400' },
              { label: t('ddr.avgROP'), value: `${cumulativeStats.avg_rop_overall || 0}`, unit: 'ft/hr', color: 'text-orange-400' },
              { label: t('ddr.nptHours'), value: `${cumulativeStats.total_npt_hours || 0}`, unit: 'hrs', color: 'text-red-400' },
              { label: t('ddr.totalCost'), value: `$${(cumulativeStats.total_cost || 0).toLocaleString()}`, unit: '', color: 'text-cyan-400' },
            ].map((stat, i) => (
              <div key={i} className="glass-panel p-4 rounded-xl border border-white/5 text-center">
                <p className="text-xs text-white/40 mb-1">{stat.label}</p>
                <p className={`text-2xl font-bold ${stat.color}`}>{stat.value}</p>
                {stat.unit && <p className="text-[10px] text-white/20 mt-0.5">{stat.unit}</p>}
              </div>
            ))}
          </div>

          {/* Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <TimeDepthChart data={timeDepthData} title={t('ddr.timeVsDepth')} />
            <ROPProgressChart
              data={timeDepthData.map(d => ({ day: d.day, date: d.date, footage: d.footage, avg_rop: d.footage > 0 ? +(d.footage / 8).toFixed(1) : 0 }))}
              title={t('ddr.ropProgress')}
            />
            <CostTrackingChart data={costData} title={t('ddr.costVsAFE')} />
            <NPTBreakdownChart
              byCategory={nptBreakdown.by_category || {}}
              totalHours={nptBreakdown.total_npt_hours || 0}
              title={t('ddr.nptBreakdown')}
            />
          </div>

          {/* Timeline of latest report */}
          {reports.length > 0 && reports[0].id && (
            <DailyOperationsTimeline
              operations={operations.filter(o => o.description || o.iadc_code)}
              title={t('ddr.dailyTimeline')}
            />
          )}
        </motion.div>
      )}

      {/* ============================================================ */}
      {/* TAB: AI Analysis */}
      {/* ============================================================ */}
      {activeTab === 'analysis' && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
          {reports.length > 0 ? (
            <AIAnalysisPanel
              moduleName={t('modules.dailyReports')}
              moduleIcon={ClipboardList}
              wellName={wellName}
              analysis={aiAnalysis?.analysis || null}
              confidence={aiAnalysis?.confidence || 'LOW'}
              agentRole={aiAnalysis?.agent_role || ''}
              isLoading={isAnalyzing}
              keyMetrics={aiAnalysis?.key_metrics || []}
              onAnalyze={runAIAnalysis}
              provider={provider}
              onProviderChange={setProvider}
              availableProviders={availableProviders}
            />
          ) : (
            <div className="glass-panel p-12 text-center">
              <Activity size={48} className="mx-auto text-white/10 mb-4" />
              <p className="text-white/30 text-sm">{t('ddr.noReportsForAnalysis') || 'Create at least one report to enable AI analysis.'}</p>
            </div>
          )}
        </motion.div>
      )}

      {/* Hidden PDF template for export */}
      <DDRReportPDF
        ref={pdfRef}
        wellName={wellName}
        reportNumber={editingId ? (reports.find(r => r.id === editingId)?.report_number || 0) : 0}
        reportDate={reportDate}
        reportType={reportType}
        depthStart={depthStart}
        depthEnd={depthEnd}
        depthTVD={depthTvd}
        headerData={headerData}
        operations={operations}
        drillingParams={drillingParams}
        mudProperties={mudProps}
        bhaData={bhaData}
        gasMonitoring={gasMonitoring}
        costSummary={costSummary}
        hsseData={hsseData}
        mudInventory={mudInventory}
        completionData={completionData}
        terminationData={terminationData}
        status={editingId ? (reports.find(r => r.id === editingId)?.status || 'draft') : 'draft'}
      />
        </>
      )}
    </div>
  );
};

export default DailyReportsModule;
