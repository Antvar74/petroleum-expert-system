/**
 * Types for the Shot Efficiency / Perforating module.
 */

export interface ShotEfficiencyResult {
  effective_shots: number;
  total_shots: number;
  efficiency_percent: number;
  penetration_depth_in: number;
  tunnel_diameter_in: number;
  [key: string]: unknown;
}

export interface ChargePerformanceResult {
  entrance_hole_diameter_in: number;
  penetration_depth_in: number;
  perforation_tunnel_volume_cu_in: number;
}
