/**
 * DDRKPIDashboard.tsx — KPI cards + charts for DDR module
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';

// Charts
import TimeDepthChart from '../charts/ddr/TimeDepthChart';
import CostTrackingChart from '../charts/ddr/CostTrackingChart';
import NPTBreakdownChart from '../charts/ddr/NPTBreakdownChart';
import DailyOperationsTimeline from '../charts/ddr/DailyOperationsTimeline';
import ROPProgressChart from '../charts/ddr/ROPProgressChart';

export interface DDRKPIDashboardProps {
  cumulativeStats: Record<string, number>;
  timeDepthData: Record<string, number>[];
  costData: Record<string, number>[];
  nptBreakdown: Record<string, unknown>;
  operations: { from_time: number; to_time: number; hours: number; iadc_code: string; category: string; description: string; depth_start: number | null; depth_end: number | null; is_npt: boolean; npt_code: string }[];
  hasReports: boolean;
  latestReportId: number | null;
}

const DDRKPIDashboard: React.FC<DDRKPIDashboardProps> = ({
  cumulativeStats,
  timeDepthData,
  costData,
  nptBreakdown,
  operations,
  hasReports,
  latestReportId,
}) => {
  const { t } = useTranslation();

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      {/* Cumulative Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: t('ddr.totalFootage'), value: `${cumulativeStats.total_footage || 0}`, unit: 'ft', color: 'text-green-400' },
          { label: t('ddr.avgROP'), value: `${cumulativeStats.avg_rop_overall || 0}`, unit: 'ft/hr', color: 'text-orange-400' },
          { label: t('ddr.nptHours'), value: `${cumulativeStats.total_npt_hours || 0}`, unit: 'hrs', color: 'text-red-400' },
          { label: t('ddr.totalCost'), value: `$${(cumulativeStats.total_cost || 0).toLocaleString()}`, unit: '', color: 'text-cyan-400' },
        ].map((stat, i) => (
          <div key={i} className="glass-panel p-4 rounded-xl border border-white/5 text-center">
            <p className="text-xs text-white/40 mb-1">{stat.label}</p>
            <p className={`text-2xl font-bold ${stat.color}`}>{stat.value}</p>
            {stat.unit && <p className="text-[10px] text-white/20 mt-0.5">{stat.unit}</p>}
          </div>
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <TimeDepthChart data={timeDepthData} title={t('ddr.timeVsDepth')} />
        <ROPProgressChart
          data={timeDepthData.map(d => ({ day: d.day, date: d.date, footage: d.footage, avg_rop: d.footage > 0 ? +(d.footage / 8).toFixed(1) : 0 }))}
          title={t('ddr.ropProgress')}
        />
        <CostTrackingChart data={costData} title={t('ddr.costVsAFE')} />
        <NPTBreakdownChart
          byCategory={(nptBreakdown as Record<string, unknown>).by_category as Record<string, number> || {}}
          totalHours={((nptBreakdown as Record<string, unknown>).total_npt_hours as number) || 0}
          title={t('ddr.nptBreakdown')}
        />
      </div>

      {/* Timeline of latest report */}
      {hasReports && latestReportId && (
        <DailyOperationsTimeline
          operations={operations.filter(o => o.description || o.iadc_code)}
          title={t('ddr.dailyTimeline')}
        />
      )}
    </motion.div>
  );
};

export default DDRKPIDashboard;
