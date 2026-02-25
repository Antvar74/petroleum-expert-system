/**
 * Types for the Hydraulics module.
 */

export interface CircuitSection {
  section_type: string;
  length: number;
  od: number;
  id_inner: number;
}

export interface HydParams {
  flow_rate: number;
  mud_weight: number;
  plastic_viscosity: number;
  yield_point: number;
  k?: number;
  n?: number;
  rheology_model: string;
  hole_diameter: number;
  nozzle_sizes: number[];
}

export interface HydSectionResult {
  section_type: string;
  length: number;
  velocity_fpm: number;
  pressure_loss_psi: number;
}

export interface HydResult {
  section_results: HydSectionResult[];
  bit_hydraulics: {
    impact_force_lbf: number;
    bit_pressure_drop_psi: number;
    jet_velocity_fpm: number;
  };
  summary: {
    total_pressure_loss_psi: number;
    equivalent_circulating_density_ppg: number;
    pump_pressure_psi: number;
    maximum_pressure_psi: number;
  };
}

export interface SurgeSwabResult {
  surge_pressure_psi: number;
  swab_pressure_psi: number;
  effective_mud_weight_surge_ppg: number;
  effective_mud_weight_swab_ppg: number;
}

export interface BHABreakdownResult {
  tools: Array<{
    tool_name: string;
    pressure_loss_psi: number;
    percent_total: number;
  }>;
  total_pressure_loss_psi: number;
}

export interface PressureWaterfallResult {
  stages: Array<{
    name: string;
    pressure_psi: number;
    loss_psi: number;
  }>;
  chart_data: Array<[string, number]>;
}

export interface RheologyFitResult {
  k: number;
  n: number;
  tau_0: number;
  r_squared: number;
}
