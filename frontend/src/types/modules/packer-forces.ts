/**
 * Types for the Packer Forces module.
 */

export interface PackerForceResult {
  total_force_lbs: number;
  tubing_movement_in: number;
  pressure_effect_lbs: number;
  temperature_effect_lbs: number;
  ballooning_effect_lbs: number;
  buckling_effect_lbs: number;
  [key: string]: unknown;
}

export interface TubingMovementResult {
  total_length_change_in: number;
  pressure_length_change_in: number;
  temperature_length_change_in: number;
  ballooning_length_change_in: number;
}
