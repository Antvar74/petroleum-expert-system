/**
 * DDRReportPDF.tsx — Hidden component that renders DDR report HTML for pdf generation.
 * Uses html2pdf.js pattern from ExecutiveReport.tsx.
 * Generates IADC-format daily drilling reports.
 */
import React, { forwardRef } from 'react';
import { useTranslation } from 'react-i18next';

/* ─── types ─── */
interface Operation {
  from_time: number;
  to_time: number;
  hours: number;
  iadc_code: string;
  category: string;
  description: string;
  depth_start?: number | null;
  depth_end?: number | null;
  is_npt: boolean;
  npt_code?: string;
}

interface BHAComponent {
  component_type: string;
  od: number;
  length: number;
  weight: number;
  serial_number?: string;
}

interface DDRReportPDFProps {
  wellName: string;
  reportNumber: number;
  reportDate: string;
  reportType: string;
  depthStart?: number;
  depthEnd?: number;
  depthTVD?: number;
  headerData: Record<string, any>;
  operations: Operation[];
  drillingParams: Record<string, any>;
  mudProperties: Record<string, any>;
  bhaData: BHAComponent[];
  gasMonitoring: Record<string, any>;
  costSummary: Record<string, any>;
  completionData?: Record<string, any>;
  terminationData?: Record<string, any>;
  status: string;
}

/* ─── helpers ─── */
const fmtNum = (v: any, dec = 1): string => {
  if (v === undefined || v === null || v === '') return '—';
  const n = Number(v);
  return isNaN(n) ? String(v) : n.toFixed(dec);
};

const fmtMoney = (v: any): string => {
  if (v === undefined || v === null || v === '') return '—';
  const n = Number(v);
  if (isNaN(n)) return String(v);
  return '$' + n.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
};

const today = () => new Date().toISOString().split('T')[0];

/* ─── styles (inline for html2pdf) ─── */
const S = {
  page: {
    fontFamily: "'Inter', system-ui, sans-serif",
    color: '#1a1a1a',
    background: 'white',
    padding: '32px 36px',
    maxWidth: 820,
    fontSize: 11,
    lineHeight: 1.45,
  } as React.CSSProperties,
  header: {
    borderBottom: '3px solid #1e40af',
    paddingBottom: 12,
    marginBottom: 20,
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-end',
  } as React.CSSProperties,
  title: {
    fontSize: 20,
    fontWeight: 800,
    color: '#1e3a5f',
    letterSpacing: 1.5,
    textTransform: 'uppercase' as const,
  } as React.CSSProperties,
  subtitle: {
    fontSize: 12,
    color: '#64748b',
    marginTop: 2,
  } as React.CSSProperties,
  metaBlock: {
    textAlign: 'right' as const,
    fontSize: 10,
    color: '#64748b',
    lineHeight: 1.6,
  } as React.CSSProperties,
  sectionTitle: {
    fontSize: 13,
    fontWeight: 700,
    color: '#1e40af',
    borderBottom: '1px solid #e2e8f0',
    paddingBottom: 4,
    marginTop: 18,
    marginBottom: 8,
  } as React.CSSProperties,
  table: {
    width: '100%',
    borderCollapse: 'collapse' as const,
    fontSize: 10,
    marginBottom: 12,
  } as React.CSSProperties,
  th: {
    background: '#1e3a5f',
    color: 'white',
    padding: '5px 6px',
    textAlign: 'left' as const,
    fontWeight: 600,
    fontSize: 9,
    whiteSpace: 'nowrap' as const,
  } as React.CSSProperties,
  td: {
    padding: '4px 6px',
    borderBottom: '1px solid #e2e8f0',
    fontSize: 10,
  } as React.CSSProperties,
  tdNPT: {
    padding: '4px 6px',
    borderBottom: '1px solid #e2e8f0',
    fontSize: 10,
    background: '#fef2f2',
    color: '#b91c1c',
  } as React.CSSProperties,
  kpiGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: 10,
    margin: '12px 0 16px',
  } as React.CSSProperties,
  kpiCard: {
    border: '1px solid #e2e8f0',
    borderRadius: 6,
    padding: '8px 6px',
    textAlign: 'center' as const,
    background: '#f8fafc',
  } as React.CSSProperties,
  kpiLabel: {
    fontSize: 8,
    color: '#64748b',
    textTransform: 'uppercase' as const,
    letterSpacing: 0.5,
  } as React.CSSProperties,
  kpiValue: {
    fontSize: 18,
    fontWeight: 700,
    color: '#1e40af',
  } as React.CSSProperties,
  kpiUnit: {
    fontSize: 8,
    color: '#94a3b8',
  } as React.CSSProperties,
  paramGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: 8,
    marginBottom: 12,
  } as React.CSSProperties,
  paramCell: {
    background: '#f8fafc',
    border: '1px solid #e2e8f0',
    borderRadius: 4,
    padding: '6px 8px',
  } as React.CSSProperties,
  paramLabel: {
    fontSize: 8,
    color: '#64748b',
    textTransform: 'uppercase' as const,
  } as React.CSSProperties,
  paramValue: {
    fontSize: 13,
    fontWeight: 600,
    color: '#1e3a5f',
  } as React.CSSProperties,
  footer: {
    marginTop: 28,
    paddingTop: 8,
    borderTop: '1px solid #e2e8f0',
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: 8,
    color: '#94a3b8',
  } as React.CSSProperties,
  badge: (color: string) => ({
    display: 'inline-block',
    padding: '2px 8px',
    borderRadius: 9999,
    fontSize: 9,
    fontWeight: 700,
    background: color,
    color: 'white',
  } as React.CSSProperties),
};

/* ─── component ─── */
const DDRReportPDF = forwardRef<HTMLDivElement, DDRReportPDFProps>((props, ref) => {
  const {
    wellName, reportNumber, reportDate, reportType,
    depthStart, depthEnd, depthTVD,
    headerData, operations, drillingParams, mudProperties,
    bhaData, gasMonitoring, costSummary,
    completionData, terminationData, status,
  } = props;

  const { t } = useTranslation();

  // Calculate summary KPIs
  const footage = (depthEnd || 0) - (depthStart || 0);
  const totalHours = operations.reduce((s, o) => s + (o.hours || 0), 0);
  const nptHours = operations.filter(o => o.is_npt).reduce((s, o) => s + (o.hours || 0), 0);
  const drillingHours = operations.filter(o => o.category === 'Drilling').reduce((s, o) => s + (o.hours || 0), 0);
  const avgROP = drillingHours > 0 ? footage / drillingHours : 0;

  const statusColor = status === 'approved' ? '#16a34a' : status === 'submitted' ? '#2563eb' : '#94a3b8';
  const typeLabel = reportType === 'drilling' ? t('ddr.pdf.dailyDrillingReport') :
    reportType === 'completion' ? t('ddr.pdf.completionReport') : t('ddr.pdf.terminationReport');

  return (
    <div ref={ref} style={{ display: 'none' }}>
      <div style={S.page}>
        {/* ──── HEADER ──── */}
        <div style={S.header}>
          <div>
            <div style={S.title}>PETROEXPERT — {typeLabel}</div>
            <div style={S.subtitle}>
              {t('ddr.pdf.well')}: <strong>{wellName}</strong> &nbsp;|&nbsp; {t('ddr.pdf.reportNum')}{reportNumber}
              &nbsp;|&nbsp; {t('ddr.pdf.date')}: {reportDate || today()}
              &nbsp;&nbsp;
              <span style={S.badge(statusColor)}>{status?.toUpperCase() || 'DRAFT'}</span>
            </div>
          </div>
          <div style={S.metaBlock}>
            <div>{t('ddr.pdf.operator')}: {headerData.operator || '—'}</div>
            <div>{t('ddr.pdf.contractor')}: {headerData.contractor || '—'}</div>
            <div>{t('ddr.pdf.rig')}: {headerData.rig_name || '—'}</div>
            <div>{t('ddr.pdf.field')}: {headerData.field_name || '—'}</div>
          </div>
        </div>

        {/* ──── KPI SUMMARY ──── */}
        <div style={S.kpiGrid}>
          <div style={S.kpiCard}>
            <div style={S.kpiLabel}>{t('ddr.pdf.depthStart')}</div>
            <div style={S.kpiValue}>{fmtNum(depthStart, 0)}</div>
            <div style={S.kpiUnit}>ft MD</div>
          </div>
          <div style={S.kpiCard}>
            <div style={S.kpiLabel}>{t('ddr.pdf.depthEnd')}</div>
            <div style={S.kpiValue}>{fmtNum(depthEnd, 0)}</div>
            <div style={S.kpiUnit}>ft MD</div>
          </div>
          <div style={S.kpiCard}>
            <div style={S.kpiLabel}>{t('ddr.pdf.footageDrilled')}</div>
            <div style={S.kpiValue}>{fmtNum(footage, 0)}</div>
            <div style={S.kpiUnit}>ft</div>
          </div>
          <div style={S.kpiCard}>
            <div style={S.kpiLabel}>{t('ddr.pdf.averageROP')}</div>
            <div style={S.kpiValue}>{fmtNum(avgROP, 1)}</div>
            <div style={S.kpiUnit}>ft/hr</div>
          </div>
        </div>

        <div style={S.kpiGrid}>
          <div style={S.kpiCard}>
            <div style={S.kpiLabel}>{t('ddr.pdf.totalHours')}</div>
            <div style={S.kpiValue}>{fmtNum(totalHours, 1)}</div>
            <div style={S.kpiUnit}>hrs</div>
          </div>
          <div style={S.kpiCard}>
            <div style={S.kpiLabel}>{t('ddr.pdf.drillingHours')}</div>
            <div style={S.kpiValue}>{fmtNum(drillingHours, 1)}</div>
            <div style={S.kpiUnit}>hrs</div>
          </div>
          <div style={S.kpiCard}>
            <div style={S.kpiLabel}>{t('ddr.pdf.nptHours')}</div>
            <div style={{ ...S.kpiValue, color: nptHours > 0 ? '#dc2626' : '#16a34a' }}>{fmtNum(nptHours, 1)}</div>
            <div style={S.kpiUnit}>hrs</div>
          </div>
          <div style={S.kpiCard}>
            <div style={S.kpiLabel}>TVD</div>
            <div style={S.kpiValue}>{fmtNum(depthTVD, 0)}</div>
            <div style={S.kpiUnit}>ft</div>
          </div>
        </div>

        {/* ──── OPERATIONS LOG ──── */}
        {operations.length > 0 && (
          <>
            <div style={S.sectionTitle}>{t('ddr.pdf.operationsLog')}</div>
            <table style={S.table}>
              <thead>
                <tr>
                  <th style={S.th}>{t('ddr.pdf.from')}</th>
                  <th style={S.th}>{t('ddr.pdf.to')}</th>
                  <th style={S.th}>{t('ddr.pdf.hrs')}</th>
                  <th style={S.th}>{t('ddr.pdf.iadc')}</th>
                  <th style={S.th}>{t('ddr.pdf.category')}</th>
                  <th style={{ ...S.th, width: '40%' }}>{t('ddr.pdf.description')}</th>
                  <th style={S.th}>{t('ddr.pdf.depth')}</th>
                  <th style={S.th}>{t('ddr.pdf.npt')}</th>
                </tr>
              </thead>
              <tbody>
                {operations.map((op, i) => {
                  const rowStyle = op.is_npt ? S.tdNPT : S.td;
                  return (
                    <tr key={i}>
                      <td style={rowStyle}>{fmtNum(op.from_time, 1)}</td>
                      <td style={rowStyle}>{fmtNum(op.to_time, 1)}</td>
                      <td style={rowStyle}>{fmtNum(op.hours, 1)}</td>
                      <td style={rowStyle}>{op.iadc_code || '—'}</td>
                      <td style={rowStyle}>{op.category || '—'}</td>
                      <td style={rowStyle}>{op.description || '—'}</td>
                      <td style={rowStyle}>
                        {op.depth_start != null && op.depth_end != null
                          ? `${fmtNum(op.depth_start, 0)}-${fmtNum(op.depth_end, 0)}`
                          : '—'}
                      </td>
                      <td style={rowStyle}>{op.is_npt ? (op.npt_code || 'YES') : ''}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </>
        )}

        {/* ──── DRILLING PARAMETERS ──── */}
        {drillingParams && Object.keys(drillingParams).length > 0 && (
          <>
            <div style={S.sectionTitle}>{t('ddr.pdf.drillingParams')}</div>
            <div style={S.paramGrid}>
              {[
                { label: t('ddr.pdf.wob'), key: 'wob', unit: 'klb' },
                { label: t('ddr.pdf.rpm'), key: 'rpm', unit: '' },
                { label: t('ddr.pdf.spm'), key: 'spm', unit: '' },
                { label: t('ddr.pdf.flowRate'), key: 'flow_rate', unit: 'gpm' },
                { label: t('ddr.pdf.spp'), key: 'spp', unit: 'psi' },
                { label: t('ddr.pdf.torque'), key: 'torque', unit: 'ft-lb' },
                { label: t('ddr.pdf.rop'), key: 'rop', unit: 'ft/hr' },
                { label: t('ddr.pdf.ecd'), key: 'ecd', unit: 'ppg' },
              ].map(p => (
                <div key={p.key} style={S.paramCell}>
                  <div style={S.paramLabel}>{p.label}</div>
                  <div style={S.paramValue}>
                    {fmtNum(drillingParams[p.key])} <span style={{ fontSize: 9, color: '#94a3b8' }}>{p.unit}</span>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {/* ──── MUD PROPERTIES ──── */}
        {mudProperties && Object.keys(mudProperties).length > 0 && (
          <>
            <div style={S.sectionTitle}>{t('ddr.pdf.mudProperties')}</div>
            <div style={S.paramGrid}>
              {[
                { label: t('ddr.pdf.mudWeight'), key: 'density', unit: 'ppg' },
                { label: t('ddr.pdf.pv'), key: 'pv', unit: 'cP' },
                { label: t('ddr.pdf.yp'), key: 'yp', unit: 'lb/100ft²' },
                { label: t('ddr.pdf.gels10s'), key: 'gels_10s', unit: '' },
                { label: t('ddr.pdf.gels10m'), key: 'gels_10m', unit: '' },
                { label: t('ddr.pdf.filtrate'), key: 'filtrate', unit: 'mL' },
                { label: t('ddr.pdf.ph'), key: 'ph', unit: '' },
                { label: t('ddr.pdf.chlorides'), key: 'chlorides', unit: 'mg/L' },
              ].map(p => (
                <div key={p.key} style={S.paramCell}>
                  <div style={S.paramLabel}>{p.label}</div>
                  <div style={S.paramValue}>
                    {fmtNum(mudProperties[p.key])} <span style={{ fontSize: 9, color: '#94a3b8' }}>{p.unit}</span>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {/* ──── BHA ──── */}
        {bhaData && bhaData.length > 0 && (
          <>
            <div style={S.sectionTitle}>{t('ddr.pdf.bhaConfig')}</div>
            <table style={S.table}>
              <thead>
                <tr>
                  <th style={S.th}>#</th>
                  <th style={S.th}>{t('ddr.pdf.component')}</th>
                  <th style={S.th}>{t('ddr.pdf.odIn')}</th>
                  <th style={S.th}>{t('ddr.pdf.lengthFt')}</th>
                  <th style={S.th}>{t('ddr.pdf.weightLb')}</th>
                  <th style={S.th}>{t('ddr.pdf.serialNum')}</th>
                </tr>
              </thead>
              <tbody>
                {bhaData.map((c, i) => (
                  <tr key={i}>
                    <td style={S.td}>{i + 1}</td>
                    <td style={S.td}>{c.component_type || '—'}</td>
                    <td style={S.td}>{fmtNum(c.od)}</td>
                    <td style={S.td}>{fmtNum(c.length, 0)}</td>
                    <td style={S.td}>{fmtNum(c.weight, 0)}</td>
                    <td style={S.td}>{c.serial_number || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}

        {/* ──── GAS MONITORING ──── */}
        {gasMonitoring && Object.keys(gasMonitoring).length > 0 && (
          <>
            <div style={S.sectionTitle}>{t('ddr.pdf.gasMonitoring')}</div>
            <div style={S.paramGrid}>
              {[
                { label: t('ddr.pdf.backgroundGas'), key: 'background_gas', unit: '%' },
                { label: t('ddr.pdf.connectionGas'), key: 'connection_gas', unit: '%' },
                { label: t('ddr.pdf.tripGas'), key: 'trip_gas', unit: '%' },
                { label: t('ddr.pdf.h2s'), key: 'h2s', unit: 'ppm' },
                { label: t('ddr.pdf.co2'), key: 'co2', unit: '%' },
              ].map(p => (
                <div key={p.key} style={S.paramCell}>
                  <div style={S.paramLabel}>{p.label}</div>
                  <div style={{
                    ...S.paramValue,
                    color: (p.key === 'h2s' && Number(gasMonitoring[p.key]) > 10) ? '#dc2626' : '#1e3a5f',
                  }}>
                    {fmtNum(gasMonitoring[p.key])} <span style={{ fontSize: 9, color: '#94a3b8' }}>{p.unit}</span>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {/* ──── COST SUMMARY ──── */}
        {costSummary && Object.keys(costSummary).length > 0 && (
          <>
            <div style={S.sectionTitle}>{t('ddr.pdf.costSummary')}</div>
            <div style={{ ...S.paramGrid, gridTemplateColumns: 'repeat(3, 1fr)' }}>
              {[
                { label: t('ddr.pdf.rigCost'), key: 'rig_cost' },
                { label: t('ddr.pdf.services'), key: 'services' },
                { label: t('ddr.pdf.consumables'), key: 'consumables' },
                { label: t('ddr.pdf.dayTotal'), key: 'total_day' },
                { label: t('ddr.pdf.cumulative'), key: 'total_cumulative' },
                { label: t('ddr.pdf.afeRemaining'), key: 'afe_remaining' },
              ].map(p => (
                <div key={p.key} style={S.paramCell}>
                  <div style={S.paramLabel}>{p.label}</div>
                  <div style={{
                    ...S.paramValue,
                    color: p.key === 'afe_remaining' && Number(costSummary[p.key]) < 0 ? '#dc2626' : '#1e3a5f',
                  }}>
                    {fmtMoney(costSummary[p.key])}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {/* ──── COMPLETION DATA (if applicable) ──── */}
        {reportType === 'completion' && completionData && Object.keys(completionData).length > 0 && (
          <>
            <div style={S.sectionTitle}>{t('ddr.pdf.completionParams')}</div>
            <div style={S.paramGrid}>
              {[
                { label: t('ddr.pdf.fracPressure'), key: 'frac_pressure', unit: 'psi' },
                { label: t('ddr.pdf.fracRate'), key: 'frac_rate', unit: 'bpm' },
                { label: t('ddr.pdf.proppantType'), key: 'proppant_type', unit: '' },
                { label: t('ddr.pdf.proppantVolume'), key: 'proppant_volume', unit: 'lbs' },
                { label: t('ddr.pdf.acidType'), key: 'acid_type', unit: '' },
                { label: t('ddr.pdf.acidConc'), key: 'acid_concentration', unit: '%' },
                { label: t('ddr.pdf.acidVolume'), key: 'acid_volume', unit: 'gal' },
              ].map(p => (
                <div key={p.key} style={S.paramCell}>
                  <div style={S.paramLabel}>{p.label}</div>
                  <div style={S.paramValue}>
                    {completionData[p.key] != null ? String(completionData[p.key]) : '—'}{' '}
                    <span style={{ fontSize: 9, color: '#94a3b8' }}>{p.unit}</span>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {/* ──── TERMINATION DATA (if applicable) ──── */}
        {reportType === 'termination' && terminationData && Object.keys(terminationData).length > 0 && (
          <>
            <div style={S.sectionTitle}>{t('ddr.pdf.terminationData')}</div>
            <div style={{ ...S.paramGrid, gridTemplateColumns: 'repeat(2, 1fr)' }}>
              {[
                { label: t('ddr.pdf.wellheadType'), key: 'wellhead_type' },
                { label: t('ddr.pdf.ratedPressure'), key: 'wellhead_pressure' },
                { label: t('ddr.pdf.xmasTreeType'), key: 'xmas_tree_type' },
                { label: t('ddr.pdf.paBarriers'), key: 'pa_barriers' },
              ].map(p => (
                <div key={p.key} style={S.paramCell}>
                  <div style={S.paramLabel}>{p.label}</div>
                  <div style={S.paramValue}>{terminationData[p.key] || '—'}</div>
                </div>
              ))}
            </div>
            {terminationData.well_summary && (
              <div style={{ background: '#f8fafc', padding: 12, borderRadius: 6, border: '1px solid #e2e8f0', fontSize: 10, marginTop: 8 }}>
                <strong>{t('ddr.pdf.wellSummary')}:</strong> {terminationData.well_summary}
              </div>
            )}
          </>
        )}

        {/* ──── FOOTER ──── */}
        <div style={S.footer}>
          <span>{t('ddr.pdf.footerConfidential')}</span>
          <span>{t('ddr.pdf.generated')}: {new Date().toLocaleString()}</span>
          <span>{t('ddr.pdf.well')}: {wellName} | {t('ddr.pdf.reportNum')}{reportNumber}</span>
        </div>
      </div>
    </div>
  );
});

DDRReportPDF.displayName = 'DDRReportPDF';
export default DDRReportPDF;
