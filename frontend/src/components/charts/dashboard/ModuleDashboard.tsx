/**
 * ModuleDashboard.tsx — Global summary dashboard with module cards.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import {
  Activity, Droplets, AlertTriangle, Shield, ChevronRight, BarChart3,
  Waves, Anchor, Wrench, Filter, ClipboardList,
} from 'lucide-react';
import SparklineChart from './SparklineChart';

interface ModuleDashboardProps {
  onNavigate: (view: string) => void;
  wellId?: number;
}

interface ModuleCard {
  id: string;
  view: string;
  nameKey: string;
  descKey: string;
  icon: React.ElementType;
  color: string;
  bgColor: string;
  sparkColor: string;
}

const modules: ModuleCard[] = [
  {
    id: 'td',
    view: 'torque-drag',
    nameKey: 'modules.torqueDrag',
    descKey: 'dashboard.moduleDescTD',
    icon: Activity,
    color: 'text-orange-400',
    bgColor: 'bg-orange-500/10 border-orange-500/20',
    sparkColor: '#f97316',
  },
  {
    id: 'hyd',
    view: 'hydraulics',
    nameKey: 'modules.hydraulicsECD',
    descKey: 'dashboard.moduleDescHyd',
    icon: Droplets,
    color: 'text-cyan-400',
    bgColor: 'bg-cyan-500/10 border-cyan-500/20',
    sparkColor: '#06b6d4',
  },
  {
    id: 'sp',
    view: 'stuck-pipe',
    nameKey: 'modules.stuckPipe',
    descKey: 'dashboard.moduleDescSP',
    icon: AlertTriangle,
    color: 'text-yellow-400',
    bgColor: 'bg-yellow-500/10 border-yellow-500/20',
    sparkColor: '#eab308',
  },
  {
    id: 'wc',
    view: 'well-control',
    nameKey: 'modules.wellControl',
    descKey: 'dashboard.moduleDescWC',
    icon: Shield,
    color: 'text-red-400',
    bgColor: 'bg-red-500/10 border-red-500/20',
    sparkColor: '#ef4444',
  },
  {
    id: 'cu',
    view: 'wellbore-cleanup',
    nameKey: 'modules.wellboreCleanup',
    descKey: 'dashboard.moduleDescCU',
    icon: Waves,
    color: 'text-green-400',
    bgColor: 'bg-green-500/10 border-green-500/20',
    sparkColor: '#22c55e',
  },
  {
    id: 'pf',
    view: 'packer-forces',
    nameKey: 'modules.packerForces',
    descKey: 'dashboard.moduleDescPF',
    icon: Anchor,
    color: 'text-purple-400',
    bgColor: 'bg-purple-500/10 border-purple-500/20',
    sparkColor: '#a855f7',
  },
  {
    id: 'wh',
    view: 'workover-hydraulics',
    nameKey: 'modules.workoverHydraulics',
    descKey: 'dashboard.moduleDescWH',
    icon: Wrench,
    color: 'text-teal-400',
    bgColor: 'bg-teal-500/10 border-teal-500/20',
    sparkColor: '#14b8a6',
  },
  {
    id: 'sc',
    view: 'sand-control',
    nameKey: 'modules.sandControl',
    descKey: 'dashboard.moduleDescSC',
    icon: Filter,
    color: 'text-amber-400',
    bgColor: 'bg-amber-500/10 border-amber-500/20',
    sparkColor: '#f59e0b',
  },
  {
    id: 'ddr',
    view: 'daily-reports',
    nameKey: 'modules.dailyReports',
    descKey: 'dashboard.moduleDescDDR',
    icon: ClipboardList,
    color: 'text-blue-400',
    bgColor: 'bg-blue-500/10 border-blue-500/20',
    sparkColor: '#3b82f6',
  },
];

const ModuleDashboard: React.FC<ModuleDashboardProps> = ({ onNavigate, wellId }) => {
  const { t } = useTranslation();
  return (
    <div className="max-w-6xl mx-auto py-8">
      <div className="flex items-center gap-3 mb-8">
        <BarChart3 className="text-industrial-500" size={28} />
        <div>
          <h2 className="text-2xl font-bold">{t('dashboard.title')}</h2>
          <p className="text-white/40 text-sm">{t('dashboard.wellModuleOverview', { wellId })}</p>
        </div>
      </div>

      {/* Module cards grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        {modules.map((mod, i) => {
          const Icon = mod.icon;
          return (
            <motion.div
              key={mod.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
              onClick={() => onNavigate(mod.view)}
              className={`glass-panel p-6 rounded-2xl border cursor-pointer transition-all hover:scale-[1.02] hover:shadow-xl ${mod.bgColor}`}
            >
              <div className="flex justify-between items-start mb-4">
                <div className="flex items-center gap-3">
                  <div className={`p-2.5 rounded-xl ${mod.bgColor}`}>
                    <Icon size={22} className={mod.color} />
                  </div>
                  <div>
                    <h3 className="font-bold text-lg">{t(mod.nameKey)}</h3>
                    <p className="text-white/30 text-xs mt-0.5">{t(mod.descKey)}</p>
                  </div>
                </div>
                <ChevronRight size={20} className="text-white/20 mt-1" />
              </div>

              {/* Placeholder sparkline area */}
              <div className="flex justify-between items-end mt-4">
                <div className="flex items-center gap-2">
                  <SparklineChart
                    data={[
                      { v: 30 }, { v: 45 }, { v: 38 }, { v: 52 }, { v: 48 },
                      { v: 60 }, { v: 55 }, { v: 70 }, { v: 65 },
                    ]}
                    dataKey="v"
                    color={mod.sparkColor}
                  />
                  <span className="text-[10px] text-white/20">{t('dashboard.sample')}</span>
                </div>
                <span className={`px-3 py-1 rounded-full text-[10px] font-bold ${mod.bgColor} ${mod.color}`}>
                  {t('dashboard.ready')}
                </span>
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Quick info panel */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        className="glass-panel p-6 rounded-2xl border border-white/5"
      >
        <h3 className="font-bold text-sm mb-4">{t('dashboard.systemCapabilities')}</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: t('dashboard.engineeringModules'), value: '9', detail: 'T&D, Hyd, SP, WC, CU, PF, WH, SC, DDR' },
            { label: t('dashboard.chartTypes'), value: '41+', detail: t('dashboard.rechartsCustomSVG') },
            { label: t('dashboard.calculationEngines'), value: '9', detail: t('dashboard.purePython') },
            { label: t('dashboard.pdfExport'), value: t('dashboard.yes'), detail: t('dashboard.professionalReports') },
          ].map((stat, i) => (
            <div key={i} className="bg-white/5 rounded-xl p-4 text-center">
              <p className="text-xs text-white/40 mb-1">{stat.label}</p>
              <p className="text-2xl font-bold text-industrial-400">{stat.value}</p>
              <p className="text-[10px] text-white/20 mt-1">{stat.detail}</p>
            </div>
          ))}
        </div>
      </motion.div>
    </div>
  );
};

export default ModuleDashboard;
