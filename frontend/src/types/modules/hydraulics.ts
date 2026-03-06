/**
 * Types for the Hydraulics module.
 * Matches actual API response shapes from orchestrator/hydraulics_engine/.
 */

export interface CircuitSection {
  section_type: string;
  length: number;
  od: number;
  id_inner: number;
  [key: string]: string | number;
}

export interface HydSectionResult {
  section_type: string;
  length: number;
  velocity_ft_min: number;
  pressure_loss_psi: number;
  flow_regime: string;
  reynolds: number;
}

export interface HydResult {
  section_results: HydSectionResult[];
  bit_hydraulics: {
    hsi: number;
    impact_force_lb: number;
    jet_velocity_fps: number;
    percent_at_bit: number;
    tfa_sqin: number;
    pressure_drop_psi: number;
    hhp_bit: number;
    nozzle_count: number;
  };
  ecd: {
    ecd_ppg: number;
    ecd_from_apl: number;
    status: string;
    cuttings_effect_ppg: number;
    temperature_effect_ppg: number;
    total_margin_ppg: number;
  };
  ecd_profile: Array<{ tvd: number; ecd: number }>;
  annular_analysis: {
    sections: Array<{
      section_type: string;
      velocity_ftmin: number;
      ecd_local_ppg: number;
      pressure_loss_psi: number;
      tvd_ft: number;
    }>;
    critical_section: string | null;
    min_velocity_ftmin: number;
  };
  summary: {
    total_spp_psi: number;
    surface_equipment_psi: number;
    pipe_loss_psi: number;
    bit_loss_psi: number;
    annular_loss_psi: number;
    ecd_at_td: number;
    ecd_status: string;
    flow_rate: number;
    mud_weight: number;
    rheology_model: string;
  };
}

export interface SurgeSwabResult {
  surge_pressure_psi: number;
  swab_pressure_psi: number;
  surge_emw_ppg: number;
  swab_emw_ppg: number;
  surge_ecd_ppg: number;
  swab_ecd_ppg: number;
  effective_velocity_fpm: number;
  clinging_constant: number;
  pipe_velocity_fpm: number;
  pipe_status: string;
  surge_margin: string;
  swab_margin: string;
}
