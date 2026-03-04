"""
Ghost-field detection for the Shot Efficiency engine.
Pruebas SE-01 through SE-21 — one field changed at a time vs BASE params.

Run:
    python -m tests.ghost_field_test_shot_efficiency
or:
    python tests/ghost_field_test_shot_efficiency.py
"""
import sys
import os
import copy

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from orchestrator.shot_efficiency_engine.pipeline import calculate_full_shot_efficiency


# ── Log entries: 3 net-pay intervals covering all parameter interactions ──────
#
# Zone A  (8000–8009, 9 ft): clean sand, high φ, low Sw  → Archie model
#   GR=25 → Vsh≈0.012 (clean), RHOB=2.25/NPHI=0.22 → φ≈0.231, RT=20 → Sw≈0.216
#
# Zone B  (8012–8019, 7 ft): moderately shaly, Vsh≈0.30 → Simandoux model
#   GR=80 → Vsh≈0.304, RHOB=2.40/NPHI=0.17 → φ≈0.161, RT=10 → Sw≈0.384
#   (exercises rsh via Simandoux B_coeff = Vsh/rsh)
#   (Vsh=0.304 > vsh_max=0.30 ALT → Zone B excluded in SE-11)
#
# Zone C  (8021–8024, 3 ft): marginal φ and Sw (near both cutoffs)
#   GR=25 → Vsh≈0.012, RHOB=2.52/NPHI=0.09 → φ≈0.085, RT=25 → Sw≈0.526
#   φ=0.085 (> 0.08 BASE, < 0.12 ALT → excluded in SE-09)
#   Sw=0.526 (< 0.60 BASE, > 0.50 ALT → excluded in SE-10)
#   thickness=3 ft (≥2 BASE, <5 ALT → excluded in SE-12)
#
LOG_ENTRIES = (
    # Zone A — clean, excellent reservoir
    [{"md": float(md), "gr": 25.0, "rhob": 2.25, "nphi": 0.22, "rt": 20.0}
     for md in range(8000, 8010)]
    # Shale break
    + [{"md": float(md), "gr": 100.0, "rhob": 2.55, "nphi": 0.10, "rt": 1.5}
       for md in range(8010, 8012)]
    # Zone B — moderately shaly (Simandoux zone)
    + [{"md": float(md), "gr": 80.0, "rhob": 2.40, "nphi": 0.17, "rt": 10.0}
       for md in range(8012, 8020)]
    # Single shale point break
    + [{"md": 8020.0, "gr": 100.0, "rhob": 2.55, "nphi": 0.10, "rt": 1.5}]
    # Zone C — marginal φ/Sw (tests cutoffs)
    + [{"md": float(md), "gr": 25.0, "rhob": 2.52, "nphi": 0.09, "rt": 25.0}
       for md in range(8021, 8025)]
)


# ── BASE parameters (Section 2 of test document) ──────────────────────────────
BASE = dict(
    log_entries=LOG_ENTRIES,
    archie_params={"a": 1.0, "m": 2.0, "n": 2.0, "rw": 0.05},
    matrix_params={"rho_matrix": 2.65, "rho_fluid": 1.0, "gr_clean": 20.0, "gr_shale": 120.0},
    cutoffs={"phi_min": 0.08, "sw_max": 0.60, "vsh_max": 0.40, "min_thickness_ft": 2.0},
    perf_params={"spf": 4, "phasing_deg": 90, "perf_length_in": 12.0, "tunnel_radius_in": 0.20},
    reservoir_params={"kv_kh": 0.5, "wellbore_radius_ft": 0.354},
    sw_model="auto",
    rsh=5.0,
    estimate_permeability=True,   # enables sw_irreducible → Timur k
    sw_irreducible=0.25,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_alt(base: dict, field_path: str, new_val) -> dict:
    """Return params dict with one field changed.
    field_path: 'archie_params.a' → base['archie_params']['a'] = new_val
    """
    result = copy.deepcopy(base)
    if "." in field_path:
        parent, child = field_path.split(".", 1)
        result[parent] = {**result[parent], child: new_val}
    else:
        result[field_path] = new_val
    return result


def _flatten(result: dict) -> dict:
    """Pull out all numeric/string outputs that should change with input."""
    summ = result.get("summary", {})
    best_meta = summ.get("best_interval") or {}

    # Locate best interval detail for skin components
    best_top = best_meta.get("top_md")
    all_ivs = result.get("intervals_with_skin", [])
    best_iv = next(
        (iv for iv in all_ivs if iv.get("top_md") == best_top),
        {}
    )
    skin_comps = best_iv.get("skin_components", {})

    # Average k_md across all processed points (only when estimate_permeability=True)
    proc = result.get("processed_logs", [])
    k_vals = [p["k_md"] for p in proc if "k_md" in p]
    avg_k_md = round(sum(k_vals) / len(k_vals), 3) if k_vals else None

    return {
        # Summary averages (change with Archie/matrix/model params)
        "avg_porosity":      summ.get("avg_porosity"),
        "avg_sw":            summ.get("avg_sw"),
        "avg_vsh":           summ.get("avg_vsh"),
        "avg_sw_archie":     summ.get("avg_sw_archie"),   # None when model=archie
        # Net pay (change with cutoffs and GR matrix params)
        "net_pay_count":     summ.get("net_pay_intervals_count"),
        "total_net_pay_ft":  summ.get("total_net_pay_ft"),
        # Model selection indicator
        "sw_model_used":     summ.get("sw_model_used"),
        # Best interval stats (change with petrophysics + cutoffs)
        "best_avg_phi":      best_meta.get("avg_phi"),
        "best_avg_sw":       best_meta.get("avg_sw"),
        "best_score":        best_meta.get("score"),
        "best_thickness":    best_meta.get("thickness_ft"),
        "best_skin":         best_meta.get("skin_total"),
        # Skin components of best interval (change with perf/reservoir params)
        "skin_sp":           skin_comps.get("s_p"),
        "skin_sv":           skin_comps.get("s_v"),    # sensitive to kv_kh
        "skin_swb":          skin_comps.get("s_wb"),   # sensitive to wellbore_radius
        "skin_total":        best_iv.get("skin_total"),
        # Permeability (change with sw_irreducible when estimate_permeability=True)
        "avg_k_md":          avg_k_md,
    }


def _changed(base_flat: dict, alt_flat: dict) -> list:
    """Return list of keys that differ between base and alt."""
    return [k for k in base_flat if base_flat[k] != alt_flat[k]]


def run_test(test_id: str, description: str, field_path: str, alt_value):
    params_alt = _make_alt(BASE, field_path, alt_value)
    r_base = calculate_full_shot_efficiency(**BASE)
    r_alt  = calculate_full_shot_efficiency(**params_alt)

    f_base = _flatten(r_base)
    f_alt  = _flatten(r_alt)
    changed_keys = _changed(f_base, f_alt)

    verdict = "✅ PASA" if changed_keys else "❌ FANTASMA"
    print(f"{test_id:6s}  {verdict}  [{description}]")
    if changed_keys:
        for k in changed_keys[:4]:
            print(f"         {k}: {f_base[k]} → {f_alt[k]}")
    else:
        print(f"         Todos los outputs idénticos con {field_path}={_get_base_val(field_path)!r} vs {alt_value!r}")
    print()
    return bool(changed_keys), changed_keys


def _get_base_val(field_path: str):
    if "." in field_path:
        parent, child = field_path.split(".", 1)
        return BASE[parent][child]
    return BASE[field_path]


def main():
    print("=" * 72)
    print("PETROEXPERT — Ghost-field detection: Shot Efficiency engine")
    print("=" * 72)
    print()

    tests = [
        # ── Archie params (affect Sw → avg_sw) ──────────────────────────────
        ("SE-01", "Archie a: 1.0→0.62",              "archie_params.a",                     0.62),
        ("SE-02", "Archie m: 2.0→2.15",              "archie_params.m",                     2.15),
        ("SE-03", "Archie n: 2.0→1.94",              "archie_params.n",                     1.94),
        ("SE-04", "Rw (ohm-m): 0.05→0.12",           "archie_params.rw",                    0.12),
        # ── Matrix params (affect φ and Vsh) ─────────────────────────────────
        ("SE-05", "Rho matrix (g/cc): 2.65→2.71",    "matrix_params.rho_matrix",            2.71),
        ("SE-06", "Rho fluid (g/cc): 1.0→1.10",      "matrix_params.rho_fluid",             1.10),
        ("SE-07", "GR clean (API): 20→30",           "matrix_params.gr_clean",              30.0),
        ("SE-08", "GR shale (API): 120→90",          "matrix_params.gr_shale",              90.0),
        # ── Cutoffs (change net-pay interval count / thickness) ───────────────
        ("SE-09", "Phi min cutoff: 0.08→0.12",       "cutoffs.phi_min",                     0.12),
        ("SE-10", "Sw max cutoff: 0.60→0.50",        "cutoffs.sw_max",                      0.50),
        ("SE-11", "Vsh max cutoff: 0.40→0.30",       "cutoffs.vsh_max",                     0.30),
        ("SE-12", "Min thickness (ft): 2→5",         "cutoffs.min_thickness_ft",            5.0),
        # ── Perforation params (affect Karakas–Tariq skin) ────────────────────
        ("SE-13", "SPF: 4→8",                        "perf_params.spf",                     8),
        ("SE-14", "Phasing (°): 90→60",              "perf_params.phasing_deg",             60),
        ("SE-15", "Perf Length (in): 12→18",         "perf_params.perf_length_in",          18.0),
        ("SE-16", "kv/kh: 0.5→1.0",                 "reservoir_params.kv_kh",              1.0),
        ("SE-17", "Tunnel radius (in): 0.20→0.35",   "perf_params.tunnel_radius_in",        0.35),
        ("SE-18", "Wellbore radius (ft): 0.354→0.50","reservoir_params.wellbore_radius_ft", 0.50),
        # ── Global model params ───────────────────────────────────────────────
        ("SE-19", "Rsh (ohm-m): 5→15",              "rsh",                                 15.0),
        ("SE-20", "Sw model: auto→archie",           "sw_model",                            "archie"),
        ("SE-21", "Sw irreducible: 0.25→0.15",      "sw_irreducible",                      0.15),
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
