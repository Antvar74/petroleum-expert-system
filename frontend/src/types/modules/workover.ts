/**
 * Types for the Workover Hydraulics module.
 */

export interface WorkoverHydResult {
  coiled_tubing_pressure_loss_psi: number;
  annular_pressure_loss_psi: number;
  total_pressure_loss_psi: number;
  ecd_ppg: number;
  [key: string]: unknown;
}

export interface CTFatigueResult {
  fatigue_life_trips: number;
  current_trip_count: number;
  remaining_life_percent: number;
  recommendation: string;
}
