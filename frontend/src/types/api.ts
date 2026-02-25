/**
 * Shared API response types for PETROEXPERT.
 *
 * These types mirror the backend Pydantic models / return dicts and are used
 * across multiple frontend components.
 */

// ---------------------------------------------------------------------------
// Common
// ---------------------------------------------------------------------------

/** Standard message-only response from the backend. */
export interface MessageResponse {
  message: string;
}

/** Shape returned by all per-module `/analyze` endpoints. */
export interface AIAnalysisResponse {
  agent: string;
  role: string;
  analysis: string;
  confidence: string;
  query?: string;
}

/** Axios-compatible error shape for catch blocks. */
export interface APIError {
  response?: {
    status: number;
    data?: {
      detail?: string;
    };
  };
  message?: string;
}

// ---------------------------------------------------------------------------
// Wells
// ---------------------------------------------------------------------------

export interface Well {
  id: number;
  name: string;
  location: string | null;
}

export interface ProblemDetail {
  id: number;
  well_id: number;
  depth_md: number;
  depth_tvd: number;
  description: string;
  operation: string;
  formation: string | null;
  mud_weight: number | null;
  inclination: number | null;
  azimuth: number | null;
  torque: number | null;
  drag: number | null;
  overpull: number | null;
  string_weight: number | null;
  additional_data: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Events
// ---------------------------------------------------------------------------

export interface EventData {
  workflow?: string[];
  leader?: string;
  phase?: string;
  family?: string;
  event_type?: string;
  description?: string;
  parameters?: Record<string, unknown>;
}

export interface EventCreationResponse {
  id: number;
  problem_id: number;
  message: string;
}

// ---------------------------------------------------------------------------
// Analysis
// ---------------------------------------------------------------------------

export interface AnalysisInit {
  id: number;
  analysis_id: number;
  event_id?: number;
  workflow: string[];
  leader: string | null;
  current_agent_index: number;
}

export interface CompletedAnalysis {
  role: string;
  confidence: string;
  agent: string;
  analysis?: string;
}

export interface AnalysisDetail {
  id: number;
  problem_id: number | null;
  event_id: number | null;
  workflow: string[];
  individual_analyses: CompletedAnalysis[];
  final_synthesis: CompletedAnalysis | null;
  event?: {
    id: number;
    phase: string;
    family: string;
    event_type: string;
    description: string;
  };
  problem?: {
    id: number;
    description: string;
    additional_data: Record<string, unknown>;
    well: { name: string };
  };
}

export interface AgentInfo {
  id: string;
  role: string;
  name: string;
}

export interface QueryResponse {
  query: string;
  context?: {
    previous_analyses: CompletedAnalysis[];
    well_data?: {
      well_name: string;
      description: string;
      phase?: string;
      family?: string;
      event_type?: string;
      depth_md?: number;
      depth_tvd?: number;
      mud_weight?: number;
    };
    extracted_report_text?: string;
  };
}

// ---------------------------------------------------------------------------
// RCA
// ---------------------------------------------------------------------------

export interface RCAReport {
  root_cause_category: string;
  root_cause_description: string;
  five_whys: Record<string, string>;
  fishbone_factors: Record<string, string[]>;
  corrective_actions: string[];
  prevention_actions: string[];
  confidence_score: number;
  cached?: boolean;
}

// ---------------------------------------------------------------------------
// System Health (Sidebar)
// ---------------------------------------------------------------------------

export interface ProviderHealth {
  available: boolean;
  model?: string;
  error?: string;
}

export interface SystemHealth {
  api: string;
  llm: { status: string; providers?: Record<string, ProviderHealth> };
  agents: number;
  database: string;
}

// ---------------------------------------------------------------------------
// DDR Report
// ---------------------------------------------------------------------------

export interface Operation {
  time_start: string;
  time_end: string;
  duration_hrs: number;
  code: string;
  description: string;
}

export interface BHAComponent {
  position: number;
  component: string;
  od: number;
  id_inner: number;
  length: number;
  weight: number;
}

export interface HeaderData {
  rig_name?: string;
  contractor?: string;
  field?: string;
  lease?: string;
  spud_date?: string;
  days_since_spud?: number;
  [key: string]: string | number | undefined;
}

export interface DrillingParams {
  wob?: number;
  rpm?: number;
  torque?: number;
  flow_rate?: number;
  spp?: number;
  rop?: number;
  [key: string]: number | string | undefined;
}

export interface MudProperties {
  mud_weight?: number;
  viscosity?: number;
  pv?: number;
  yp?: number;
  gel_10s?: number;
  gel_10m?: number;
  pH?: number;
  [key: string]: number | string | undefined;
}

export interface GasMonitoring {
  total_gas?: number;
  c1?: number;
  c2?: number;
  c3?: number;
  h2s?: number;
  [key: string]: number | string | undefined;
}

export interface CostSummary {
  daily_cost?: number;
  cumulative_cost?: number;
  afe_budget?: number;
  variance?: number;
  [key: string]: number | string | undefined;
}

export interface HSSEData {
  incidents?: number;
  near_misses?: number;
  safety_observations?: number;
  [key: string]: number | string | boolean | undefined;
}
