/**
 * ContributingFactorsRadar.tsx — Radar chart of contributing risk factors.
 */
import React from 'react';
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Tooltip,
} from 'recharts';
import ChartContainer from '../ChartContainer';
import { RISK_COLORS, CHART_DEFAULTS } from '../ChartTheme';
import { Crosshair } from 'lucide-react';

interface Factor {
  factor: string;
  score: number;
  detail: string;
}

interface ContributingFactorsRadarProps {
  factors: Factor[];
  riskLevel: string;
  height?: number;
}

const ContributingFactorsRadar: React.FC<ContributingFactorsRadarProps> = ({
  factors,
  riskLevel,
  height = 300,
}) => {
  if (!factors?.length) return null;

  // Recharts RadarChart needs uniform data with subject key
  const data = factors.map(f => ({
    subject: f.factor.length > 15 ? f.factor.substring(0, 14) + '...' : f.factor,
    fullName: f.factor,
    score: Math.round(f.score * 100),
    detail: f.detail,
  }));

  const fillColor = RISK_COLORS[riskLevel] || '#f97316';

  return (
    <ChartContainer
      title="Contributing Factors"
      icon={Crosshair}
      height={height}
      badge={{ text: riskLevel, color: `${riskLevel === 'CRITICAL' ? 'bg-red-500/20 text-red-400' : riskLevel === 'HIGH' ? 'bg-orange-500/20 text-orange-400' : riskLevel === 'MEDIUM' ? 'bg-yellow-500/20 text-yellow-400' : 'bg-green-500/20 text-green-400'}` }}
    >
      <RadarChart data={data} margin={{ top: 10, right: 30, bottom: 10, left: 30 }}>
        <PolarGrid stroke="rgba(255,255,255,0.08)" />
        <PolarAngleAxis
          dataKey="subject"
          tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 10 }}
        />
        <PolarRadiusAxis
          angle={90}
          domain={[0, 100]}
          tick={{ fill: 'rgba(255,255,255,0.2)', fontSize: 9 }}
          tickCount={3}
        />
        <Radar
          name="Risk Score"
          dataKey="score"
          stroke={fillColor}
          fill={fillColor}
          fillOpacity={0.3}
          strokeWidth={2}
        />
        <Tooltip
          content={({ active, payload }) => {
            if (!active || !payload?.length) return null;
            const d = payload[0].payload;
            return (
              <div style={{ backgroundColor: CHART_DEFAULTS.tooltipBg, border: `1px solid ${CHART_DEFAULTS.tooltipBorder}`, borderRadius: 8, padding: '8px 12px', fontSize: 12 }}>
                <p style={{ color: fillColor, fontWeight: 700 }}>{d.fullName}</p>
                <p style={{ color: 'rgba(255,255,255,0.5)' }}>{d.detail}</p>
                <p style={{ color: 'white' }}>Score: {d.score}%</p>
              </div>
            );
          }}
        />
      </RadarChart>
    </ChartContainer>
  );
};

export default ContributingFactorsRadar;
