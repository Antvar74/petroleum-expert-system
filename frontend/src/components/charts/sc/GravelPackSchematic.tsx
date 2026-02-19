/**
 * GravelPackSchematic.tsx — Visual schematic of gravel pack configuration.
 */
import React from 'react';
import ChartContainer from '../ChartContainer';
import { Layers } from 'lucide-react';

interface GravelPackSchematicProps {
  gravel: { recommended_pack: string; gravel_min_mm: number; gravel_max_mm: number; reference_d_mm: number };
  screen: { recommended_standard_slot_in: number; screen_type: string; slot_size_mm: number };
  volume: { gravel_volume_bbl: number; gravel_weight_lb: number; interval_length_ft: number };
  height?: number;
}

const GravelPackSchematic: React.FC<GravelPackSchematicProps> = ({ gravel, screen, volume, height = 350 }) => {
  if (!gravel || !screen || !volume) return null;

  return (
    <ChartContainer title="Esquema Gravel Pack" icon={Layers} height={height} isFluid={true}
      badge={{ text: gravel.recommended_pack, color: 'bg-cyan-500/20 text-cyan-400' }}>
      <div className="flex flex-col items-center justify-center gap-4 p-6">
        {/* Visual cross-section */}
        <div className="relative w-48 h-40 flex items-center justify-center">
          {/* Formation */}
          <div className="absolute inset-0 rounded-2xl border-2 border-dashed border-amber-500/30 bg-amber-500/5 flex items-center justify-center">
            <span className="text-[10px] text-amber-400 absolute top-1 left-2">Formación</span>
          </div>
          {/* Gravel */}
          <div className="absolute inset-4 rounded-xl border-2 border-cyan-500/40 bg-cyan-500/10 flex items-center justify-center">
            <span className="text-[10px] text-cyan-400 absolute top-1 left-2">Grava</span>
          </div>
          {/* Screen */}
          <div className="absolute inset-10 rounded-lg border-2 border-green-500/50 bg-green-500/10 flex items-center justify-center">
            <span className="text-[10px] text-green-400">Screen</span>
          </div>
        </div>

        {/* Specs table */}
        <div className="grid grid-cols-2 gap-x-8 gap-y-2 text-sm w-full max-w-xs">
          <div className="text-gray-400">Grava:</div>
          <div className="font-mono text-white">{gravel.recommended_pack} mesh</div>
          <div className="text-gray-400">Rango Grava:</div>
          <div className="font-mono text-white">{gravel.gravel_min_mm}-{gravel.gravel_max_mm} mm</div>
          <div className="text-gray-400">Screen Slot:</div>
          <div className="font-mono text-white">{screen.recommended_standard_slot_in}" ({screen.screen_type})</div>
          <div className="text-gray-400">Volumen:</div>
          <div className="font-mono text-white">{volume.gravel_volume_bbl} bbl</div>
          <div className="text-gray-400">Peso:</div>
          <div className="font-mono text-white">{volume.gravel_weight_lb?.toLocaleString()} lb</div>
          <div className="text-gray-400">Intervalo:</div>
          <div className="font-mono text-white">{volume.interval_length_ft} ft</div>
        </div>
      </div>
    </ChartContainer>
  );
};

export default GravelPackSchematic;
