/**
 * Types for the Well Control module.
 *
 * These types are derived from the actual backend response shapes as consumed
 * by WellControlModule.tsx and the well-control chart components.
 */

// ---------------------------------------------------------------------------
// Pre-Record Kill Sheet
// ---------------------------------------------------------------------------

export interface KillSheetPreRecordResult {
  reference_values?: {
    hydrostatic_psi?: number;
    maasp_psi?: number;
    [key: string]: number | undefined;
  };
  capacities_bbl_ft?: {
    dp_capacity?: number;
    annular_oh_dp?: number;
    [key: string]: number | undefined;
  };
  strokes?: {
    strokes_surface_to_bit?: number;
    strokes_bit_to_surface?: number;
    total_strokes?: number;
  };
  volumes_bbl?: {
    total_well_volume?: number;
    [key: string]: number | undefined;
  };
  [key: string]: unknown;
}

// ---------------------------------------------------------------------------
// Kill Sheet Calculation
// ---------------------------------------------------------------------------

export interface WCPressureScheduleStep {
  step: number;
  strokes: number;
  pressure_psi: number;
  percent_complete: number;
}

export interface KillSheetResult {
  formation_pressure_psi?: number;
  kill_mud_weight_ppg?: number;
  icp_psi?: number;
  fcp_psi?: number;
  maasp_psi?: number;
  mud_weight_increase_ppg?: number;
  influx_type?: string;
  influx_height_ft?: number;
  alerts?: string[];
  pressure_schedule?: WCPressureScheduleStep[];
  [key: string]: unknown;
}

// ---------------------------------------------------------------------------
// Volumetric Method
// ---------------------------------------------------------------------------

export interface WCVolumetricCycle {
  cycle: number;
  bleed_volume_bbl: number;
  casing_pressure_psi: number;
  [key: string]: number;
}

export interface WCVolumetricResult {
  parameters?: {
    volume_per_cycle_bbl?: number;
    estimated_cycles?: number;
    [key: string]: number | undefined;
  };
  initial_conditions?: {
    working_pressure_psi?: number;
    [key: string]: number | undefined;
  };
  cycles?: WCVolumetricCycle[];
  [key: string]: unknown;
}

// ---------------------------------------------------------------------------
// Bullhead
// ---------------------------------------------------------------------------

export interface WCBullheadResult {
  calculations?: {
    required_pump_pressure_psi?: number;
    displacement_volume_bbl?: number;
    [key: string]: number | undefined;
  };
  shoe_integrity?: {
    safe?: boolean;
    margin_psi?: number;
  };
  [key: string]: unknown;
}

// ---------------------------------------------------------------------------
// Kick Migration Simulation
// ---------------------------------------------------------------------------

export interface KickMigrationTimeStep {
  time_min: number;
  kick_top_depth_tvd_ft?: number;
  kick_bottom_depth_tvd_ft?: number;
  kick_volume_bbl?: number;
  sidpp_psi?: number;
  sicp_psi?: number;
  casing_pressure_psi?: number;
  [key: string]: number | undefined;
}

export interface KickMigrationResult {
  time_series?: KickMigrationTimeStep[];
  max_casing_pressure?: number;
  surface_arrival_min?: number | null;
  [key: string]: unknown;
}

// ---------------------------------------------------------------------------
// Kill Circulation Simulation
// ---------------------------------------------------------------------------

export interface KillSimPressurePoint {
  stroke: number;
  pressure_psi: number;
}

export interface KillSimulationResult {
  drill_pipe_pressure?: KillSimPressurePoint[];
  casing_pressure?: KillSimPressurePoint[];
  icp?: number;
  fcp?: number;
  total_strokes?: number;
  method?: string;
  [key: string]: unknown;
}

// ---------------------------------------------------------------------------
// Standalone calculation results (used in other contexts)
// ---------------------------------------------------------------------------

export interface KickToleranceResult {
  kick_tolerance_bbl: number;
  maximum_pit_gain_bbl: number;
  safety_margin_ppg: number;
}

export interface BariteRequirementsResult {
  barite_weight_lbs: number;
  barite_sacks: number;
  final_mud_weight_ppg: number;
}

export interface ZFactorResult {
  z_factor: number;
  real_gas_density_lb_scf: number;
}
