"""
Ghost-field detection for the Completion Design engine.
Pruebas CO-01 through CO-30 — one field changed at a time vs BASE params.

Run:
    python -m tests.ghost_field_test_completion_design
or:
    python tests/ghost_field_test_completion_design.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from orchestrator.completion_design_engine.pipeline import calculate_full_completion_design


# ── BASE parameters (Section 2 of test document) ──────────────────────────────
BASE = dict(
    # Casing & Formation
    casing_id_in=6.276,
    formation_permeability_md=100.0,
    formation_thickness_ft=30.0,
    reservoir_pressure_psi=5000.0,
    wellbore_pressure_psi=4500.0,
    depth_tvd_ft=10000.0,
    overburden_stress_psi=10000.0,
    pore_pressure_psi=4700.0,
    sigma_min_psi=6500.0,
    sigma_max_psi=8000.0,
    tensile_strength_psi=500.0,
    poisson_ratio=0.25,
    wellbore_radius_ft=0.354,
    kv_kh_ratio=0.5,
    tubing_od_in=0.0,
    temperature_f=200.0,
    formation_type="sandstone",
    completion_fluid="brine",
    # Perforation & Damage
    penetration_berea_in=12.0,
    effective_stress_psi=3000.0,
    damage_radius_ft=0.5,
    damage_permeability_md=50.0,
    # Production & VLP (Beggs & Brill)
    tubing_id_in=2.992,
    wellhead_pressure_psi=200.0,
    gor_scf_stb=500.0,
    water_cut=0.10,
    oil_api=35.0,
    gas_sg=0.70,
    water_sg=1.07,
    surface_temp_f=80.0,
)


# ── Flatten: capture outputs from ALL pipeline stages ─────────────────────────

def _flatten(result: dict) -> dict:
    """Pull out numeric/string outputs that should change with each input."""
    summ  = result.get("summary", {})
    pen   = result.get("penetration", {})
    gun   = result.get("gun_selection", {})
    ub    = result.get("underbalance", {})
    frac  = result.get("fracture_initiation", {})
    fg    = result.get("fracture_gradient", {})
    opt   = result.get("optimization", {})
    ipr   = result.get("ipr", {})
    nodal = result.get("nodal", {})

    rec_gun   = gun.get("recommended") or {}
    pt_check  = rec_gun.get("pt_check") or {}
    opt_conf  = opt.get("optimal_configuration") or {}
    skin_c    = opt_conf.get("skin_components") or {}

    return {
        # ── Penetration (CO-08, CO-10, CO-19, CO-20) ──────────────────────
        "pen_corrected_in":  summ.get("penetration_corrected_in"),
        "cf_stress":         pen.get("correction_factors", {}).get("cf_stress"),
        "cf_temp":           pen.get("correction_factors", {}).get("cf_temperature"),
        "cf_fluid":          pen.get("correction_factors", {}).get("cf_fluid"),
        # ── Gun selection (CO-01, CO-07) ───────────────────────────────────
        "gun_size":          rec_gun.get("gun_size"),
        "gun_clearance":     rec_gun.get("clearance_in"),
        "total_guns":        gun.get("total_compatible_guns"),
        "is_through_tubing": gun.get("is_through_tubing"),
        # ── P/T rating check (CO-08, CO-11) ───────────────────────────────
        "gun_pt_overall":    pt_check.get("overall_pass"),
        # ── Underbalance (CO-02, CO-09, CO-11, CO-12) ─────────────────────
        "ub_psi":            summ.get("underbalance_psi"),
        "ub_status":         summ.get("underbalance_status"),
        "ub_range":          str(ub.get("recommended_range_psi")),  # list → str for diff
        "perm_class":        ub.get("permeability_class"),
        # ── Fracture initiation (CO-13 to CO-17) ──────────────────────────
        "breakdown_psi":     summ.get("breakdown_pressure_psi"),
        "closure_psi":       frac.get("closure_pressure_psi"),
        "reopen_psi":        frac.get("reopening_pressure_psi"),
        "stress_ratio":      frac.get("stress_ratio"),
        "stress_regime":     frac.get("stress_regime"),
        # ── Fracture gradient (CO-04, CO-13, CO-14, CO-18) ────────────────
        "fg_ppg":            summ.get("fracture_gradient_ppg"),
        "mw_window_ppg":     summ.get("mud_weight_window_ppg"),
        # ── Optimization / Karakas-Tariq skin (CO-05, CO-06, CO-19–22) ───
        "opt_pr":            summ.get("productivity_ratio"),
        "skin_total":        summ.get("skin_total"),
        "skin_sv":           skin_c.get("s_vertical"),
        "skin_sd":           skin_c.get("s_damage"),
        # ── IPR (CO-02, CO-03, CO-05, CO-11) ──────────────────────────────
        "aof_stbd":          ipr.get("AOF_stbd"),
        "flow_eff":          ipr.get("flow_efficiency"),
        # ── Nodal analysis (CO-03, CO-04, CO-11, CO-23–CO-30) ─────────────
        "q_op":              nodal.get("operating_point_q"),
        "pwf_op":            nodal.get("operating_point_Pwf_psi"),
    }


def _changed(base_flat: dict, alt_flat: dict) -> list:
    return [k for k in base_flat if base_flat[k] != alt_flat[k]]


def run_test(test_id: str, description: str, field: str, alt_value):
    params_alt = {**BASE, field: alt_value}
    r_base = calculate_full_completion_design(**BASE)
    r_alt  = calculate_full_completion_design(**params_alt)

    f_base = _flatten(r_base)
    f_alt  = _flatten(r_alt)
    changed_keys = _changed(f_base, f_alt)

    verdict = "✅ PASA" if changed_keys else "❌ FANTASMA"
    print(f"{test_id:6s}  {verdict}  [{description}]")
    if changed_keys:
        for k in changed_keys[:4]:
            print(f"         {k}: {f_base[k]} → {f_alt[k]}")
    else:
        print(f"         Todos los outputs idénticos con {field}={BASE[field]!r} vs {alt_value!r}")
    print()
    return bool(changed_keys), changed_keys


def main():
    print("=" * 72)
    print("PETROEXPERT — Ghost-field detection: Completion Design engine")
    print("=" * 72)
    print()

    tests = [
        # ── Grupo A: Casing & Formation ───────────────────────────────────────
        ("CO-01", "ID Casing (in): 6.276→4.950",          "casing_id_in",              4.950),
        ("CO-02", "Permeabilidad (mD): 100→1000",         "formation_permeability_md", 1000.0),
        ("CO-03", "Espesor Neto (ft): 30→5",              "formation_thickness_ft",    5.0),
        ("CO-04", "TVD (ft): 10000→5000",                 "depth_tvd_ft",              5000.0),
        ("CO-05", "Radio Pozo (ft): 0.354→0.25",          "wellbore_radius_ft",        0.25),
        ("CO-06", "Kv/Kh: 0.5→0.1",                      "kv_kh_ratio",               0.1),
        ("CO-07", "OD Tubing (in): 0→2.875",              "tubing_od_in",              2.875),
        ("CO-08", "BHT (°F): 200→400",                    "temperature_f",             400.0),
        ("CO-09", "Tipo Formación: sandstone→carbonate",  "formation_type",            "carbonate"),
        ("CO-10", "Fluido Completación: brine→diesel",    "completion_fluid",          "diesel"),
        # ── Grupo B: Pressures & Stresses ────────────────────────────────────
        ("CO-11", "P Reservorio (psi): 5000→3000",        "reservoir_pressure_psi",    3000.0),
        ("CO-12", "P Pozo (psi): 4500→3000",              "wellbore_pressure_psi",     3000.0),
        ("CO-13", "P Poro (psi): 4700→3000",              "pore_pressure_psi",         3000.0),
        ("CO-14", "Sobrecarga (psi): 10000→15000",        "overburden_stress_psi",     15000.0),
        ("CO-15", "σ_min (psi): 6500→4000",               "sigma_min_psi",             4000.0),
        ("CO-16", "σ_max (psi): 8000→12000",              "sigma_max_psi",             12000.0),
        ("CO-17", "T. Tensión (psi): 500→2000",           "tensile_strength_psi",      2000.0),
        ("CO-18", "Ratio Poisson: 0.25→0.35",             "poisson_ratio",             0.35),
        # ── Grupo C: Perforation & Damage ─────────────────────────────────────
        ("CO-19", "Penetración Berea (in): 12→6",         "penetration_berea_in",      6.0),
        ("CO-20", "Esfuerzo Efectivo (psi): 3000→8000",   "effective_stress_psi",      8000.0),
        ("CO-21", "Radio Daño (ft): 0.5→0",               "damage_radius_ft",          0.0),
        ("CO-22", "Perm. Daño (mD): 50→5",                "damage_permeability_md",    5.0),
        # ── Grupo D: Producción & Tubing/VLP ──────────────────────────────────
        ("CO-23", "ID Tubing (in): 2.992→1.995",          "tubing_id_in",              1.995),
        ("CO-24", "P Cabezal (psi): 200→1000",            "wellhead_pressure_psi",     1000.0),
        ("CO-25", "GOR (scf/STB): 500→2000",              "gor_scf_stb",               2000.0),
        ("CO-26", "Corte Agua: 0.10→0.80",                "water_cut",                 0.80),
        ("CO-27", "API Gravity (°API): 35→15",            "oil_api",                   15.0),
        ("CO-28", "Gas SG: 0.70→1.0",                     "gas_sg",                    1.0),
        ("CO-29", "Water SG: 1.07→1.20",                  "water_sg",                  1.20),
        ("CO-30", "T Superficie (°F): 80→40",             "surface_temp_f",            40.0),
    ]

    results = []
    for args in tests:
        passed, keys = run_test(*args)
        results.append((args[0], args[1], passed))

    # ── Summary table ─────────────────────────────────────────────────────────
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
