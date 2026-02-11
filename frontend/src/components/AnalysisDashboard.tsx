import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
    Check,
    Terminal,
    Clipboard,
    ChevronRight,
    BrainCircuit,
    ShieldCheck,
    AlertCircle,
    FileText,
    Zap
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const API_BASE_URL = 'http://localhost:8000';

interface AnalysisDashboardProps {
    analysisId: number;
    workflow: string[];
    onComplete?: () => void;
}

const AnalysisDashboard: React.FC<AnalysisDashboardProps> = ({ analysisId, workflow, onComplete }) => {
    const [currentStep, setCurrentStep] = useState(0);
    const [query, setQuery] = useState<any>(null);
    const [response, setResponse] = useState('');
    const [isCopied, setIsCopied] = useState(false);
    const [isProcessing, setIsProcessing] = useState(false);
    const [completedAnalyses, setCompletedAnalyses] = useState<any[]>([]);
    const [isSynthesisMode, setIsSynthesisMode] = useState(false);
    const [finalReport, setFinalReport] = useState<any>(null);
    const [isAutomated, setIsAutomated] = useState(false);

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

    const handleCopy = () => {
        navigator.clipboard.writeText(query.query);
        setIsCopied(true);
        setTimeout(() => setIsCopied(false), 2000);
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

    if (finalReport) {
        return (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="max-w-4xl mx-auto py-12">
                <div className="glass-panel p-8">
                    <div className="flex items-center gap-4 mb-8">
                        <div className="w-12 h-12 bg-green-500/10 border border-green-500/20 rounded-full flex items-center justify-center text-green-500">
                            <ShieldCheck size={24} />
                        </div>
                        <div>
                            <h2 className="text-2xl font-bold">Integrated Executive Synthesis</h2>
                            <p className="text-white/40">Multi-agent analysis complete. Results synthesized below.</p>
                        </div>
                    </div>

                    <div className="prose prose-invert max-w-none bg-black/30 p-8 rounded-2xl border border-white/5 whitespace-pre-wrap font-sans text-white/80 leading-relaxed max-h-[500px] overflow-y-auto custom-scrollbar">
                        {finalReport}
                    </div>

                    <div className="mt-8 flex justify-end gap-4">
                        <button className="btn-secondary" onClick={() => window.print()}>
                            <FileText size={18} />
                            Export to PDF
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
        <div className="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-8 pb-20">
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
                                            <div className="absolute top-0 right-0 p-4">
                                                <button
                                                    onClick={handleCopy}
                                                    className={cn(
                                                        "flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-bold transition-all",
                                                        isCopied ? "bg-green-500 text-white" : "bg-white/10 text-white/60 hover:bg-white/20 hover:text-white"
                                                    )}
                                                >
                                                    {isCopied ? <Check size={14} /> : <Clipboard size={14} />}
                                                    {isCopied ? 'Copied to clipboard' : 'Copy Prompt'}
                                                </button>
                                            </div>
                                            <div className="flex items-center gap-3 mb-4">
                                                <h3 className="text-lg font-bold text-white/80">
                                                    Prompt for {isSynthesisMode ? 'Synthesis' : query.role}
                                                </h3>
                                            </div>
                                            <div className="bg-black/40 rounded-xl p-4 font-mono text-xs text-white/30 h-48 overflow-y-auto border border-white/5 scrollbar-thin">
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
    );
};

// Simplified cn helper for the component
function cn(...inputs: any[]) {
    return inputs.filter(Boolean).join(' ');
}

export default AnalysisDashboard;
