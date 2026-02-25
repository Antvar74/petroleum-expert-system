/**
 * DDRListView.tsx — Reports table/list with filter, edit, delete actions
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import {
  ClipboardList, Edit3, Trash2, FileText, Filter,
} from 'lucide-react';

export interface ReportListItem {
  id: number;
  report_type: string;
  report_date: string;
  report_number: number;
  depth_md_start: number | null;
  depth_md_end: number | null;
  status: string;
  summary: { footage_drilled: number; avg_rop: number; npt_hours: number; npt_percentage: number };
}

export interface DDRListViewProps {
  reports: ReportListItem[];
  filterType: string;
  onFilterChange: (ft: string) => void;
  onEdit: (id: number) => void;
  onDelete: (id: number) => void;
}

const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const { t } = useTranslation();
  const colors: Record<string, string> = {
    draft: 'bg-yellow-500/20 text-yellow-400',
    submitted: 'bg-blue-500/20 text-blue-400',
    approved: 'bg-green-500/20 text-green-400',
  };
  return <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase ${colors[status] || colors.draft}`}>{t(`ddr.${status}`) || status}</span>;
};

const DDRListView: React.FC<DDRListViewProps> = ({
  reports,
  filterType,
  onFilterChange,
  onEdit,
  onDelete,
}) => {
  const { t } = useTranslation();

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
      {/* Filters */}
      <div className="flex gap-3 items-center">
        <Filter size={14} className="text-white/30" />
        {['', 'mobilization', 'drilling', 'completion', 'termination'].map(ft => (
          <button
            key={ft}
            onClick={() => onFilterChange(ft)}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${filterType === ft ? 'bg-blue-600 text-white' : 'bg-white/5 text-white/40 hover:bg-white/10'}`}
          >
            {ft ? t(`ddr.${ft}`) || ft.charAt(0).toUpperCase() + ft.slice(1) : t('ddr.allTypes') || 'All'}
          </button>
        ))}
      </div>

      {reports.length === 0 ? (
        <div className="glass-panel p-12 text-center">
          <ClipboardList size={48} className="mx-auto text-white/10 mb-4" />
          <p className="text-white/30 text-sm">{t('ddr.noReportsYet') || 'No reports yet. Create a new DDR to get started.'}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {reports.map(r => (
            <div key={r.id} className="glass-panel p-5 rounded-xl border border-white/5 flex items-center justify-between hover:border-blue-500/30 transition-colors group">
              <div className="flex items-center gap-4 flex-1 min-w-0">
                <div className="w-10 h-10 bg-blue-500/10 border border-blue-500/20 rounded-lg flex items-center justify-center flex-shrink-0">
                  <FileText size={18} className="text-blue-400" />
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-sm">#{r.report_number}</span>
                    <StatusBadge status={r.status} />
                    <span className="text-[10px] text-white/20 uppercase font-bold">{r.report_type}</span>
                  </div>
                  <p className="text-xs text-white/40 mt-0.5">{r.report_date} — {r.summary.footage_drilled} ft drilled, ROP {r.summary.avg_rop} ft/hr, NPT {r.summary.npt_hours}h ({r.summary.npt_percentage}%)</p>
                </div>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                <button onClick={() => onEdit(r.id)} className="p-2 rounded-lg hover:bg-white/5 text-white/30 hover:text-white transition-colors" title={t('common.edit')}>
                  <Edit3 size={16} />
                </button>
                <button onClick={() => onDelete(r.id)} className="p-2 rounded-lg hover:bg-red-500/10 text-white/20 hover:text-red-400 transition-colors" title={t('common.delete')}>
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </motion.div>
  );
};

export default DDRListView;
