/**
 * InteractiveRiskMatrix.tsx — Enhanced 5x5 risk matrix with tooltips and animations.
 */
import React from 'react';
import { motion } from 'framer-motion';

interface InteractiveRiskMatrixProps {
  probability: number; // 1-5
  severity: number;    // 1-5
  riskLevel: string;
  riskScore: number;
  mechanism?: string;
}

const SEVERITY_LABELS = ['Very Low', 'Low', 'Medium', 'High', 'Very High'];
const PROB_LABELS = ['Rare', 'Unlikely', 'Possible', 'Likely', 'Certain'];

const getCellColor = (p: number, s: number): string => {
  const score = p * s;
  if (score >= 20) return 'rgba(239,68,68,0.5)';
  if (score >= 15) return 'rgba(239,68,68,0.35)';
  if (score >= 10) return 'rgba(249,115,22,0.3)';
  if (score >= 5) return 'rgba(234,179,8,0.25)';
  return 'rgba(34,197,94,0.2)';
};

const InteractiveRiskMatrix: React.FC<InteractiveRiskMatrixProps> = ({
  probability,
  severity,
  riskScore,
}) => {
  const gridSize = 5;
  const cellSize = 52;
  const pad = 55;
  const w = gridSize * cellSize + pad + 20;
  const h = gridSize * cellSize + pad + 20;

  return (
    <div className="print-chart">
      <svg viewBox={`0 0 ${w} ${h}`} className="w-full max-w-sm">
        {/* Axis titles */}
        <text x={w / 2} y={h - 2} fill="rgba(255,255,255,0.4)" fontSize="10" fontWeight="600" textAnchor="middle">
          PROBABILITY
        </text>
        <text x={10} y={h / 2 - 10} fill="rgba(255,255,255,0.4)" fontSize="10" fontWeight="600" textAnchor="middle"
          transform={`rotate(-90, 10, ${h / 2 - 10})`}>
          SEVERITY
        </text>

        {/* Grid cells */}
        {Array.from({ length: gridSize }, (_, px) =>
          Array.from({ length: gridSize }, (_, sy) => {
            const x = pad + px * cellSize;
            const y = 10 + (gridSize - 1 - sy) * cellSize;
            const isActive = (px + 1) === probability && (sy + 1) === severity;
            const score = (px + 1) * (sy + 1);

            return (
              <g key={`${px}-${sy}`}>
                <rect
                  x={x} y={y}
                  width={cellSize} height={cellSize}
                  fill={getCellColor(px + 1, sy + 1)}
                  stroke="rgba(255,255,255,0.08)"
                  strokeWidth={1}
                  rx={4}
                />
                <text
                  x={x + cellSize / 2}
                  y={y + cellSize / 2 + 4}
                  fill="rgba(255,255,255,0.15)"
                  fontSize="9"
                  textAnchor="middle"
                >
                  {score}
                </text>

                {/* Active cell indicator */}
                {isActive && (
                  <>
                    <motion.rect
                      x={x + 2} y={y + 2}
                      width={cellSize - 4} height={cellSize - 4}
                      fill="none"
                      stroke="#f97316"
                      strokeWidth={2.5}
                      rx={4}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: [0.5, 1, 0.5] }}
                      transition={{ repeat: Infinity, duration: 2 }}
                    />
                    <motion.circle
                      cx={x + cellSize / 2}
                      cy={y + cellSize / 2}
                      r={14}
                      fill="#f97316"
                      stroke="white"
                      strokeWidth={2}
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ type: 'spring', stiffness: 300 }}
                    />
                    <text
                      x={x + cellSize / 2}
                      y={y + cellSize / 2 + 4}
                      fill="white"
                      fontSize="10"
                      fontWeight="700"
                      textAnchor="middle"
                    >
                      {riskScore}
                    </text>
                  </>
                )}
              </g>
            );
          })
        )}

        {/* Axis labels */}
        {[1, 2, 3, 4, 5].map(n => (
          <g key={`label-${n}`}>
            {/* Probability (bottom) */}
            <text
              x={pad + (n - 0.5) * cellSize}
              y={h - 18}
              fill="rgba(255,255,255,0.35)"
              fontSize="8"
              textAnchor="middle"
            >
              {PROB_LABELS[n - 1]}
            </text>
            {/* Severity (left) */}
            <text
              x={pad - 8}
              y={10 + (gridSize - n + 0.5) * cellSize + 4}
              fill="rgba(255,255,255,0.35)"
              fontSize="8"
              textAnchor="end"
            >
              {SEVERITY_LABELS[n - 1]}
            </text>
          </g>
        ))}
      </svg>

      {/* Legend */}
      <div className="flex justify-center gap-3 mt-3">
        {[
          { label: 'Low', color: 'rgba(34,197,94,0.5)' },
          { label: 'Medium', color: 'rgba(234,179,8,0.5)' },
          { label: 'High', color: 'rgba(249,115,22,0.5)' },
          { label: 'Critical', color: 'rgba(239,68,68,0.5)' },
        ].map(item => (
          <div key={item.label} className="flex items-center gap-1 text-[10px] text-white/40">
            <div className="w-3 h-3 rounded" style={{ backgroundColor: item.color }} />
            {item.label}
          </div>
        ))}
      </div>
    </div>
  );
};

export default InteractiveRiskMatrix;
