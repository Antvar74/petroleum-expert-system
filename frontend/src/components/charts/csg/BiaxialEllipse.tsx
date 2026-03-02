/**
 * BiaxialEllipse.tsx — API 5C3 biaxial ellipse with full-string state line.
 * Normalized axes: X = σ_a/Fy, Y = Pnet/Pco.
 * Shows the von Mises yield boundary and operating state at each depth.
 *
 * Reference: API TR 5C3 (ISO 10400) — Biaxial yield criterion
 * Equation: (σ_a/Fy)² + (Pnet/Pco)² - (σ_a/Fy)(Pnet/Pco) = 1
 */
import React, { useMemo } from 'react';
import ChartContainer from '../ChartContainer';
import { CircleDot } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface BiaxialStatePoint {
  tvd_ft: number;
  sigma_a_over_fy: number;
  p_net_over_pco: number;
}

interface BiaxialEllipseProps {
  biaxial: {
    yield_strength_psi?: number;
    effective_yield_psi?: number;
    axial_stress_psi?: number;
    stress_ratio?: number;
    original_collapse_psi?: number;
    corrected_collapse_psi?: number;
    reduction_factor?: number;
  } | null;
  stateLine?: BiaxialStatePoint[];
  height?: number;
}

const BiaxialEllipse: React.FC<BiaxialEllipseProps> = ({
  biaxial,
  stateLine,
  height = 350,
}) => {
  const { t } = useTranslation();
  if (!biaxial) return null;

  const originalCollapse = biaxial.original_collapse_psi || 0;
  const correctedCollapse = biaxial.corrected_collapse_psi || 0;
  const reductionFactor = biaxial.reduction_factor || 1.0;

  // SVG dimensions and plot area
  const w = 440, h = 380;
  const margin = { top: 25, right: 25, bottom: 45, left: 55 };
  const plotW = w - margin.left - margin.right;
  const plotH = h - margin.top - margin.bottom;

  // Axis range: -1.25 to 1.25 for both normalized axes
  const axisMin = -1.25;
  const axisMax = 1.25;
  const axisRange = axisMax - axisMin;

  // Coordinate transforms
  const toSvgX = (norm: number) => margin.left + ((norm - axisMin) / axisRange) * plotW;
  const toSvgY = (norm: number) => margin.top + ((axisMax - norm) / axisRange) * plotH;

  // Generate API 5C3 von Mises ellipse boundary points
  // Equation: a² + b² - ab = 1 => b = (a ± sqrt(4 - 3a²)) / 2
  const ellipsePath = useMemo(() => {
    const pts: string[] = [];
    const steps = 120;
    const aMax = 2 / Math.sqrt(3); // ~1.1547

    // Upper branch
    for (let i = 0; i <= steps; i++) {
      const a = -aMax + (2 * aMax * i) / steps;
      const disc = 4 - 3 * a * a;
      if (disc < 0) continue;
      const b = (a + Math.sqrt(disc)) / 2;
      pts.push(`${toSvgX(a)},${toSvgY(b)}`);
    }
    // Lower branch (reverse)
    for (let i = steps; i >= 0; i--) {
      const a = -aMax + (2 * aMax * i) / steps;
      const disc = 4 - 3 * a * a;
      if (disc < 0) continue;
      const b = (a - Math.sqrt(disc)) / 2;
      pts.push(`${toSvgX(a)},${toSvgY(b)}`);
    }

    return pts.length > 0 ? `M ${pts[0]} ${pts.slice(1).map(p => `L ${p}`).join(' ')} Z` : '';
  }, []);

  // State line points (from backend or fallback single point)
  const statePoints = useMemo(() => {
    if (stateLine?.length) return stateLine;
    // Fallback: single operating point from biaxial summary data
    const yp = biaxial?.yield_strength_psi || biaxial?.effective_yield_psi;
    if (biaxial?.axial_stress_psi != null && yp && yp > 0) {
      const sa = biaxial.axial_stress_psi / yp;
      return [{ tvd_ft: 0, sigma_a_over_fy: sa, p_net_over_pco: 0 }];
    }
    return [];
  }, [stateLine, biaxial]);

  // Operating point (surface condition — always visible as the key design point)
  const operatingPoint = useMemo(() => {
    const yp = biaxial?.yield_strength_psi || biaxial?.effective_yield_psi;
    if (biaxial?.axial_stress_psi != null && yp && yp > 0 && originalCollapse > 0) {
      const sa = biaxial.axial_stress_psi / yp;
      const pRatio = biaxial.stress_ratio != null ? biaxial.stress_ratio : sa;
      return { x: pRatio, y: -(correctedCollapse / originalCollapse - 1) };
    }
    return null;
  }, [biaxial, originalCollapse, correctedCollapse]);

  const ticks = [-1.0, -0.5, 0, 0.5, 1.0];

  return (
    <ChartContainer title={t('casingDesign.chartTitles.biaxialEllipse')} icon={CircleDot} height={height} isFluid>
      <div className="flex flex-col h-full">
        <svg viewBox={`0 0 ${w} ${h}`} className="flex-1" preserveAspectRatio="xMidYMid meet">
          {/* Grid */}
          {ticks.map(t => (
            <React.Fragment key={`grid-${t}`}>
              <line x1={toSvgX(t)} y1={margin.top} x2={toSvgX(t)} y2={h - margin.bottom}
                stroke="rgba(255,255,255,0.06)" />
              <line x1={margin.left} y1={toSvgY(t)} x2={w - margin.right} y2={toSvgY(t)}
                stroke="rgba(255,255,255,0.06)" />
            </React.Fragment>
          ))}

          {/* Zero axes (stronger) */}
          <line x1={toSvgX(0)} y1={margin.top} x2={toSvgX(0)} y2={h - margin.bottom}
            stroke="rgba(255,255,255,0.15)" />
          <line x1={margin.left} y1={toSvgY(0)} x2={w - margin.right} y2={toSvgY(0)}
            stroke="rgba(255,255,255,0.15)" />

          {/* Yield ellipse (filled + stroke) */}
          <path d={ellipsePath} fill="#6366f1" fillOpacity={0.05}
            stroke="#6366f1" strokeWidth={2} strokeDasharray="4 4" opacity={0.7} />

          {/* State line */}
          {statePoints.length > 1 && (
            <polyline
              points={statePoints
                .map(p => `${toSvgX(p.sigma_a_over_fy)},${toSvgY(p.p_net_over_pco)}`)
                .join(' ')}
              fill="none"
              stroke="#ef4444"
              strokeWidth={2.5}
              strokeLinejoin="round"
            />
          )}

          {/* State line dots */}
          {statePoints.map((p, i) => {
            const sx = toSvgX(Math.max(axisMin, Math.min(axisMax, p.sigma_a_over_fy)));
            const sy = toSvgY(Math.max(axisMin, Math.min(axisMax, p.p_net_over_pco)));
            const isFirst = i === 0;
            const isLast = i === statePoints.length - 1;
            const showLabel = isFirst || isLast;
            return (
              <g key={i}>
                <circle cx={sx} cy={sy} r={showLabel ? 5 : 2.5}
                  fill={isFirst ? '#ef4444' : isLast ? '#3b82f6' : '#ef4444'}
                  opacity={showLabel ? 0.9 : 0.4} />
                {isFirst && (
                  <text x={sx + 8} y={sy + 4} fill="#ef4444" fontSize={9} fontWeight="bold">
                    {t('casingDesign.surface')}
                  </text>
                )}
                {isLast && statePoints.length > 1 && (
                  <text x={sx + 8} y={sy + 4} fill="#3b82f6" fontSize={9} fontWeight="bold">
                    {p.tvd_ft.toLocaleString()} ft
                  </text>
                )}
              </g>
            );
          })}

          {/* Operating point — prominent red dot (design point at surface) */}
          {operatingPoint && (
            <g>
              <circle cx={toSvgX(operatingPoint.x)} cy={toSvgY(0)} r={8}
                fill="#ef4444" opacity={0.8} />
              <circle cx={toSvgX(operatingPoint.x)} cy={toSvgY(0)} r={13}
                fill="none" stroke="#ef4444" strokeWidth={1} opacity={0.3} />
              <text x={toSvgX(operatingPoint.x) + 16} y={toSvgY(0) + 4}
                fill="#ef4444" fontSize={9} fontWeight="bold">
                σ/Fy = {operatingPoint.x.toFixed(3)}
              </text>
            </g>
          )}

          {/* Axis labels */}
          <text x={w / 2} y={h - 5} fill="rgba(255,255,255,0.5)" fontSize={10} textAnchor="middle">
            σ_a / Fy (Axial Stress Ratio)
          </text>
          <text x={12} y={h / 2} fill="rgba(255,255,255,0.5)" fontSize={10}
            textAnchor="middle" transform={`rotate(-90, 12, ${h / 2})`}>
            Pnet / Pco (Pressure Ratio)
          </text>

          {/* Tick labels */}
          {ticks.map(t => (
            <React.Fragment key={`tick-${t}`}>
              <text x={toSvgX(t)} y={h - margin.bottom + 14}
                fill="rgba(255,255,255,0.3)" fontSize={9} textAnchor="middle">
                {t.toFixed(1)}
              </text>
              <text x={margin.left - 6} y={toSvgY(t) + 3}
                fill="rgba(255,255,255,0.3)" fontSize={9} textAnchor="end">
                {t.toFixed(1)}
              </text>
            </React.Fragment>
          ))}

          {/* Legend */}
          <text x={w - margin.right - 5} y={margin.top + 12}
            fill="rgba(255,255,255,0.3)" fontSize={9} textAnchor="end">
            {t('casingDesign.yieldEnvelope')}
          </text>
        </svg>

        {/* Data summary */}
        <div className="grid grid-cols-3 gap-3 text-xs border-t border-white/10 pt-3 pb-4">
          <div className="text-center">
            <div className="text-gray-500">{t('casingDesign.originalCollapse')}</div>
            <div className="font-mono font-bold text-white">{originalCollapse.toLocaleString()} psi</div>
          </div>
          <div className="text-center">
            <div className="text-gray-500">{t('casingDesign.correctedCollapse')}</div>
            <div className="font-mono font-bold text-yellow-400">{correctedCollapse.toLocaleString()} psi</div>
          </div>
          <div className="text-center">
            <div className="text-gray-500">{t('casingDesign.reductionFactor')}</div>
            <div className="font-mono font-bold text-indigo-400">{reductionFactor.toFixed(3)}</div>
          </div>
        </div>
      </div>
    </ChartContainer>
  );
};

export default BiaxialEllipse;
