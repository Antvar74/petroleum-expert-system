/**
 * Types for the Vibrations module.
 */

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
