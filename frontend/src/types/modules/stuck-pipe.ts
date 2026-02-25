/**
 * Types for the Stuck Pipe module.
 *
 * Derived from backend responses as consumed by StuckPipeAnalyzer.tsx
 * and the stuck-pipe chart components.
 */

// ---------------------------------------------------------------------------
// Diagnosis Wizard
// ---------------------------------------------------------------------------

export interface DiagnosisOption {
  value: string;
  label: string;
}

/** A question node returned by /stuck-pipe/diagnose/start or /answer. */
export interface DiagnosisQuestion {
  node_id: string;
  question: string;
  options?: DiagnosisOption[];
  hint?: string;
  type?: string;
}

/** A step in the breadcrumb path the user has walked through. */
export interface DiagnosisStep {
  node_id: string;
  question: string;
  answer: string;
}

/** Final result when the decision tree reaches a leaf. */
export interface DiagnosisResult {
  type?: string;
  mechanism: string;
  description?: string;
  confidence?: number;
  indicators?: string[];
  node_id?: string;
  question?: string;
  options?: DiagnosisOption[];
}

// ---------------------------------------------------------------------------
// Free Point Calculator
// ---------------------------------------------------------------------------

export interface FreePointResult {
  free_point_depth_ft: number;
  pipe_stretch_ft?: number;
  pipe_area_sqin?: number;
  calculated_stress_psi?: number;
  pull_safe?: boolean;
  pull_pct_of_yield?: number;
  error?: string;
}

// ---------------------------------------------------------------------------
// Risk Assessment
// ---------------------------------------------------------------------------

export interface RiskAssessmentResult {
  mechanism: string;
  risk_level: string;
  risk_score: number;
  probability?: number;
  severity?: number;
  contributing_factors: Array<string | { factor: string; score: number }>;
  [key: string]: unknown;
}

export interface StuckPipeActionsResult {
  immediate: string[];
  contingency: string[];
}

// ---------------------------------------------------------------------------
// Specialty calculations
// ---------------------------------------------------------------------------

export interface DifferentialStickingResult {
  sticking_force_lbf: number;
  sticking_force_klb: number;
  contact_area_sq_in: number;
  differential_pressure_psi: number;
}

export interface PackoffRiskResult {
  packoff_risk_score: number;
  risk_level: string;
  mitigation_actions: string[];
}

// ---------------------------------------------------------------------------
// Combined event-level analysis
// ---------------------------------------------------------------------------

export interface FullStuckPipeAnalysis {
  classification: {
    mechanism: string;
    decision_path: string[];
  };
  risk: RiskAssessmentResult;
  actions: StuckPipeActionsResult;
  free_point: { free_point_depth_ft: number } | null;
}
