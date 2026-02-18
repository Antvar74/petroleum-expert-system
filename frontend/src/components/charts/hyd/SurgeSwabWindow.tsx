/**
 * SurgeSwabWindow.tsx — Operational window visualization for surge/swab margins.
 * Shows MW, Surge ECD, Swab ECD relative to LOT and pore pressure.
 */
import React from 'react';
import { motion } from 'framer-motion';

interface SurgeSwabWindowProps {
  surgeEcd: number;
  swabEcd: number;
  mudWeight: number;
  lotEmw?: number;
  porePressure?: number;
  surgeMargin: string;
  swabMargin: string;
  height?: number;
}

const SurgeSwabWindow: React.FC<SurgeSwabWindowProps> = ({
  surgeEcd,
  swabEcd,
  mudWeight,
  lotEmw = 16,
  porePressure = 8,
  surgeMargin,
  swabMargin,
  height = 350,
}) => {
  const allValues = [surgeEcd, swabEcd, mudWeight, lotEmw, porePressure];
  const minVal = Math.min(...allValues) - 0.5;
  const maxVal = Math.max(...allValues) + 0.5;
  const range = maxVal - minVal || 1;

  const yPos = (v: number) => ((v - minVal) / range) * 100;
  // Invert for top-down display (high EMW at top)
  const barTop = (v: number) => 100 - yPos(v);

  const barWidth = 60;
  const chartHeight = height - 80;

  return (
    <div className="glass-panel p-6 rounded-2xl border border-white/5 print-chart">
      <div className="flex justify-between items-center mb-4">
        <h4 className="font-bold text-sm">Operational Window (Surge/Swab)</h4>
        <div className="flex gap-2">
          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${surgeMargin === 'OK' ? 'bg-green-500/20 text-green-400' : surgeMargin === 'WARNING' ? 'bg-yellow-500/20 text-yellow-400' : 'bg-red-500/20 text-red-400'}`}>
            Surge: {surgeMargin}
          </span>
          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${swabMargin === 'OK' ? 'bg-green-500/20 text-green-400' : swabMargin === 'WARNING' ? 'bg-yellow-500/20 text-yellow-400' : 'bg-red-500/20 text-red-400'}`}>
            Swab: {swabMargin}
          </span>
        </div>
      </div>

      <div className="relative mx-auto" style={{ width: barWidth + 120, height: chartHeight }}>
        {/* Loss zone (above LOT) */}
        <div
          className="absolute bg-red-500/10 border-b border-red-500/30"
          style={{
            left: 30,
            width: barWidth,
            top: 0,
            height: `${barTop(lotEmw)}%`,
          }}
        />

        {/* Safe window */}
        <div
          className="absolute bg-green-500/10"
          style={{
            left: 30,
            width: barWidth,
            top: `${barTop(lotEmw)}%`,
            height: `${yPos(lotEmw) - yPos(porePressure)}%`,
          }}
        />

        {/* Kick zone (below pore pressure) */}
        <div
          className="absolute bg-red-500/10 border-t border-red-500/30"
          style={{
            left: 30,
            width: barWidth,
            top: `${barTop(porePressure)}%`,
            bottom: 0,
          }}
        />

        {/* Marker lines */}
        {[
          { value: lotEmw, label: 'LOT', color: '#ef4444' },
          { value: porePressure, label: 'PP', color: '#3b82f6' },
          { value: mudWeight, label: 'MW', color: '#ffffff' },
          { value: surgeEcd, label: 'Surge', color: '#f97316' },
          { value: swabEcd, label: 'Swab', color: '#06b6d4' },
        ].map((marker, i) => (
          <React.Fragment key={i}>
            <motion.div
              className="absolute"
              style={{
                left: 30,
                width: barWidth,
                top: `${barTop(marker.value)}%`,
                height: 2,
                backgroundColor: marker.color,
                opacity: 0.8,
              }}
              initial={{ scaleX: 0 }}
              animate={{ scaleX: 1 }}
              transition={{ delay: i * 0.1, duration: 0.3 }}
            />
            <span
              className="absolute text-[10px] font-bold"
              style={{
                right: 0,
                top: `calc(${barTop(marker.value)}% - 7px)`,
                color: marker.color,
              }}
            >
              {marker.label}: {marker.value.toFixed(1)}
            </span>
          </React.Fragment>
        ))}

        {/* Y-axis scale */}
        {Array.from({ length: 5 }, (_, i) => {
          const val = minVal + (range * i) / 4;
          return (
            <span
              key={i}
              className="absolute text-[9px] text-white/30"
              style={{ left: 0, top: `${100 - (i / 4) * 100}%`, transform: 'translateY(-50%)' }}
            >
              {val.toFixed(1)}
            </span>
          );
        })}
      </div>

      <p className="text-center text-[10px] text-white/30 mt-2">EMW (ppg)</p>
    </div>
  );
};

export default SurgeSwabWindow;
