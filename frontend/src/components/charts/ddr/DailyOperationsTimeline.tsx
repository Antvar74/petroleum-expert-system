/**
 * DailyOperationsTimeline.tsx — 24-hour timeline with color-coded activities.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import ChartContainer from '../ChartContainer';
import { Clock } from 'lucide-react';

interface Operation {
  from_time: number;
  to_time: number;
  hours: number;
  category?: string;
  iadc_code?: string;
  description?: string;
  is_npt?: boolean;
}

interface DailyOperationsTimelineProps {
  operations: Operation[];
  height?: number;
  title?: string;
}

const CATEGORY_COLORS: Record<string, string> = {
  Drilling: '#22c55e',
  Tripping: '#3b82f6',
  Connection: '#06b6d4',
  Circulating: '#8b5cf6',
  'Casing/Cementing': '#a855f7',
  Casing: '#a855f7',
  Cementing: '#a855f7',
  Logging: '#14b8a6',
  NPT: '#ef4444',
  Waiting: '#f97316',
  'Rig Repair': '#eab308',
  Testing: '#ec4899',
  Completion: '#f59e0b',
  Survey: '#6366f1',
  Other: '#6b7280',
};

const getColor = (op: Operation): string => {
  if (op.is_npt) return '#ef4444';
  const cat = op.category || '';
  return CATEGORY_COLORS[cat] || CATEGORY_COLORS.Other;
};

const DailyOperationsTimeline: React.FC<DailyOperationsTimelineProps> = ({
  operations,
  height = 180,
  title = 'Daily Operations Timeline',
}) => {
  const { t } = useTranslation();

  if (!operations || operations.length === 0) {
    return (
      <ChartContainer title={title} icon={Clock} height={height} isFluid>
        <div className="flex items-center justify-center h-full text-white/20 text-sm">
          {t('ddr.charts.noOperationsLogged')}
        </div>
      </ChartContainer>
    );
  }

  // Build hour markers
  const hourMarkers = Array.from({ length: 25 }, (_, i) => i);

  // Get unique categories for legend
  const categories = [...new Set(operations.map(op => op.is_npt ? 'NPT' : (op.category || 'Other')))];

  return (
    <ChartContainer title={title} icon={Clock} height={height} isFluid>
      <div className="space-y-3">
        {/* Hour axis */}
        <div className="relative h-6">
          {hourMarkers.map(h => (
            <span
              key={h}
              className="absolute text-[9px] text-white/30 -translate-x-1/2"
              style={{ left: `${(h / 24) * 100}%` }}
            >
              {h}
            </span>
          ))}
        </div>

        {/* Timeline bar */}
        <div className="relative h-10 bg-white/5 rounded-lg overflow-hidden">
          {operations.map((op, i) => {
            const left = (op.from_time / 24) * 100;
            const width = ((op.to_time - op.from_time) / 24) * 100;
            const color = getColor(op);
            return (
              <div
                key={i}
                className="absolute top-0 h-full opacity-85 hover:opacity-100 transition-opacity cursor-pointer group"
                style={{ left: `${left}%`, width: `${Math.max(width, 0.5)}%`, backgroundColor: color }}
                title={`${op.from_time}-${op.to_time}h [${op.iadc_code || ''}] ${op.description || op.category || ''}`}
              >
                {width > 6 && (
                  <span className="absolute inset-0 flex items-center justify-center text-[8px] text-white font-bold truncate px-1">
                    {op.iadc_code || op.category?.substring(0, 4) || ''}
                  </span>
                )}
              </div>
            );
          })}
        </div>

        {/* Legend */}
        <div className="flex flex-wrap gap-3 mt-2">
          {categories.map(cat => (
            <div key={cat} className="flex items-center gap-1.5">
              <div
                className="w-2.5 h-2.5 rounded-sm"
                style={{ backgroundColor: CATEGORY_COLORS[cat] || CATEGORY_COLORS.Other }}
              />
              <span className="text-[10px] text-white/40">{cat}</span>
            </div>
          ))}
        </div>
      </div>
    </ChartContainer>
  );
};

export default DailyOperationsTimeline;
