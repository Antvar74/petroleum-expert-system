/**
 * WellborePressureProfile.tsx — Wellbore pressure vs depth with pore/frac/kill lines.
 */
import React, { useMemo } from 'react';
import ChartContainer from '../ChartContainer';
import DepthTrack from '../DepthTrack';
import type { DepthSeries, DepthRefLine } from '../DepthTrack';
import { WC_COLORS } from '../ChartTheme';
import { Layers } from 'lucide-react';

interface WellborePressureProfileProps {
  tvd: number;            // Total vertical depth (ft)
  mudWeight: number;      // ppg
  killMudWeight?: number; // ppg
  formationPressure?: number; // psi
  lotEmw?: number;        // ppg (leak-off test equivalent mud weight)
  casingShoe?: number;    // TVD ft
  height?: number;
}

const WellborePressureProfile: React.FC<WellborePressureProfileProps> = ({
  tvd,
  mudWeight,
  killMudWeight,
  formationPressure,
  lotEmw,
  casingShoe,
  height = 400,
}) => {
  const data = useMemo(() => {
    if (!tvd || tvd <= 0) return [];

    // Generate depth points every 500 ft
    const step = Math.max(500, Math.floor(tvd / 20));
    const points: Array<Record<string, number>> = [];

    for (let d = 0; d <= tvd; d += step) {
      const point: Record<string, number> = { tvd: d };
      // Hydrostatic: P = MW × 0.052 × TVD
      point.hydrostatic = Math.round(mudWeight * 0.052 * d);
      // Kill mud hydrostatic
      if (killMudWeight) {
        point.kill_hydrostatic = Math.round(killMudWeight * 0.052 * d);
      }
      // Frac gradient line (from LOT)
      if (lotEmw) {
        point.frac_gradient = Math.round(lotEmw * 0.052 * d);
      }
      // Formation pressure: linear from 0 to formation_pressure
      if (formationPressure) {
        point.formation = Math.round((formationPressure / tvd) * d);
      }
      points.push(point);
    }

    // Ensure we have the exact TD point
    const lastD = points[points.length - 1]?.tvd;
    if (lastD !== tvd) {
      const point: Record<string, number> = { tvd };
      point.hydrostatic = Math.round(mudWeight * 0.052 * tvd);
      if (killMudWeight) point.kill_hydrostatic = Math.round(killMudWeight * 0.052 * tvd);
      if (lotEmw) point.frac_gradient = Math.round(lotEmw * 0.052 * tvd);
      if (formationPressure) point.formation = Math.round(formationPressure);
      points.push(point);
    }

    return points;
  }, [tvd, mudWeight, killMudWeight, formationPressure, lotEmw]);

  if (!data.length) return null;

  const series: DepthSeries[] = [
    { dataKey: 'hydrostatic', name: `Hydrostatic (${mudWeight} ppg)`, color: '#3b82f6', strokeWidth: 2 },
  ];

  if (killMudWeight) {
    series.push({
      dataKey: 'kill_hydrostatic',
      name: `Kill Mud (${killMudWeight} ppg)`,
      color: WC_COLORS.fcp,
      strokeWidth: 2,
      strokeDasharray: '6 3',
    });
  }

  if (formationPressure) {
    series.push({
      dataKey: 'formation',
      name: 'Formation Pressure',
      color: WC_COLORS.formation,
      strokeWidth: 2,
    });
  }

  if (lotEmw) {
    series.push({
      dataKey: 'frac_gradient',
      name: `Frac Gradient (${lotEmw} ppg)`,
      color: WC_COLORS.icp,
      strokeWidth: 2,
      strokeDasharray: '4 2',
    });
  }

  const refLines: DepthRefLine[] = [];
  if (casingShoe) {
    refLines.push({
      y: casingShoe,
      label: `Shoe: ${casingShoe.toLocaleString()} ft`,
      color: 'rgba(255,255,255,0.3)',
      strokeDasharray: '8 4',
    });
  }

  return (
    <ChartContainer title="Wellbore Pressure Profile" icon={Layers} height={height}>
      <DepthTrack
        data={data}
        series={series}
        depthKey="tvd"
        xLabel="Pressure (psi)"
        yLabel="TVD (ft)"
        referenceLines={refLines}
        tooltipFormatter={(v) => `${Number(v).toLocaleString()} psi`}
      />
    </ChartContainer>
  );
};

export default WellborePressureProfile;
