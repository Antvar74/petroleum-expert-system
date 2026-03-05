"""
Ghost-field detection for the Packer Forces engine.
Pruebas PF-01 through PF-16 — one field changed at a time vs BASE params.

Run:
    python -m tests.ghost_field_test_packer_forces
or:
    python tests/ghost_field_test_packer_forces.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from orchestrator.packer_forces_engine.pipeline import calculate_total_packer_force


# ── BASE parameters (match document Pruebas_CamposFantasma_PackerForces) ───────
BASE = dict(
    tubing_od=2.875,
    tubing_id=2.441,
    tubing_weight=6.5,
    tubing_length=10000.0,
    seal_bore_id=3.25,
    initial_tubing_pressure=0.0,
    final_tubing_pressure=3000.0,
    initial_annulus_pressure=0.0,
    final_annulus_pressure=0.0,
    initial_temperature=80.0,
    final_temperature=250.0,
    packer_depth_tvd=10000.0,
    mud_weight_tubing=8.34,
    mud_weight_annulus=8.34,
    poisson_ratio=0.30,
    thermal_expansion=6.9e-6,
)


# ── Extract a flat comparison dict from the full result ───────────────────────
def _flatten(result: dict) -> dict:
    """Pull out all numeric/string outputs that should change with input."""
    s  = result.get("summary", {})
    fc = result.get("force_components", {})
    mv = result.get("movements", {})

    return {
        # summary
        "total_force_lbs":          s.get("total_force_lbs"),
        "force_direction":          s.get("force_direction"),
        "piston_force_lbs":         s.get("piston_force_lbs"),
        "ballooning_force_lbs":     s.get("ballooning_force_lbs"),
        "temperature_force_lbs":    s.get("temperature_force_lbs"),
        "total_movement_inches":    s.get("total_movement_inches"),
        "movement_piston_in":       s.get("movement_piston_in"),
        "movement_balloon_in":      s.get("movement_balloon_in"),
        "movement_thermal_in":      s.get("movement_thermal_in"),
        "buckling_status":          s.get("buckling_status"),
        "buckling_critical_lbs":    s.get("buckling_critical_load_lbs"),
        # force components (redundant but explicit)
        "fc_piston":                fc.get("piston"),
        "fc_ballooning":            fc.get("ballooning"),
        "fc_temperature":           fc.get("temperature"),
        "fc_total":                 fc.get("total"),
        # movements
        "mv_piston_in":             mv.get("piston_in"),
        "mv_ballooning_in":         mv.get("ballooning_in"),
        "mv_thermal_in":            mv.get("thermal_in"),
        "mv_total_in":              mv.get("total_in"),
        # alert count (catches cases where only alert text changes)
        "alert_count":              len(s.get("alerts", [])),
    }


def _changed(base_flat: dict, alt_flat: dict) -> list:
    """Return list of keys that differ between base and alt."""
    return [k for k in base_flat if base_flat[k] != alt_flat[k]]


def run_test(test_id: str, description: str, field: str, alt_value):
    params_alt = {**BASE, field: alt_value}
    r_base = calculate_total_packer_force(**BASE)
    r_alt  = calculate_total_packer_force(**params_alt)

    f_base = _flatten(r_base)
    f_alt  = _flatten(r_alt)
    changed_keys = _changed(f_base, f_alt)

    verdict = "✅ PASA" if changed_keys else "❌ FANTASMA"
    print(f"{test_id:6s}  {verdict}  [{description}]")
    if changed_keys:
        for k in changed_keys[:4]:
            print(f"         {k}: {f_base[k]} → {f_alt[k]}")
    else:
        print(f"         Todos los outputs idénticos con {field}={BASE[field]} vs {alt_value}")
    print()
    return bool(changed_keys), changed_keys


def main():
    print("=" * 72)
    print("PETROEXPERT — Ghost-field detection: Packer Forces engine")
    print("=" * 72)
    print()

    tests = [
        ("PF-01", "Tubing OD (in): 2.875 → 3.500",           "tubing_od",               3.500),
        ("PF-02", "Tubing ID (in): 2.441 → 2.200 (thicker wall; 2.992>OD is invalid)", "tubing_id", 2.200),
        ("PF-03", "Tubing Weight (lb/ft): 6.5 → 9.3",        "tubing_weight",           9.3),
        ("PF-04", "Tubing Length (ft): 10000 → 8000",        "tubing_length",           8000.0),
        ("PF-05", "Seal Bore ID (in): 3.25 → 4.00",          "seal_bore_id",            4.00),
        ("PF-06", "Final Tubing Press (psi): 3000 → 5000",   "final_tubing_pressure",   5000.0),
        ("PF-07", "Initial Tubing Press (psi): 0 → 500",     "initial_tubing_pressure", 500.0),
        ("PF-08", "Final Annulus Press (psi): 0 → 1000",     "final_annulus_pressure",  1000.0),
        ("PF-09", "Initial Annulus Press (psi): 0 → 500",    "initial_annulus_pressure",500.0),
        ("PF-10", "Initial Temperature (°F): 80 → 120",      "initial_temperature",     120.0),
        ("PF-11", "Final Temperature (°F): 250 → 350",       "final_temperature",       350.0),
        ("PF-12", "Packer Depth TVD (ft): 10000 → 5000",     "packer_depth_tvd",        5000.0),
        ("PF-13", "MW Tubing (ppg): 8.34 → 10.0",            "mud_weight_tubing",       10.0),
        ("PF-14", "MW Annulus (ppg): 8.34 → 10.0",           "mud_weight_annulus",      10.0),
        ("PF-15", "Poisson Ratio: 0.30 → 0.28",              "poisson_ratio",           0.28),
        ("PF-16", "Thermal Expansion: 6.9e-6 → 6.5e-6",      "thermal_expansion",       6.5e-6),
    ]

    results = []
    for args in tests:
        passed, keys = run_test(*args)
        results.append((args[0], args[1], passed))

    # ── Summary table ──────────────────────────────────────────────────────────
    print("=" * 72)
    print("RESUMEN")
    print("=" * 72)
    ghosts = [r for r in results if not r[2]]
    passes = [r for r in results if r[2]]
    print(f"PASA:     {len(passes):2d} / {len(results)}")
    print(f"FANTASMA: {len(ghosts):2d} / {len(results)}")
    if ghosts:
        print()
        print("Campos fantasma detectados:")
        for tid, desc, _ in ghosts:
            print(f"  {tid}: {desc}")
    else:
        print()
        print("Sin campos fantasma — todos los inputs afectan al menos un output.")


if __name__ == "__main__":
    main()
