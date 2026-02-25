/**
 * DDRForm.tsx — DDR Form with all sections
 * Sections: header, operations, drilling, mud, BHA, gas, NPT, HSSE, costs, completion, termination
 */
import React, { useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ChevronDown, ChevronUp,
  Plus, Save, Send, CheckCircle, Trash2, FileText, Download,
  Activity, AlertTriangle, Clock, DollarSign,
  TrendingDown, Zap, Shield, Navigation, Layers, Gauge, Users, Package, Crosshair, Timer,
  Upload,
} from 'lucide-react';
import { useToast } from '../ui/Toast';

// ── Factory functions (exported for reuse) ──

export const emptyOperation = () => ({
  from_time: 0, to_time: 0, hours: 0, iadc_code: '', category: '',
  description: '', depth_start: null as number | null, depth_end: null as number | null,
  is_npt: false, npt_code: '',
});

export const emptyBHA = () => ({
  component_type: '', od: 0, length: 0, weight: 0, serial_number: '',
});

// ── BHA Column Map for CSV/Excel upload ──

export const BHA_COL_MAP: Record<string, string> = {
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

// ── Types ──

export type OperationRow = ReturnType<typeof emptyOperation>;
export type BHARow = ReturnType<typeof emptyBHA>;

export interface DDRFormProps {
  // Report meta
  reportType: string;
  setReportType: (v: string) => void;
  reportDate: string;
  setReportDate: (v: string) => void;
  depthStart: number;
  setDepthStart: (v: string | number) => void;
  depthEnd: number;
  setDepthEnd: (v: string | number) => void;
  depthTvd: number;
  setDepthTvd: (v: string | number) => void;
  // Header
  headerData: Record<string, unknown>;
  setHeaderData: (v: Record<string, unknown>) => void;
  // Operations
  operations: OperationRow[];
  setOperations: (v: OperationRow[]) => void;
  // Drilling
  drillingParams: Record<string, string | number>;
  setDrillingParams: (v: Record<string, string | number>) => void;
  // Mud
  mudProps: Record<string, string | number>;
  setMudProps: (v: Record<string, string | number>) => void;
  mudInventory: Record<string, unknown>;
  setMudInventory: (v: Record<string, unknown>) => void;
  // BHA
  bhaData: BHARow[];
  setBhaData: (v: BHARow[]) => void;
  // Gas
  gasMonitoring: Record<string, string | number>;
  setGasMonitoring: (v: Record<string, string | number>) => void;
  // NPT
  nptEvents: Record<string, string | number>[];
  // HSSE
  hsseData: Record<string, unknown>;
  setHsseData: (v: Record<string, unknown>) => void;
  // Cost
  costSummary: Record<string, string | number>;
  setCostSummary: (v: Record<string, string | number>) => void;
  // Completion
  completionData: Record<string, string | number>;
  setCompletionData: (v: Record<string, string | number>) => void;
  // Termination
  terminationData: Record<string, string | number>;
  setTerminationData: (v: Record<string, string | number>) => void;
  // Sections
  expandedSections: Set<string>;
  toggleSection: (s: string) => void;
  // Reference data
  iadcCodes: Record<string, string>;
  opCategories: string[];
  // Actions
  editingId: number | null;
  loading: boolean;
  isGeneratingPDF: boolean;
  onSave: (status: string) => void;
  onExportPDF: () => void;
  onCancel: () => void;
}

// ── Helper Components ──

const Section: React.FC<{
  id: string;
  title: string;
  icon: React.ElementType;
  expandedSections: Set<string>;
  toggleSection: (s: string) => void;
  children: React.ReactNode;
}> = ({ id, title, icon: Icon, expandedSections, toggleSection, children }) => (
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

const Field: React.FC<{
  label: string;
  value: string | number;
  onChange: (v: string | number) => void;
  type?: string;
  unit?: string;
}> = ({ label, value, onChange, type = 'number', unit = '' }) => (
  <div>
    <label className="text-xs text-white/40 block mb-1">{label}{unit && ` (${unit})`}</label>
    <input type={type} value={value || ''} onChange={e => onChange(type === 'number' ? parseFloat(e.target.value) || 0 : e.target.value)} className="input-field w-full py-2 px-3 text-sm" />
  </div>
);

const TextArea: React.FC<{
  label: string;
  value: string | number;
  onChange: (v: string) => void;
  rows?: number;
}> = ({ label, value, onChange, rows = 3 }) => (
  <div>
    <label className="text-xs text-white/40 block mb-1">{label}</label>
    <textarea value={value || ''} onChange={e => onChange(e.target.value)} rows={rows} className="input-field w-full py-2 px-3 text-sm resize-y min-h-[60px]" />
  </div>
);

// ── Main Component ──

const DDRForm: React.FC<DDRFormProps> = ({
  reportType, setReportType, reportDate, setReportDate,
  depthStart, setDepthStart, depthEnd, setDepthEnd, depthTvd, setDepthTvd,
  headerData, setHeaderData,
  operations, setOperations,
  drillingParams, setDrillingParams,
  mudProps, setMudProps, mudInventory, setMudInventory,
  bhaData, setBhaData,
  gasMonitoring, setGasMonitoring,
  hsseData, setHsseData,
  costSummary, setCostSummary,
  completionData, setCompletionData,
  terminationData, setTerminationData,
  expandedSections, toggleSection,
  iadcCodes, opCategories,
  editingId, loading, isGeneratingPDF,
  onSave, onExportPDF, onCancel,
}) => {
  const { t } = useTranslation();
  const { addToast } = useToast();
  const bhaFileRef = useRef<HTMLInputElement>(null);

  // ── Operation helpers ──
  const updateOp = (idx: number, field: string, value: string | number | boolean) => {
    const updated = [...operations];
    updated[idx] = { ...updated[idx], [field]: value };
    if (field === 'from_time' || field === 'to_time') {
      const from = field === 'from_time' ? parseFloat(String(value)) || 0 : updated[idx].from_time;
      const to = field === 'to_time' ? parseFloat(String(value)) || 0 : updated[idx].to_time;
      updated[idx].hours = Math.max(0, to - from);
    }
    setOperations(updated);
  };
  const addOp = () => setOperations([...operations, emptyOperation()]);
  const removeOp = (idx: number) => setOperations(operations.filter((_, i) => i !== idx));

  // ── BHA helpers ──
  const updateBHA = (idx: number, field: string, value: string | number) => {
    const updated = [...bhaData];
    updated[idx] = { ...updated[idx], [field]: value };
    setBhaData(updated);
  };
  const addBHA = () => setBhaData([...bhaData, emptyBHA()]);
  const removeBHA = (idx: number) => setBhaData(bhaData.filter((_, i) => i !== idx));

  // ── BHA file upload ──
  const handleBHAFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async (evt) => {
      try {
        const XLSX = await import('xlsx');
        const data = new Uint8Array(evt.target?.result as ArrayBuffer);
        const wb = XLSX.read(data, { type: 'array' });
        const sheet = wb.Sheets[wb.SheetNames[0]];
        if (!sheet) { addToast(t('ddr.bhaUploadEmpty'), 'error'); return; }
        const rows: Record<string, string | number>[] = XLSX.utils.sheet_to_json(sheet, { defval: '' });
        if (rows.length === 0) { addToast(t('ddr.bhaUploadEmpty'), 'error'); return; }

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
              if (bf === 'component_type' || bf === 'serial_number') (bha as Record<string, string | number>)[bf] = String(v || '').trim();
              else (bha as Record<string, string | number>)[bf] = parseFloat(String(v)) || 0;
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
  const updateSurvey = (idx: number, field: string, value: string | number) => {
    const surveys = [...((headerData.surveys as Record<string, string | number>[]) || [])];
    surveys[idx] = { ...surveys[idx], [field]: value };
    setHeaderData({ ...headerData, surveys });
  };
  const addSurvey = () => setHeaderData({ ...headerData, surveys: [...((headerData.surveys as Record<string, string | number>[]) || []), { md: 0, tvd: 0, inc: 0, azi: 0, dls: 0 }] });
  const removeSurvey = (idx: number) => setHeaderData({ ...headerData, surveys: ((headerData.surveys as Record<string, string | number>[]) || []).filter((_: unknown, i: number) => i !== idx) });

  // ── Personnel companies helpers ──
  const updateCompany = (idx: number, field: string, value: string | number) => {
    const companies = [...((hsseData.personnel_companies as Record<string, string | number>[]) || [])];
    companies[idx] = { ...companies[idx], [field]: value };
    setHsseData({ ...hsseData, personnel_companies: companies });
  };
  const addCompany = () => setHsseData({ ...hsseData, personnel_companies: [...((hsseData.personnel_companies as Record<string, string | number>[]) || []), { company: '', headcount: 0 }] });
  const removeCompany = (idx: number) => setHsseData({ ...hsseData, personnel_companies: ((hsseData.personnel_companies as Record<string, string | number>[]) || []).filter((_: unknown, i: number) => i !== idx) });

  // ── Materials helpers ──
  const updateMaterial = (idx: number, field: string, value: string | number) => {
    const materials = [...((mudInventory.materials as Record<string, string | number>[]) || [])];
    materials[idx] = { ...materials[idx], [field]: value };
    setMudInventory({ ...mudInventory, materials });
  };
  const addMaterial = () => setMudInventory({ ...mudInventory, materials: [...((mudInventory.materials as Record<string, string | number>[]) || []), { product: '', inventory: 0, used: 0, unit: '' }] });
  const removeMaterial = (idx: number) => setMudInventory({ ...mudInventory, materials: ((mudInventory.materials as Record<string, string | number>[]) || []).filter((_: unknown, i: number) => i !== idx) });

  // ── Shorthand section render ──
  const S: React.FC<{ id: string; title: string; icon: React.ElementType; children: React.ReactNode }> = ({ id, title, icon, children }) => (
    <Section id={id} title={title} icon={icon} expandedSections={expandedSections} toggleSection={toggleSection}>
      {children}
    </Section>
  );

  return (
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
          <Field label={t('ddr.reportDate')} value={reportDate} onChange={setReportDate as (v: string | number) => void} type="date" />
          <Field label={t('ddr.depthStart')} value={depthStart} onChange={setDepthStart} unit="ft" />
          <Field label={t('ddr.depthEnd')} value={depthEnd} onChange={setDepthEnd} unit="ft" />
        </div>
      </div>

      {/* Header */}
      <S id="header" title={t('ddr.headerSection')} icon={FileText}>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Field label={t('ddr.operator')} value={headerData.operator as string} onChange={(v: string | number) => setHeaderData({ ...headerData, operator: v })} type="text" />
          <Field label={t('ddr.contractor')} value={headerData.contractor as string} onChange={(v: string | number) => setHeaderData({ ...headerData, contractor: v })} type="text" />
          <Field label={t('ddr.rigName')} value={headerData.rig as string} onChange={(v: string | number) => setHeaderData({ ...headerData, rig: v })} type="text" />
          <Field label={t('ddr.fieldName')} value={headerData.field as string} onChange={(v: string | number) => setHeaderData({ ...headerData, field: v })} type="text" />
          <Field label={t('ddr.apiNumber')} value={headerData.api_number as string} onChange={(v: string | number) => setHeaderData({ ...headerData, api_number: v })} type="text" />
          <Field label={t('ddr.contractNumber')} value={headerData.contract_number as string} onChange={(v: string | number) => setHeaderData({ ...headerData, contract_number: v })} type="text" />
          <Field label="AFE #" value={headerData.afe_number as string} onChange={(v: string | number) => setHeaderData({ ...headerData, afe_number: v })} type="text" />
          <Field label="AFE Budget" value={headerData.afe_budget as number} onChange={(v: string | number) => setHeaderData({ ...headerData, afe_budget: v })} unit="USD" />
          <Field label={t('ddr.spudDate')} value={headerData.spud_date as string} onChange={(v: string | number) => setHeaderData({ ...headerData, spud_date: v })} type="date" />
          <Field label={t('ddr.plannedDepth')} value={headerData.planned_depth as number} onChange={(v: string | number) => setHeaderData({ ...headerData, planned_depth: v })} unit="ft" />
          <Field label={t('ddr.plannedDays')} value={headerData.planned_days as number} onChange={(v: string | number) => setHeaderData({ ...headerData, planned_days: v })} />
          <Field label="TVD" value={depthTvd} onChange={setDepthTvd} unit="ft" />
          <Field label={t('ddr.wellPhase')} value={headerData.phase as string} onChange={(v: string | number) => setHeaderData({ ...headerData, phase: v })} type="text" />
          <Field label={t('ddr.wellActivity')} value={headerData.activity as string} onChange={(v: string | number) => setHeaderData({ ...headerData, activity: v })} type="text" />
        </div>
      </S>

      {/* HSEQ / Safety */}
      <S id="hseq" title={t('ddr.hsseStructured')} icon={Shield}>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <Field label={t('ddr.dslti')} value={hsseData.dslti as number} onChange={(v: string | number) => setHsseData({ ...hsseData, dslti: v })} />
          <Field label={t('ddr.dslta')} value={hsseData.dslta as number} onChange={(v: string | number) => setHsseData({ ...hsseData, dslta: v })} />
          <Field label={t('ddr.daysNoSpills')} value={hsseData.days_no_spills as number} onChange={(v: string | number) => setHsseData({ ...hsseData, days_no_spills: v })} />
          <Field label={t('ddr.daysNoIncidents')} value={hsseData.days_no_incidents as number} onChange={(v: string | number) => setHsseData({ ...hsseData, days_no_incidents: v })} />
          <Field label={t('ddr.safetyCards')} value={hsseData.safety_cards as number} onChange={(v: string | number) => setHsseData({ ...hsseData, safety_cards: v })} />
        </div>
        <div className="grid grid-cols-2 gap-4 mt-4">
          <Field label={t('ddr.supervisorDrilling')} value={hsseData.supervisor_drilling as string} onChange={(v: string | number) => setHsseData({ ...hsseData, supervisor_drilling: v })} type="text" />
          <Field label={t('ddr.supervisorCompany')} value={hsseData.supervisor_company as string} onChange={(v: string | number) => setHsseData({ ...hsseData, supervisor_company: v })} type="text" />
        </div>
      </S>

      {/* Operations Log */}
      <S id="operations" title={`${t('ddr.operationsLog')} (${operations.length})`} icon={Clock}>
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
      </S>

      {/* Summary / Program */}
      <S id="summary" title={t('ddr.summaryProgramSection')} icon={FileText}>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <TextArea label={t('ddr.prevDaySummary')} value={headerData.prev_day_summary as string} onChange={(v: string) => setHeaderData({ ...headerData, prev_day_summary: v })} rows={3} />
          <TextArea label={t('ddr.daySummary')} value={headerData.day_summary as string} onChange={(v: string) => setHeaderData({ ...headerData, day_summary: v })} rows={3} />
          <TextArea label={t('ddr.plannedProgram')} value={headerData.planned_program as string} onChange={(v: string) => setHeaderData({ ...headerData, planned_program: v })} rows={3} />
          <TextArea label={t('ddr.urgentItems')} value={headerData.urgent_items as string} onChange={(v: string) => setHeaderData({ ...headerData, urgent_items: v })} rows={3} />
        </div>
      </S>

      {/* Time Classification */}
      <S id="timeclass" title={t('ddr.timeClassification')} icon={Timer}>
        <div className="grid grid-cols-3 md:grid-cols-6 gap-4">
          <div className="col-span-3 md:col-span-6 flex gap-2 items-center">
            <span className="text-xs text-white/40 font-bold">{t('ddr.dailyHrs')}</span>
          </div>
          <Field label={t('ddr.productiveTime')} value={headerData.time_productive as number} onChange={(v: string | number) => setHeaderData({ ...headerData, time_productive: v })} unit="hrs" />
          <Field label={t('ddr.unproductiveTime')} value={headerData.time_unproductive as number} onChange={(v: string | number) => setHeaderData({ ...headerData, time_unproductive: v })} unit="hrs" />
          <Field label={t('ddr.downtimeHours')} value={headerData.time_downtime as number} onChange={(v: string | number) => setHeaderData({ ...headerData, time_downtime: v })} unit="hrs" />
          <Field label={`${t('ddr.productiveTime')} ${t('ddr.cumulativeHrs')}`} value={headerData.cum_productive as number} onChange={(v: string | number) => setHeaderData({ ...headerData, cum_productive: v })} unit="hrs" />
          <Field label={`${t('ddr.unproductiveTime')} ${t('ddr.cumulativeHrs')}`} value={headerData.cum_unproductive as number} onChange={(v: string | number) => setHeaderData({ ...headerData, cum_unproductive: v })} unit="hrs" />
          <Field label={`${t('ddr.downtimeHours')} ${t('ddr.cumulativeHrs')}`} value={headerData.cum_downtime as number} onChange={(v: string | number) => setHeaderData({ ...headerData, cum_downtime: v })} unit="hrs" />
        </div>
      </S>

      {/* Drilling-specific sections (hidden for mobilization reports) */}
      {reportType !== 'mobilization' && (
        <>
          {/* Drilling Parameters */}
          <S id="drilling" title={t('ddr.drillingParams')} icon={Activity}>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Field label="WOB" value={drillingParams.wob} onChange={(v: string | number) => setDrillingParams({ ...drillingParams, wob: v as number })} unit="klb" />
              <Field label="RPM" value={drillingParams.rpm} onChange={(v: string | number) => setDrillingParams({ ...drillingParams, rpm: v as number })} />
              <Field label="SPM" value={drillingParams.spm} onChange={(v: string | number) => setDrillingParams({ ...drillingParams, spm: v as number })} />
              <Field label={t('ddr.flowRate')} value={drillingParams.flow_rate} onChange={(v: string | number) => setDrillingParams({ ...drillingParams, flow_rate: v as number })} unit="gpm" />
              <Field label="SPP" value={drillingParams.spp} onChange={(v: string | number) => setDrillingParams({ ...drillingParams, spp: v as number })} unit="psi" />
              <Field label={t('ddr.torque')} value={drillingParams.torque} onChange={(v: string | number) => setDrillingParams({ ...drillingParams, torque: v as number })} unit="ft-lb" />
              <Field label="ROP" value={drillingParams.rop} onChange={(v: string | number) => setDrillingParams({ ...drillingParams, rop: v as number })} unit="ft/hr" />
              <Field label="ECD" value={drillingParams.ecd} onChange={(v: string | number) => setDrillingParams({ ...drillingParams, ecd: v as number })} unit="ppg" />
              <Field label={t('ddr.hookLoad')} value={drillingParams.hook_load} onChange={(v: string | number) => setDrillingParams({ ...drillingParams, hook_load: v as number })} unit="klb" />
              <Field label="ESD" value={drillingParams.esd} onChange={(v: string | number) => setDrillingParams({ ...drillingParams, esd: v as number })} unit="ppg" />
            </div>
          </S>

          {/* Mud Properties */}
          <S id="mud" title={t('ddr.mudProperties')} icon={TrendingDown}>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Field label={t('ddr.mudWeight')} value={mudProps.density} onChange={(v: string | number) => setMudProps({ ...mudProps, density: v as number })} unit="ppg" />
              <Field label="PV" value={mudProps.pv} onChange={(v: string | number) => setMudProps({ ...mudProps, pv: v as number })} unit="cP" />
              <Field label="YP" value={mudProps.yp} onChange={(v: string | number) => setMudProps({ ...mudProps, yp: v as number })} unit="lb/100ft²" />
              <Field label={t('ddr.gels10s')} value={mudProps.gels_10s} onChange={(v: string | number) => setMudProps({ ...mudProps, gels_10s: v as number })} unit="lb/100ft²" />
              <Field label={t('ddr.gels10m')} value={mudProps.gels_10m} onChange={(v: string | number) => setMudProps({ ...mudProps, gels_10m: v as number })} unit="lb/100ft²" />
              <Field label={t('ddr.filtrate')} value={mudProps.filtrate} onChange={(v: string | number) => setMudProps({ ...mudProps, filtrate: v as number })} unit="ml/30min" />
              <Field label="pH" value={mudProps.ph} onChange={(v: string | number) => setMudProps({ ...mudProps, ph: v as number })} />
              <Field label={t('ddr.chlorides')} value={mudProps.chlorides} onChange={(v: string | number) => setMudProps({ ...mudProps, chlorides: v as number })} unit="mg/L" />
              <Field label="MBT" value={mudProps.mbt} onChange={(v: string | number) => setMudProps({ ...mudProps, mbt: v as number })} unit="lb/bbl" />
              <Field label={t('ddr.solidsPct')} value={mudProps.solids_pct} onChange={(v: string | number) => setMudProps({ ...mudProps, solids_pct: v as number })} unit="%" />
            </div>
          </S>

          {/* BHA */}
          <S id="bha" title={`${t('ddr.bhaSection')} (${bhaData.length})`} icon={Zap}>
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
          </S>

          {/* Gas Monitoring */}
          <S id="gas" title={t('ddr.gasMonitoring')} icon={AlertTriangle}>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Field label={t('ddr.backgroundGas')} value={gasMonitoring.background_gas} onChange={(v: string | number) => setGasMonitoring({ ...gasMonitoring, background_gas: v as number })} unit="%" />
              <Field label={t('ddr.connectionGas')} value={gasMonitoring.connection_gas} onChange={(v: string | number) => setGasMonitoring({ ...gasMonitoring, connection_gas: v as number })} unit="%" />
              <Field label={t('ddr.tripGas')} value={gasMonitoring.trip_gas} onChange={(v: string | number) => setGasMonitoring({ ...gasMonitoring, trip_gas: v as number })} unit="%" />
              <Field label="C1 (Methane)" value={gasMonitoring.c1} onChange={(v: string | number) => setGasMonitoring({ ...gasMonitoring, c1: v as number })} unit="ppm" />
              <Field label="C2 (Ethane)" value={gasMonitoring.c2} onChange={(v: string | number) => setGasMonitoring({ ...gasMonitoring, c2: v as number })} unit="ppm" />
              <Field label="H2S" value={gasMonitoring.h2s} onChange={(v: string | number) => setGasMonitoring({ ...gasMonitoring, h2s: v as number })} unit="ppm" />
              <Field label="CO2" value={gasMonitoring.co2} onChange={(v: string | number) => setGasMonitoring({ ...gasMonitoring, co2: v as number })} unit="%" />
            </div>
          </S>

          {/* Bit Data */}
          <S id="bitdata" title={t('ddr.bitDataSection')} icon={Crosshair}>
            <p className="text-[10px] text-white/30 font-bold uppercase mb-3">{t('ddr.currentBit')}</p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Field label={t('ddr.bitBrand')} value={drillingParams.bit_brand} onChange={(v: string | number) => setDrillingParams({ ...drillingParams, bit_brand: v as string })} type="text" />
              <Field label={t('ddr.bitSerial')} value={drillingParams.bit_serial} onChange={(v: string | number) => setDrillingParams({ ...drillingParams, bit_serial: v as string })} type="text" />
              <Field label={t('ddr.bitType')} value={drillingParams.bit_type} onChange={(v: string | number) => setDrillingParams({ ...drillingParams, bit_type: v as string })} type="text" />
              <Field label={t('ddr.bitSize')} value={drillingParams.bit_size} onChange={(v: string | number) => setDrillingParams({ ...drillingParams, bit_size: v as number })} unit="in" />
              <Field label={t('ddr.bitNozzles')} value={drillingParams.bit_nozzles} onChange={(v: string | number) => setDrillingParams({ ...drillingParams, bit_nozzles: v as string })} type="text" />
              <Field label={t('ddr.bitDullIn')} value={drillingParams.bit_dull_in} onChange={(v: string | number) => setDrillingParams({ ...drillingParams, bit_dull_in: v as string })} type="text" />
              <Field label={t('ddr.bitDullOut')} value={drillingParams.bit_dull_out} onChange={(v: string | number) => setDrillingParams({ ...drillingParams, bit_dull_out: v as string })} type="text" />
              <Field label={t('ddr.bitFootage')} value={drillingParams.bit_footage} onChange={(v: string | number) => setDrillingParams({ ...drillingParams, bit_footage: v as number })} unit="ft" />
            </div>
            <p className="text-[10px] text-white/30 font-bold uppercase mb-3 mt-5">{t('ddr.previousBit')}</p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Field label={t('ddr.bitBrand')} value={drillingParams.prev_bit_brand} onChange={(v: string | number) => setDrillingParams({ ...drillingParams, prev_bit_brand: v as string })} type="text" />
              <Field label={t('ddr.bitSerial')} value={drillingParams.prev_bit_serial} onChange={(v: string | number) => setDrillingParams({ ...drillingParams, prev_bit_serial: v as string })} type="text" />
              <Field label={t('ddr.bitType')} value={drillingParams.prev_bit_type} onChange={(v: string | number) => setDrillingParams({ ...drillingParams, prev_bit_type: v as string })} type="text" />
              <Field label={t('ddr.bitSize')} value={drillingParams.prev_bit_size} onChange={(v: string | number) => setDrillingParams({ ...drillingParams, prev_bit_size: v as number })} unit="in" />
              <Field label={t('ddr.bitDullIn')} value={drillingParams.prev_bit_dull_in} onChange={(v: string | number) => setDrillingParams({ ...drillingParams, prev_bit_dull_in: v as string })} type="text" />
              <Field label={t('ddr.bitDullOut')} value={drillingParams.prev_bit_dull_out} onChange={(v: string | number) => setDrillingParams({ ...drillingParams, prev_bit_dull_out: v as string })} type="text" />
              <Field label={t('ddr.bitFootage')} value={drillingParams.prev_bit_footage} onChange={(v: string | number) => setDrillingParams({ ...drillingParams, prev_bit_footage: v as number })} unit="ft" />
            </div>
          </S>

          {/* Survey / Deviation */}
          <S id="survey" title={`${t('ddr.surveySection')} (${((headerData.surveys as unknown[]) || []).length})`} icon={Navigation}>
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
                  {((headerData.surveys as Record<string, string | number>[]) || []).map((s: Record<string, string | number>, i: number) => (
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
          </S>

          {/* Casing Record */}
          <S id="casing" title={t('ddr.casingRecord')} icon={Layers}>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Field label={t('ddr.lastCasing')} value={headerData.last_casing as string} onChange={(v: string | number) => setHeaderData({ ...headerData, last_casing: v })} type="text" />
              <Field label={t('ddr.lastCasingDepth')} value={headerData.last_casing_depth as number} onChange={(v: string | number) => setHeaderData({ ...headerData, last_casing_depth: v })} unit="ft" />
              <Field label={t('ddr.nextCasing')} value={headerData.next_casing as string} onChange={(v: string | number) => setHeaderData({ ...headerData, next_casing: v })} type="text" />
              <Field label={t('ddr.nextCasingDepth')} value={headerData.next_casing_depth as number} onChange={(v: string | number) => setHeaderData({ ...headerData, next_casing_depth: v })} unit="ft" />
            </div>
          </S>

          {/* Surface Equipment Tests */}
          <S id="surfacetests" title={t('ddr.surfaceEquipTests')} icon={Gauge}>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <Field label={t('ddr.bopTestDate')} value={headerData.bop_test_date as string} onChange={(v: string | number) => setHeaderData({ ...headerData, bop_test_date: v })} type="date" />
              <Field label={t('ddr.bopTestPressure')} value={headerData.bop_test_pressure as number} onChange={(v: string | number) => setHeaderData({ ...headerData, bop_test_pressure: v })} unit="psi" />
              <Field label={t('ddr.koomeyTime')} value={headerData.koomey_time as number} onChange={(v: string | number) => setHeaderData({ ...headerData, koomey_time: v })} unit="sec" />
              <Field label={t('ddr.tonMiles')} value={headerData.ton_miles as number} onChange={(v: string | number) => setHeaderData({ ...headerData, ton_miles: v })} />
              <Field label={t('ddr.standpipePressureSurf')} value={headerData.standpipe_pressure as number} onChange={(v: string | number) => setHeaderData({ ...headerData, standpipe_pressure: v })} unit="psi" />
              <Field label={t('ddr.casingPressureSurf')} value={headerData.casing_pressure as number} onChange={(v: string | number) => setHeaderData({ ...headerData, casing_pressure: v })} unit="psi" />
            </div>
          </S>

          {/* Pump Data */}
          <S id="pumpdata" title={t('ddr.pumpDataSection')} icon={Gauge}>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <Field label={t('ddr.pump1Liner')} value={drillingParams.pump1_liner} onChange={(v: string | number) => setDrillingParams({ ...drillingParams, pump1_liner: v as number })} unit="in" />
              <Field label={t('ddr.pump2Liner')} value={drillingParams.pump2_liner} onChange={(v: string | number) => setDrillingParams({ ...drillingParams, pump2_liner: v as number })} unit="in" />
              <Field label={t('ddr.pump3Liner')} value={drillingParams.pump3_liner} onChange={(v: string | number) => setDrillingParams({ ...drillingParams, pump3_liner: v as number })} unit="in" />
              <Field label={t('ddr.annularVelocity')} value={drillingParams.annular_velocity} onChange={(v: string | number) => setDrillingParams({ ...drillingParams, annular_velocity: v as number })} unit="ft/min" />
              <Field label={t('ddr.stringWeightUp')} value={drillingParams.string_weight_up} onChange={(v: string | number) => setDrillingParams({ ...drillingParams, string_weight_up: v as number })} unit="klb" />
              <Field label={t('ddr.stringWeightDown')} value={drillingParams.string_weight_down} onChange={(v: string | number) => setDrillingParams({ ...drillingParams, string_weight_down: v as number })} unit="klb" />
            </div>
          </S>
        </>
      )}

      {/* Extended Mud Properties */}
      {reportType !== 'mobilization' && (
        <S id="mudext" title={`${t('ddr.mudProperties')} — ${t('ddr.mudType') || 'Extended'}`} icon={TrendingDown}>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <Field label={t('ddr.mudType')} value={mudProps.mud_type} onChange={(v: string | number) => setMudProps({ ...mudProps, mud_type: v as string })} type="text" />
            <Field label={t('ddr.marshFunnel')} value={mudProps.marsh_funnel} onChange={(v: string | number) => setMudProps({ ...mudProps, marsh_funnel: v as number })} unit="sec" />
            <Field label={t('ddr.oilPct')} value={mudProps.oil_pct} onChange={(v: string | number) => setMudProps({ ...mudProps, oil_pct: v as number })} unit="%" />
            <Field label={t('ddr.waterPct')} value={mudProps.water_pct} onChange={(v: string | number) => setMudProps({ ...mudProps, water_pct: v as number })} unit="%" />
            <Field label={t('ddr.calcium')} value={mudProps.calcium} onChange={(v: string | number) => setMudProps({ ...mudProps, calcium: v as number })} unit="mg/L" />
            <Field label={t('ddr.alkalinity')} value={mudProps.alkalinity} onChange={(v: string | number) => setMudProps({ ...mudProps, alkalinity: v as number })} unit="mL" />
            <Field label={t('ddr.va')} value={mudProps.va} onChange={(v: string | number) => setMudProps({ ...mudProps, va: v as number })} unit="cP" />
            <Field label={t('ddr.es')} value={mudProps.es} onChange={(v: string | number) => setMudProps({ ...mudProps, es: v as number })} unit="V" />
            <Field label={t('ddr.mudTemperature')} value={mudProps.temperature} onChange={(v: string | number) => setMudProps({ ...mudProps, temperature: v as number })} unit="°F" />
          </div>
        </S>
      )}

      {/* Cost Summary */}
      <S id="cost" title={t('ddr.costSummary')} icon={DollarSign}>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Field label={t('ddr.rigCost')} value={costSummary.rig_cost} onChange={(v: string | number) => setCostSummary({ ...costSummary, rig_cost: v as number })} unit="USD" />
          <Field label={t('ddr.servicesCost')} value={costSummary.services} onChange={(v: string | number) => setCostSummary({ ...costSummary, services: v as number })} unit="USD" />
          <Field label={t('ddr.consumablesCost')} value={costSummary.consumables} onChange={(v: string | number) => setCostSummary({ ...costSummary, consumables: v as number })} unit="USD" />
          <Field label={t('ddr.mudChemicals')} value={costSummary.mud_chemicals} onChange={(v: string | number) => setCostSummary({ ...costSummary, mud_chemicals: v as number })} unit="USD" />
          <Field label={t('ddr.logistics')} value={costSummary.logistics} onChange={(v: string | number) => setCostSummary({ ...costSummary, logistics: v as number })} unit="USD" />
          <Field label={t('ddr.otherCost')} value={costSummary.other} onChange={(v: string | number) => setCostSummary({ ...costSummary, other: v as number })} unit="USD" />
          <Field label={t('ddr.totalDayCost')} value={costSummary.total_day} onChange={(v: string | number) => setCostSummary({ ...costSummary, total_day: v as number })} unit="USD" />
          <Field label={t('ddr.totalCumCost')} value={costSummary.total_cumulative} onChange={(v: string | number) => setCostSummary({ ...costSummary, total_cumulative: v as number })} unit="USD" />
        </div>
      </S>

      {/* Personnel on Location */}
      <S id="personnel" title={`${t('ddr.personnelSection')} (${((hsseData.personnel_companies as unknown[]) || []).length})`} icon={Users}>
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
              {((hsseData.personnel_companies as Record<string, string | number>[]) || []).map((c: Record<string, string | number>, i: number) => (
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
      </S>

      {/* Materials / Inventory */}
      <S id="materials" title={`${t('ddr.materialsSection')} (${((mudInventory.materials as unknown[]) || []).length})`} icon={Package}>
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
              {((mudInventory.materials as Record<string, string | number>[]) || []).map((m: Record<string, string | number>, i: number) => (
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
      </S>

      {/* Completion-specific */}
      {reportType === 'completion' && (
        <S id="completion" title={t('ddr.fracParams')} icon={Zap}>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Field label={t('ddr.fracPressure')} value={completionData.frac_pressure} onChange={(v: string | number) => setCompletionData({ ...completionData, frac_pressure: v as number })} unit="psi" />
            <Field label={t('ddr.fracRate')} value={completionData.pump_rate} onChange={(v: string | number) => setCompletionData({ ...completionData, pump_rate: v as number })} unit="bpm" />
            <Field label={t('ddr.proppantType')} value={completionData.proppant_type} onChange={(v: string | number) => setCompletionData({ ...completionData, proppant_type: v as string })} type="text" />
            <Field label={t('ddr.proppantVolume')} value={completionData.proppant_volume} onChange={(v: string | number) => setCompletionData({ ...completionData, proppant_volume: v as number })} unit="lb" />
            <Field label={t('ddr.fluidVolume')} value={completionData.fluid_volume} onChange={(v: string | number) => setCompletionData({ ...completionData, fluid_volume: v as number })} unit="bbl" />
            <Field label="ISIP" value={completionData.isip} onChange={(v: string | number) => setCompletionData({ ...completionData, isip: v as number })} unit="psi" />
            <Field label={t('ddr.closurePressure')} value={completionData.closure_pressure} onChange={(v: string | number) => setCompletionData({ ...completionData, closure_pressure: v as number })} unit="psi" />
            <Field label={t('ddr.acidType')} value={completionData.acid_type} onChange={(v: string | number) => setCompletionData({ ...completionData, acid_type: v as string })} type="text" />
          </div>
        </S>
      )}

      {/* Termination-specific */}
      {reportType === 'termination' && (
        <S id="termination" title={t('ddr.wellSummary')} icon={CheckCircle}>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Field label={t('ddr.wellheadType')} value={terminationData.wellhead_type} onChange={(v: string | number) => setTerminationData({ ...terminationData, wellhead_type: v as string })} type="text" />
            <Field label="X-mas Tree Type" value={terminationData.xmas_tree_type} onChange={(v: string | number) => setTerminationData({ ...terminationData, xmas_tree_type: v as string })} type="text" />
            <Field label="P&A Barriers" value={terminationData.pa_barriers} onChange={(v: string | number) => setTerminationData({ ...terminationData, pa_barriers: v as number })} />
            <Field label={t('ddr.cementPlugs')} value={terminationData.cement_plugs} onChange={(v: string | number) => setTerminationData({ ...terminationData, cement_plugs: v as number })} />
            <Field label={t('ddr.totalWellDays')} value={terminationData.total_well_days} onChange={(v: string | number) => setTerminationData({ ...terminationData, total_well_days: v as number })} />
            <Field label={t('ddr.finalStatus')} value={terminationData.final_status} onChange={(v: string | number) => setTerminationData({ ...terminationData, final_status: v as string })} type="text" />
          </div>
        </S>
      )}

      {/* Action buttons */}
      <div className="flex gap-3 sticky bottom-0 bg-gradient-to-t from-black/80 via-black/60 to-transparent pt-6 pb-2">
        <button onClick={() => onSave('draft')} disabled={loading} className="flex items-center gap-2 px-5 py-2.5 bg-white/5 hover:bg-white/10 rounded-xl text-sm font-bold transition-all disabled:opacity-50">
          <Save size={16} /> {loading ? '...' : t('ddr.saveDraft')}
        </button>
        <button onClick={() => onSave('submitted')} disabled={loading} className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 rounded-xl text-sm font-bold transition-all disabled:opacity-50 shadow-lg">
          <Send size={16} /> {t('ddr.submitReport')}
        </button>
        {editingId && (
          <>
            <button onClick={onExportPDF} disabled={isGeneratingPDF} className="flex items-center gap-2 px-5 py-2.5 bg-green-600/20 hover:bg-green-600/30 border border-green-500/30 rounded-xl text-sm font-bold text-green-400 transition-all disabled:opacity-50">
              <Download size={16} /> {isGeneratingPDF ? '...' : t('ddr.exportPDF')}
            </button>
            <button onClick={onCancel} className="px-5 py-2.5 bg-white/5 hover:bg-white/10 rounded-xl text-sm font-bold text-white/40 transition-all">
              {t('common.cancel')}
            </button>
          </>
        )}
      </div>
    </motion.div>
  );
};

export default DDRForm;
