/**
 * FreePointIndicator.tsx — Visual wellbore schematic showing free point depth.
 */
import React from 'react';
import { motion } from 'framer-motion';

interface FreePointIndicatorProps {
  freePointDepth: number; // ft
  totalDepth: number;     // ft (assumed total depth for scaling)
  pipeSafe: boolean;
  pullPctYield: number;
  height?: number;
}

const FreePointIndicator: React.FC<FreePointIndicatorProps> = ({
  freePointDepth,
  totalDepth,
  pipeSafe,
  pullPctYield,
  height = 350,
}) => {
  const effectiveTD = totalDepth || freePointDepth * 1.2;
  const fpRatio = Math.min(freePointDepth / effectiveTD, 0.95);

  const svgH = height - 40;
  const svgW = 140;
  const pipeW = 24;
  const pipeX = svgW / 2 - pipeW / 2;
  const topMargin = 20;
  const bottomMargin = 20;
  const usableH = svgH - topMargin - bottomMargin;
  const fpY = topMargin + fpRatio * usableH;

  return (
    <div className="glass-panel p-6 rounded-2xl border border-white/5 print-chart">
      <h4 className="font-bold text-sm mb-4 text-center">Free Point Estimate</h4>

      <svg width={svgW} height={svgH} viewBox={`0 0 ${svgW} ${svgH}`} className="mx-auto">
        {/* Wellbore (outer) */}
        <rect
          x={pipeX - 8} y={topMargin} width={pipeW + 16} height={usableH}
          fill="rgba(255,255,255,0.03)" stroke="rgba(255,255,255,0.1)"
          strokeWidth={1} rx={4}
        />

        {/* Free section (green) */}
        <motion.rect
          x={pipeX} y={topMargin} width={pipeW}
          height={fpY - topMargin}
          fill="rgba(34,197,94,0.3)"
          stroke="#22c55e" strokeWidth={1.5} rx={2}
          initial={{ height: 0 }}
          animate={{ height: fpY - topMargin }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        />

        {/* Stuck section (red) */}
        <motion.rect
          x={pipeX} y={fpY} width={pipeW}
          height={usableH - (fpY - topMargin)}
          fill="rgba(239,68,68,0.2)"
          stroke="#ef4444" strokeWidth={1.5} rx={2}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
        />

        {/* Free point marker */}
        <motion.g
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.8 }}
        >
          <line x1={pipeX - 15} y1={fpY} x2={pipeX + pipeW + 15} y2={fpY}
            stroke="#f97316" strokeWidth={2} strokeDasharray="4 2" />
          <circle cx={pipeX + pipeW + 15} cy={fpY} r={4} fill="#f97316" />
        </motion.g>

        {/* Labels */}
        <text x={pipeX + pipeW + 22} y={fpY + 4} fill="#f97316" fontSize="10" fontWeight="700">
          {freePointDepth.toLocaleString()} ft
        </text>
        <text x={pipeX + pipeW / 2} y={topMargin + (fpY - topMargin) / 2 + 3}
          fill="#22c55e" fontSize="8" fontWeight="600" textAnchor="middle">
          FREE
        </text>
        <text x={pipeX + pipeW / 2} y={fpY + (usableH - (fpY - topMargin)) / 2 + 3}
          fill="#ef4444" fontSize="8" fontWeight="600" textAnchor="middle">
          STUCK
        </text>

        {/* Surface label */}
        <text x={pipeX + pipeW / 2} y={14} fill="rgba(255,255,255,0.4)" fontSize="9" textAnchor="middle">
          Surface
        </text>
        {/* TD label */}
        <text x={pipeX + pipeW / 2} y={svgH - 5} fill="rgba(255,255,255,0.4)" fontSize="9" textAnchor="middle">
          TD
        </text>
      </svg>

      {/* Pull safety indicator */}
      <div className={`mt-4 p-3 rounded-lg text-center text-xs font-bold ${pipeSafe ? 'bg-green-500/10 text-green-400 border border-green-500/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'}`}>
        Pull: {pullPctYield}% of yield — {pipeSafe ? 'SAFE' : 'EXCEEDS 80%'}
      </div>
    </div>
  );
};

export default FreePointIndicator;
