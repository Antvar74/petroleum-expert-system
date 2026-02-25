/**
 * Types for the Wellbore Cleanup module.
 */

export interface CleanupResult {
  cuttings_transport_ratio: number;
  minimum_flow_rate_gpm: number;
  recommended_flow_rate_gpm: number;
  annular_velocity_fpm: number;
  [key: string]: unknown;
}

export interface HoleSweepResult {
  sweep_volume_bbl: number;
  sweep_weight_ppg: number;
  pump_time_min: number;
}
