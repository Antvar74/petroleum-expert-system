import React, { useRef } from 'react';
import { motion } from 'framer-motion';
import { AlertTriangle, CheckCircle, ArrowRight, Brain, Shield, FileText, Loader2 } from 'lucide-react';

// @ts-ignore
import html2pdf from 'html2pdf.js';

interface RCAReport {
    root_cause_category?: string;
    root_cause_description?: string;
    five_whys?: string[];
    fishbone_factors?: Record<string, string[]>;
    corrective_actions?: string[];
    prevention_actions?: string[];
    confidence_score?: number;
}

interface RCAVisualizerProps {
    report: RCAReport;
}

const RCAVisualizer: React.FC<RCAVisualizerProps> = ({ report }) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const [isExportingPDF, setIsExportingPDF] = React.useState(false);

    if (!report) return null;

    const hasRootCause = report.root_cause_category || report.root_cause_description;
    const hasFiveWhys = Array.isArray(report.five_whys) && report.five_whys.length > 0;
    const hasFishbone = report.fishbone_factors && Object.keys(report.fishbone_factors).length > 0;
    const hasCorrectiveActions = Array.isArray(report.corrective_actions) && report.corrective_actions.length > 0;
    const hasPreventionActions = Array.isArray(report.prevention_actions) && report.prevention_actions.length > 0;
    const confidencePct = typeof report.confidence_score === 'number'
        ? (report.confidence_score > 1 ? report.confidence_score : report.confidence_score * 100)
        : null;

    const handleExportPDF = async () => {
        if (!containerRef.current) return;
        setIsExportingPDF(true);
        try {
            const opt = {
                margin: 10,
                filename: `PetroExpert_RCA_Report.pdf`,
                image: { type: 'jpeg' as const, quality: 0.98 },
                html2canvas: { scale: 2, useCORS: true },
                jsPDF: { unit: 'mm' as const, format: 'a4' as const, orientation: 'portrait' as const }
            };
            await html2pdf().set(opt).from(containerRef.current).save();
        } catch (error) {
            console.error("Error exporting RCA PDF:", error);
        } finally {
            setIsExportingPDF(false);
        }
    };

    // Ishikawa SVG icon
    const IshikawaIcon = () => (
        <svg width="32" height="32" viewBox="0 0 32 32" fill="none" className="text-industrial-400">
            <line x1="4" y1="16" x2="28" y2="16" stroke="currentColor" strokeWidth="2" />
            <line x1="28" y1="16" x2="24" y2="12" stroke="currentColor" strokeWidth="2" />
            <line x1="28" y1="16" x2="24" y2="20" stroke="currentColor" strokeWidth="2" />
            <line x1="10" y1="16" x2="6" y2="8" stroke="currentColor" strokeWidth="1.5" />
            <line x1="14" y1="16" x2="10" y2="24" stroke="currentColor" strokeWidth="1.5" />
            <line x1="18" y1="16" x2="14" y2="8" stroke="currentColor" strokeWidth="1.5" />
            <line x1="22" y1="16" x2="18" y2="24" stroke="currentColor" strokeWidth="1.5" />
            <circle cx="6" cy="8" r="2" fill="currentColor" opacity="0.5" />
            <circle cx="10" cy="24" r="2" fill="currentColor" opacity="0.5" />
            <circle cx="14" cy="8" r="2" fill="currentColor" opacity="0.5" />
            <circle cx="18" cy="24" r="2" fill="currentColor" opacity="0.5" />
        </svg>
    );

    // Empty state for sections
    const EmptySection = ({ message }: { message: string }) => (
        <div className="text-white/30 text-sm italic py-4 text-center border border-dashed border-white/10 rounded-lg">
            {message}
        </div>
    );

    return (
        <div ref={containerRef} className="space-y-8">
            {/* Header / Root Cause */}
            {hasRootCause ? (
                <div className="glass-panel p-6 border-l-4 border-red-500">
                    <div className="flex items-start gap-4">
                        <div className="p-3 bg-red-500/10 rounded-lg shrink-0">
                            <AlertTriangle className="text-red-400" size={32} />
                        </div>
                        <div className="flex-1 min-w-0">
                            <h3 className="text-lg font-bold text-white mb-1">Causa Raíz Identificada</h3>
                            {report.root_cause_category && (
                                <div className="inline-block px-3 py-1 rounded-full bg-red-500/20 text-red-300 text-sm font-medium mb-3">
                                    {report.root_cause_category}
                                </div>
                            )}
                            {report.root_cause_description && (
                                <p className="text-white/80 text-lg leading-relaxed">
                                    {report.root_cause_description}
                                </p>
                            )}
                            {confidencePct !== null && (
                                <div className="mt-4 flex items-center gap-3">
                                    <Brain size={16} className="text-white/40" />
                                    <span className="text-sm text-white/40">Confianza IA:</span>
                                    <div className="flex-1 max-w-32 h-2 bg-white/10 rounded-full overflow-hidden">
                                        <div
                                            className={`h-full rounded-full ${confidencePct >= 70 ? 'bg-green-500' : confidencePct >= 40 ? 'bg-yellow-500' : 'bg-red-500'}`}
                                            style={{ width: `${Math.min(confidencePct, 100)}%` }}
                                        />
                                    </div>
                                    <span className="text-sm font-bold text-white/60">{confidencePct.toFixed(0)}%</span>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            ) : (
                <div className="glass-panel p-6 border-l-4 border-yellow-500">
                    <div className="flex items-center gap-3 text-yellow-400">
                        <AlertTriangle size={20} />
                        <span className="font-medium">No se pudo identificar una causa raíz definitiva. Revise los datos del evento.</span>
                    </div>
                </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* 5 Whys Chain */}
                <div className="glass-panel p-6">
                    <h4 className="text-lg font-bold mb-6 flex items-center gap-2">
                        <span className="w-8 h-8 rounded-full bg-industrial-700 flex items-center justify-center text-sm font-bold">5W</span>
                        Análisis de los 5 Por Qué
                    </h4>
                    {hasFiveWhys ? (
                        <div className="space-y-4">
                            {report.five_whys!.map((why: string, idx: number) => (
                                <motion.div
                                    key={idx}
                                    initial={{ opacity: 0, x: -20 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    transition={{ delay: idx * 0.1 }}
                                    className="relative pl-8 border-l-2 border-industrial-700 pb-4 last:border-0 last:pb-0"
                                >
                                    <div className="absolute -left-[9px] top-0 w-4 h-4 rounded-full bg-industrial-600 border-2 border-industrial-900" />
                                    <div className="text-[10px] font-bold text-industrial-500 uppercase mb-1">¿Por qué #{idx + 1}?</div>
                                    <p className="text-white/90 text-sm leading-relaxed">{why}</p>
                                </motion.div>
                            ))}
                        </div>
                    ) : (
                        <EmptySection message="Análisis de 5 Por Qué no disponible" />
                    )}
                </div>

                {/* Fishbone Factors */}
                <div className="glass-panel p-6">
                    <h4 className="text-lg font-bold mb-6 flex items-center gap-2">
                        <IshikawaIcon />
                        Factores Contribuyentes (Ishikawa)
                    </h4>
                    {hasFishbone ? (
                        <div className="space-y-4">
                            {Object.entries(report.fishbone_factors!).map(([category, items]) => (
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
                    ) : (
                        <EmptySection message="Factores Ishikawa no disponibles" />
                    )}
                </div>
            </div>

            {/* Corrective Actions (CAPA) */}
            <div className="glass-panel p-6 bg-green-500/5 border border-green-500/20">
                <h4 className="text-lg font-bold mb-4 text-green-400 flex items-center gap-2">
                    <CheckCircle size={20} />
                    Acciones Correctivas (CAPA)
                </h4>
                {hasCorrectiveActions ? (
                    <ul className="space-y-3">
                        {report.corrective_actions!.map((action: string, idx: number) => (
                            <li key={idx} className="flex items-start gap-3">
                                <ArrowRight className="text-green-500/50 mt-1 shrink-0" size={16} />
                                <span className="text-white/90 text-sm">{action}</span>
                            </li>
                        ))}
                    </ul>
                ) : (
                    <EmptySection message="No se generaron acciones correctivas" />
                )}
            </div>

            {/* Prevention Actions */}
            {hasPreventionActions && (
                <div className="glass-panel p-6 bg-blue-500/5 border border-blue-500/20">
                    <h4 className="text-lg font-bold mb-4 text-blue-400 flex items-center gap-2">
                        <Shield size={20} />
                        Acciones Preventivas
                    </h4>
                    <ul className="space-y-3">
                        {report.prevention_actions!.map((action: string, idx: number) => (
                            <li key={idx} className="flex items-start gap-3">
                                <ArrowRight className="text-blue-500/50 mt-1 shrink-0" size={16} />
                                <span className="text-white/90 text-sm">{action}</span>
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {/* Export Button */}
            <div className="flex justify-end">
                <button
                    onClick={handleExportPDF}
                    disabled={isExportingPDF}
                    className="btn-secondary flex items-center gap-2"
                >
                    {isExportingPDF ? (
                        <><Loader2 size={16} className="animate-spin" /> Exportando...</>
                    ) : (
                        <><FileText size={16} /> Exportar RCA a PDF</>
                    )}
                </button>
            </div>
        </div>
    );
};

export default RCAVisualizer;
