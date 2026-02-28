/**
 * Types for the Vibrations module.
 */

// --- Request types ---

export interface VibrationsCalcRequest {
  wob_klb: number;
  rpm: number;
  rop_fph: number;
  torque_ftlb: number;
  bit_diameter_in: number;
  dp_od_in?: number;
  dp_id_in?: number;
  dp_weight_lbft?: number;
  bha_length_ft?: number;
  bha_od_in?: number;
  bha_id_in?: number;
  bha_weight_lbft?: number;
  mud_weight_ppg?: number;
  hole_diameter_in?: number;
  inclination_deg?: number;
  friction_factor?: number;
  // New Phase 1/2 fields
  stabilizer_spacing_ft?: number;
  ucs_psi?: number;
  n_blades?: number;
}

// --- Response types ---

export interface AxialVibrationResult {
  critical_rpm_1st: number;
  critical_rpm_2nd: number;
  critical_rpm_3rd: number;
  natural_freq_hz_1st: number;
  natural_freq_hz_2nd: number;
  buoyancy_factor: number;
  safe_operating_bands: Array<{ min_rpm: number; max_rpm: number }>;
  mode: string;
}

export interface LateralVibrationResult {
  critical_rpm: number;
  mode: string;
  radial_clearance_in: number;
  buoyed_weight_lbft: number;
  moment_of_inertia_in4: number;
  whirl_severity_factor: number;
  prediction: string;
  // New Phase 1 fields
  span_used_ft?: number;
  span_source?: 'user' | 'estimated';
  // Multi-component route fields
  modes?: Array<{
    mode_number: number;
    natural_freq_hz: number;
    critical_rpm: number;
    omega_rad_s: number;
  }>;
  critical_rpm_spans?: Array<{
    span: string;
    length_ft: number;
    critical_rpm: number;
  }>;
}

export interface StickSlipResult {
  severity_index: number;
  classification: string;
  color: string;
  rpm_min_at_bit: number;
  rpm_max_at_bit: number;
  surface_rpm: number;
  friction_torque_ftlb: number;
  torsional_stiffness_inlb_rad: number;
  angular_displacement_deg: number;
  recommendation: string;
}

export interface MSEResult {
  mse_total_psi: number;
  mse_rotary_psi: number;
  mse_thrust_psi: number;
  rotary_pct: number;
  thrust_pct: number;
  bit_area_in2: number;
  efficiency_pct: number | null;
  classification: string;
  color: string;
  classification_basis: 'ucs_based' | 'absolute_mse';
}

export interface StabilityResult {
  stability_index: number;
  status: string;
  color: string;
  mode_scores: Record<string, number>;
  weights: Record<string, number>;
  operating_rpm: number;
}

export interface VibrationMapPoint {
  wob_klb: number;
  rpm: number;
  stability_index: number;
  status: string;
  stick_slip_severity: number;
  mse_psi: number;
}

export interface VibrationMapResult {
  map_data: VibrationMapPoint[];
  wob_range: number[];
  rpm_range: number[];
  optimal_point: { wob: number; rpm: number; score: number };
  critical_rpm_axial: number;
  critical_rpm_lateral: number;
}

export interface VibrationsSummary {
  stability_index: number;
  stability_status: string;
  critical_rpm_axial: number;
  critical_rpm_lateral: number;
  stick_slip_severity: number;
  stick_slip_class: string;
  mse_psi: number;
  mse_efficiency_pct: number | null;
  optimal_wob: number;
  optimal_rpm: number;
  alerts: string[];
}

export interface VibrationsFullResult {
  summary: VibrationsSummary;
  axial_vibrations: AxialVibrationResult;
  lateral_vibrations: LateralVibrationResult;
  stick_slip: StickSlipResult;
  mse: MSEResult;
  stability: StabilityResult;
  vibration_map: VibrationMapResult;
  alerts: string[];
}

// Legacy interfaces (kept for backward compatibility)
export interface VibrationResult {
  vibration_type: string;
  severity: string;
  frequency_hz: number;
  amplitude: number;
  recommended_rpm_range: { min: number; max: number };
  [key: string]: unknown;
}

export interface CriticalSpeedResult {
  critical_speed_rpm: number;
  safety_margin_percent: number;
  operating_rpm: number;
  is_safe: boolean;
}

export interface WhirlAnalysisResult {
  whirl_type: string;
  threshold_rpm: number;
  current_rpm: number;
  risk_level: string;
}
