/**
 * Types for the Completion Design module.
 */

export interface CompletionDesignSummary {
  productivity_index: number;
  skin_factor: number;
  optimal_perforation_diameter_in: number;
  fcd: number;
}

export interface CompletionDesignResult {
  id: number;
  well_id: number;
  summary: CompletionDesignSummary;
  perforation_design: {
    gun_type: string;
    charge_size_in: string;
    shot_density_spf: number;
    penetration_depth_in: number;
  };
  fracture_design: {
    fracture_length_ft: number;
    fracture_conductivity: number;
    fcd: number;
  };
}

export interface IPRDataPoint {
  flowrate_bopd: number;
  pwf_psi: number;
}

export interface IPRResult {
  model: string;
  data_points: IPRDataPoint[];
  summary: {
    max_flowrate_bopd: number;
    bubble_point_psi?: number;
    productivity_index?: number;
  };
}

export interface NodalAnalysisResult {
  intersection_point: {
    flowrate_bopd: number;
    pwf_psi: number;
  };
  ipr_curve: Array<[number, number]>;
  vlp_curve: Array<[number, number]>;
  operating_envelope: {
    minimum_bopd: number;
    maximum_bopd: number;
  };
}
