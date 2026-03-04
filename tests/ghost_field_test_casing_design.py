"""
Ghost-field detection for the Casing Design engine.
Pruebas CD-01 through CD-20 — one field changed at a time vs BASE params.

NOTE on CD-04: The test document lists "Grade" as an input, but Grade is
COMPUTED by select_casing_grade() from loads + SFs. It is NOT a direct
pipeline input. CD-04 is reformulated to test casing_id_in (8.535→8.000),
which affects cross-sectional area, axial stress, and biaxial correction.

NOTE on CD-11: fracture_gradient_ppg is declared as a pipeline parameter
but is never forwarded to any sub-module call. Expected FANTASMA.

NOTE on CD-18: internal_fluid_density_ppg is only active when
evacuation_level_ft > 0 (partial evac). With BASE evac=0 (full evacuation),
effective_evac = tvd_ft and p_internal = 0 for all depths regardless of
internal fluid. If CD-18 shows FANTASMA it is a TEST-DESIGN ghost, not a
structural bug (the field IS wired in calculate_collapse_load).

Run:
    python -m tests.ghost_field_test_casing_design
or:
    python tests/ghost_field_test_casing_design.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from orchestrator.casing_design_engine.pipeline import calculate_full_casing_design


# ── BASE parameters ────────────────────────────────────────────────────────────
# Casing: 9-5/8" 53.5 ppf Q125 (wall=0.545", ID=8.535")
# Well: 15000 ft MD / 9500 ft TVD, DLS=3°/100ft
# Fluids: MW=14 ppg, PP=12 ppg, FG=16.5 ppg, gas_grad=0.1 ppg
# Cement: TOC@5000 ft TVD, 16 ppg
# Design criteria: SFb=1.1, SFc=1.0, SFt=1.6
BASE = dict(
    casing_od_in=9.625,
    casing_id_in=8.535,
    wall_thickness_in=0.545,
    casing_weight_ppf=53.5,
    casing_length_ft=15000.0,
    tvd_ft=9500.0,
    mud_weight_ppg=14.0,
    pore_pressure_ppg=12.0,
    fracture_gradient_ppg=16.5,
    gas_gradient_ppg=0.1,
    cement_top_tvd_ft=5000.0,
    cement_density_ppg=16.0,
    bending_dls=3.0,
    overpull_lbs=50000.0,
    sf_burst=1.10,
    sf_collapse=1.00,
    sf_tension=1.60,
    bottomhole_temp_f=200.0,
    tubing_pressure_psi=0.0,
    internal_fluid_density_ppg=0.0,
    evacuation_level_ft=0.0,       # 0 = full evacuation (worst-case collapse)
    h2s_partial_pressure_psi=0.0,
)


# ── Flatten: capture outputs from ALL pipeline stages ──────────────────────────
def _flatten(result: dict) -> dict:
    """Pull out numeric/string outputs covering every pipeline stage."""
    summ  = result.get("summary", {})
    tl    = result.get("tension_load", {})
    bl    = result.get("burst_load", {})
    bx    = result.get("biaxial_correction", {})
    nace  = result.get("nace_compliance", {})
    tp    = result.get("tension_profile", {})
    cs    = result.get("collapse_scenarios", {})
    bscen = result.get("burst_scenarios", {})
    tscen = result.get("tension_scenarios", {})
    gsel  = result.get("grade_selection", {})

    bl_profile  = bl.get("profile", [])
    bscen_scen  = bscen.get("scenarios", {})
    cs_scen     = cs.get("scenarios", {})

    return {
        # ── Summary (most downstream aggregation) ──────────────────────────
        "max_burst_psi":        summ.get("max_burst_load_psi"),
        "max_collapse_psi":     summ.get("max_collapse_load_psi"),
        "total_tension_lbs":    summ.get("total_tension_lbs"),
        "burst_rating_psi":     summ.get("burst_rating_psi"),
        "collapse_rating_psi":  summ.get("collapse_rating_psi"),     # biaxial-corrected
        "collapse_orig_psi":    summ.get("collapse_rating_original_psi"),
        "tension_rating_lbs":   summ.get("tension_rating_lbs"),
        "sf_burst":             summ.get("sf_burst"),
        "sf_collapse":          summ.get("sf_collapse"),
        "sf_tension":           summ.get("sf_tension"),
        "sf_vme":               summ.get("sf_vme"),
        "selected_grade":       summ.get("selected_grade"),
        "overall_status":       summ.get("overall_status"),
        "eff_yield_psi":        summ.get("effective_yield_psi"),
        "temp_derate_factor":   summ.get("temp_derate_factor"),
        "triaxial_util_pct":    summ.get("triaxial_utilization_pct"),
        "governing_burst_scen": summ.get("governing_burst_scenario"),
        # ── Tension load components ─────────────────────────────────────────
        # catches: ppf, length, mud_wt (BF), od, id, dls
        "buoyant_wt_lbs":       tl.get("buoyant_weight_lbs"),
        "shock_lbs":            tl.get("shock_load_lbs"),
        "bending_lbs":          tl.get("bending_load_lbs"),
        "axial_stress_psi":     tl.get("axial_stress_psi"),
        "bf":                   tl.get("buoyancy_factor"),
        # ── Burst load profile (catches: cement_top, cement_density at depth) ─
        # max_burst is at surface where P_ext=0 (cement irrelevant), so use TD point
        "reservoir_psi":        bl.get("reservoir_pressure_psi"),
        "max_burst_bl_psi":     bl.get("max_burst_load_psi"),
        "burst_at_td_psi":      bl_profile[-1]["burst_load_psi"] if bl_profile else None,
        # ── Biaxial correction (catches: od, id, wall, yield, axial stress) ─
        "biaxial_rf":           bx.get("reduction_factor"),
        "biaxial_corr_psi":     bx.get("corrected_collapse_psi"),
        # ── NACE (catches: h2s, co2, temperature, grade) ───────────────────
        "nace_compliant":       nace.get("compliant"),
        "nace_severity":        nace.get("severity"),
        # ── Tension profile (catches: ppf, od, dls, mud_wt, shock_flag) ────
        "tp_max_tension_lbs":   tp.get("max_tension_lbs"),
        # ── Burst scenarios (catches: tubing_pressure, cement at depth) ────
        # gas_to_surface max is at surface — add tubing_leak to capture tubing_pressure_psi
        "tl_burst_psi":         bscen_scen.get("tubing_leak", {}).get("max_burst_psi"),
        # ── Collapse scenarios (catches: cement, internal_fluid, pp) ───────
        # governing_collapse_psi uses cement for p_external (CD-12, CD-13)
        # partial_evacuation uses int_fluid_ppg at depth>evac (CD-18)
        "cs_governing_scen":    cs.get("governing_scenario"),
        "cs_governing_psi":     cs.get("governing_collapse_psi"),   # key fixed
        "cs_pe_collapse_psi":   cs_scen.get("partial_evacuation", {}).get("max_collapse_psi"),
        # ── Tension scenarios (catches: overpull_lbs via stuck_pipe) ───────
        # governing is tension_running (shock > overpull with BASE values),
        # so stuck_pipe is the only place overpull propagates
        "stuck_tension_lbs":    tscen.get("stuck_pipe", {}).get("total_tension_lbs"),
        # ── Grade selection (catches: sf_burst_min / sf_collapse_min / sf_tension_min) ─
        # sf_min changes which grades qualify — captured via candidate count
        "grade_candidates":     len(gsel.get("all_candidates", [])),
    }


def _changed(base_flat: dict, alt_flat: dict) -> list:
    return [k for k in base_flat if base_flat[k] != alt_flat[k]]


def run_test(test_id: str, description: str, field: str, alt_value, note: str = ""):
    params_alt = {**BASE, field: alt_value}
    r_base = calculate_full_casing_design(**BASE)
    r_alt  = calculate_full_casing_design(**params_alt)

    f_base = _flatten(r_base)
    f_alt  = _flatten(r_alt)
    changed_keys = _changed(f_base, f_alt)

    verdict = "✅ PASA" if changed_keys else "❌ FANTASMA"
    print(f"{test_id:6s}  {verdict}  [{description}]")
    if note:
        print(f"         NOTE: {note}")
    if changed_keys:
        for k in changed_keys[:4]:
            print(f"         {k}: {f_base[k]} → {f_alt[k]}")
    else:
        print(f"         Todos los outputs idénticos con {field}={BASE.get(field)!r} vs {alt_value!r}")
    print()
    return bool(changed_keys), changed_keys


def main():
    print("=" * 72)
    print("PETROEXPERT — Ghost-field detection: Casing Design engine")
    print("=" * 72)
    print()

    tests = [
        # ── Grupo A: Geometría del Casing ─────────────────────────────────────
        ("CD-01", "OD (in): 9.625→7.000",
         "casing_od_in", 7.000, ""),
        ("CD-02", "Wall (in): 0.545→0.400",
         "wall_thickness_in", 0.400, ""),
        ("CD-03", "Weight (ppf): 53.5→47.0",
         "casing_weight_ppf", 47.0, ""),
        ("CD-04", "ID (in): 8.535→8.000  [Grade is computed, not input — testing casing_id_in]",
         "casing_id_in", 8.000, "Grade=Q125 is selected internally; casing_id_in tests area/axial/biaxial"),
        # ── Grupo B: Geometría del Pozo ───────────────────────────────────────
        ("CD-05", "Length/MD (ft): 15000→8000",
         "casing_length_ft", 8000.0, ""),
        ("CD-06", "TVD (ft): 9500→14000",
         "tvd_ft", 14000.0, ""),
        ("CD-07", "DLS (°/100ft): 3→10",
         "bending_dls", 10.0, ""),
        # ── Grupo C: Fluidos y Presiones ──────────────────────────────────────
        ("CD-08", "Mud Weight (ppg): 14→10",
         "mud_weight_ppg", 10.0, ""),
        ("CD-09", "Pore Pressure (ppg): 12→9",
         "pore_pressure_ppg", 9.0, ""),
        ("CD-10", "Gas Gradient (ppg): 0.1→0.15",
         "gas_gradient_ppg", 0.15, ""),
        ("CD-11", "Frac Gradient (ppg): 16.5→13.0  [alta sospecha de fantasma]",
         "fracture_gradient_ppg", 13.0,
         "fracture_gradient_ppg is declared in pipeline() but never forwarded to any sub-module"),
        # ── Grupo D: Cemento ──────────────────────────────────────────────────
        ("CD-12", "TOC TVD (ft): 5000→8000",
         "cement_top_tvd_ft", 8000.0, ""),
        ("CD-13", "Cement Density (ppg): 16→12",
         "cement_density_ppg", 12.0, ""),
        # ── Grupo E: Scenarios & Additional ───────────────────────────────────
        ("CD-14", "Evacuation Level: 0→-1  [ya confirmado PASA]",
         "evacuation_level_ft", -1.0, "-1 = no evacuation; collapse_load → 0"),
        ("CD-15", "H2S Partial Pressure (psi): 0→100  [ya confirmado PASA]",
         "h2s_partial_pressure_psi", 100.0, "Activates NACE sour-service compliance check"),
        ("CD-16", "BHT (°F): 200→400",
         "bottomhole_temp_f", 400.0, ""),
        ("CD-17", "Tubing Pressure (psi): 0→2000",
         "tubing_pressure_psi", 2000.0, ""),
        ("CD-18", "Internal Fluid (ppg): 0→8.6",
         "internal_fluid_density_ppg", 8.6,
         "With evac=0 (full evac), effective_evac=TVD so p_internal=0 for all depths. "
         "May appear as TEST-DESIGN ghost — field IS wired in calculate_collapse_load "
         "but BASE with full evac prevents it from having an effect"),
        ("CD-19", "Overpull (lbs): 50000→0",
         "overpull_lbs", 0.0, ""),
        # ── Grupo F: Design Criteria ───────────────────────────────────────────
        ("CD-20", "SF Burst Min: 1.1→1.5",
         "sf_burst", 1.5,
         "SF_burst actual=2.11 satisfies both 1.1 and 1.5 — grade may not change. "
         "FANTASMA = test-design issue (alt value must cross actual SF boundary to force grade change)"),
    ]

    results = []
    for args in tests:
        passed, keys = run_test(*args)
        results.append((args[0], args[1], passed))

    # ── Summary ────────────────────────────────────────────────────────────────
    print("=" * 72)
    print("RESUMEN")
    print("=" * 72)
    ghosts = [r for r in results if not r[2]]
    passes = [r for r in results if r[2]]
    print(f"PASA:    {len(passes):2d}")
    print(f"FANTASMA:{len(ghosts):2d}")
    if ghosts:
        print()
        print("Campos fantasma detectados:")
        for tid, desc, _ in ghosts:
            print(f"  {tid}: {desc}")
    print()


if __name__ == "__main__":
    main()
