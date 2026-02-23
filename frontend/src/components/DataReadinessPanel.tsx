/**
 * DataReadinessPanel.tsx — Shows data readiness checklist per module/phase/event.
 *
 * Fetches requirements from /modules/{id}/data-requirements and cross-checks
 * against currentData to show status with readiness percentage.
 */
import React, { useState, useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ClipboardCheck, CheckCircle2, XCircle, AlertTriangle,
  ChevronDown, FileUp, Info,
} from 'lucide-react';
import { API_BASE_URL } from '../config';

interface DataRequirement {
  key: string;
  label: string;
  source?: string;
  unit?: string;
  min_points?: number;
  default?: string;
  impact?: string;
}

interface RequirementsResponse {
  module: string;
  phase: string;
  event: string | null;
  required: DataRequirement[];
  optional: DataRequirement[];
  recommended_files: string[];
  min_readiness_pct: number;
}

interface DataReadinessPanelProps {
  moduleId: string;
  phase: string;
  event?: string;
  currentData: Record<string, unknown>;
  onPhaseChange?: (phase: string) => void;
  onEventChange?: (event: string | undefined) => void;
  phases?: string[];
  events?: string[];
}

const DataReadinessPanel: React.FC<DataReadinessPanelProps> = ({
  moduleId,
  phase,
  event,
  currentData,
  onPhaseChange,
  onEventChange,
  phases = ['drilling', 'completion', 'workover'],
  events = [],
}) => {
  const { t } = useTranslation();
  const [requirements, setRequirements] = useState<RequirementsResponse | null>(null);
  const [isExpanded, setIsExpanded] = useState(true);
  const [isLoading, setIsLoading] = useState(false);

  // -- Fetch requirements ---------------------------------------------------
  useEffect(() => {
    const fetchRequirements = async () => {
      setIsLoading(true);
      try {
        const params = new URLSearchParams({ phase });
        if (event) params.append('event', event);
        const res = await fetch(`${API_BASE_URL}/modules/${moduleId}/data-requirements?${params}`);
        if (res.ok) {
          const data = await res.json();
          setRequirements(data);
        }
      } catch {
        // Silently fail -- panel is supplementary
      } finally {
        setIsLoading(false);
      }
    };
    fetchRequirements();
  }, [moduleId, phase, event]);

  // -- Compute readiness ----------------------------------------------------
  const readiness = useMemo(() => {
    if (!requirements) return { pct: 0, present: 0, total: 0, items: [] as Array<DataRequirement & { isPresent: boolean; value: unknown; type: 'required' }>, optionalItems: [] as Array<DataRequirement & { isPresent: boolean; value: unknown; type: 'optional' }> };

    const items = requirements.required.map((req) => {
      const value = currentData[req.key];
      const isPresent = value !== undefined && value !== null && value !== '' &&
        !(Array.isArray(value) && value.length === 0);
      return { ...req, isPresent, value, type: 'required' as const };
    });

    const optionalItems = requirements.optional.map((opt) => {
      const value = currentData[opt.key];
      const isPresent = value !== undefined && value !== null && value !== '';
      return { ...opt, isPresent, value, type: 'optional' as const };
    });

    const present = items.filter((i) => i.isPresent).length;
    const total = items.length;
    const pct = total > 0 ? Math.round((present / total) * 100) : 0;

    return { pct, present, total, items, optionalItems };
  }, [requirements, currentData]);

  if (!requirements && !isLoading) return null;

  const minPct = requirements?.min_readiness_pct ?? 60;
  const isSufficient = readiness.pct >= minPct;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-panel rounded-2xl border border-white/5 mb-6 overflow-hidden"
    >
      {/* -- Header -- */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-white/5 transition-colors"
      >
        <div className="flex items-center gap-3">
          <ClipboardCheck size={20} className="text-industrial-400" />
          <span className="font-bold text-sm">{t('dataReadiness.title')}</span>
          {onPhaseChange && (
            <span className="text-xs text-white/40 bg-white/5 px-2 py-0.5 rounded-full">
              {t(`dataReadiness.phases.${phase}`)}
              {event && ` \u2022 ${event.replace(/_/g, ' ')}`}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          {/* Readiness badge */}
          <div className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold ${
            isSufficient
              ? 'bg-green-500/10 text-green-400 border border-green-500/20'
              : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
          }`}>
            <span>{readiness.pct}%</span>
          </div>
          <ChevronDown
            size={16}
            className={`text-white/30 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          />
        </div>
      </button>

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            <div className="px-4 pb-4 space-y-4">
              {/* -- Phase/Event selectors -- */}
              {(onPhaseChange || onEventChange) && (
                <div className="flex gap-3">
                  {onPhaseChange && (
                    <select
                      value={phase}
                      onChange={(e) => onPhaseChange(e.target.value)}
                      className="bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-white/70 focus:outline-none focus:border-industrial-400"
                    >
                      {phases.map((p) => (
                        <option key={p} value={p}>{t(`dataReadiness.phases.${p}`)}</option>
                      ))}
                    </select>
                  )}
                  {onEventChange && events.length > 0 && (
                    <select
                      value={event || ''}
                      onChange={(e) => onEventChange(e.target.value || undefined)}
                      className="bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-white/70 focus:outline-none focus:border-industrial-400"
                    >
                      <option value="">{t('dataReadiness.noEvent')}</option>
                      {events.map((ev) => (
                        <option key={ev} value={ev}>{ev.replace(/_/g, ' ')}</option>
                      ))}
                    </select>
                  )}
                </div>
              )}

              {/* -- Required fields -- */}
              <div>
                <p className="text-xs font-semibold text-white/50 mb-2">{t('dataReadiness.required')}</p>
                <div className="space-y-1.5">
                  {readiness.items.map((item) => (
                    <div key={item.key} className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2">
                        {item.isPresent ? (
                          <CheckCircle2 size={14} className="text-green-400 shrink-0" />
                        ) : (
                          <XCircle size={14} className="text-red-400 shrink-0" />
                        )}
                        <span className={item.isPresent ? 'text-white/70' : 'text-red-300'}>
                          {item.label}
                        </span>
                      </div>
                      <span className="text-white/30 text-[10px]">
                        {item.isPresent
                          ? `${typeof item.value === 'number' ? item.value : t('dataReadiness.present')}${item.unit ? ` ${item.unit}` : ''}`
                          : t('dataReadiness.missingAction')}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* -- Optional fields -- */}
              {readiness.optionalItems && readiness.optionalItems.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-white/50 mb-2">{t('dataReadiness.optional')}</p>
                  <div className="space-y-1.5">
                    {readiness.optionalItems.map((item) => (
                      <div key={item.key} className="flex items-center justify-between text-xs">
                        <div className="flex items-center gap-2">
                          {item.isPresent ? (
                            <CheckCircle2 size={14} className="text-green-400 shrink-0" />
                          ) : (
                            <AlertTriangle size={14} className="text-amber-400 shrink-0" />
                          )}
                          <span className="text-white/50">{item.label}</span>
                        </div>
                        <span className="text-white/30 text-[10px]">
                          {item.isPresent
                            ? `${typeof item.value === 'number' ? item.value : t('dataReadiness.present')}`
                            : t('dataReadiness.usingDefault', { value: item.default || '\u2014' })}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* -- Recommended files -- */}
              {requirements?.recommended_files && requirements.recommended_files.length > 0 && (
                <div className="flex items-start gap-2 bg-white/5 rounded-xl p-3">
                  <FileUp size={14} className="text-industrial-400 mt-0.5 shrink-0" />
                  <div>
                    <p className="text-[10px] text-white/40 font-semibold mb-1">{t('dataReadiness.recommendedUploads')}</p>
                    <p className="text-xs text-white/60">{requirements.recommended_files.join(', ')}</p>
                  </div>
                </div>
              )}

              {/* -- Status message -- */}
              <div className={`flex items-center gap-2 text-[10px] px-3 py-2 rounded-lg ${
                isSufficient ? 'bg-green-500/5 text-green-400' : 'bg-amber-500/5 text-amber-400'
              }`}>
                <Info size={12} />
                <span>
                  {isSufficient ? t('dataReadiness.sufficient') : t('dataReadiness.insufficient')}
                  {' \u2014 '}{readiness.present}/{readiness.total} {t('dataReadiness.required').toLowerCase()}
                </span>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

export default DataReadinessPanel;
