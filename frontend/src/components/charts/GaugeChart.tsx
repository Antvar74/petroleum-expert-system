/**
 * GaugeChart.tsx — Semicircular gauge with animated needle.
 * Used for HSI, Impact Force, Jet Velocity, % at Bit, Influx severity.
 */
import React from 'react';
import { motion } from 'framer-motion';

interface GaugeThreshold {
  value: number;
  color: string;
}

interface GaugeChartProps {
  value: number;
  min: number;
  max: number;
  unit: string;
  label: string;
  thresholds?: GaugeThreshold[];
  size?: number;
  optimalRange?: [number, number]; // [low, high] for green zone
}

const GaugeChart: React.FC<GaugeChartProps> = ({
  value,
  min,
  max,
  unit,
  label,
  thresholds,
  size = 180,
  optimalRange,
}) => {
  const cx = size / 2;
  const cy = size / 2 + 10;
  const radius = size / 2 - 20;
  const strokeWidth = 14;

  // Clamp value to range
  const clamped = Math.min(Math.max(value, min), max);
  const fraction = (clamped - min) / (max - min || 1);

  // Angle: 180 (left) to 0 (right), so we go from -180 to 0 degrees in SVG
  const startAngle = Math.PI; // 180 degrees (left)
  const endAngle = 0; // 0 degrees (right)
  const needleAngle = startAngle - fraction * Math.PI;

  // Arc path helper
  const polarToCartesian = (angle: number, r: number) => ({
    x: cx + r * Math.cos(angle),
    y: cy - r * Math.sin(angle),
  });

  // Background arc segments (colored by threshold or gradient)
  const renderArcSegments = () => {
    if (thresholds && thresholds.length >= 2) {
      const segments: React.ReactNode[] = [];
      const sorted = [...thresholds].sort((a, b) => a.value - b.value);

      for (let i = 0; i < sorted.length; i++) {
        const segStart = i === 0 ? min : sorted[i - 1].value;
        const segEnd = sorted[i].value;
        const f1 = (segStart - min) / (max - min || 1);
        const f2 = (segEnd - min) / (max - min || 1);
        const a1 = startAngle - f1 * Math.PI;
        const a2 = startAngle - f2 * Math.PI;
        const p1 = polarToCartesian(a1, radius);
        const p2 = polarToCartesian(a2, radius);
        const largeArc = (a1 - a2) > Math.PI ? 1 : 0;

        segments.push(
          <path
            key={i}
            d={`M ${p1.x} ${p1.y} A ${radius} ${radius} 0 ${largeArc} 1 ${p2.x} ${p2.y}`}
            fill="none"
            stroke={sorted[i].color}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            opacity={0.3}
          />
        );
      }
      return segments;
    }

    const p1 = polarToCartesian(startAngle, radius);
    const p2 = polarToCartesian(endAngle, radius);
    return (
      <path
        d={`M ${p1.x} ${p1.y} A ${radius} ${radius} 0 1 1 ${p2.x} ${p2.y}`}
        fill="none"
        stroke="rgba(255,255,255,0.08)"
        strokeWidth={strokeWidth}
        strokeLinecap="round"
      />
    );
  };

  // Active arc (filled portion)
  const renderActiveArc = () => {
    if (fraction <= 0) return null;
    const p1 = polarToCartesian(startAngle, radius);
    const p2 = polarToCartesian(needleAngle, radius);
    const largeArc = (startAngle - needleAngle) > Math.PI ? 1 : 0;

    let color = '#f97316';
    if (optimalRange) {
      if (value >= optimalRange[0] && value <= optimalRange[1]) color = '#22c55e';
      else if (value < optimalRange[0] * 0.7 || value > optimalRange[1] * 1.3) color = '#ef4444';
      else color = '#eab308';
    }

    return (
      <motion.path
        d={`M ${p1.x} ${p1.y} A ${radius} ${radius} 0 ${largeArc} 1 ${p2.x} ${p2.y}`}
        fill="none"
        stroke={color}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 0.8, ease: 'easeOut' }}
      />
    );
  };

  // Needle
  const needleTip = polarToCartesian(needleAngle, radius - 25);

  // Display value
  const displayValue = typeof value === 'number'
    ? value >= 1000 ? value.toLocaleString(undefined, { maximumFractionDigits: 0 })
      : value.toFixed(value < 10 ? 2 : 1)
    : value;

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size / 2 + 30} viewBox={`0 0 ${size} ${size / 2 + 30}`}>
        {/* Background arc */}
        {renderArcSegments()}

        {/* Active arc */}
        {renderActiveArc()}

        {/* Needle */}
        <motion.line
          x1={cx}
          y1={cy}
          x2={needleTip.x}
          y2={needleTip.y}
          stroke="white"
          strokeWidth={2}
          strokeLinecap="round"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
        />
        <circle cx={cx} cy={cy} r={4} fill="white" />

        {/* Min / Max labels */}
        <text x={cx - radius} y={cy + 18} fill="rgba(255,255,255,0.3)" fontSize="9" textAnchor="middle">{min}</text>
        <text x={cx + radius} y={cy + 18} fill="rgba(255,255,255,0.3)" fontSize="9" textAnchor="middle">{max}</text>

        {/* Center value */}
        <text x={cx} y={cy - 8} fill="white" fontSize="22" fontWeight="700" textAnchor="middle">
          {displayValue}
        </text>
        <text x={cx} y={cy + 10} fill="rgba(255,255,255,0.4)" fontSize="10" textAnchor="middle">
          {unit}
        </text>
      </svg>
      <p className="text-xs text-white/50 mt-1">{label}</p>
    </div>
  );
};

export default GaugeChart;
