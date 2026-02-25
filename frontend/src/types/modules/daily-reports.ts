/**
 * Types for the Daily Reports (DDR) module.
 */
import type {
  Operation,
  BHAComponent,
  HeaderData,
  DrillingParams,
  MudProperties,
  GasMonitoring,
  CostSummary,
  HSSEData,
} from '../api';

export interface DailyReport {
  id: number;
  well_id: number;
  report_number: number;
  report_date: string;
  report_type: string;
  depth_start: number;
  depth_end: number;
  depth_tvd?: number;
  status: string;
}

export interface DailyReportDetail extends DailyReport {
  headerData: HeaderData;
  operations: Operation[];
  drillingParams: DrillingParams;
  mudProperties: MudProperties;
  bhaData: BHAComponent[];
  gasMonitoring: GasMonitoring;
  costSummary: CostSummary;
  hsseData?: HSSEData;
  mudInventory?: Record<string, string | number>;
  completionData?: Record<string, string | number>;
  terminationData?: Record<string, string | number>;
}

export interface DDRFormSection {
  [key: string]: string | number | boolean | undefined;
}

export interface DDRSummaryResult {
  total_reports: number;
  latest_depth_ft: number;
  total_operating_hours: number;
  npt_hours: number;
  average_rop: number;
}

export interface DDRAIAnalysis {
  summary: string;
  highlights: string[];
  concerns: string[];
  recommendations: string[];
}
