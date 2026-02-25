/**
 * DailyReportsModule.tsx — DDR / Operations Reports Module (Orchestrator)
 * Composes: DDRForm, DDRKPIDashboard, DDRListView + AI analysis + well selector + tabs
 */
import React, { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { useLanguage } from '../hooks/useLanguage';
import { useAIAnalysis } from '../hooks/useAIAnalysis';
import { useToast } from './ui/Toast';
import api from '../lib/api';
import { motion } from 'framer-motion';
import { ClipboardList, Plus, BarChart3, Activity, Database } from 'lucide-react';
import AIAnalysisPanel from './AIAnalysisPanel';
import DDRReportPDF from './DDRReportPDF';
// @ts-ignore — html2pdf has no types
import html2pdf from 'html2pdf.js';
import type { APIError } from '../types/api';
import DDRForm, { emptyOperation, emptyBHA } from './ddr/DDRForm';
import DDRKPIDashboard from './ddr/DDRKPIDashboard';
import DDRListView from './ddr/DDRListView';
import type { ReportListItem } from './ddr/DDRListView';

const DailyReportsModule: React.FC = () => {
  const { t } = useTranslation();
  useLanguage(); // kept for language reactivity
  const { addToast } = useToast();

  // ── Well management ──
  const [wells, setWells] = useState<{id: number; name: string; location?: string}[]>([]);
  const [selectedReportWell, setSelectedReportWell] = useState<{id: number; name: string} | null>(null);
  const [wellsLoading, setWellsLoading] = useState(true);
  const [isCreatingWell, setIsCreatingWell] = useState(false);
  const [newWellName, setNewWellName] = useState('');
  const wellId = selectedReportWell?.id;
  const wellName = selectedReportWell?.name || '';

  const { aiAnalysis, isAnalyzing, runAnalysis, provider, setProvider, availableProviders } = useAIAnalysis({ module: 'daily-reports', wellId, wellName });

  useEffect(() => {
    (async () => {
      try { setWells((await api.get(`/wells`)).data); }
      catch (e) { console.error('Error fetching wells:', e); }
      finally { setWellsLoading(false); }
    })();
  }, []);

  const handleCreateWell = async () => {
    if (!newWellName.trim()) return;
    try {
      const newWell = (await api.post(`/wells?name=${encodeURIComponent(newWellName.trim())}`)).data;
      setWells(prev => [...prev, newWell]);
      setSelectedReportWell({ id: newWell.id, name: newWell.name });
      setNewWellName(''); setIsCreatingWell(false);
      addToast(t('ddr.wellCreated'), 'success');
    } catch (e: unknown) {
      addToast('Error: ' + ((e as APIError).response?.data?.detail || (e as APIError).message || 'Unknown error'), 'error');
    }
  };

  // ── Tab / loading ──
  const [activeTab, setActiveTab] = useState('reports');
  const [loading, setLoading] = useState(false);

  // ── Reports list ──
  const [reports, setReports] = useState<ReportListItem[]>([]);
  const [filterType, setFilterType] = useState('');

  // ── Form state ──
  const [editingId, setEditingId] = useState<number | null>(null);
  const [reportType, setReportType] = useState('drilling');
  const [reportDate, setReportDate] = useState(new Date().toISOString().split('T')[0]);
  const [depthStart, setDepthStart] = useState(0);
  const [depthEnd, setDepthEnd] = useState(0);
  const [depthTvd, setDepthTvd] = useState(0);
  const [headerData, setHeaderData] = useState<Record<string, unknown>>({});
  const [operations, setOperations] = useState([emptyOperation()]);
  const [drillingParams, setDrillingParams] = useState<Record<string, string | number>>({});
  const [mudProps, setMudProps] = useState<Record<string, string | number>>({});
  const [mudInventory, setMudInventory] = useState<Record<string, unknown>>({});
  const [bhaData, setBhaData] = useState([emptyBHA()]);
  const [gasMonitoring, setGasMonitoring] = useState<Record<string, string | number>>({});
  const [nptEvents, setNptEvents] = useState<Record<string, string | number>[]>([]);
  const [hsseData, setHsseData] = useState<Record<string, unknown>>({});
  const [costSummary, setCostSummary] = useState<Record<string, string | number>>({});
  const [completionData, setCompletionData] = useState<Record<string, string | number>>({});
  const [terminationData, setTerminationData] = useState<Record<string, string | number>>({});
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['header', 'operations']));

  // ── KPI data ──
  const [timeDepthData, setTimeDepthData] = useState<Record<string, number>[]>([]);
  const [costData, setCostData] = useState<Record<string, number>[]>([]);
  const [nptBreakdown, setNptBreakdown] = useState<Record<string, unknown>>({});
  const [cumulativeStats, setCumulativeStats] = useState<Record<string, number>>({});

  // ── Reference data ──
  const [iadcCodes, setIadcCodes] = useState<Record<string, string>>({});
  const [, setNptCodes] = useState<Record<string, string>>({});
  const [opCategories, setOpCategories] = useState<string[]>([]);

  // ── PDF ──
  const pdfRef = useRef<HTMLDivElement>(null);
  const [isGeneratingPDF, setIsGeneratingPDF] = useState(false);

  // ── Data fetching ──
  useEffect(() => { fetchReports(); fetchReferenceData(); }, [wellId]);
  useEffect(() => { if (activeTab === 'kpis') fetchKPIs(); }, [activeTab, wellId]);

  const fetchReports = async () => {
    if (!wellId) return;
    try { setReports((await api.get(filterType ? `/wells/${wellId}/daily-reports?report_type=${filterType}` : `/wells/${wellId}/daily-reports`)).data); }
    catch (e) { console.error('Error fetching reports:', e); }
  };
  const fetchReferenceData = async () => {
    try {
      const [iadc, npt, cats] = await Promise.all([api.get(`/ddr/iadc-codes`), api.get(`/ddr/npt-codes`), api.get(`/ddr/operation-categories`)]);
      setIadcCodes(iadc.data); setNptCodes(npt.data); setOpCategories(cats.data);
    } catch (e) { console.error('Error fetching ref data:', e); }
  };
  const fetchKPIs = async () => {
    if (!wellId) return;
    try {
      const [td, cost, npt, stats] = await Promise.all([api.get(`/wells/${wellId}/daily-reports/time-depth`), api.get(`/wells/${wellId}/daily-reports/cost-tracking`), api.get(`/wells/${wellId}/daily-reports/npt-breakdown`), api.get(`/wells/${wellId}/daily-reports/stats`)]);
      setTimeDepthData(td.data); setCostData(cost.data.daily_costs || []); setNptBreakdown(npt.data); setCumulativeStats(stats.data);
    } catch (e) { console.error('Error fetching KPIs:', e); }
  };

  const toggleSection = (s: string) => { const next = new Set(expandedSections); next.has(s) ? next.delete(s) : next.add(s); setExpandedSections(next); };

  const resetForm = () => {
    setEditingId(null); setReportDate(new Date().toISOString().split('T')[0]);
    setDepthStart(0); setDepthEnd(0); setDepthTvd(0);
    setHeaderData({}); setOperations([emptyOperation()]); setDrillingParams({}); setMudProps({});
    setMudInventory({}); setBhaData([emptyBHA()]); setGasMonitoring({}); setNptEvents([]);
    setHsseData({}); setCostSummary({}); setCompletionData({}); setTerminationData({});
  };

  // ── CRUD ──
  const saveReport = async (status: string = 'draft') => {
    if (!wellId) return;
    setLoading(true);
    const payload: Record<string, unknown> = {
      report_type: reportType, report_date: reportDate,
      depth_md_start: depthStart || null, depth_md_end: depthEnd || null, depth_tvd: depthTvd || null,
      header_data: headerData, operations_log: operations.filter(o => o.description || o.iadc_code),
      drilling_params: drillingParams, mud_properties: mudProps, mud_inventory: mudInventory,
      bha_data: bhaData.filter(b => b.component_type), gas_monitoring: gasMonitoring,
      npt_events: nptEvents, hsse_data: hsseData, cost_summary: costSummary,
      completion_data: reportType === 'completion' ? completionData : null,
      termination_data: reportType === 'termination' ? terminationData : null, status,
    };
    try {
      editingId ? await api.put(`/wells/${wellId}/daily-reports/${editingId}`, payload) : await api.post(`/wells/${wellId}/daily-reports`, payload);
      fetchReports();
      if (status !== 'draft') { resetForm(); setActiveTab('reports'); }
    } catch (e: unknown) { addToast('Error: ' + ((e as APIError).response?.data?.detail || (e as APIError).message || 'Unknown error'), 'error'); }
    setLoading(false);
  };

  const deleteReport = async (id: number) => {
    if (!wellId || !confirm(t('ddr.confirmDelete') || 'Delete this report?')) return;
    try { await api.delete(`/wells/${wellId}/daily-reports/${id}`); fetchReports(); } catch (e) { console.error(e); }
  };

  const loadReport = async (id: number) => {
    if (!wellId) return;
    try {
      const r = (await api.get(`/wells/${wellId}/daily-reports/${id}`)).data;
      setEditingId(r.id); setReportType(r.report_type); setReportDate(r.report_date);
      setDepthStart(r.depth_md_start || 0); setDepthEnd(r.depth_md_end || 0); setDepthTvd(r.depth_tvd || 0);
      setHeaderData(r.header_data || {}); setOperations(r.operations_log?.length ? r.operations_log : [emptyOperation()]);
      setDrillingParams(r.drilling_params || {}); setMudProps(r.mud_properties || {});
      setMudInventory(r.mud_inventory || {}); setBhaData(r.bha_data?.length ? r.bha_data : [emptyBHA()]);
      setGasMonitoring(r.gas_monitoring || {}); setNptEvents(r.npt_events || []); setHsseData(r.hsse_data || {});
      setCostSummary(r.cost_summary || {}); setCompletionData(r.completion_data || {}); setTerminationData(r.termination_data || {});
      setActiveTab('newDDR');
    } catch (e) { console.error(e); }
  };

  const handleExportPDF = async () => {
    const el = pdfRef.current; if (!el) return;
    setIsGeneratingPDF(true);
    try {
      el.style.display = 'block';
      const reportNum = editingId ? reports.find(r => r.id === editingId)?.report_number || 0 : 0;
      await html2pdf().set({ margin: 10, filename: `DDR_${wellName || 'Well'}_Report-${reportNum}_${reportDate}.pdf`, image: { type: 'jpeg' as const, quality: 0.98 }, html2canvas: { scale: 2, useCORS: true }, jsPDF: { unit: 'mm' as const, format: 'a4' as const, orientation: 'portrait' as const } }).from(el).save();
    } catch (err) { console.error('PDF generation error:', err); }
    finally { if (pdfRef.current) pdfRef.current.style.display = 'none'; setIsGeneratingPDF(false); }
  };

  const handleRunAnalysis = async () => {
    if (!wellId || reports.length === 0) return;
    try { runAnalysis((await api.get(`/wells/${wellId}/daily-reports/${reports[0].id}`)).data, { report_type: reports[0].report_type }); } catch { /* handled internally */ }
  };

  const handleFilterChange = (ft: string) => { setFilterType(ft); setTimeout(fetchReports, 50); };

  const tabs = [
    { id: 'reports', label: t('ddr.reports'), icon: ClipboardList },
    { id: 'newDDR', label: editingId ? t('ddr.editReport') || 'Edit Report' : t('ddr.newDDR'), icon: Plus },
    { id: 'kpis', label: t('ddr.kpis'), icon: BarChart3 },
    { id: 'analysis', label: t('ddr.aiAnalysis'), icon: Activity },
  ];

  return (
    <div className="space-y-6">
      {/* Well Selector Bar */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-blue-500/10 rounded-xl border border-blue-500/20"><ClipboardList size={22} className="text-blue-400" /></div>
          <div><h2 className="text-xl font-bold">{t('modules.dailyReports')}</h2><p className="text-white/30 text-xs">{t('ddr.operationalReports')}</p></div>
        </div>
        <div className="flex items-center gap-3">
          <select value={selectedReportWell?.id ?? ''} onChange={(e) => { const id = parseInt(e.target.value); const well = wells.find(w => w.id === id); setSelectedReportWell(well ? { id: well.id, name: well.name } : null); }} className="bg-white/5 border border-white/10 rounded-xl px-4 py-2 text-sm text-white/70 focus:outline-none focus:border-blue-500 min-w-[220px]" disabled={wellsLoading}>
            <option value="">{wellsLoading ? t('common.loading') : t('ddr.selectAWell')}</option>
            {wells.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
          </select>
          <button onClick={() => setIsCreatingWell(!isCreatingWell)} className="flex items-center gap-1.5 px-3 py-2 bg-blue-600/20 hover:bg-blue-600/30 border border-blue-500/30 rounded-xl text-xs font-bold text-blue-400 transition-all"><Plus size={14} /> {t('ddr.newWell')}</button>
        </div>
      </div>

      {isCreatingWell && (
        <div className="bg-white/5 p-4 rounded-xl border border-blue-500/20 flex items-center gap-3">
          <input type="text" value={newWellName} onChange={(e) => setNewWellName(e.target.value)} placeholder="e.g. WELL-X106-OFFSHORE" className="bg-white/5 border border-white/10 rounded-lg flex-1 py-2 px-3 text-sm text-white focus:outline-none focus:border-blue-500" autoFocus onKeyDown={(e) => e.key === 'Enter' && handleCreateWell()} />
          <button onClick={handleCreateWell} className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-xs font-bold text-white transition-colors">{t('well.createProject')}</button>
          <button onClick={() => { setIsCreatingWell(false); setNewWellName(''); }} className="px-3 py-2 bg-white/5 hover:bg-white/10 rounded-lg text-xs text-white/40">{t('common.cancel')}</button>
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
          <div className="flex items-center gap-2 text-xs text-white/40"><Database size={14} /><span>{t('ddr.activeWell')} <span className="text-white/70 font-bold">{wellName}</span></span></div>

          <div className="flex gap-2 flex-wrap">
            {tabs.map(tab => (
              <button key={tab.id} onClick={() => { if (tab.id === 'newDDR' && !editingId) resetForm(); setActiveTab(tab.id); }} className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-bold transition-all ${activeTab === tab.id ? 'bg-blue-600 text-white shadow-lg' : 'bg-white/5 text-white/40 hover:bg-white/10 hover:text-white/60'}`}>
                <tab.icon size={16} />{tab.label}
              </button>
            ))}
          </div>

          {activeTab === 'reports' && <DDRListView reports={reports} filterType={filterType} onFilterChange={handleFilterChange} onEdit={loadReport} onDelete={deleteReport} />}

          {activeTab === 'newDDR' && (
            <DDRForm reportType={reportType} setReportType={setReportType} reportDate={reportDate} setReportDate={setReportDate}
              depthStart={depthStart} setDepthStart={setDepthStart} depthEnd={depthEnd} setDepthEnd={setDepthEnd}
              depthTvd={depthTvd} setDepthTvd={setDepthTvd} headerData={headerData} setHeaderData={setHeaderData}
              operations={operations} setOperations={setOperations} drillingParams={drillingParams} setDrillingParams={setDrillingParams}
              mudProps={mudProps} setMudProps={setMudProps} mudInventory={mudInventory} setMudInventory={setMudInventory}
              bhaData={bhaData} setBhaData={setBhaData} gasMonitoring={gasMonitoring} setGasMonitoring={setGasMonitoring}
              nptEvents={nptEvents} hsseData={hsseData} setHsseData={setHsseData}
              costSummary={costSummary} setCostSummary={setCostSummary} completionData={completionData} setCompletionData={setCompletionData}
              terminationData={terminationData} setTerminationData={setTerminationData}
              expandedSections={expandedSections} toggleSection={toggleSection} iadcCodes={iadcCodes} opCategories={opCategories}
              editingId={editingId} loading={loading} isGeneratingPDF={isGeneratingPDF}
              onSave={saveReport} onExportPDF={handleExportPDF} onCancel={() => { resetForm(); setActiveTab('reports'); }} />
          )}

          {activeTab === 'kpis' && <DDRKPIDashboard cumulativeStats={cumulativeStats} timeDepthData={timeDepthData} costData={costData} nptBreakdown={nptBreakdown} operations={operations} hasReports={reports.length > 0} latestReportId={reports.length > 0 ? reports[0].id : null} />}

          {activeTab === 'analysis' && (
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
              {reports.length > 0 ? (
                <AIAnalysisPanel moduleName={t('modules.dailyReports')} moduleIcon={ClipboardList} wellName={wellName}
                  analysis={aiAnalysis?.analysis || null} confidence={aiAnalysis?.confidence || 'LOW'} agentRole={aiAnalysis?.agent_role || ''}
                  isLoading={isAnalyzing} keyMetrics={aiAnalysis?.key_metrics || []} onAnalyze={handleRunAnalysis}
                  provider={provider} onProviderChange={setProvider} availableProviders={availableProviders} />
              ) : (
                <div className="glass-panel p-12 text-center"><Activity size={48} className="mx-auto text-white/10 mb-4" /><p className="text-white/30 text-sm">{t('ddr.noReportsForAnalysis') || 'Create at least one report to enable AI analysis.'}</p></div>
              )}
            </motion.div>
          )}

          <DDRReportPDF ref={pdfRef} wellName={wellName} reportNumber={editingId ? (reports.find(r => r.id === editingId)?.report_number || 0) : 0}
            reportDate={reportDate} reportType={reportType} depthStart={depthStart} depthEnd={depthEnd} depthTVD={depthTvd}
            headerData={headerData} operations={operations} drillingParams={drillingParams} mudProperties={mudProps}
            bhaData={bhaData} gasMonitoring={gasMonitoring} costSummary={costSummary} hsseData={hsseData}
            mudInventory={mudInventory} completionData={completionData} terminationData={terminationData}
            status={editingId ? (reports.find(r => r.id === editingId)?.status || 'draft') : 'draft'} />
        </>
      )}
    </div>
  );
};

export default DailyReportsModule;
