"""
Ghost Field Detection — Wellbore Cleanup Module
Tests that every UI input field affects at least one output.

Methodology:
1. Run engine with BASE parameters → record all outputs
2. Change ONLY one field to ALT value → re-run
3. Compare: at least 1 output changed → PASS. All identical → GHOST

12 fields total.
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.wellbore_cleanup_engine import WellboreCleanupEngine


# ── BASE parameters ──────────────────────────────────────────────────
BASE = {
    "flow_rate": 500,
    "mud_weight": 10.0,
    "pv": 15,
    "yp": 10,
    "hole_id": 8.5,
    "pipe_od": 5.0,
    "inclination": 0,
    "rop": 60.0,
    "cutting_size": 0.25,
    "cutting_density": 21.0,
    "rpm": 0,
    "annular_length": 1000.0,
}

# ── ALT values per field ─────────────────────────────────────────────
ALTS = {
    "flow_rate":       {"alt": 250,    "id": "WC-01", "label": "Caudal (gpm)"},
    "hole_id":         {"alt": 12.25,  "id": "WC-02", "label": "Diámetro Hoyo (in)"},
    "pipe_od":         {"alt": 3.5,    "id": "WC-03", "label": "OD DP (in)"},
    "mud_weight":      {"alt": 14.0,   "id": "WC-04", "label": "Peso Lodo (ppg)"},
    "pv":              {"alt": 40,     "id": "WC-05", "label": "VP (cP)"},
    "yp":              {"alt": 25,     "id": "WC-06", "label": "PC (lb/100ft²)"},
    "inclination":     {"alt": 45,     "id": "WC-07", "label": "Inclinación (°)"},
    "rpm":             {"alt": 120,    "id": "WC-08", "label": "RPM"},
    "rop":             {"alt": 150,    "id": "WC-09", "label": "ROP (ft/hr)"},
    "cutting_size":    {"alt": 0.75,   "id": "WC-10", "label": "Cutting Size (in)"},
    "cutting_density": {"alt": 25.0,   "id": "WC-11", "label": "Cutting Density (ppg)"},
    "annular_length":  {"alt": 5000.0, "id": "WC-12", "label": "Annular Length (ft)"},
}


def flatten(d: dict, prefix: str = "") -> dict:
    """Recursively flatten a nested dict, capturing ALL downstream outputs."""
    out = {}
    for k, v in d.items():
        key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            out.update(flatten(v, key))
        elif isinstance(v, list):
            # Flatten list items (alerts, etc.)
            for i, item in enumerate(v):
                if isinstance(item, dict):
                    out.update(flatten(item, f"{key}[{i}]"))
                else:
                    out[f"{key}[{i}]"] = item
            out[f"{key}.__len__"] = len(v)
        else:
            out[key] = v
    return out


def run_test():
    # ── BASE run ──────────────────────────────────────────────────────
    base_result = WellboreCleanupEngine.calculate_full_cleanup(**BASE)
    base_flat = flatten(base_result)

    print("=" * 80)
    print("GHOST FIELD TEST — Wellbore Cleanup Module")
    print("=" * 80)

    # Print BASE outputs for reference
    print("\n── BASE Outputs ──")
    for k in sorted(base_flat.keys()):
        print(f"  {k}: {base_flat[k]}")

    print("\n── Test Results ──")
    print(f"{'ID':<7} {'Campo':<25} {'Base→Alt':<20} {'Δ Outputs':<10} {'Veredicto'}")
    print("-" * 80)

    results = []
    ghosts = []

    for field, spec in ALTS.items():
        alt_params = {**BASE, field: spec["alt"]}
        alt_result = WellboreCleanupEngine.calculate_full_cleanup(**alt_params)
        alt_flat = flatten(alt_result)

        # Compare all keys
        all_keys = set(base_flat.keys()) | set(alt_flat.keys())
        changed = []
        for k in sorted(all_keys):
            bv = base_flat.get(k)
            av = alt_flat.get(k)
            if bv != av:
                changed.append((k, bv, av))

        verdict = "PASA" if changed else "FANTASMA"
        base_val = BASE[field]
        alt_val = spec["alt"]

        print(f"{spec['id']:<7} {spec['label']:<25} {str(base_val)+'→'+str(alt_val):<20} {len(changed):<10} {verdict}")

        if changed:
            for k, bv, av in changed[:5]:  # Show first 5 changes
                print(f"        Δ {k}: {bv} → {av}")
            if len(changed) > 5:
                print(f"        ... and {len(changed) - 5} more")
        else:
            ghosts.append(spec["id"])

        results.append({
            "id": spec["id"],
            "field": field,
            "label": spec["label"],
            "base": base_val,
            "alt": alt_val,
            "n_changed": len(changed),
            "verdict": verdict,
            "changes": [(k, str(bv), str(av)) for k, bv, av in changed],
        })

    # ── Summary ───────────────────────────────────────────────────────
    passed = sum(1 for r in results if r["verdict"] == "PASA")
    total = len(results)

    print("\n" + "=" * 80)
    print(f"RESUMEN: {passed}/{total} PASA")
    if ghosts:
        print(f"FANTASMAS DETECTADOS: {', '.join(ghosts)}")
    else:
        print("SIN CAMPOS FANTASMA — todos los inputs afectan al menos un output")
    print("=" * 80)

    return results, ghosts


if __name__ == "__main__":
    results, ghosts = run_test()
    sys.exit(1 if ghosts else 0)
