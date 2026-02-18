import React from 'react';
import { motion } from 'framer-motion';
import { AlertTriangle, CheckCircle, ArrowRight, Brain } from 'lucide-react';

interface RCAVisualizerProps {
    report: any; // RCAReport JSON
}

const RCAVisualizer: React.FC<RCAVisualizerProps> = ({ report }) => {
    if (!report) return null;

    return (
        <div className="space-y-8">
            {/* Header / Root Cause */}
            <div className="glass-panel p-6 border-l-4 border-red-500">
                <div className="flex items-start gap-4">
                    <div className="p-3 bg-red-500/10 rounded-lg">
                        <AlertTriangle className="text-red-400" size={32} />
                    </div>
                    <div>
                        <h3 className="text-lg font-bold text-white mb-1">Root Cause Identified</h3>
                        <div className="inline-block px-3 py-1 rounded-full bg-red-500/20 text-red-300 text-sm font-medium mb-3">
                            {report.root_cause_category}
                        </div>
                        <p className="text-white/80 text-lg leading-relaxed">
                            {report.root_cause_description}
                        </p>
                        <div className="mt-4 flex items-center gap-2 text-sm text-white/40">
                            <Brain size={16} />
                            <span>AI Confidence Score: {(report.confidence_score * 100).toFixed(0)}%</span>
                        </div>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* 5 Whys Chain */}
                <div className="glass-panel p-6">
                    <h4 className="text-lg font-bold mb-6 flex items-center gap-2">
                        <span className="w-8 h-8 rounded-full bg-industrial-700 flex items-center justify-center text-sm">5W</span>
                        The 5 Whys Analysis
                    </h4>
                    <div className="space-y-4">
                        {report.five_whys?.map((why: string, idx: number) => (
                            <motion.div
                                key={idx}
                                initial={{ opacity: 0, x: -20 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: idx * 0.1 }}
                                className="relative pl-8 border-l-2 border-industrial-700 pb-4 last:border-0 last:pb-0"
                            >
                                <div className="absolute -left-[9px] top-0 w-4 h-4 rounded-full bg-industrial-600 border-2 border-industrial-900" />
                                <p className="text-white/90">{why}</p>
                            </motion.div>
                        ))}
                    </div>
                </div>

                {/* Fishbone Factors */}
                <div className="glass-panel p-6">
                    <h4 className="text-lg font-bold mb-6 flex items-center gap-2">
                        <span className="w-8 h-8 rounded-full bg-industrial-700 flex items-center justify-center text-sm">{"><"}</span>
                        Contributing Factors (Ishikawa)
                    </h4>
                    <div className="space-y-4">
                        {Object.entries(report.fishbone_factors || {}).map(([category, items]: [string, any]) => (
                            <div key={category} className="bg-white/5 p-4 rounded-lg">
                                <h5 className="text-sm font-bold text-industrial-300 mb-2 uppercase tracking-wider">{category}</h5>
                                <div className="flex flex-wrap gap-2">
                                    {Array.isArray(items) && items.map((item: string, i: number) => (
                                        <span key={i} className="px-2 py-1 bg-black/40 rounded text-sm text-white/70 border border-white/5">
                                            {item}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Application / CAPA */}
            <div className="glass-panel p-6 bg-green-500/5 border border-green-500/20">
                <h4 className="text-lg font-bold mb-4 text-green-400 flex items-center gap-2">
                    <CheckCircle size={20} />
                    Corrective Actions (CAPA)
                </h4>
                <ul className="space-y-3">
                    {report.corrective_actions?.map((action: string, idx: number) => (
                        <li key={idx} className="flex items-start gap-3">
                            <ArrowRight className="text-green-500/50 mt-1 shrink-0" size={16} />
                            <span className="text-white/90">{action}</span>
                        </li>
                    ))}
                </ul>
            </div>
        </div>
    );
};

export default RCAVisualizer;
