"""
Ghost-field detection for the Vibrations engine.
Pruebas VI-01 through VI-17 — one field changed at a time vs BASE params.

Run:
    python -m tests.ghost_field_test_vibrations
or:
    python tests/ghost_field_test_vibrations.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from orchestrator.vibrations_engine.pipeline import calculate_full_vibration_analysis


# ── BASE parameters (match document Section 2) ────────────────────────────────
BASE = dict(
    wob_klb=20.0,
    rpm=120.0,
    rop_fph=60.0,
    torque_ftlb=12000.0,
    bit_diameter_in=8.5,
    mud_weight_ppg=10.0,
    pv_cp=None,
    hole_diameter_in=8.5,
    inclination_deg=15.0,
    friction_factor=0.25,
    dp_od_in=5.0,
    dp_id_in=4.276,
    dp_weight_lbft=19.5,
    stabilizer_spacing_ft=None,   # Auto → max 90 ft
    n_blades=None,
    ucs_psi=None,
    total_depth_ft=10000.0,       # Real well depth → activates two-section torsional model
    # pipeline also accepts bha_components=None (uses single-component defaults)
)

# ── Extract a flat comparison dict from the full result ───────────────────────
def _flatten(result: dict) -> dict:
    """Pull out all numeric/string outputs that should change with input."""
    s = result.get("summary", {})
    lat = result.get("lateral_vibrations", {})
    ax  = result.get("axial_vibrations", {})
    ss  = result.get("stick_slip", {})
    mse = result.get("mse", {})
    stab = result.get("stability", {})
    vmap = result.get("vibration_map", {})
    opt  = vmap.get("optimal_point", {})

    flat = {
        # summary
        "stability_index":      s.get("stability_index"),
        "crit_rpm_axial":       s.get("critical_rpm_axial"),
        "crit_rpm_lateral":     s.get("critical_rpm_lateral"),
        "stick_slip_severity":  s.get("stick_slip_severity"),
        "stick_slip_class":     s.get("stick_slip_class"),
        "mse_psi":              s.get("mse_psi"),
        "mse_efficiency_pct":   s.get("mse_efficiency_pct"),
        "optimal_wob":          opt.get("wob"),
        "optimal_rpm":          opt.get("rpm"),
        # lateral detail
        "lat_whirl_severity":   lat.get("whirl_severity_factor"),
        "lat_buoyed_weight":    lat.get("buoyed_weight_lbft"),
        "lat_lateral_weight":   lat.get("lateral_weight_lbft"),
        "lat_span_ft":          lat.get("span_used_ft"),
        # axial detail
        "ax_buoyancy_factor":   ax.get("buoyancy_factor"),
        # stick-slip detail (correct keys from stick_slip.py return dict)
        "ss_friction_torque":   ss.get("friction_torque_ftlb"),
        "ss_min_rpm_bit":       ss.get("rpm_min_at_bit"),
        "ss_max_rpm_bit":       ss.get("rpm_max_at_bit"),
        "ss_torsional_const":   ss.get("torsional_stiffness_inlb_rad"),
        "ss_damping_factor":    ss.get("damping_factor"),
        # MSE detail
        "mse_rotary_psi":       mse.get("mse_rotary_psi"),
        "mse_thrust_psi":       mse.get("mse_thrust_psi"),
        # stability scores
        "score_axial":          stab.get("mode_scores", {}).get("axial"),
        "score_lateral":        stab.get("mode_scores", {}).get("lateral"),
        "score_torsional":      stab.get("mode_scores", {}).get("torsional"),
        "score_mse":            stab.get("mode_scores", {}).get("mse"),
        # bit excitation (None when n_blades not provided)
        "bit_excite_present":   "bit_excitation" in result,
    }
    return flat


def _changed(base_flat: dict, alt_flat: dict) -> list:
    """Return list of keys that differ between base and alt."""
    return [k for k in base_flat if base_flat[k] != alt_flat[k]]


def run_test(test_id: str, description: str, field: str, alt_value):
    params_alt = {**BASE, field: alt_value}
    r_base = calculate_full_vibration_analysis(**BASE)
    r_alt  = calculate_full_vibration_analysis(**params_alt)

    f_base = _flatten(r_base)
    f_alt  = _flatten(r_alt)
    changed_keys = _changed(f_base, f_alt)

    verdict = "✅ PASA" if changed_keys else "❌ FANTASMA"
    print(f"{test_id:6s}  {verdict}  [{description}]")
    if changed_keys:
        for k in changed_keys[:4]:   # show max 4 changed keys
            print(f"         {k}: {f_base[k]} → {f_alt[k]}")
    else:
        print(f"         Todos los outputs idénticos con {field}={BASE[field]} vs {alt_value}")
    print()
    return bool(changed_keys), changed_keys


def main():
    print("=" * 72)
    print("PETROEXPERT — Ghost-field detection: Vibrations engine")
    print("=" * 72)
    print()

    tests = [
        ("VI-01", "WOB (klb): 20 → 40",                 "wob_klb",              40.0),
        ("VI-02", "RPM: 120 → 60",                       "rpm",                  60.0),
        ("VI-03", "Torque (ft-lb): 12000 → 6000",        "torque_ftlb",          6000.0),
        ("VI-04", "ROP (ft/hr): 60 → 120",               "rop_fph",              120.0),
        ("VI-05", "Bit Diameter (in): 8.5 → 12.25",      "bit_diameter_in",      12.25),
        ("VI-06", "Inclination (°): 15 → 60",            "inclination_deg",      60.0),
        ("VI-07", "Friction Coeff.: 0.25 → 0.50",        "friction_factor",      0.50),
        ("VI-08", "Mud Weight (ppg): 10 → 16",           "mud_weight_ppg",       16.0),
        ("VI-09", "DP OD (in): 5 → 6.625",               "dp_od_in",             6.625),
        ("VI-10", "DP ID (in): 4.276 → 3.500",           "dp_id_in",             3.500),
        ("VI-11", "DP Weight (lb/ft): 19.5 → 30",        "dp_weight_lbft",       30.0),
        ("VI-12", "UCS (psi): None → 15000",             "ucs_psi",              15000.0),
        ("VI-13", "PV (cP): None → 20",                  "pv_cp",                20.0),
        ("VI-14", "Stabilizer (ft): Auto → 30",          "stabilizer_spacing_ft", 30.0),
        ("VI-15", "Blades PDC: None → 5",                "n_blades",             5),
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
    print("NOTE: YP (VI-14 original) y Flow Rate (VI-15 original) no son parámetros")
    print("      del pipeline — se clasifican como campos inexistentes (no ghost).")


if __name__ == "__main__":
    main()
