import React, { useState, useEffect } from 'react';
import api from '../lib/api';
import {
    Check,
    Terminal,
    ChevronRight,
    BrainCircuit,
    ShieldCheck,
    AlertTriangle,
    FileText,
    Zap,
    Loader2,
    RotateCcw,
    ArrowLeft
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import RCAVisualizer from './RCAVisualizer';
import { useToast } from './ui/Toast';

// @ts-ignore
import html2pdf from 'html2pdf.js';

interface CompletedAnalysis {
    role: string;
    confidence: string;
    agent: string;
    analysis?: string;
}

interface AnalysisDashboardProps {
    analysisId: number;
    workflow: string[];
    onBack?: () => void;
}

const AnalysisDashboard: React.FC<AnalysisDashboardProps> = ({ analysisId, workflow, onBack }) => {
    const { t } = useTranslation();
    const { addToast } = useToast();

    // RCA State
    const [rcaReport, setRcaReport] = useState<Record<string, unknown> | null>(null);
    const [isGeneratingRCA, setIsGeneratingRCA] = useState(false);

    // Pipeline State
    const [currentStep, setCurrentStep] = useState(0);
    const [query, setQuery] = useState<Record<string, unknown> | null>(null);
    const [isProcessing, setIsProcessing] = useState(false);
    const [completedAnalyses, setCompletedAnalyses] = useState<CompletedAnalysis[]>([]);
    const [isSynthesisMode, setIsSynthesisMode] = useState(false);
    const [finalReport, setFinalReport] = useState<Record<string, unknown> | null>(null);
    const [isGeneratingPDF, setIsGeneratingPDF] = useState(false);
    const [isAutoRunAll, setIsAutoRunAll] = useState(false);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);
    const [expandedAgent, setExpandedAgent] = useState<string | null>(null);

    // Event ID for RCA
    const [eventId, setEventId] = useState<number | null>(null);

    useEffect(() => {
        const fetchAnalysisDetails = async () => {
            try {
                const res = await api.get(`/analysis/${analysisId}`);
                // Try direct event_id first, fallback to legacy bridge
                if (res.data?.event_id) {
                    setEventId(res.data.event_id);
                } else if (res.data?.problem?.additional_data?.event_id) {
                    setEventId(res.data.problem.additional_data.event_id);
                }
            } catch (e) {
                console.warn("Could not load event ID for RCA:", e);
            }
        };
        fetchAnalysisDetails();
    }, [analysisId]);

    useEffect(() => {
        if (currentStep < workflow.length) {
            fetchQuery(workflow[currentStep]);
        } else if (!isSynthesisMode) {
            fetchSynthesisQuery();
        }
    }, [currentStep, workflow]);

    const fetchQuery = async (agentId: string) => {
        try {
            setErrorMessage(null);
            const response = await api.get(`/analysis/${analysisId}/agent/${agentId}/query`);
            setQuery(response.data);
        } catch (error) {
            const msg = `${t('analysis.errorLoadingQuery')} ${agentId.replace(/_/g, ' ')}`;
            setErrorMessage(msg);
            addToast(msg, 'error');
        }
    };

    const fetchSynthesisQuery = async () => {
        try {
            setErrorMessage(null);
            setIsSynthesisMode(true);
            const response = await api.get(`/analysis/${analysisId}/synthesis/query`);
            setQuery(response.data);
        } catch (error) {
            const msg = t('analysis.errorLoadingSynthesis');
            setErrorMessage(msg);
            addToast(msg, 'error');
        }
    };

    const handleAutoRun = async () => {
        setIsProcessing(true);
        setErrorMessage(null);
        try {
            if (!isSynthesisMode) {
                const agentId = workflow[currentStep];
                const res = await api.post(`/analysis/${analysisId}/agent/${agentId}/auto`);
                setCompletedAnalyses(prev => [...prev, {
                    role: query?.role || agentId,
                    confidence: res.data.confidence || 'MEDIUM',
                    agent: agentId,
                    analysis: res.data.analysis
                }]);
                addToast(`${(query?.role || agentId).replace(/_/g, ' ')} ${t('analysis.completed')}`, 'success', 3000);
                setCurrentStep(prev => prev + 1);
            } else {
                const res = await api.post(`/analysis/${analysisId}/synthesis/auto`);
                setFinalReport(res.data.analysis);
                addToast(t('analysis.synthesisCompleted'), 'success');
            }
        } catch (error) {
            const agentName = isSynthesisMode ? t('analysis.synthesis') : (query?.role || workflow[currentStep]);
            const msg = `${t('analysis.errorRunning')} ${agentName}: ${error instanceof Error ? error.message : t('analysis.serverError')}`;
            setErrorMessage(msg);
            addToast(msg, 'error', 8000);
        } finally {
            setIsProcessing(false);
        }
    };

    const handleRunAll = async () => {
        setIsAutoRunAll(true);
        setErrorMessage(null);
        for (let i = currentStep; i < workflow.length; i++) {
            try {
                setIsProcessing(true);
                const agentId = workflow[i];
                const queryRes = await api.get(`/analysis/${analysisId}/agent/${agentId}/query`);
                setQuery(queryRes.data);
                const res = await api.post(`/analysis/${analysisId}/agent/${agentId}/auto`);
                setCompletedAnalyses(prev => [...prev, {
                    role: queryRes.data?.role || agentId,
                    confidence: res.data.confidence || 'MEDIUM',
                    agent: agentId,
                    analysis: res.data.analysis
                }]);
                setCurrentStep(i + 1);
            } catch (error) {
                const msg = `${t('analysis.errorInAgent')} ${workflow[i].replace(/_/g, ' ')}. ${t('analysis.pipelineStopped')}`;
                setErrorMessage(msg);
                addToast(msg, 'error', 8000);
                setIsProcessing(false);
                setIsAutoRunAll(false);
                return;
            }
        }
        // Run synthesis
        try {
            setIsSynthesisMode(true);
            const synthQuery = await api.get(`/analysis/${analysisId}/synthesis/query`);
            setQuery(synthQuery.data);
            const res = await api.post(`/analysis/${analysisId}/synthesis/auto`);
            setFinalReport(res.data.analysis);
            addToast(t('analysis.pipelineComplete'), 'success');
        } catch (error) {
            const msg = t('analysis.errorGeneratingSynthesis');
            setErrorMessage(msg);
            addToast(msg, 'error', 8000);
        } finally {
            setIsProcessing(false);
            setIsAutoRunAll(false);
        }
    };

    const handleGenerateRCA = async () => {
        if (!eventId) return;
        setIsGeneratingRCA(true);
        try {
            const res = await api.post(`/events/${eventId}/rca`);
            setRcaReport(res.data);
            addToast(t('analysis.rcaGenerated'), 'success');
        } catch (error) {
            addToast(t('analysis.errorGeneratingRCA'), 'error');
        } finally {
            setIsGeneratingRCA(false);
        }
    };

    const generatePDFConfig = () => ({
        margin: 10,
        filename: `PetroExpert_Analysis_${analysisId}.pdf`,
        image: { type: 'jpeg', quality: 0.98 },
        html2canvas: { scale: 2, useCORS: true },
        jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
    });

    const handleSavePDF = async () => {
        setIsGeneratingPDF(true);
        try {
            const element = document.querySelector('.print-report-container');
            if (element) {
                element.classList.add('pdf-generation');
                const header = element.querySelector('.print-header');
                if (header) header.classList.remove('hidden');
                const opt = generatePDFConfig();
                // @ts-ignore
                await html2pdf().set(opt).from(element).save();
                if (header) header.classList.add('hidden');
                element.classList.remove('pdf-generation');
            }
        } catch (error) {
            console.error("Error generating PDF:", error);
        } finally {
            setIsGeneratingPDF(false);
        }
    };

    // --- RENDER: Final Report with Synthesis ---
    if (finalReport) {
        return (
            <div className="animate-fadeIn max-w-5xl mx-auto py-12 space-y-8">
                <style>{`
                    .pdf-generation { background-color: white !important; color: black !important; }
                    .pdf-generation .prose { color: black !important; }
                `}</style>

                {/* Back Navigation */}
                {onBack && (
                    <div>
                        <button
                            onClick={onBack}
                            className="flex items-center gap-2 text-sm text-white/40 hover:text-white transition-colors group"
                        >
                            <ArrowLeft size={16} className="group-hover:-translate-x-1 transition-transform" />
                            {t('analysis.backToWizard')}
                        </button>
                    </div>
                )}

                {/* Completed Agents Summary */}
                {completedAnalyses.length > 0 && (
                    <div className="glass-panel p-6">
                        <h3 className="text-sm font-bold uppercase tracking-widest text-green-400 mb-4 flex items-center gap-2">
                            <Check size={16} /> {t('analysis.specialistsConsulted')} ({completedAnalyses.length})
                        </h3>
                        <div className="flex flex-wrap gap-2">
                            {completedAnalyses.map((a, i) => (
                                <span key={i} className="px-3 py-1 rounded-full text-xs font-bold border text-green-400 bg-green-500/10 border-green-500/30">
                                    {a.role}
                                </span>
                            ))}
                        </div>
                    </div>
                )}

                {/* Synthesis Report */}
                <div className="glass-panel p-8 print-report-container">
                    <div className="hidden print-header">
                        <div className="print-header-logo">
                            PETROEXPERT <span className="text-sm font-normal text-gray-500">System v3.0 Elite</span>
                        </div>
                        <div className="print-header-meta">
                            <p>Generated: {new Date().toLocaleDateString()}</p>
                            <p>Analysis ID: #{analysisId}</p>
                        </div>
                    </div>

                    <div className="flex items-center gap-4 mb-8">
                        <div className="w-12 h-12 bg-green-500/10 border border-green-500/20 rounded-full flex items-center justify-center text-green-500">
                            <ShieldCheck size={24} />
                        </div>
                        <div>
                            <h2 className="text-2xl font-bold">{t('analysis.executiveSynthesis')}</h2>
                            <p className="text-white/40">{t('analysis.multiAgentCompleted')}</p>
                        </div>
                    </div>

                    <div className="prose prose-invert max-w-none bg-black/30 p-8 rounded-2xl border border-white/5 whitespace-pre-wrap font-sans text-white/80 leading-relaxed max-h-[500px] overflow-y-auto custom-scrollbar">
                        {finalReport}
                    </div>

                    <div className="mt-8 flex justify-end gap-4">
                        <button className="btn-secondary" onClick={handleSavePDF} disabled={isGeneratingPDF}>
                            <FileText size={18} />
                            {isGeneratingPDF ? t('analysis.generatingPDF') : t('analysis.savePDF')}
                        </button>

                        {eventId && !rcaReport && (
                            <button
                                onClick={handleGenerateRCA}
                                disabled={isGeneratingRCA}
                                className="btn-primary bg-red-600 hover:bg-red-500 shadow-red-900/40"
                            >
                                {isGeneratingRCA ? (
                                    <><Loader2 size={18} className="animate-spin" /> {t('analysis.generatingRCA')}</>
                                ) : (
                                    <><AlertTriangle size={18} /> {t('analysis.generateRCA')}</>
                                )}
                            </button>
                        )}
                    </div>
                </div>

                {/* RCA Section */}
                {rcaReport && (
                    <div className="animate-fadeIn">
                        <div className="flex items-center gap-4 mb-6">
                            <div className="w-12 h-12 bg-red-500/10 border border-red-500/20 rounded-full flex items-center justify-center text-red-500">
                                <AlertTriangle size={24} />
                            </div>
                            <div>
                                <h2 className="text-2xl font-bold">{t('analysis.investigationFindings')}</h2>
                                <p className="text-white/40">{t('analysis.rcaStructured')}</p>
                            </div>
                        </div>
                        <RCAVisualizer report={rcaReport} />
                    </div>
                )}
            </div>
        );
    }

    // --- RENDER: Pipeline View ---
    return (
        <div className="w-full mx-auto pb-20">
            {/* Back Navigation */}
            {onBack && (
                <div className="mb-6">
                    <button
                        onClick={onBack}
                        className="flex items-center gap-2 text-sm text-white/40 hover:text-white transition-colors group"
                    >
                        <ArrowLeft size={16} className="group-hover:-translate-x-1 transition-transform" />
                        {t('analysis.backToWizard')}
                    </button>
                </div>
            )}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Left Column: Progress */}
                <div className="lg:col-span-1 space-y-6">
                    <div className="glass-panel p-6">
                        <h3 className="text-sm font-bold uppercase tracking-widest text-industrial-500 mb-4 flex items-center gap-2">
                            <BrainCircuit size={16} />
                            {t('analysis.specialistPipeline')}
                        </h3>

                        {/* Progress Bar */}
                        <div className="mb-4">
                            <div className="flex justify-between text-xs text-white/40 mb-1">
                                <span>{t('analysis.progress')}</span>
                                <span>{Math.min(currentStep, workflow.length)} / {workflow.length}</span>
                            </div>
                            <div className="w-full h-1.5 bg-white/5 rounded-full overflow-hidden">
                                <div
                                    className="h-full bg-industrial-500 rounded-full transition-all duration-500"
                                    style={{ width: `${(Math.min(currentStep, workflow.length) / workflow.length) * 100}%` }}
                                />
                            </div>
                        </div>

                        <div className="space-y-3">
                            {workflow.map((agent, index) => {
                                const completed = completedAnalyses.find(a => a.agent === agent);
                                return (
                                    <div key={`${agent}-${index}`} className={`flex items-center gap-3 p-3 rounded-xl transition-all ${
                                        index === currentStep && !isSynthesisMode ? 'bg-industrial-600/10 border border-industrial-600/20 text-white' :
                                        index < currentStep ? 'text-green-400' : 'text-white/20'
                                    }`}>
                                        <div className={`w-8 h-8 rounded-lg flex items-center justify-center border ${
                                            index === currentStep && !isSynthesisMode ? 'border-industrial-500 bg-industrial-500/10' :
                                            index < currentStep ? 'border-green-500 bg-green-500/10' : 'border-white/5 bg-white/5'
                                        }`}>
                                            {index < currentStep ? <Check size={14} /> : <span>{index + 1}</span>}
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className="text-xs font-bold uppercase truncate">{agent.replace(/_/g, ' ')}</p>
                                            {index === currentStep && !isSynthesisMode && (
                                                <span className="text-[10px] text-industrial-400 animate-pulse">{t('analysis.analyzing')}</span>
                                            )}
                                        </div>
                                        {completed && (
                                            <span className="px-2 py-0.5 rounded text-[10px] font-bold border text-green-400 bg-green-500/10 border-green-500/30">
                                                ✓
                                            </span>
                                        )}
                                    </div>
                                );
                            })}

                            {/* Synthesis step */}
                            <div className={`flex items-center gap-3 p-3 rounded-xl transition-all ${
                                isSynthesisMode ? 'bg-industrial-600/10 border border-industrial-600/20 text-white' : 'text-white/20'
                            }`}>
                                <div className={`w-8 h-8 rounded-lg flex items-center justify-center border ${
                                    isSynthesisMode ? 'border-industrial-500 bg-industrial-500/10' : 'border-white/5 bg-white/5'
                                }`}>
                                    <Terminal size={14} />
                                </div>
                                <div>
                                    <p className="text-xs font-bold uppercase">{t('analysis.finalSynthesis')}</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Right Column: Agent Execution */}
                <div className="lg:col-span-2 space-y-6">
                    {/* Error Banner */}
                    {errorMessage && (
                        <div
                            className="animate-fadeIn bg-red-500/10 border border-red-500/30 rounded-xl p-4 flex items-center gap-3"
                        >
                            <AlertTriangle size={20} className="text-red-400 shrink-0" />
                            <p className="text-sm text-red-300 flex-1">{errorMessage}</p>
                            <button
                                onClick={() => { setErrorMessage(null); handleAutoRun(); }}
                                className="text-xs text-red-400 hover:text-red-300 flex items-center gap-1 shrink-0"
                            >
                                <RotateCcw size={12} /> {t('common.retry')}
                            </button>
                        </div>
                    )}

                    {/* Completed Analyses - Expandable */}
                    {completedAnalyses.length > 0 && (
                        <div className="space-y-2">
                            {completedAnalyses.map((a, i) => (
                                <div key={`${a.agent}-${i}`} className="glass-panel overflow-hidden">
                                    <button
                                        onClick={() => setExpandedAgent(expandedAgent === a.agent ? null : a.agent)}
                                        className="w-full flex items-center gap-3 p-4 text-left hover:bg-white/5 transition-colors"
                                    >
                                        <div className="w-6 h-6 rounded-full bg-green-500/20 border border-green-500/30 flex items-center justify-center">
                                            <Check size={12} className="text-green-400" />
                                        </div>
                                        <span className="text-sm font-bold flex-1">{a.role}</span>
                                        <ChevronRight size={14} className={`text-white/30 transition-transform ${expandedAgent === a.agent ? 'rotate-90' : ''}`} />
                                    </button>
                                    <AnimatePresence>
                                        {expandedAgent === a.agent && a.analysis && (
                                            <motion.div
                                                initial={{ height: 0, opacity: 0 }}
                                                animate={{ height: 'auto', opacity: 1 }}
                                                exit={{ height: 0, opacity: 0 }}
                                                className="overflow-hidden"
                                            >
                                                <div className="px-4 pb-4 pt-0">
                                                    <div className="bg-black/30 rounded-xl p-4 text-sm text-white/70 whitespace-pre-wrap max-h-60 overflow-y-auto custom-scrollbar leading-relaxed">
                                                        {a.analysis}
                                                    </div>
                                                </div>
                                            </motion.div>
                                        )}
                                    </AnimatePresence>
                                </div>
                            ))}
                        </div>
                    )}

                    <AnimatePresence mode="wait">
                        <motion.div
                            key={currentStep + (isSynthesisMode ? 'synth' : 'step')}
                            initial={{ opacity: 0, x: 20 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: -20 }}
                            className="space-y-6"
                        >
                            {query && (
                                <div className="glass-panel p-12 flex flex-col items-center justify-center text-center space-y-6">
                                    <div className="w-20 h-20 bg-industrial-600/20 rounded-full flex items-center justify-center text-industrial-500 relative">
                                        <BrainCircuit size={40} className={isProcessing ? "animate-pulse" : ""} />
                                        {isProcessing && (
                                            <div className="absolute inset-0 border-4 border-industrial-500 border-t-transparent rounded-full animate-spin" />
                                        )}
                                    </div>
                                    <div>
                                        <h3 className="text-xl font-bold mb-2">
                                            {isProcessing
                                                ? t('analysis.agentAnalyzing')
                                                : `${t('analysis.readyToQuery')} ${isSynthesisMode ? t('analysis.synthesis') : query.role}`}
                                        </h3>
                                        <p className="text-sm text-white/40 max-w-md">
                                            {isProcessing
                                                ? t('analysis.processingDescription')
                                                : t('analysis.clickToExecute')}
                                        </p>
                                    </div>

                                    <div className="flex gap-3">
                                        <button
                                            onClick={handleAutoRun}
                                            disabled={isProcessing || isAutoRunAll}
                                            className="btn-primary h-12 px-8 text-base shadow-xl shadow-industrial-900/40 disabled:opacity-50"
                                        >
                                            {isProcessing ? (
                                                <><Loader2 size={18} className="animate-spin" /> {t('analysis.processing')}</>
                                            ) : (
                                                <>{isSynthesisMode ? t('analysis.runSynthesis') : t('analysis.runStep')} <Zap size={18} /></>
                                            )}
                                        </button>

                                        {!isSynthesisMode && currentStep < workflow.length && (
                                            <button
                                                onClick={handleRunAll}
                                                disabled={isProcessing || isAutoRunAll}
                                                className="h-12 px-6 text-sm rounded-lg border border-industrial-500/30 text-industrial-400 hover:bg-industrial-500/10 transition-colors disabled:opacity-50 flex items-center gap-2"
                                            >
                                                {isAutoRunAll ? (
                                                    <><Loader2 size={16} className="animate-spin" /> {t('analysis.runningAll')}</>
                                                ) : (
                                                    <><ChevronRight size={16} /> {t('analysis.runAll')}</>
                                                )}
                                            </button>
                                        )}
                                    </div>
                                </div>
                            )}
                        </motion.div>
                    </AnimatePresence>
                </div>
            </div>
        </div>
    );
};

export default AnalysisDashboard;
