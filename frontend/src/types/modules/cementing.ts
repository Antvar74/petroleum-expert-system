/**
 * Types for the Cementing module.
 */

export interface CementSlurryResult {
  slurry_density_ppg: number;
  slurry_yield_cuft_sk: number;
  water_requirement_gal_sk: number;
  mix_water_gal: number;
  cement_sacks: number;
  total_volume_bbl: number;
}

export interface CementVolumeResult {
  lead_slurry_bbl: number;
  tail_slurry_bbl: number;
  total_slurry_bbl: number;
  excess_percent: number;
}

export interface CementPressureResult {
  bottom_hole_pressure_psi: number;
  u_tube_balance_point_ft: number;
  ecd_ppg: number;
}

export interface CementDisplacementResult {
  displacement_volume_bbl: number;
  displacement_strokes: number;
  displacement_time_min: number;
  pump_rate_bpm: number;
}
