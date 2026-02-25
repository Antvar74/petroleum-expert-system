import { forwardRef } from 'react';
import { useTranslation } from 'react-i18next';
import { useLanguage } from '../hooks/useLanguage';

interface KeyMetric {
  label: string;
  value: string | number;
  unit?: string;
}

interface ExecutiveReportProps {
  moduleName: string;
  wellName: string;
  agentRole: string;
  confidence: string;
  keyMetrics: KeyMetric[];
  analysisText: string;
}

/**
 * Executive Report — Hidden layout captured by html2pdf.js for PDF generation.
 * White background, professional layout, designed for A4 printing.
 */
const ExecutiveReport = forwardRef<HTMLDivElement, ExecutiveReportProps>(
  ({ moduleName, wellName, agentRole, keyMetrics, analysisText }, ref) => {
    const { t } = useTranslation();
    const { language } = useLanguage();
    const locale = language === 'es' ? 'es-MX' : 'en-US';
    const now = new Date();
    const dateStr = now.toLocaleDateString(locale, { year: 'numeric', month: '2-digit', day: '2-digit' });
    const timeStr = now.toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' });

    // Parse analysis text into sections
    const sections = parseAnalysisSections(analysisText || '');

    return (
      <div ref={ref} style={{ display: 'none' }} className="executive-report">
        {/* Header */}
        <div className="executive-report-header">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <div className="executive-report-title">PETROEXPERT</div>
              <div style={{ fontSize: '16px', fontWeight: 600, color: '#475569', marginTop: '4px' }}>
                {t('ai.executiveReport')}: {moduleName}
              </div>
            </div>
            <div className="executive-report-meta">
              <div style={{ fontWeight: 700, fontSize: '13px', color: '#1e3a5f' }}>{t('ai.well')}: {wellName}</div>
              <div>{t('ai.date')}: {dateStr} | {timeStr}</div>
              <div>{t('ai.analyst')}: {agentRole}</div>
            </div>
          </div>
        </div>

        {/* KPI Grid */}
        {keyMetrics && keyMetrics.length > 0 && (
          <>
            <div style={{ fontSize: '12px', fontWeight: 700, textTransform: 'uppercase', color: '#64748b', marginBottom: '8px', letterSpacing: '0.5px' }}>
              {t('ai.kpiTitle')}
            </div>
            <div className="executive-kpi-grid">
              {keyMetrics.map((m, i) => (
                <div key={i} className="executive-kpi-card">
                  <div className="executive-kpi-value">
                    {typeof m.value === 'number' ? formatNumber(m.value, locale) : m.value}
                  </div>
                  <div className="executive-kpi-label">
                    {m.label} {m.unit ? `(${m.unit})` : ''}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {/* Analysis Sections */}
        {sections.map((section, idx) => {
          let sectionClass = 'executive-section';
          if (section.type === 'summary') sectionClass += ' summary';
          if (section.type === 'alert') sectionClass += ' alert';
          if (section.type === 'recommendation') sectionClass += ' recommendation';

          return (
            <div key={idx} className={sectionClass}>
              {section.title && (
                <div className="executive-section-title" style={{ paddingBottom: '6px', marginBottom: '10px' }}>
                  {section.title}
                </div>
              )}
              <div style={{ fontSize: '12px', lineHeight: '1.7', color: '#334155', whiteSpace: 'pre-wrap' }}>
                {section.content}
              </div>
            </div>
          );
        })}

        {/* Footer */}
        <div className="executive-footer">
          <span>{t('ai.expertSystem')}</span>
          <span>{t('ai.confidential')}</span>
          <span>{t('ai.generatedBy')}: {agentRole}</span>
        </div>
      </div>
    );
  }
);

ExecutiveReport.displayName = 'ExecutiveReport';

// ================================================================
// Helpers
// ================================================================

function formatNumber(val: number, locale: string = 'en-US'): string {
  if (val === 0) return '0';
  if (Math.abs(val) >= 1000) return val.toLocaleString(locale, { maximumFractionDigits: 1 });
  if (Math.abs(val) < 1) return val.toFixed(3);
  return val.toFixed(1);
}

interface ParsedSection {
  title: string;
  content: string;
  type: 'summary' | 'alert' | 'recommendation' | 'default';
}

function parseAnalysisSections(text: string): ParsedSection[] {
  if (!text) return [{ title: '', content: 'No analysis available.', type: 'default' }];

  // Try to split by numbered headers like "1. EXECUTIVE SUMMARY" or "## EXECUTIVE SUMMARY"
  const headerPatterns = [
    /(?:^|\n)\s*\d+\.\s*(RESUMEN EJECUTIVO|EXECUTIVE SUMMARY)/i,
    /(?:^|\n)\s*\d+\.\s*(HALLAZGOS CLAVE|KEY FINDINGS)/i,
    /(?:^|\n)\s*\d+\.\s*(ALERTAS Y RIESGOS|ALERTS AND RISKS)/i,
    /(?:^|\n)\s*\d+\.\s*(RECOMENDACIONES OPERATIVAS|OPERATIONAL RECOMMENDATIONS)/i,
    /(?:^|\n)\s*\d+\.\s*(CONCLUSI[OÓ]N GERENCIAL|MANAGERIAL CONCLUSION)/i,
  ];

  const sectionTypes: Array<ParsedSection['type']> = ['summary', 'default', 'alert', 'recommendation', 'default'];

  // Find all header positions
  const positions: Array<{ start: number; title: string; type: ParsedSection['type'] }> = [];
  headerPatterns.forEach((pat, idx) => {
    const match = text.match(pat);
    if (match && match.index !== undefined) {
      positions.push({
        start: match.index,
        title: match[1],
        type: sectionTypes[idx],
      });
    }
  });

  // Also check for markdown-style headers (## Header)
  const mdHeaderRegex = /(?:^|\n)\s*#{1,3}\s*(.*)/g;
  let mdMatch;
  while ((mdMatch = mdHeaderRegex.exec(text)) !== null) {
    const title = mdMatch[1].trim();
    // Only add if not already captured by numbered patterns
    const alreadyCaptured = positions.some(p => Math.abs(p.start - mdMatch!.index!) < 10);
    if (!alreadyCaptured && title.length > 3) {
      let type: ParsedSection['type'] = 'default';
      if (/resumen|summary|ejecutivo/i.test(title)) type = 'summary';
      if (/alerta|alert|riesgo|risk/i.test(title)) type = 'alert';
      if (/recomendaci|recommendation/i.test(title)) type = 'recommendation';
      positions.push({ start: mdMatch.index!, title, type });
    }
  }

  // Sort by position
  positions.sort((a, b) => a.start - b.start);

  if (positions.length === 0) {
    // No headers found — return as single section
    return [{ title: '', content: text.trim(), type: 'default' }];
  }

  // Extract sections
  const sections: ParsedSection[] = [];

  // If there's content before the first header
  if (positions[0].start > 0) {
    const preContent = text.substring(0, positions[0].start).trim();
    if (preContent) {
      sections.push({ title: '', content: preContent, type: 'default' });
    }
  }

  for (let i = 0; i < positions.length; i++) {
    const startOfContent = positions[i].start + text.substring(positions[i].start).indexOf('\n') + 1;
    const endOfContent = i + 1 < positions.length ? positions[i + 1].start : text.length;
    const content = text.substring(startOfContent, endOfContent).trim();

    // Clean up the content: remove leading "---" or "***" separators
    const cleanContent = content.replace(/^[-*=]{3,}\s*/gm, '').trim();

    sections.push({
      title: positions[i].title,
      content: cleanContent,
      type: positions[i].type,
    });
  }

  return sections.length > 0 ? sections : [{ title: '', content: text.trim(), type: 'default' }];
}

export default ExecutiveReport;
