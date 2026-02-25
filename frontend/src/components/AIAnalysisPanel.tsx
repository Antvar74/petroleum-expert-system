import React, { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { motion, AnimatePresence } from 'framer-motion';
import { BrainCircuit, FileText, Share2, RefreshCw, X, ChevronDown, ChevronUp } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import ExecutiveReport from './ExecutiveReport';
import { useLanguage } from '../hooks/useLanguage';
import { useToast } from './ui/Toast';
import type { Provider, ProviderOption } from '../types/ai';

// @ts-ignore - html2pdf has no types
import html2pdf from 'html2pdf.js';

interface KeyMetric {
  label: string;
  value: string | number;
  unit?: string;
}

interface AIAnalysisPanelProps {
  moduleName: string;
  moduleIcon: LucideIcon;
  wellName: string;
  analysis: string | null;
  confidence: string;
  agentRole: string;
  isLoading: boolean;
  keyMetrics: KeyMetric[];
  onAnalyze: () => void;
  onClose?: () => void;
  provider: Provider;
  onProviderChange: (provider: Provider) => void;
  availableProviders: ProviderOption[];
}

const AIAnalysisPanel: React.FC<AIAnalysisPanelProps> = ({
  moduleName,
  moduleIcon: ModuleIcon,
  wellName,
  analysis,
  confidence,
  agentRole,
  isLoading,
  keyMetrics,
  onAnalyze,
  onClose,
  provider,
  onProviderChange,
  availableProviders,
}) => {
  const { t } = useTranslation();
  const { language, setLanguage } = useLanguage();
  const { addToast } = useToast();
  const locale = language === 'es' ? 'es-MX' : 'en-US';
  const [displayedText, setDisplayedText] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [isGeneratingPDF, setIsGeneratingPDF] = useState(false);
  const [isExpanded, setIsExpanded] = useState(true);
  const reportRef = useRef<HTMLDivElement>(null);
  const textRef = useRef<HTMLDivElement>(null);

  // Typing animation effect
  useEffect(() => {
    if (!analysis) {
      setDisplayedText('');
      return;
    }

    setIsTyping(true);
    setDisplayedText('');
    const words = analysis.split(' ');
    let currentIndex = 0;

    const interval = setInterval(() => {
      if (currentIndex < words.length) {
        setDisplayedText(prev => prev + (currentIndex > 0 ? ' ' : '') + words[currentIndex]);
        currentIndex++;
        // Auto-scroll
        if (textRef.current) {
          textRef.current.scrollTop = textRef.current.scrollHeight;
        }
      } else {
        clearInterval(interval);
        setIsTyping(false);
      }
    }, 30); // 30ms per word for smooth animation

    return () => clearInterval(interval);
  }, [analysis]);

  // PDF generation
  const handleSavePDF = async () => {
    const el = reportRef.current;
    if (!el) return;

    setIsGeneratingPDF(true);
    try {
      el.style.display = 'block';
      const opt = {
        margin: 10,
        filename: `PetroExpert_${moduleName.replace(/\s+/g, '_')}_${wellName.replace(/\s+/g, '_')}.pdf`,
        image: { type: 'jpeg' as const, quality: 0.98 },
        html2canvas: { scale: 2, useCORS: true },
        jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' as const },
      };
      // @ts-ignore - html2pdf types are loose
      await html2pdf().set(opt).from(el).save();
    } catch (err) {
      console.error('PDF generation error:', err);
    } finally {
      if (reportRef.current) reportRef.current.style.display = 'none';
      setIsGeneratingPDF(false);
    }
  };

  // Share as PDF
  const handleSharePDF = async () => {
    if (!navigator.share) {
      addToast(t('ai.sharingNotSupported'), 'info');
      return;
    }

    const el = reportRef.current;
    if (!el) return;

    setIsGeneratingPDF(true);
    try {
      el.style.display = 'block';
      const opt = {
        margin: 10,
        filename: `PetroExpert_${moduleName.replace(/\s+/g, '_')}_${wellName.replace(/\s+/g, '_')}.pdf`,
        image: { type: 'jpeg' as const, quality: 0.98 },
        html2canvas: { scale: 2, useCORS: true },
        jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' as const },
      };

      // @ts-ignore - html2pdf types are loose
      const pdfBlob = await html2pdf().set(opt).from(el).output('blob');
      el.style.display = 'none';

      const file = new File(
        [pdfBlob],
        `PetroExpert_${moduleName.replace(/\s+/g, '_')}_${wellName}.pdf`,
        { type: 'application/pdf' }
      );

      if (navigator.canShare && navigator.canShare({ files: [file] })) {
        await navigator.share({
          files: [file],
          title: `PetroExpert - ${moduleName} - ${wellName}`,
          text: `${t('ai.reportFor')} ${moduleName}.`,
        });
      } else {
        addToast(t('ai.filesNotSupported'), 'info');
      }
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        console.error('Share error:', err);
      }
    } finally {
      if (reportRef.current) reportRef.current.style.display = 'none';
      setIsGeneratingPDF(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="mt-8"
    >
      <div className="glass-panel rounded-2xl border border-industrial-500/20 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/5 bg-industrial-600/5">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-industrial-600/20 rounded-lg">
              <BrainCircuit size={22} className="text-industrial-400" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                {t('ai.executiveAnalysis')}
                <ModuleIcon size={16} className="text-white/40" />
                <span className="text-white/40 font-normal text-sm">{moduleName}</span>
              </h3>
              <div className="flex items-center gap-3 mt-1">
                <span className="text-xs text-white/40">{agentRole}</span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Language toggle */}
            <div className="flex items-center bg-white/5 rounded-lg overflow-hidden border border-white/10">
              {(['en', 'es'] as const).map((lang) => (
                <button
                  key={lang}
                  onClick={() => setLanguage(lang)}
                  className={`px-2.5 py-1 text-xs font-bold transition-all ${
                    language === lang
                      ? 'bg-industrial-600 text-white'
                      : 'text-white/40 hover:text-white/70'
                  }`}
                >
                  {lang.toUpperCase()}
                </button>
              ))}
            </div>

            {/* Provider selector */}
            {availableProviders.length > 1 && (
              <select
                value={provider}
                onChange={(e) => onProviderChange(e.target.value as Provider)}
                className="bg-white/5 border border-white/10 rounded-lg text-white/80 py-1 px-2 text-xs focus:outline-none focus:border-industrial-500/50"
                title={t('ai.provider')}
              >
                {availableProviders.map((p) => (
                  <option key={p.id} value={p.id} className="bg-gray-900 text-white">
                    {language === 'es' ? p.name_es : p.name}
                  </option>
                ))}
              </select>
            )}

            <div className="w-px h-5 bg-white/10" />

            {/* Action buttons */}
            <button
              onClick={handleSavePDF}
              disabled={isGeneratingPDF || isLoading || !analysis}
              className="btn-secondary text-xs py-1.5 px-3 disabled:opacity-30"
              title={t('ai.exportPdf')}
            >
              <FileText size={14} />
              {isGeneratingPDF ? t('ai.generatingPdf') : t('ai.exportPdf')}
            </button>
            <button
              onClick={handleSharePDF}
              disabled={isGeneratingPDF || isLoading || !analysis}
              className="btn-secondary text-xs py-1.5 px-3 disabled:opacity-30"
              title={t('ai.share')}
            >
              <Share2 size={14} />
              {t('ai.share')}
            </button>
            <button
              onClick={onAnalyze}
              disabled={isLoading}
              className="btn-secondary text-xs py-1.5 px-3 disabled:opacity-30"
              title={t('ai.regenerate')}
            >
              <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
            </button>
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="p-1.5 text-white/40 hover:text-white/80 transition-colors"
            >
              {isExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
            </button>
            {onClose && (
              <button
                onClick={onClose}
                className="p-1.5 text-white/40 hover:text-red-400 transition-colors"
              >
                <X size={18} />
              </button>
            )}
          </div>
        </div>

        {/* Body */}
        <AnimatePresence>
          {isExpanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.3 }}
            >
              {/* Key Metrics Bar */}
              {keyMetrics && keyMetrics.length > 0 && (
                <div className="px-6 py-3 border-b border-white/5 bg-white/[0.02]">
                  <div className="flex flex-wrap gap-4">
                    {keyMetrics.map((m, i) => (
                      <div key={i} className="flex items-baseline gap-1.5">
                        <span className="text-xs text-white/40">{m.label}:</span>
                        <span className="text-sm font-bold text-industrial-400">
                          {typeof m.value === 'number'
                            ? m.value.toLocaleString(locale, { maximumFractionDigits: 2 })
                            : m.value}
                        </span>
                        {m.unit && <span className="text-xs text-white/30">{m.unit}</span>}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Analysis Text */}
              <div
                ref={textRef}
                className="px-6 py-5 max-h-[500px] overflow-y-auto custom-scrollbar"
              >
                {isLoading && !analysis ? (
                  <div className="flex items-center gap-3 py-8 justify-center">
                    <div className="w-5 h-5 border-2 border-industrial-500/30 border-t-industrial-500 rounded-full animate-spin" />
                    <span className="text-white/50 text-sm">{t('ai.analyzingWithAgent')} ({agentRole})...</span>
                  </div>
                ) : (
                  <div className="prose prose-invert max-w-none">
                    <div className="text-sm text-white/80 leading-relaxed whitespace-pre-wrap">
                      {displayedText || analysis || t('ai.noAnalysis')}
                      {isTyping && (
                        <span className="inline-block w-2 h-4 bg-industrial-400 ml-0.5 animate-pulse" />
                      )}
                    </div>
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Hidden Executive Report for PDF generation */}
      <ExecutiveReport
        ref={reportRef}
        moduleName={moduleName}
        wellName={wellName}
        agentRole={agentRole}
        confidence={confidence}
        keyMetrics={keyMetrics}
        analysisText={analysis || ''}
      />
    </motion.div>
  );
};

export default AIAnalysisPanel;
