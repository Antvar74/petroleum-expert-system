import React, { useState } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import {
    GitBranch,
    HelpCircle,
    CheckCircle2,
    Settings,
    ArrowRight
} from 'lucide-react';
import FiveWhysEditor from './FiveWhysEditor';
import FishboneEditor from './FishboneEditor';

interface RCAVisualizerProps {
    analysisData: any;
    analysisId: number; // Needed for API call
    onGenerateReport?: (report: any) => void;
}

type AnalysisMode = 'select' | '5whys' | 'fishbone' | 'report';

const RCAVisualizer: React.FC<RCAVisualizerProps> = ({ analysisId, onGenerateReport }) => {
    const [mode, setMode] = useState<AnalysisMode>('select');
    const [isGenerating, setIsGenerating] = useState(false);
    const [finalReport, setFinalReport] = useState<any>(null);


    const handleInvestigationComplete = async (methodology: '5whys' | 'fishbone', data: any) => {
        setIsGenerating(true);
        try {
            // Call API to audit and generate report
            const response = await axios.post(`http://localhost:8000/analysis/${analysisId}/rca/generate`, {
                methodology,
                data
            });

            setFinalReport(response.data);
            setMode('report');
            if (onGenerateReport) {
                onGenerateReport(response.data);
            }
        } catch (error) {
            console.error("Error generating RCA report:", error);
            alert("Failed to generate report. See console for details.");
        } finally {
            setIsGenerating(false);
        }
    };

    const renderSelector = () => (
        <div className="grid grid-cols-2 gap-6 h-full min-h-[400px]">
            <button
                onClick={() => setMode('5whys')}
                className="group relative flex flex-col items-center justify-center p-8 bg-white/5 border border-white/10 rounded-2xl hover:bg-white/10 hover:border-industrial-500 transition-all text-left space-y-4"
            >
                <div className="w-16 h-16 rounded-full bg-industrial-900 border border-white/10 flex items-center justify-center group-hover:scale-110 transition-transform">
                    <HelpCircle size={32} className="text-industrial-500" />
                </div>
                <div>
                    <h3 className="text-xl font-bold text-white mb-2">5-Whys Logic</h3>
                    <p className="text-sm text-white/50">
                        Linear drill-down for single-event failures. Best for equipment failure or simple procedural errors.
                    </p>
                </div>
                <div className="absolute bottom-6 right-6 opacity-0 group-hover:opacity-100 transition-opacity">
                    <ArrowRight className="text-industrial-500" />
                </div>
            </button>

            <button
                onClick={() => setMode('fishbone')}
                className="group relative flex flex-col items-center justify-center p-8 bg-white/5 border border-white/10 rounded-2xl hover:bg-white/10 hover:border-industrial-500 transition-all text-left space-y-4"
            >
                <div className="w-16 h-16 rounded-full bg-industrial-900 border border-white/10 flex items-center justify-center group-hover:scale-110 transition-transform">
                    <GitBranch size={32} className="text-industrial-500" />
                </div>
                <div>
                    <h3 className="text-xl font-bold text-white mb-2">Fishbone (Ishikawa)</h3>
                    <p className="text-sm text-white/50">
                        Systemic 6M analysis. Best for complex, multi-causal events involving Man, Machine, and Environment.
                    </p>
                </div>
                <div className="absolute bottom-6 right-6 opacity-0 group-hover:opacity-100 transition-opacity">
                    <ArrowRight className="text-industrial-500" />
                </div>
            </button>
        </div>
    );

    const renderReport = () => (
        <div className="space-y-6">
            <div className="bg-green-500/10 border border-green-500/20 p-6 rounded-xl flex items-start gap-4">
                <CheckCircle2 className="text-green-500 mt-1" />
                <div>
                    <h3 className="font-bold text-white text-lg">Investigation Complete</h3>
                    <p className="text-white/60 text-sm">
                        The RCA Lead Agent has audited your input and generated a formal API RP 585 Report.
                    </p>
                </div>
            </div>

            <div className="glass-panel p-8 bg-black/40 font-mono text-sm leading-relaxed whitespace-pre-wrap text-white/80 border-l-4 border-industrial-500">
                {finalReport?.analysis || finalReport?.query?.split("SYSTEM PROMPT")[0]} {/* Fallback if structure varies */}
            </div>

            <div className="flex gap-4">
                <button
                    onClick={() => setMode('select')}
                    className="px-4 py-2 text-white/40 hover:text-white transition-colors"
                >
                    Start New Investigation
                </button>
            </div>
        </div>
    );

    return (
        <div className="glass-panel p-8 space-y-8 overflow-hidden min-h-[600px]">
            <div className="flex justify-between items-center border-b border-white/5 pb-6">
                <div>
                    <h2 className="text-2xl font-bold flex items-center gap-3">
                        <Settings className="text-industrial-500" />
                        Investigation Builder
                    </h2>
                    <p className="text-white/40 text-sm">
                        {mode === 'select' && "Select your investigation methodology"}
                        {mode === '5whys' && "Root Cause Analysis: 5-Whys"}
                        {mode === 'fishbone' && "Root Cause Analysis: Ishikawa Diagram"}
                        {mode === 'report' && "Final API RP 585 Report"}
                    </p>
                </div>
            </div>

            {isGenerating ? (
                <div className="flex flex-col items-center justify-center h-[400px] space-y-4">
                    <div className="w-12 h-12 border-4 border-industrial-500 border-t-transparent rounded-full animate-spin" />
                    <p className="text-industrial-500 font-bold animate-pulse">
                        Auditing Logic & Generating Report...
                    </p>
                    <p className="text-xs text-white/30">Applying API RP 585 Standards</p>
                </div>
            ) : (
                <AnimatePresence mode='wait'>
                    <motion.div
                        key={mode}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        className="h-full"
                    >
                        {mode === 'select' && renderSelector()}
                        {mode === '5whys' && (
                            <FiveWhysEditor
                                onComplete={(data) => handleInvestigationComplete('5whys', data)}
                            />
                        )}
                        {mode === 'fishbone' && (
                            <FishboneEditor
                                onComplete={(data) => handleInvestigationComplete('fishbone', data)}
                            />
                        )}
                        {mode === 'report' && renderReport()}
                    </motion.div>
                </AnimatePresence>
            )}
        </div>
    );
};

export default RCAVisualizer;
