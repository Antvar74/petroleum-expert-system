/**
 * CasingProgramSchematic.tsx — Visual wellbore schematic showing casing string.
 * Displays OD, weight, grade, depths, and cement column.
 */
import React from 'react';
import ChartContainer from '../ChartContainer';
import { Columns } from 'lucide-react';

interface CasingProgramSchematicProps {
  summary: any;
  params: any;
  height?: number;
}

const CasingProgramSchematic: React.FC<CasingProgramSchematicProps> = ({ summary, params, height = 380 }) => {
  if (!summary && !params) return null;

  const grade = summary?.selected_grade || '—';
  const status = summary?.overall_status;
  const od = params?.casing_od_in;
  const weight = params?.casing_weight_ppf;
  const tvd = params?.tvd_ft || 0;
  const cementTop = params?.cement_top_tvd_ft || 0;
  const cementDensity = params?.cement_density_ppg;

  // SVG layout
  const w = 400, h = 340;
  const casingLeft = 140, casingRight = 260;
  const topY = 30, bottomY = 300;
  const cementTopY = topY + ((cementTop / (tvd || 1)) * (bottomY - topY));

  return (
    <ChartContainer title="Esquema de Casing" icon={Columns} height={height} isFluid>
      <div className="flex flex-col h-full">
        <svg viewBox={`0 0 ${w} ${h}`} className="flex-1" preserveAspectRatio="xMidYMid meet">
          {/* Surface */}
          <line x1={60} y1={topY} x2={340} y2={topY} stroke="rgba(255,255,255,0.3)" strokeWidth={2} />
          <text x={50} y={topY - 5} fill="rgba(255,255,255,0.5)" fontSize={10} textAnchor="end">Surface</text>

          {/* Open hole */}
          <rect x={120} y={topY} width={160} height={bottomY - topY}
            fill="rgba(139,92,40,0.1)" stroke="rgba(139,92,40,0.3)" strokeWidth={1} strokeDasharray="4 4" rx={2} />

          {/* Cement column (annular) */}
          <rect x={120} y={cementTopY} width={casingLeft - 120} height={bottomY - cementTopY}
            fill="rgba(107,114,128,0.3)" stroke="none" />
          <rect x={casingRight} y={cementTopY} width={280 - casingRight} height={bottomY - cementTopY}
            fill="rgba(107,114,128,0.3)" stroke="none" />

          {/* Casing string */}
          <rect x={casingLeft} y={topY} width={casingRight - casingLeft} height={bottomY - topY}
            fill="rgba(99,102,241,0.15)" stroke="#6366f1" strokeWidth={2} rx={2} />

          {/* Grade label inside casing */}
          <text x={(casingLeft + casingRight) / 2} y={(topY + bottomY) / 2 - 15}
            fill="#6366f1" fontSize={16} fontWeight="bold" textAnchor="middle">{grade}</text>
          <text x={(casingLeft + casingRight) / 2} y={(topY + bottomY) / 2 + 5}
            fill="rgba(255,255,255,0.5)" fontSize={10} textAnchor="middle">{od}" {weight} ppf</text>

          {/* Cement TOC annotation */}
          <line x1={80} y1={cementTopY} x2={120} y2={cementTopY}
            stroke="#9ca3af" strokeDasharray="3 3" />
          <text x={75} y={cementTopY + 4} fill="#9ca3af" fontSize={9} textAnchor="end">TOC {cementTop} ft</text>

          {/* Shoe depth */}
          <line x1={casingLeft} y1={bottomY} x2={casingRight} y2={bottomY}
            stroke="#ef4444" strokeWidth={3} />
          <text x={(casingLeft + casingRight) / 2} y={bottomY + 15}
            fill="#ef4444" fontSize={10} textAnchor="middle">Zapata: {tvd} ft TVD</text>

          {/* Cement density */}
          <text x={300} y={cementTopY + (bottomY - cementTopY) / 2}
            fill="#9ca3af" fontSize={9} textAnchor="start">{cementDensity} ppg</text>

          {/* Status badge */}
          <rect x={w / 2 - 40} y={5} width={80} height={18} rx={9}
            fill={status === 'ALL PASS' ? 'rgba(34,197,94,0.2)' : 'rgba(239,68,68,0.2)'} />
          <text x={w / 2} y={17}
            fill={status === 'ALL PASS' ? '#22c55e' : '#ef4444'}
            fontSize={9} fontWeight="bold" textAnchor="middle">{status}</text>
        </svg>
      </div>
    </ChartContainer>
  );
};

export default CasingProgramSchematic;
