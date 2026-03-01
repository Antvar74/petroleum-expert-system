import { forwardRef } from 'react';
import { useTranslation } from 'react-i18next';
import { useLanguage } from '../hooks/useLanguage';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

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
  chartImages?: Record<string, string>;
}

const CHART_SECTIONS: Record<string, { chartKey: string; figureNum: number; figureTitle: string }> = {
  'SF_VS_DEPTH_ANALYSIS': { chartKey: 'sf-vs-depth', figureNum: 1, figureTitle: 'Safety Factor vs Depth' },
  'BIAXIAL_ANALYSIS': { chartKey: 'biaxial-ellipse', figureNum: 2, figureTitle: 'Biaxial Ellipse API 5C3' },
  'SCENARIO_ENVELOPE_ANALYSIS': { chartKey: 'scenario-envelope', figureNum: 3, figureTitle: 'Multi-Scenario Envelope' },
  'TENSION_PROFILE_ANALYSIS': { chartKey: 'tension-profile', figureNum: 4, figureTitle: 'Tension vs Depth Profile' },
};

interface ChartSection {
  marker: string;
  title: string;
  content: string;
  chartKey?: string;
  figureNum?: number;
  figureTitle?: string;
}

/**
 * Executive Report — Hidden layout captured by html2pdf.js for PDF generation.
 * White background, professional layout, designed for A4 printing.
 */
const ExecutiveReport = forwardRef<HTMLDivElement, ExecutiveReportProps>(
  ({ moduleName, wellName, agentRole, keyMetrics, analysisText, chartImages }, ref) => {
    const { t } = useTranslation();
    const { language } = useLanguage();
    const locale = language === 'es' ? 'es-MX' : 'en-US';
    const now = new Date();
    const dateStr = now.toLocaleDateString(locale, { year: 'numeric', month: '2-digit', day: '2-digit' });
    const timeStr = now.toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' });

    // Parse analysis text into sections (marker-based for casing, legacy fallback for others)
    const sections = parseMarkerSections(analysisText || '');

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

        {/* Analysis Sections with Charts */}
        {sections.map((section, idx) => {
          const chartImg = section.chartKey && chartImages?.[section.chartKey];

          return (
            <div key={idx} className="executive-section" style={{
              pageBreakInside: section.chartKey ? 'avoid' : 'auto',
            }}>
              {section.title && (
                <div className="executive-section-title" style={{ paddingBottom: '6px', marginBottom: '10px' }}>
                  {section.marker === 'EXECUTIVE_SUMMARY' ? '1. EXECUTIVE SUMMARY' :
                   section.marker === 'RECOMMENDATIONS' ? '6. RECOMMENDATIONS' :
                   section.figureNum ? `${section.figureNum + 1}. ${section.title}` :
                   section.title}
                </div>
              )}

              {/* Chart Image */}
              {chartImg && (
                <div className="executive-chart-container">
                  <img
                    src={chartImg}
                    alt={section.figureTitle || ''}
                    className="executive-chart-image"
                  />
                  <div className="executive-chart-caption">
                    Figure {section.figureNum}. {section.figureTitle}
                  </div>
                </div>
              )}

              {/* Analysis Text */}
              <div className="executive-markdown-content">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {section.content}
                </ReactMarkdown>
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

function parseMarkerSections(text: string): ChartSection[] {
  if (!text) return [{ marker: '', title: 'Analysis', content: 'No analysis available.' }];

  // Normalize markers: LLMs often wrap them in bold/italic markdown like **[MARKER]** or *[MARKER]*
  const normalized = text.replace(/\*{1,3}\[([A-Z_]+)\]\*{1,3}/g, '[$1]');

  // Try marker-based parsing first
  const markerRegex = /\[([A-Z_]+)\]/g;
  const markers: Array<{ tag: string; index: number }> = [];
  let m;
  while ((m = markerRegex.exec(normalized)) !== null) {
    markers.push({ tag: m[1], index: m.index });
  }

  if (markers.length === 0) {
    // Fallback: use legacy parser for non-marker analysis
    return parseLegacySections(normalized);
  }

  const sections: ChartSection[] = [];

  // Content before first marker
  if (markers[0].index > 0) {
    const pre = normalized.substring(0, markers[0].index).trim();
    if (pre) sections.push({ marker: '', title: '', content: pre });
  }

  for (let i = 0; i < markers.length; i++) {
    const tag = markers[i].tag;
    const contentStart = markers[i].index + tag.length + 2; // +2 for [ and ]
    const contentEnd = i + 1 < markers.length ? markers[i + 1].index : normalized.length;
    const content = normalized.substring(contentStart, contentEnd).trim();

    const chartInfo = CHART_SECTIONS[tag];
    const title = tag.replace(/_/g, ' ');

    sections.push({
      marker: tag,
      title,
      content,
      chartKey: chartInfo?.chartKey,
      figureNum: chartInfo?.figureNum,
      figureTitle: chartInfo?.figureTitle,
    });
  }

  return sections;
}

function parseLegacySections(text: string): ChartSection[] {
  if (!text) return [{ marker: '', title: '', content: 'No analysis available.' }];

  // Try to split by numbered headers like "1. EXECUTIVE SUMMARY" or "## EXECUTIVE SUMMARY"
  const headerPatterns = [
    /(?:^|\n)\s*\d+\.\s*(RESUMEN EJECUTIVO|EXECUTIVE SUMMARY)/i,
    /(?:^|\n)\s*\d+\.\s*(HALLAZGOS CLAVE|KEY FINDINGS)/i,
    /(?:^|\n)\s*\d+\.\s*(ALERTAS Y RIESGOS|ALERTS AND RISKS)/i,
    /(?:^|\n)\s*\d+\.\s*(RECOMENDACIONES OPERATIVAS|OPERATIONAL RECOMMENDATIONS)/i,
    /(?:^|\n)\s*\d+\.\s*(CONCLUSI[OÓ]N GERENCIAL|MANAGERIAL CONCLUSION)/i,
  ];

  // Find all header positions
  const positions: Array<{ start: number; title: string }> = [];
  headerPatterns.forEach((pat) => {
    const match = text.match(pat);
    if (match && match.index !== undefined) {
      positions.push({
        start: match.index,
        title: match[1],
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
      positions.push({ start: mdMatch.index!, title });
    }
  }

  // Sort by position
  positions.sort((a, b) => a.start - b.start);

  if (positions.length === 0) {
    // No headers found — return as single section
    return [{ marker: '', title: '', content: text.trim() }];
  }

  // Extract sections
  const sections: ChartSection[] = [];

  // If there's content before the first header
  if (positions[0].start > 0) {
    const preContent = text.substring(0, positions[0].start).trim();
    if (preContent) {
      sections.push({ marker: '', title: '', content: preContent });
    }
  }

  for (let i = 0; i < positions.length; i++) {
    const startOfContent = positions[i].start + text.substring(positions[i].start).indexOf('\n') + 1;
    const endOfContent = i + 1 < positions.length ? positions[i + 1].start : text.length;
    const content = text.substring(startOfContent, endOfContent).trim();

    // Clean up the content: remove leading "---" or "***" separators
    const cleanContent = content.replace(/^[-*=]{3,}\s*/gm, '').trim();

    sections.push({
      marker: '',
      title: positions[i].title,
      content: cleanContent,
    });
  }

  return sections.length > 0 ? sections : [{ marker: '', title: '', content: text.trim() }];
}

export default ExecutiveReport;
