/**
 * InfluxAnalysisGauge.tsx — Gauge for influx severity + info cards.
 */
import React from 'react';
import { motion } from 'framer-motion';
import GaugeChart from '../GaugeChart';
import { Droplets } from 'lucide-react';

interface InfluxAnalysisGaugeProps {
  influxType: string;
  influxHeight: number;        // ft
  influxGradient?: number;     // psi/ft
  formationPressure: number;   // psi
  killMudWeight: number;       // ppg
  sidpp: number;               // psi
  sicp: number;                // psi
}

const getInfluxColor = (type: string): string => {
  const lower = type?.toLowerCase() || '';
  if (lower.includes('gas')) return '#ef4444';
  if (lower.includes('oil')) return '#f97316';
  if (lower.includes('salt') || lower.includes('water')) return '#3b82f6';
  return '#a855f7';
};

const getInfluxSeverity = (sidpp: number, sicp: number, influxHeight: number): number => {
  // Severity score 0-100 based on:
  // - SICP/SIDPP ratio (gas has much higher SICP)
  // - Influx height relative to typical max (100 ft)
  const ratio = sicp / (sidpp || 1);
  const ratioScore = Math.min(ratio / 3 * 50, 50);  // max 50 from ratio
  const heightScore = Math.min(influxHeight / 100 * 50, 50); // max 50 from height
  return Math.round(ratioScore + heightScore);
};

const InfluxAnalysisGauge: React.FC<InfluxAnalysisGaugeProps> = ({
  influxType,
  influxHeight,
  formationPressure,
  killMudWeight,
  sidpp,
  sicp,
}) => {
  const severity = getInfluxSeverity(sidpp, sicp, influxHeight);
  const influxColor = getInfluxColor(influxType);

  const cards = [
    { label: 'Influx Type', value: influxType || 'Unknown', unit: '', color: influxColor },
    { label: 'Influx Height', value: influxHeight.toFixed(1), unit: 'ft', color: 'text-white' },
    { label: 'Formation P', value: formationPressure.toLocaleString(), unit: 'psi', color: 'text-red-400' },
    { label: 'Kill Mud Wt', value: killMudWeight.toFixed(2), unit: 'ppg', color: 'text-industrial-400' },
  ];

  return (
    <div className="glass-panel p-6 rounded-2xl border border-white/5 print-chart">
      <div className="flex items-center gap-2 mb-4">
        <Droplets size={18} className="text-industrial-400" />
        <h4 className="font-bold text-sm">Influx Analysis</h4>
      </div>

      <div className="flex flex-col items-center mb-4">
        <GaugeChart
          value={severity}
          min={0}
          max={100}
          unit="severity"
          label="Influx Severity"
          optimalRange={[0, 30]}
          size={160}
        />

        {/* Influx type icon badge */}
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: 'spring', stiffness: 300, delay: 0.5 }}
          className="mt-2 px-4 py-1.5 rounded-full text-xs font-bold border"
          style={{
            backgroundColor: `${influxColor}15`,
            borderColor: `${influxColor}40`,
            color: influxColor,
          }}
        >
          {influxType?.toUpperCase() || 'UNKNOWN'} INFLUX
        </motion.div>
      </div>

      {/* Info cards grid */}
      <div className="grid grid-cols-2 gap-3">
        {cards.map((card, i) => (
          <motion.div
            key={card.label}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 + i * 0.1 }}
            className="bg-white/5 rounded-lg p-3 text-center"
          >
            <p className="text-[10px] text-white/40 mb-1">{card.label}</p>
            <p className={`text-lg font-bold ${typeof card.color === 'string' && card.color.startsWith('#') ? '' : card.color}`}
              style={typeof card.color === 'string' && card.color.startsWith('#') ? { color: card.color } : {}}>
              {card.value}
            </p>
            {card.unit && <p className="text-[10px] text-white/30">{card.unit}</p>}
          </motion.div>
        ))}
      </div>

      {/* SIDPP vs SICP comparison */}
      <div className="mt-4 flex gap-3">
        <div className="flex-1 bg-white/5 rounded-lg p-2 text-center">
          <p className="text-[10px] text-white/30">SIDPP</p>
          <p className="text-sm font-bold text-white">{sidpp} psi</p>
        </div>
        <div className="flex-1 bg-white/5 rounded-lg p-2 text-center">
          <p className="text-[10px] text-white/30">SICP</p>
          <p className="text-sm font-bold text-white">{sicp} psi</p>
        </div>
        <div className="flex-1 bg-white/5 rounded-lg p-2 text-center">
          <p className="text-[10px] text-white/30">SICP/SIDPP</p>
          <p className="text-sm font-bold" style={{ color: influxColor }}>
            {(sicp / (sidpp || 1)).toFixed(2)}
          </p>
        </div>
      </div>
    </div>
  );
};

export default InfluxAnalysisGauge;
