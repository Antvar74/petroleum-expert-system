/**
 * Types for the Torque & Drag module.
 */

export interface SurveyStation {
  md: number;
  inclination: number;
  azimuth: number;
}

export interface ComputedSurveyStation extends SurveyStation {
  tvd: number;
  north: number;
  east: number;
  dls: number;
}

export interface DrillstringComponent {
  section_name: string;
  od: number;
  id_inner: number;
  weight: number;
  length: number;
  order_from_bit: number;
}

export interface TDParams {
  operation: string;
  friction_cased: number;
  friction_open: number;
  mud_weight: number;
  wob: number;
  rpm: number;
  casing_shoe_md: number;
}

export interface TDStationResult {
  md: number;
  inclination: number;
  axial_force: number;
  torque: number;
  normal_force: number;
}

export interface TDResult {
  station_results: TDStationResult[];
  summary: {
    surface_hookload_klb: number;
    surface_torque_ftlb: number;
    max_axial_force_klb: number;
    max_torque_ftlb: number;
  };
}

export interface TDComparisonResult {
  operations: Record<string, TDStationResult[]>;
  combined: Array<Record<string, number>>;
  summary_comparison: Array<{
    operation: string;
    hookload_klb: number;
    torque_ftlb: number;
  }>;
}

export interface TDBackCalcResult {
  calculated_friction_cased: number;
  calculated_friction_open: number;
  station_results: Array<{
    md: number;
    calculated_friction: number;
  }>;
}
