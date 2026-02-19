/**
 * FractureGradientProfile.tsx — Depth vs gradient (pore, frac, overburden) profile.
 */
import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';
import ChartContainer, { DarkTooltip } from '../ChartContainer';
import { CHART_DEFAULTS } from '../ChartTheme';
import { TrendingUp } from 'lucide-react';

interface FractureGradientProfileProps {
  fractureGradient: {
    fracture_gradient_ppg: number;
    pore_gradient_ppg: number;
    overburden_gradient_ppg: number;
    mud_weight_window_ppg: number;
    depth_profile: {
      depth_ft: number;
      pore_pressure_ppg: number;
      fracture_gradient_ppg: number;
      overburden_ppg: number;
    }[];
  };
  height?: number;
}

const FractureGradientProfile: React.FC<FractureGradientProfileProps> = ({ fractureGradient, height = 380 }) => {
  if (!fractureGradient?.depth_profile) return null;

  const data = fractureGradient.depth_profile.map(d => ({
    depth: d.depth_ft,
    pore: d.pore_pressure_ppg,
    frac: d.fracture_gradient_ppg,
    overburden: d.overburden_ppg,
  }));

  return (
    <ChartContainer
      title="Perfil de Gradientes vs Profundidad (Eaton)"
      icon={TrendingUp}
      height={height}
      badge={{ text: `Ventana: ${fractureGradient.mud_weight_window_ppg} ppg`, color: 'bg-cyan-500/20 text-cyan-400' }}
    >
      <LineChart data={data} margin={{ ...CHART_DEFAULTS.margin, left: 30, bottom: 30 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_DEFAULTS.gridColor} />
        <XAxis dataKey="depth" stroke={CHART_DEFAULTS.axisColor} tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 10 }}
          label={{ value: 'Profundidad (ft)', position: 'bottom', fill: CHART_DEFAULTS.axisColor, fontSize: 11 }} />
        <YAxis stroke={CHART_DEFAULTS.axisColor} tick={{ fill: CHART_DEFAULTS.axisColor, fontSize: 11 }}
          label={{ value: 'Gradiente (ppg)', angle: -90, position: 'insideLeft', fill: CHART_DEFAULTS.axisColor }} />
        <Tooltip content={<DarkTooltip />} />
        <Legend wrapperStyle={{ fontSize: 11, color: 'rgba(255,255,255,0.5)' }} />
        <Line type="monotone" dataKey="pore" stroke="#3b82f6" strokeWidth={2} dot={{ r: 3 }} name="Poro" />
        <Line type="monotone" dataKey="frac" stroke="#f97316" strokeWidth={2} dot={{ r: 3 }} name="Fractura" />
        <Line type="monotone" dataKey="overburden" stroke="#a855f7" strokeWidth={2} dot={{ r: 3 }} name="Sobrecarga" />
      </LineChart>
    </ChartContainer>
  );
};

export default FractureGradientProfile;
