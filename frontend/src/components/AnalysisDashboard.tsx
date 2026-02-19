import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
    Check,
    Terminal,
    ChevronRight,
    BrainCircuit,
    ShieldCheck,
    AlertCircle,
    FileText,
    Zap,
    AlertTriangle,
    ClipboardCopy
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import PhysicsResults from './PhysicsResults';
import RCAVisualizer from './RCAVisualizer';
import { API_BASE_URL } from '../config';



// @ts-ignore
import html2pdf from 'html2pdf.js';

interface AnalysisDashboardProps {
    analysisId: number;
    workflow: string[];
    onComplete?: () => void;
}

const AnalysisDashboard: React.FC<AnalysisDashboardProps> = ({ analysisId, workflow, onComplete }) => {
    // RCA State
    const [rcaReport, setRcaReport] = useState<any>(null);
    const [isGeneratingRCA, setIsGeneratingRCA] = useState(false);

    const handleGenerateRCA = async () => {
        if (!eventId) return;
        setIsGeneratingRCA(true);
        try {
            const res = await axios.post(`${API_BASE_URL}/events/${eventId}/rca`);
            setRcaReport(res.data);
        } catch (error) {
            console.error("Error generating RCA:", error);
            alert("Failed to generate Root Cause Analysis.");
        } finally {
            setIsGeneratingRCA(false);
        }
    };

    const [currentStep, setCurrentStep] = useState(0);

    const [query, setQuery] = useState<any>(null);
    const [response, setResponse] = useState('');
    const [isProcessing, setIsProcessing] = useState(false);
    const [completedAnalyses, setCompletedAnalyses] = useState<any[]>([]);
    const [isSynthesisMode, setIsSynthesisMode] = useState(false);
    const [finalReport, setFinalReport] = useState<any>(null);
    const [isAutomated, setIsAutomated] = useState(false);
    const [isGeneratingPDF, setIsGeneratingPDF] = useState(false);

    // Physics Engine State
    const [eventId, setEventId] = useState<number | null>(null);

    useEffect(() => {
        // Fetch analysis details to get problem_id/event_id for Physics Engine
        const fetchAnalysisDetails = async () => {
            try {
                const res = await axios.get(`${API_BASE_URL}/analysis/${analysisId}`);
                // Verify structure: might need adjustment based on exact API response
                // Assuming analysis -> problem -> additional_data -> event_id
                if (res.data?.problem?.additional_data?.event_id) {
                    setEventId(res.data.problem.additional_data.event_id);
                }
            } catch (e) {
                console.warn("Could not load event ID for physics:", e);
            }
        };
        fetchAnalysisDetails();
    }, [analysisId]);

    useEffect(() => {
        if (currentStep < workflow.length) {
            fetchQuery(workflow[currentStep]);
        } else {
            fetchSynthesisQuery();
        }
    }, [currentStep]);

    const fetchQuery = async (agentId: string) => {
        try {
            const response = await axios.get(`${API_BASE_URL}/analysis/${analysisId}/agent/${agentId}/query`);
            setQuery(response.data);
        } catch (error) {
            console.error("Error fetching query:", error);
        }
    };

    const fetchSynthesisQuery = async () => {
        try {
            setIsSynthesisMode(true);
            const response = await axios.get(`${API_BASE_URL}/analysis/${analysisId}/synthesis/query`);
            setQuery(response.data);
        } catch (error) {
            console.error("Error fetching synthesis query:", error);
        }
    };



    const handleAutoRun = async () => {
        setIsProcessing(true);
        try {
            if (!isSynthesisMode) {
                const agentId = workflow[currentStep];
                const res = await axios.post(`${API_BASE_URL}/analysis/${analysisId}/agent/${agentId}/auto`);
                setCompletedAnalyses([...completedAnalyses, { role: query.role, confidence: res.data.confidence }]);
                setResponse('');
                setCurrentStep(currentStep + 1);
            } else {
                const res = await axios.post(`${API_BASE_URL}/analysis/${analysisId}/synthesis/auto`);
                setFinalReport(res.data.analysis);
            }
        } catch (error) {
            console.error("Error in automated analysis:", error);
            alert("Error connecting to local LLM. Make sure Ollama is running.");
        } finally {
            setIsProcessing(false);
        }
    };

    const handleSubmitResponse = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!response.trim()) return;

        setIsProcessing(true);
        try {
            if (!isSynthesisMode) {
                const agentId = workflow[currentStep];
                const res = await axios.post(`${API_BASE_URL}/analysis/${analysisId}/agent/${agentId}/response`, { text: response });
                setCompletedAnalyses([...completedAnalyses, { role: query.role, confidence: res.data.confidence }]);
                setResponse('');
                setCurrentStep(currentStep + 1);
            } else {
                await axios.post(`${API_BASE_URL}/analysis/${analysisId}/synthesis/response`, { text: response });
                setFinalReport(response);
                setIsProcessing(false);
            }
        } catch (error) {
            console.error("Error submitting response:", error);
        } finally {
            setIsProcessing(false);
        }
    };

    const generatePDFConfig = () => {
        return {
            margin: 10,
            filename: `PetroExpert_Analysis_${analysisId}.pdf`,
            image: { type: 'jpeg', quality: 0.98 },
            html2canvas: { scale: 2, useCORS: true },
            jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
        };
    };

    const handleSavePDF = async () => {
        setIsGeneratingPDF(true);
        try {
            const element = document.querySelector('.print-report-container');
            if (element) {
                // Temporarily make everything visible for PDF generation
                // Force white background and black text for generation
                element.classList.add('pdf-generation');

                // Show header
                const header = element.querySelector('.print-header');
                if (header) header.classList.remove('hidden');

                const opt = generatePDFConfig();
                // @ts-ignore - html2pdf types are loose
                await html2pdf().set(opt).from(element).save();

                // Restore
                if (header) header.classList.add('hidden');
                element.classList.remove('pdf-generation');
            }
        } catch (error) {
            console.error("Error generating PDF:", error);
            alert("Failed to generate PDF. Please try again.");
        } finally {
            setIsGeneratingPDF(false);
        }
    };

    const handleSharePDF = async () => {
        if (!navigator.share) {
            alert("Sharing is not supported on this device/browser.");
            return;
        }

        setIsGeneratingPDF(true);
        try {
            const element = document.querySelector('.print-report-container');
            if (element) {
                // Show header temporarly
                const header = element.querySelector('.print-header');
                if (header) header.classList.remove('hidden');

                const opt = generatePDFConfig();
                // @ts-ignore - html2pdf types are loose
                const pdfBlob = await html2pdf().set(opt).from(element).output('blob');

                // Restore header hidden
                if (header) header.classList.add('hidden');

                const file = new File([pdfBlob], `PetroExpert_Analysis_${analysisId}.pdf`, { type: 'application/pdf' });

                if (navigator.canShare && navigator.canShare({ files: [file] })) {
                    await navigator.share({
                        files: [file],
                        title: 'PetroExpert Analysis Report',
                        text: `Attached is the analysis report #${analysisId}.`,
                    });
                } else {
                    alert("System does not support sharing files.");
                }
            }
        } catch (error) {
            console.error("Error sharing PDF:", error);
            // Don't alert if user cancelled share
            if ((error as Error).name !== 'AbortError') {
                alert("Failed to share PDF.");
            }
        } finally {
            setIsGeneratingPDF(false);
        }
    };


    if (finalReport) {
        return (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="max-w-4xl mx-auto py-12">
                <style>{`
                    .pdf-generation {
                        background-color: white !important;
                        color: black !important;
                    }
                    .pdf-generation .prose {
                        color: black !important;
                    }
                `}</style>
                <div className="glass-panel p-8 print-report-container">
                    {/* Print Header - Only visible when printing or generating PDF */}
                    <div className="hidden print-header">
                        <div className="print-header-logo">
                            PETROEXPERT <span className="text-sm font-normal text-gray-500">System v3.0 Elite</span>
                        </div>
                        <div className="print-header-meta">
                            <p>Generated: {new Date().toLocaleDateString()}</p>
                            <p>Analysis ID: #{analysisId}</p>
                        </div>
                    </div>

                    <div className="flex items-center gap-4 mb-8 print-no-show">
                        <div className="w-12 h-12 bg-green-500/10 border border-green-500/20 rounded-full flex items-center justify-center text-green-500">
                            <ShieldCheck size={24} />
                        </div>
                        <div>
                            <h2 className="text-2xl font-bold">Integrated Executive Synthesis</h2>
                            <p className="text-white/40">Multi-agent analysis complete. Results synthesized below.</p>
                        </div>
                    </div>

                    <div className="prose prose-invert max-w-none bg-black/30 p-8 rounded-2xl border border-white/5 whitespace-pre-wrap font-sans text-white/80 leading-relaxed max-h-[500px] overflow-y-auto custom-scrollbar print:bg-white print:text-black print:border-none print:p-0 print:max-h-none">
                        {finalReport}
                    </div>

                    <div className="mt-8 flex justify-end gap-4 print-no-show">
                        <button
                            className="btn-secondary"
                            onClick={handleSavePDF}
                            disabled={isGeneratingPDF}
                        >
                            <FileText size={18} />
                            {isGeneratingPDF ? 'Generating...' : 'Save PDF'}
                        </button>

                        <button
                            className="btn-secondary"
                            onClick={handleSharePDF}
                            disabled={isGeneratingPDF}
                        >
                            <ClipboardCopy size={18} />
                            {isGeneratingPDF ? 'Preparing...' : 'Share PDF'}
                        </button>

                        <button
                            onClick={() => onComplete && onComplete()}
                            className="btn-primary bg-industrial-600 hover:bg-industrial-500 shadow-industrial-900/40"
                        >
                            <Zap size={18} />
                            Generate RCA Visuals
                        </button>
                    </div>
                </div>
            </motion.div>
        );
    }

    return (
        <div className="w-full mx-auto pb-20">
            {/* Physics Engine Results */}
            {eventId && (
                <div className="space-y-8">
                    <PhysicsResults eventId={eventId} />

                    {/* RCA Section */}
                    <AnimatePresence>
                        {!rcaReport ? (
                            <motion.div
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="flex justify-center"
                            >
                                <button
                                    onClick={handleGenerateRCA}
                                    disabled={isGeneratingRCA}
                                    className="btn-primary bg-red-600 hover:bg-red-500 shadow-red-900/40 text-lg py-4 px-8"
                                >
                                    {isGeneratingRCA ? (
                                        <>
                                            <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                            Analyzing Event Evidence...
                                        </>
                                    ) : (
                                        <>
                                            <AlertTriangle size={24} />
                                            Generate API RP 585 Root Cause Analysis
                                        </>
                                    )}
                                </button>
                            </motion.div>
                        ) : (
                            <motion.div
                                initial={{ opacity: 0, scale: 0.95 }}
                                animate={{ opacity: 1, scale: 1 }}
                            >
                                <div className="flex items-center gap-4 mb-6">
                                    <div className="w-12 h-12 bg-red-500/10 border border-red-500/20 rounded-full flex items-center justify-center text-red-500">
                                        <AlertTriangle size={24} />
                                    </div>
                                    <div>
                                        <h2 className="text-2xl font-bold">Investigation Findings</h2>
                                        <p className="text-white/40">Structured RCA based on physical evidence.</p>
                                    </div>
                                </div>
                                <RCAVisualizer report={rcaReport} />
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Left Column: Progress */}
                <div className="lg:col-span-1 space-y-6">
                    <div className="glass-panel p-6">
                        <h3 className="text-sm font-bold uppercase tracking-widest text-industrial-500 mb-6 flex items-center gap-2">
                            <BrainCircuit size={16} />
                            Specialist Pipeline
                        </h3>
                        <div className="space-y-4">
                            {workflow.map((agent, index) => (
                                <div key={agent} className={`flex items-center gap-3 p-3 rounded-xl transition-all ${index === currentStep ? 'bg-industrial-600/10 border border-industrial-600/20 text-white' :
                                    index < currentStep ? 'text-green-400' : 'text-white/20'
                                    }`}>
                                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center border ${index === currentStep ? 'border-industrial-500 bg-industrial-500/10' :
                                        index < currentStep ? 'border-green-500 bg-green-500/10' : 'border-white/5 bg-white/5'
                                        }`}>
                                        {index < currentStep ? <Check size={14} /> : <span>{index + 1}</span>}
                                    </div>
                                    <div>
                                        <p className="text-xs font-bold uppercase">{agent.replace('_', ' ')}</p>
                                        {index === currentStep && <span className="text-[10px] animate-pulse">ACTIVE CONSULTATION</span>}
                                    </div>
                                </div>
                            ))}
                            <div className={`flex items-center gap-3 p-3 rounded-xl transition-all ${isSynthesisMode ? 'bg-industrial-600/10 border border-industrial-600/20 text-white' : 'text-white/20'
                                }`}>
                                <div className={`w-8 h-8 rounded-lg flex items-center justify-center border ${isSynthesisMode ? 'border-industrial-500 bg-industrial-500/10' : 'border-white/5 bg-white/5'
                                    }`}>
                                    <Terminal size={14} />
                                </div>
                                <div>
                                    <p className="text-xs font-bold uppercase">Final Synthesis</p>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="glass-panel p-6 bg-amber-500/5 border-amber-500/10">
                        <div className="flex gap-3 text-amber-500 mb-2">
                            <AlertCircle size={18} />
                            <span className="text-xs font-bold uppercase tracking-wider">How to proceed</span>
                        </div>
                        <p className="text-xs text-amber-500/60 leading-relaxed">
                            Because this tool operates in <strong>interactive mode</strong>, you must copy the generated system prompt and paste it into Claude to get the expert opinion.
                        </p>
                    </div>
                </div>

                {/* Right Column: Interaction */}
                <div className="lg:col-span-2 space-y-8">
                    <div className="flex justify-between items-center bg-white/5 p-4 rounded-2xl border border-white/10">
                        <div className="flex items-center gap-3">
                            <div className={cn(
                                "p-2 rounded-lg",
                                isAutomated ? "bg-industrial-500/20 text-industrial-400" : "bg-white/10 text-white/40"
                            )}>
                                <BrainCircuit size={20} />
                            </div>
                            <div>
                                <p className="text-sm font-bold uppercase tracking-wider">Analysis Mode</p>
                                <p className="text-xs text-white/40">{isAutomated ? 'Automated (Local LLM via Ollama)' : 'Interactive (Manual Copy/Paste)'}</p>
                            </div>
                        </div>
                        <button
                            onClick={() => setIsAutomated(!isAutomated)}
                            className={cn(
                                "relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none",
                                isAutomated ? "bg-industrial-600" : "bg-white/10"
                            )}
                        >
                            <span className={cn(
                                "pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out",
                                isAutomated ? "translate-x-5" : "translate-x-0"
                            )} />
                        </button>
                    </div>

                    <AnimatePresence mode="wait">
                        <motion.div
                            key={currentStep + (isSynthesisMode ? 'synth' : 'step')}
                            initial={{ opacity: 0, x: 20 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: -20 }}
                            className="space-y-6"
                        >
                            {query && (
                                <div className="space-y-6">
                                    {!isAutomated ? (
                                        <>
                                            <div className="glass-panel p-6 border-industrial-600/20 relative overflow-hidden group">
                                                <div className="flex items-center gap-3 mb-4">
                                                    <h3 className="text-lg font-bold text-white/80">
                                                        Prompt for {isSynthesisMode ? 'Synthesis' : query.role}
                                                    </h3>
                                                </div>
                                                <div className="bg-black/40 rounded-xl p-4 font-mono text-xs text-white/30 h-48 overflow-hidden select-none border border-white/5">
                                                    {query.query}
                                                </div>
                                            </div>

                                            <form onSubmit={handleSubmitResponse} className="space-y-4">
                                                <div className="relative">
                                                    <textarea
                                                        required
                                                        value={response}
                                                        onChange={(e) => setResponse(e.target.value)}
                                                        placeholder={`Paste Claude's response for ${isSynthesisMode ? 'the Final Synthesis' : query.role} here...`}
                                                        className="w-full bg-black/40 border border-white/10 rounded-2xl p-6 text-sm text-white focus:outline-none focus:border-industrial-500 transition-all min-h-[300px] shadow-inner"
                                                    />
                                                    <div className="absolute bottom-4 right-4">
                                                        <button
                                                            type="submit"
                                                            disabled={isProcessing || !response.trim()}
                                                            className="btn-primary"
                                                        >
                                                            {isProcessing ? 'Processing Analysis...' : (
                                                                <>
                                                                    {isSynthesisMode ? 'Complete Final Report' : 'Submit & Continue'}
                                                                    <ChevronRight size={18} />
                                                                </>
                                                            )}
                                                        </button>
                                                    </div>
                                                </div>
                                            </form>
                                        </>
                                    ) : (
                                        <div className="glass-panel p-12 flex flex-col items-center justify-center text-center space-y-6 animate-in zoom-in-95 duration-300">
                                            <div className="w-20 h-20 bg-industrial-600/20 rounded-full flex items-center justify-center text-industrial-500 relative">
                                                <BrainCircuit size={40} className={isProcessing ? "animate-pulse" : ""} />
                                                {isProcessing && (
                                                    <div className="absolute inset-0 border-4 border-industrial-500 border-t-transparent rounded-full animate-spin" />
                                                )}
                                            </div>
                                            <div>
                                                <h3 className="text-xl font-bold mb-2">
                                                    {isProcessing ? 'Agent is analyzing...' : `Ready to Consult ${isSynthesisMode ? 'Synthesis' : query.role}`}
                                                </h3>
                                                <p className="text-sm text-white/40 max-w-md">
                                                    {isProcessing
                                                        ? "The local LLM is processing the operational data and previous specialist findings. This may take a few seconds."
                                                        : "Ollama is ready. Click the button below to start the automated analysis for this step."}
                                                </p>
                                            </div>
                                            <button
                                                onClick={handleAutoRun}
                                                disabled={isProcessing}
                                                className="btn-primary h-12 px-8 text-base shadow-xl shadow-industrial-900/40"
                                            >
                                                {isProcessing ? 'Processing...' : `Run ${isSynthesisMode ? 'Synthesis' : 'Automated Analysis'}`}
                                                {!isProcessing && <Zap size={18} />}
                                            </button>
                                        </div>
                                    )}
                                </div>
                            )}
                        </motion.div>
                    </AnimatePresence>
                </div>
            </div>
        </div>
    );
};

// Simplified cn helper for the component
function cn(...inputs: any[]) {
    return inputs.filter(Boolean).join(' ');
}

export default AnalysisDashboard;
