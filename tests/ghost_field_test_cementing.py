"""
Ghost-field detection for the Cementing engine.
Pruebas CE-01 through CE-21 — one field changed at a time vs BASE params.

NOTE on CE-21 (pore_pressure_ppg): In calculate_ecd_during_job(), the value is
accepted and echoed in the return dict ("pore_pressure_ppg": pore_pressure_ppg)
but NEVER used in any calculation (ECD alerts only compare vs fracture_gradient,
not vs pore_pressure). Expected STRUCTURAL GHOST.

NOTE on CE-03 (hole_id_in): Document proposes 8.75 → impossible (hole < casing OD).
Corrected to 10.625 per document note.

Run:
    python -m tests.ghost_field_test_cementing
or:
    python tests/ghost_field_test_cementing.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from orchestrator.cementing_engine.pipeline import calculate_full_cementing


# ── BASE parameters ────────────────────────────────────────────────────────────
# 9-5/8" casing, 12.25" hole, 10000 ft shoe, TOC@5000 ft
# Fluids: MW=10.5, Spacer=14, Lead=13.5, Tail=16 ppg
BASE = dict(
    casing_od_in=9.625,
    casing_id_in=8.681,
    hole_id_in=12.25,
    casing_shoe_md_ft=10000.0,
    casing_shoe_tvd_ft=9500.0,
    toc_md_ft=5000.0,
    toc_tvd_ft=4750.0,
    float_collar_md_ft=9900.0,
    mud_weight_ppg=10.5,
    spacer_density_ppg=14.0,
    lead_cement_density_ppg=13.5,
    tail_cement_density_ppg=16.0,
    tail_length_ft=500.0,
    spacer_volume_bbl=25.0,
    excess_pct=50.0,
    rat_hole_ft=50.0,
    pump_rate_bbl_min=5.0,
    pv_mud=15.0,
    yp_mud=10.0,
    fracture_gradient_ppg=16.5,
    pore_pressure_ppg=9.0,
)


# ── Flatten: capture COMPUTED outputs (no echo-back of raw inputs) ─────────────
def _flatten(result: dict) -> dict:
    """Pull out computed outputs from all pipeline stages."""
    summ  = result.get("summary", {})
    vol   = result.get("volumes", {})
    disp  = result.get("displacement", {})
    ecd   = result.get("ecd_during_job", {})
    ff    = result.get("free_fall", {})
    ut    = result.get("utube", {})
    bhp   = result.get("bhp_schedule", {})
    lift  = result.get("lift_pressure", {})

    return {
        # ── Summary (catches most downstream outputs) ───────────────────────
        "total_cement_bbl":     summ.get("total_cement_bbl"),
        "total_cement_sacks":   summ.get("total_cement_sacks"),
        "displacement_bbl":     summ.get("displacement_bbl"),
        "total_pump_bbl":       summ.get("total_pump_bbl"),
        "job_time_hrs":         summ.get("job_time_hrs"),
        "max_ecd_ppg":          summ.get("max_ecd_ppg"),
        "fracture_margin_ppg":  summ.get("fracture_margin_ppg"),
        "max_bhp_psi":          summ.get("max_bhp_psi"),
        "lift_pressure_psi":    summ.get("lift_pressure_psi"),
        "free_fall_ft":         summ.get("free_fall_ft"),
        "utube_psi":            summ.get("utube_psi"),
        "ecd_status":           summ.get("ecd_status"),
        "num_alerts":           len(summ.get("alerts", [])),
        # ── Volumes (catches: od, id, hole_id, shoe_md, toc_md, fc_md,
        #                     tail_len, spacer_vol, excess, rat_hole) ──────
        "ann_cap_bbl_ft":       vol.get("annular_capacity_bbl_ft"),
        "csg_cap_bbl_ft":       vol.get("casing_capacity_bbl_ft"),
        "lead_cement_bbl":      vol.get("lead_cement_bbl"),
        "tail_cement_bbl":      vol.get("tail_cement_bbl"),
        "spacer_vol_bbl":       vol.get("spacer_volume_bbl"),
        "lead_sacks":           vol.get("lead_cement_sacks"),
        "tail_sacks":           vol.get("tail_cement_sacks"),
        # ── Displacement (catches: pump_rate) ──────────────────────────────
        "total_stages":         len(disp.get("stages", [])) if disp else None,
        # ── ECD (catches: shoe_tvd, hole_id, od, mud_wt, lead, tail dens,
        #                  pump_rate, pv, yp, fg, pore_pressure) ──────────
        "max_ecd_raw":          ecd.get("max_ecd_ppg"),
        "min_fg_margin":        ecd.get("min_fracture_margin_ppg"),
        "min_pp_margin":        ecd.get("min_pp_margin_ppg"),
        "ann_velocity":         ecd.get("annular_velocity_ft_min"),
        # ── Free-fall (catches: shoe_tvd, mud_wt, tail_cement, id, hole) ──
        "free_fall_height":     ff.get("free_fall_height_ft"),
        "free_fall_occurs":     ff.get("free_fall_occurs"),
        # ── U-tube (catches: shoe_tvd, mud_wt, lead_cement, toc_tvd,
        #                     id, hole_id, od) ────────────────────────────
        "utube_imbalance_psi":  ut.get("pressure_imbalance_psi"),
        "utube_occurs":         ut.get("utube_occurs"),
        # ── BHP schedule (catches: shoe_tvd, mud, spacer, lead, tail,
        #                          spacer_vol, lead_bbl, tail_bbl, disp_bbl,
        #                          hole, od, id, pump_rate, pv, yp) ────────
        "max_bhp_raw":          bhp.get("max_bhp_psi"),
        # ── Lift pressure (catches: shoe_tvd, toc_tvd, lead_cement,
        #                           mud_wt, hole_id, od, id) ───────────────
        "lift_psi_raw":         lift.get("lift_pressure_psi"),
    }


def _changed(base_flat: dict, alt_flat: dict) -> list:
    return [k for k in base_flat if base_flat[k] != alt_flat[k]]


def run_test(test_id: str, description: str, field: str, alt_value, note: str = ""):
    params_alt = {**BASE, field: alt_value}
    r_base = calculate_full_cementing(**BASE)
    r_alt  = calculate_full_cementing(**params_alt)

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
    print("PETROEXPERT — Ghost-field detection: Cementing engine")
    print("=" * 72)
    print()

    tests = [
        # ── Grupo A: Geometría ─────────────────────────────────────────────────
        ("CE-01", "OD Casing (in): 9.625→7.000",
         "casing_od_in", 7.000, ""),
        ("CE-02", "ID Casing (in): 8.681→6.276",
         "casing_id_in", 6.276, ""),
        ("CE-03", "ID Hoyo (in): 12.25→10.625  [8.75 imposible: hole<OD; corregido a 10.625]",
         "hole_id_in", 10.625, "10.625 > OD=9.625 → annular_cap decreases, all volumes decrease"),
        # ── Grupo B: Profundidades ─────────────────────────────────────────────
        ("CE-04", "Zapata MD (ft): 10000→6000",
         "casing_shoe_md_ft", 6000.0, ""),
        ("CE-05", "Zapata TVD (ft): 9500→6000",
         "casing_shoe_tvd_ft", 6000.0, "TVD affects BHP, ECD (pressure column), free-fall; MD affects volumes"),
        ("CE-06", "TOC MD (ft): 5000→8000",
         "toc_md_ft", 8000.0, ""),
        ("CE-07", "TOC TVD (ft): 4750→7600",
         "toc_tvd_ft", 7600.0, "Affects U-tube (cement_top_tvd_ft) and lift_pressure (toc_tvd)"),
        ("CE-08", "Float Collar MD (ft): 9900→9500",
         "float_collar_md_ft", 9500.0, "shoe_track = shoe_md - fc_md: 100→500 ft; displacement changes"),
        # ── Grupo C: Densidades ────────────────────────────────────────────────
        ("CE-09", "Peso Lodo (ppg): 10.5→14",
         "mud_weight_ppg", 14.0, ""),
        ("CE-10", "Densidad Spacer (ppg): 14→10",
         "spacer_density_ppg", 10.0,
         "Spacer density is passed to ecd_during_job and bhp_schedule"),
        ("CE-11", "Lead Cement (ppg): 13.5→11",
         "lead_cement_density_ppg", 11.0, ""),
        ("CE-12", "Tail Cement (ppg): 16→12  [ya confirmado PASA]",
         "tail_cement_density_ppg", 12.0, "ECD, BHP, free-fall, cement class all change"),
        # ── Grupo D: Volúmenes y Operacional ──────────────────────────────────
        ("CE-13", "Long. Tail (ft): 500→2000",
         "tail_length_ft", 2000.0, ""),
        ("CE-14", "Vol. Spacer (bbl): 25→50",
         "spacer_volume_bbl", 50.0, ""),
        ("CE-15", "Exceso (%): 50→0",
         "excess_pct", 0.0, ""),
        ("CE-16", "Rat Hole (ft): 50→200",
         "rat_hole_ft", 200.0, ""),
        ("CE-17", "Pump Rate (bbl/min): 5→2",
         "pump_rate_bbl_min", 2.0, ""),
        # ── Grupo E: Reología ──────────────────────────────────────────────────
        ("CE-18", "PV Lodo (cP): 15→50",
         "pv_mud", 50.0, ""),
        ("CE-19", "YP Lodo (lb/100ft²): 10→30",
         "yp_mud", 30.0, ""),
        # ── Grupo F: Pressure Boundaries ──────────────────────────────────────
        ("CE-20", "Grad. Fractura (ppg): 16.5→13",
         "fracture_gradient_ppg", 13.0, ""),
        ("CE-21", "Presión Poro (ppg): 9→12",
         "pore_pressure_ppg", 12.0,
         "In ecd.py: accepted + forwarded but only echoed in return dict; "
         "NOT used in any calculation. Expected STRUCTURAL GHOST."),
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
