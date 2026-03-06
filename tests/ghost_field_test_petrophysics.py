"""
Ghost-field detection for the Petrophysics engine.
Pruebas PE-01 through PE-11 — one parameter changed at a time vs BASE.

Tests run_full_evaluation with 20-point log dataset (MD 8000–8095, 5 ft spacing).
Also tests crossplot/pickett parameters (PE-12 through PE-16).

Run:
    python -m tests.ghost_field_test_petrophysics
or:
    python tests/ghost_field_test_petrophysics.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from orchestrator.petrophysics_engine.evaluation import run_full_evaluation
from orchestrator.petrophysics_engine.crossplots import generate_pickett_plot, crossplot_density_neutron
from orchestrator.petrophysics_engine.water_saturation import calculate_water_saturation_advanced


# ── 20-point log dataset (from TEST_GhostCmd_Petrofisica.md) ─────────────────
LOG_DATA = [
    {"md": 8000, "gr": 25, "rhob": 2.35, "nphi": 0.22, "rt": 45},
    {"md": 8005, "gr": 30, "rhob": 2.38, "nphi": 0.20, "rt": 40},
    {"md": 8010, "gr": 28, "rhob": 2.33, "nphi": 0.24, "rt": 50},
    {"md": 8015, "gr": 35, "rhob": 2.40, "nphi": 0.18, "rt": 30},
    {"md": 8020, "gr": 22, "rhob": 2.30, "nphi": 0.26, "rt": 65},
    {"md": 8025, "gr": 20, "rhob": 2.28, "nphi": 0.28, "rt": 80},
    {"md": 8030, "gr": 24, "rhob": 2.32, "nphi": 0.25, "rt": 55},
    {"md": 8035, "gr": 90, "rhob": 2.55, "nphi": 0.12, "rt": 5},
    {"md": 8040, "gr": 95, "rhob": 2.58, "nphi": 0.10, "rt": 3},
    {"md": 8045, "gr": 85, "rhob": 2.52, "nphi": 0.14, "rt": 8},
    {"md": 8050, "gr": 26, "rhob": 2.34, "nphi": 0.23, "rt": 48},
    {"md": 8055, "gr": 23, "rhob": 2.31, "nphi": 0.25, "rt": 60},
    {"md": 8060, "gr": 21, "rhob": 2.29, "nphi": 0.27, "rt": 72},
    {"md": 8065, "gr": 27, "rhob": 2.36, "nphi": 0.21, "rt": 42},
    {"md": 8070, "gr": 32, "rhob": 2.42, "nphi": 0.17, "rt": 25},
    {"md": 8075, "gr": 80, "rhob": 2.50, "nphi": 0.15, "rt": 10},
    {"md": 8080, "gr": 18, "rhob": 2.27, "nphi": 0.29, "rt": 90},
    {"md": 8085, "gr": 19, "rhob": 2.26, "nphi": 0.30, "rt": 100},
    {"md": 8090, "gr": 22, "rhob": 2.30, "nphi": 0.26, "rt": 70},
    {"md": 8095, "gr": 24, "rhob": 2.33, "nphi": 0.24, "rt": 55},
]

# ── BASE parameters ─────────────────────────────────────────────────────────
BASE_ARCHIE = {"a": 1.0, "m": 2.0, "n": 2.0, "rw": 0.05}
BASE_MATRIX = {"rho_matrix": 2.65, "rho_fluid": 1.0, "gr_clean": 20, "gr_shale": 120}
BASE_CUTOFFS = {"phi_min": 0.08, "sw_max": 0.60, "vsh_max": 0.40}


# ── Flatten the full evaluation result ───────────────────────────────────────
def _flatten(result: dict) -> dict:
    """Extract all comparable outputs from run_full_evaluation result."""
    s = result.get("summary", {})
    intervals = result.get("intervals", [])
    evaluated = result.get("evaluated_data", [])

    flat = {
        # Summary KPIs
        "total_points":     s.get("total_points"),
        "pay_points":       s.get("pay_points"),
        "net_pay_ft":       s.get("net_pay_ft"),
        "avg_phi_pay":      s.get("avg_phi_pay"),
        "avg_sw_pay":       s.get("avg_sw_pay"),
        "avg_perm_pay":     s.get("avg_perm_pay"),
        # Interval count
        "interval_count":   len(intervals),
    }

    # Per-interval data
    for i, iv in enumerate(intervals[:5]):
        flat[f"iv{i}_top"] = iv.get("top_md")
        flat[f"iv{i}_base"] = iv.get("base_md")
        flat[f"iv{i}_thick"] = iv.get("thickness_ft")
        flat[f"iv{i}_phi"] = iv.get("avg_phi")
        flat[f"iv{i}_sw"] = iv.get("avg_sw")
        flat[f"iv{i}_k"] = iv.get("avg_perm_md")

    # Per-point derived values (sample first, middle, last)
    for idx in [0, 3, 7, 10, 16, 19]:
        if idx < len(evaluated):
            pt = evaluated[idx]
            flat[f"pt{idx}_vsh"] = pt.get("vsh")
            flat[f"pt{idx}_phi_t"] = pt.get("phi_total")
            flat[f"pt{idx}_phi_e"] = pt.get("phi_effective")
            flat[f"pt{idx}_sw"] = pt.get("sw")
            flat[f"pt{idx}_sw_model"] = pt.get("sw_model")
            flat[f"pt{idx}_k_md"] = pt.get("k_md")
            flat[f"pt{idx}_is_pay"] = pt.get("is_pay")
            flat[f"pt{idx}_hc_sat"] = pt.get("hc_saturation")

    return flat


def _changed(base_flat: dict, alt_flat: dict) -> list:
    """Return list of keys that differ between base and alt."""
    return [k for k in base_flat if base_flat[k] != alt_flat[k]]


def run_eval_test(test_id: str, description: str,
                  archie_alt=None, matrix_alt=None, cutoffs_alt=None):
    """Run full evaluation with BASE vs ALT parameters, compare outputs."""
    r_base = run_full_evaluation(LOG_DATA, BASE_ARCHIE, BASE_MATRIX, BASE_CUTOFFS)
    r_alt = run_full_evaluation(
        LOG_DATA,
        archie_alt or BASE_ARCHIE,
        matrix_alt or BASE_MATRIX,
        cutoffs_alt or BASE_CUTOFFS,
    )

    f_base = _flatten(r_base)
    f_alt = _flatten(r_alt)
    changed_keys = _changed(f_base, f_alt)

    verdict = "✅ PASA" if changed_keys else "❌ FANTASMA"
    print(f"{test_id:6s}  {verdict}  [{description}]")
    if changed_keys:
        for k in changed_keys[:5]:
            print(f"         {k}: {f_base[k]} → {f_alt[k]}")
    else:
        print(f"         Todos los outputs idénticos — campo no afecta ningún cálculo")
    print()
    return bool(changed_keys), changed_keys


def run_sw_test(test_id: str, description: str, field: str, alt_value,
                base_override: dict = None):
    """Test calculate_water_saturation_advanced with one field changed."""
    base_kw = {"phi": 0.20, "rt": 45.0, "rw": 0.05, "vsh": 0.10,
               "rsh": 2.0, "a": 1.0, "m": 2.0, "n": 2.0, "method": "auto"}
    if base_override:
        base_kw.update(base_override)
    alt_kw = {**base_kw, field: alt_value}

    r_base = calculate_water_saturation_advanced(**base_kw)
    r_alt = calculate_water_saturation_advanced(**alt_kw)

    changed = [k for k in r_base if r_base[k] != r_alt[k]]
    verdict = "✅ PASA" if changed else "❌ FANTASMA"
    print(f"{test_id:6s}  {verdict}  [{description}]")
    if changed:
        for k in changed[:4]:
            print(f"         {k}: {r_base[k]} → {r_alt[k]}")
    else:
        print(f"         Todos los outputs idénticos con {field}={base_kw[field]} vs {alt_value}")
    print()
    return bool(changed), changed


def run_pickett_test(test_id: str, description: str, field: str, alt_value):
    """Test generate_pickett_plot with one param changed."""
    base_kw = {"rw": 0.05, "a": 1.0, "m": 2.0, "n": 2.0}
    # Build log data with phi/rt for pickett
    pickett_data = [{"phi": pt["nphi"], "rt": pt["rt"]} for pt in LOG_DATA if pt["nphi"] > 0.01]

    alt_kw = {**base_kw, field: alt_value}
    r_base = generate_pickett_plot(pickett_data, **base_kw)
    r_alt = generate_pickett_plot(pickett_data, **alt_kw)

    # Compare iso-Sw lines (points change with Archie params)
    base_iso = str(r_base.get("iso_sw_lines", {}))
    alt_iso = str(r_alt.get("iso_sw_lines", {}))
    changed = base_iso != alt_iso

    verdict = "✅ PASA" if changed else "❌ FANTASMA"
    print(f"{test_id:6s}  {verdict}  [{description}]")
    if changed:
        print(f"         iso_sw_lines changed with {field}={base_kw[field]} → {alt_value}")
    else:
        print(f"         iso_sw_lines identical — {field} has no effect")
    print()
    return changed, []


def run_crossplot_test(test_id: str, description: str, rho_fluid_alt: float):
    """Test crossplot_density_neutron with rho_fluid changed."""
    r_base = crossplot_density_neutron(LOG_DATA, rho_fluid=1.0)
    r_alt = crossplot_density_neutron(LOG_DATA, rho_fluid=rho_fluid_alt)

    # Compare phi_density values (change with rho_fluid)
    base_phis = [p["phi_density"] for p in r_base["points"]]
    alt_phis = [p["phi_density"] for p in r_alt["points"]]
    changed = base_phis != alt_phis

    # Compare lithology lines
    base_lith = str(r_base.get("lithology_lines", {}))
    alt_lith = str(r_alt.get("lithology_lines", {}))
    lith_changed = base_lith != alt_lith

    any_changed = changed or lith_changed
    verdict = "✅ PASA" if any_changed else "❌ FANTASMA"
    print(f"{test_id:6s}  {verdict}  [{description}]")
    if changed:
        print(f"         phi_density: {base_phis[0]} → {alt_phis[0]} (first point)")
    if lith_changed:
        print(f"         lithology_lines changed")
    if not any_changed:
        print(f"         All outputs identical with rho_fluid=1.0 vs {rho_fluid_alt}")
    print()
    return any_changed, []


def main():
    print("=" * 72)
    print("PETROEXPERT — Ghost-field detection: Petrophysics engine")
    print("Dataset: 20 points, MD 8000–8095 (5 ft spacing)")
    print("=" * 72)
    print()

    results = []

    # ── Section 1: run_full_evaluation parameters (PE-01 to PE-11) ───────────
    print("─── run_full_evaluation parameters ───")
    print()

    # Archie params
    p, k = run_eval_test("PE-01", "a (tortuosity): 1.0 → 0.81",
                         archie_alt={**BASE_ARCHIE, "a": 0.81})
    results.append(("PE-01", "a (tortuosity)", p))

    p, k = run_eval_test("PE-02", "m (cementation): 2.0 → 1.8",
                         archie_alt={**BASE_ARCHIE, "m": 1.8})
    results.append(("PE-02", "m (cementation)", p))

    p, k = run_eval_test("PE-03", "n (saturation exp): 2.0 → 1.8",
                         archie_alt={**BASE_ARCHIE, "n": 1.8})
    results.append(("PE-03", "n (saturation exp)", p))

    p, k = run_eval_test("PE-04", "Rw (ohm·m): 0.05 → 0.10",
                         archie_alt={**BASE_ARCHIE, "rw": 0.10})
    results.append(("PE-04", "Rw (ohm·m)", p))

    # Matrix params
    p, k = run_eval_test("PE-05", "rho_matrix (g/cc): 2.65 → 2.71 (limestone)",
                         matrix_alt={**BASE_MATRIX, "rho_matrix": 2.71})
    results.append(("PE-05", "rho_matrix", p))

    p, k = run_eval_test("PE-06", "rho_fluid (g/cc): 1.0 → 1.10 (saline mud)",
                         matrix_alt={**BASE_MATRIX, "rho_fluid": 1.10})
    results.append(("PE-06", "rho_fluid", p))

    p, k = run_eval_test("PE-07", "GR_clean (API): 20 → 10",
                         matrix_alt={**BASE_MATRIX, "gr_clean": 10})
    results.append(("PE-07", "GR_clean", p))

    p, k = run_eval_test("PE-08", "GR_shale (API): 120 → 100",
                         matrix_alt={**BASE_MATRIX, "gr_shale": 100})
    results.append(("PE-08", "GR_shale", p))

    # Cutoffs
    # NOTE: ALT values must cross actual data boundaries to detect effect.
    # Pay points have phi_e ~0.137–0.270, Sw ~0.083–0.327, Vsh ~0.00–0.15.
    # phi_min=0.15 excludes MD 8070 (phi_e=0.137) and MD 8015 (phi_e=0.141).
    p, k = run_eval_test("PE-09", "phi_min cutoff: 0.08 → 0.15",
                         cutoffs_alt={**BASE_CUTOFFS, "phi_min": 0.15})
    results.append(("PE-09", "phi_min cutoff", p))

    # sw_max=0.15 excludes several points with Sw > 0.15.
    p, k = run_eval_test("PE-10", "Sw_max cutoff: 0.60 → 0.15",
                         cutoffs_alt={**BASE_CUTOFFS, "sw_max": 0.15})
    results.append(("PE-10", "Sw_max cutoff", p))

    # vsh_max=0.05 excludes points with Vsh > 0.05 (MD 8005, 8010, 8015, 8065, 8070).
    p, k = run_eval_test("PE-11", "Vsh_max cutoff: 0.40 → 0.05",
                         cutoffs_alt={**BASE_CUTOFFS, "vsh_max": 0.05})
    results.append(("PE-11", "Vsh_max cutoff", p))

    # ── Section 2: Sw model direct params (PE-12 to PE-13) ──────────────────
    print("─── Water saturation direct parameters ───")
    print()

    # NOTE: rsh only used by Dual-Water model (cwb = 1/(rsh*0.3)).
    # Waxman-Smits does NOT use rsh — it's a true ghost in W-S.
    # Test W-S (vsh=0.25) to confirm ghost, then Dual-Water (vsh=0.50) to confirm it works.
    p, k = run_sw_test("PE-12a", "rsh in W-S model: 2.0 → 5.0 [vsh=0.25 → W-S]",
                       "rsh", 5.0, base_override={"vsh": 0.25})
    results.append(("PE-12a", "rsh in W-S (expected ghost)", p))

    p, k = run_sw_test("PE-12b", "rsh in Dual-Water: 2.0 → 5.0 [vsh=0.50 → DW]",
                       "rsh", 5.0, base_override={"vsh": 0.50})
    results.append(("PE-12b", "rsh in Dual-Water", p))

    p, k = run_sw_test("PE-13", "vsh (volume shale): 0.10 → 0.30 (force W-S model)",
                       "vsh", 0.30)
    results.append(("PE-13", "vsh (Sw direct)", p))

    # ── Section 3: Pickett plot params (PE-14 to PE-15) ─────────────────────
    print("─── Pickett plot parameters ───")
    print()

    p, _ = run_pickett_test("PE-14", "Pickett rw: 0.05 → 0.10", "rw", 0.10)
    results.append(("PE-14", "Pickett rw", p))

    p, _ = run_pickett_test("PE-15", "Pickett n (sat exp): 2.0 → 1.8", "n", 1.8)
    results.append(("PE-15", "Pickett n", p))

    # ── Section 4: Crossplot params (PE-16) ─────────────────────────────────
    print("─── Density-Neutron crossplot parameters ───")
    print()

    p, _ = run_crossplot_test("PE-16", "DN crossplot rho_fluid: 1.0 → 1.10", 1.10)
    results.append(("PE-16", "DN rho_fluid", p))

    # ── Summary ─────────────────────────────────────────────────────────────
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
