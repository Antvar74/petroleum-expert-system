/**
 * Types for the Casing Design module.
 */

export interface CasingGradeEvaluation {
  grade: string;
  weight_ppf: number;
  yield_strength_psi: number;
  burst_sf: number;
  collapse_sf: number;
  tension_sf: number;
  is_suitable: boolean;
}

export interface CasingDesignSummary {
  selected_grade: string;
  selected_weight_ppf: number;
  burst_sf: number;
  collapse_sf: number;
  tension_sf: number;
  minimum_sf: number;
}

export interface CasingDesignResult {
  id: number;
  well_id: number;
  summary: CasingDesignSummary;
  grades_evaluated: CasingGradeEvaluation[];
}

export interface CombinationStringSection {
  section_number: number;
  grade: string;
  weight_ppf: number;
  start_depth_ft: number;
  end_depth_ft: number;
  length_ft: number;
  connections: string;
}

export interface CombinationStringResult {
  sections: CombinationStringSection[];
  summary: {
    total_weight_lbs: number;
    minimum_burst_sf: number;
    minimum_collapse_sf: number;
    minimum_tension_sf: number;
  };
}

export interface RunningLoadsResult {
  hookload_full_string_lbs: number;
  shock_load_lbs: number;
  bending_stress_psi: number;
  total_running_tension_lbs: number;
  running_loads_per_stand: Array<{
    stand_number: number;
    depth_ft: number;
    hookload_lbs: number;
  }>;
}
