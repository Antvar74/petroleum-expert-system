/**
 * BitHydraulicsGauges.tsx — 4 radial gauges for bit optimization metrics.
 */
import React from 'react';
import GaugeChart from '../GaugeChart';

interface BitHydraulicsGaugesProps {
  bitData: {
    hsi: number;
    impact_force_lb: number;
    jet_velocity_fps: number;
    percent_at_bit: number;
    tfa_sqin: number;
    pressure_drop_psi: number;
    hhp_bit: number;
    nozzle_count: number;
  };
}

const BitHydraulicsGauges: React.FC<BitHydraulicsGaugesProps> = ({ bitData }) => {
  if (!bitData) return null;

  return (
    <div className="space-y-6">
      {/* Gauges grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="glass-panel p-4 rounded-xl border border-white/5 flex flex-col items-center">
          <GaugeChart
            value={bitData.hsi}
            min={0}
            max={5}
            unit="hp/in\u00B2"
            label="HSI"
            optimalRange={[2.5, 3.5]}
            size={150}
          />
        </div>
        <div className="glass-panel p-4 rounded-xl border border-white/5 flex flex-col items-center">
          <GaugeChart
            value={bitData.impact_force_lb}
            min={0}
            max={2000}
            unit="lb"
            label="Impact Force"
            optimalRange={[800, 1500]}
            size={150}
          />
        </div>
        <div className="glass-panel p-4 rounded-xl border border-white/5 flex flex-col items-center">
          <GaugeChart
            value={bitData.jet_velocity_fps}
            min={0}
            max={600}
            unit="ft/s"
            label="Jet Velocity"
            optimalRange={[250, 450]}
            size={150}
          />
        </div>
        <div className="glass-panel p-4 rounded-xl border border-white/5 flex flex-col items-center">
          <GaugeChart
            value={bitData.percent_at_bit}
            min={0}
            max={100}
            unit="%"
            label="% at Bit"
            optimalRange={[50, 65]}
            size={150}
          />
        </div>
      </div>

      {/* Secondary metrics row */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: 'TFA', value: bitData.tfa_sqin, unit: 'in\u00B2' },
          { label: 'Bit dP', value: bitData.pressure_drop_psi, unit: 'psi' },
          { label: 'Bit HHP', value: bitData.hhp_bit, unit: 'hp' },
          { label: 'Nozzles', value: bitData.nozzle_count, unit: '' },
        ].map((m, i) => (
          <div key={i} className="glass-panel p-3 rounded-lg border border-white/5 text-center">
            <p className="text-[10px] text-white/40 mb-1">{m.label}</p>
            <p className="text-lg font-bold text-industrial-400">{m.value}</p>
            {m.unit && <p className="text-[10px] text-white/30">{m.unit}</p>}
          </div>
        ))}
      </div>
    </div>
  );
};

export default BitHydraulicsGauges;
