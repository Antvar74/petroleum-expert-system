/**
 * Types for the Sand Control module.
 */

export interface SandControlResult {
  screen_size_gauge: number;
  gravel_pack_design: {
    gravel_size: string;
    gravel_volume_cuft: number;
  };
  formation_strength_psi: number;
  [key: string]: unknown;
}

export interface SandProductionRisk {
  risk_level: string;
  risk_score: number;
  factors: string[];
  recommendations: string[];
}
