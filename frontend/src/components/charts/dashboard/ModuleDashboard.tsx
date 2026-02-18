/**
 * ModuleDashboard.tsx — Global summary dashboard with module cards.
 */
import React from 'react';
import { motion } from 'framer-motion';
import {
  Activity, Droplets, AlertTriangle, Shield, ChevronRight, BarChart3,
} from 'lucide-react';
import SparklineChart from './SparklineChart';

interface ModuleDashboardProps {
  onNavigate: (view: string) => void;
  wellId: number;
}

interface ModuleCard {
  id: string;
  view: string;
  name: string;
  icon: React.ElementType;
  color: string;
  bgColor: string;
  description: string;
  sparkColor: string;
}

const modules: ModuleCard[] = [
  {
    id: 'td',
    view: 'torque-drag',
    name: 'Torque & Drag',
    icon: Activity,
    color: 'text-orange-400',
    bgColor: 'bg-orange-500/10 border-orange-500/20',
    description: 'Real-time axial force analysis, hookload prediction, and buckling assessment',
    sparkColor: '#f97316',
  },
  {
    id: 'hyd',
    view: 'hydraulics',
    name: 'Hydraulics / ECD',
    icon: Droplets,
    color: 'text-cyan-400',
    bgColor: 'bg-cyan-500/10 border-cyan-500/20',
    description: 'Pressure loss distribution, ECD profiling, bit optimization, and surge/swab analysis',
    sparkColor: '#06b6d4',
  },
  {
    id: 'sp',
    view: 'stuck-pipe',
    name: 'Stuck Pipe Analyzer',
    icon: AlertTriangle,
    color: 'text-yellow-400',
    bgColor: 'bg-yellow-500/10 border-yellow-500/20',
    description: 'Mechanism diagnosis, risk matrix assessment, free point estimation',
    sparkColor: '#eab308',
  },
  {
    id: 'wc',
    view: 'well-control',
    name: 'Well Control',
    icon: Shield,
    color: 'text-red-400',
    bgColor: 'bg-red-500/10 border-red-500/20',
    description: 'Kill sheet calculations, pressure schedules, volumetric & bullhead methods',
    sparkColor: '#ef4444',
  },
];

const ModuleDashboard: React.FC<ModuleDashboardProps> = ({ onNavigate, wellId }) => {
  return (
    <div className="max-w-6xl mx-auto py-8">
      <div className="flex items-center gap-3 mb-8">
        <BarChart3 className="text-industrial-500" size={28} />
        <div>
          <h2 className="text-2xl font-bold">Engineering Dashboard</h2>
          <p className="text-white/40 text-sm">Well #{wellId} — Module Overview</p>
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
                    <h3 className="font-bold text-lg">{mod.name}</h3>
                    <p className="text-white/30 text-xs mt-0.5">{mod.description}</p>
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
                  <span className="text-[10px] text-white/20">sample</span>
                </div>
                <span className={`px-3 py-1 rounded-full text-[10px] font-bold ${mod.bgColor} ${mod.color}`}>
                  READY
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
        <h3 className="font-bold text-sm mb-4">System Capabilities</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'Engineering Modules', value: '4', detail: 'T&D, Hyd, SP, WC' },
            { label: 'Chart Types', value: '20+', detail: 'Recharts + Custom SVG' },
            { label: 'Calculation Engines', value: '4', detail: 'Pure Python' },
            { label: 'PDF Export', value: 'Yes', detail: 'Professional reports' },
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
