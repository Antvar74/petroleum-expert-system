/**
 * Types for the Petrophysics module.
 */

export interface LASParseResult {
  curves: string[];
  well_info: Record<string, string | number>;
  data: Array<Record<string, number>>;
  error?: string;
}

export interface SaturationResult {
  sw: number;
  method: string;
  model_selected: string;
  archie: {
    a: number;
    m: number;
    n: number;
    rw: number;
  };
}

export interface PickettPlotPoint {
  rt: number;
  phi: number;
  sw: number;
}

export interface PickettPlotResult {
  points: PickettPlotPoint[];
  iso_sw_lines: Array<{
    sw_percent: number;
    curve: Array<[number, number]>;
  }>;
}

export interface CrossplotPoint {
  rhob: number;
  nphi: number;
  lithology: string;
  gas_flag: boolean;
}

export interface CrossplotResult {
  points: CrossplotPoint[];
  lithology_lines: Array<{
    name: string;
    curve: Array<[number, number]>;
  }>;
}

export interface EvaluationInterval {
  depth_ft: number;
  vsh: number;
  phi: number;
  sw: number;
  k_md: number;
  net_pay: boolean;
}

export interface FullEvaluationResult {
  summary: {
    net_pay_ft: number;
    gross_pay_ft: number;
    avg_porosity: number;
    avg_sw: number;
    avg_permeability_md: number;
    reserves_mmbo?: number;
  };
  intervals: EvaluationInterval[];
}
