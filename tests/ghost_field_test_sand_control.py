"""
Ghost-field detection — Sand Control module
============================================
Each test changes ONE input vs BASE and verifies that at least one
computed output changes. If ALL outputs remain identical → CAMPO FANTASMA.

Methodology: same as ghost_field_test_cementing.py, ghost_field_test_vibrations.py, etc.

Standards: Saucier (1974), API RP 19C, Mohr-Coulomb, Kirsch (1898)
Date: 2026-03-04
"""
import pytest
from orchestrator.sand_control_engine import SandControlEngine

# ── BASE parameters (mirror UI defaults) ──────────────────────────────────────
BASE = dict(
    sieve_sizes_mm=[2.0, 0.85, 0.425, 0.25, 0.15, 0.075],
    cumulative_passing_pct=[100, 95, 70, 40, 15, 2],
    hole_id=8.5,
    screen_od=5.5,
    interval_length=50,
    ucs_psi=500,
    friction_angle_deg=30,
    reservoir_pressure_psi=4500,
    overburden_stress_psi=10000,
    formation_permeability_md=500,
    wellbore_radius_ft=0.354,
    wellbore_type="cased",
    gravel_permeability_md=80000,
    pack_factor=1.4,
    washout_factor=1.1,
)


def _run(**overrides):
    """Run full pipeline with BASE params, optionally overriding fields."""
    params = {**BASE, **overrides}
    return SandControlEngine.calculate_full_sand_control(**params)


def _flatten(r: dict) -> dict:
    """
    Extract all COMPUTED outputs (no echoed inputs).
    Rule: only include values that are derived from calculations,
    not direct re-echoes of input parameters.
    """
    psd = r.get("psd", {})
    gravel = r.get("gravel", {})
    screen = r.get("screen", {})
    drawdown = r.get("drawdown", {})
    volume = r.get("volume", {})
    skin = r.get("skin", {})
    completion = r.get("completion", {})

    # Completion method scores (list → flatten to dict for comparison)
    method_scores = {m["method"]: m["score"] for m in completion.get("methods", [])}

    return {
        # PSD computed values
        "d10_mm": psd.get("d10_mm"),
        "d50_mm": psd.get("d50_mm"),
        "d90_mm": psd.get("d90_mm"),
        "uniformity_coefficient": psd.get("uniformity_coefficient"),
        "sorting": psd.get("sorting"),
        # Gravel selection (Saucier)
        "gravel_min_mm": gravel.get("gravel_min_mm"),
        "gravel_max_mm": gravel.get("gravel_max_mm"),
        "recommended_pack": gravel.get("recommended_pack"),
        "reference_d_mm": gravel.get("reference_d_mm"),
        # Screen selection
        "slot_size_mm": screen.get("slot_size_mm"),
        "screen_type": screen.get("screen_type"),
        "estimated_retention_pct": screen.get("estimated_retention_pct"),
        # Drawdown (Mohr-Coulomb + Kirsch)
        "critical_drawdown_psi": drawdown.get("critical_drawdown_psi"),
        "effective_overburden_psi": drawdown.get("effective_overburden_psi"),
        "effective_horizontal_psi": drawdown.get("effective_horizontal_psi"),
        "kirsch_sigma_theta": drawdown.get("kirsch_sigma_theta"),
        "cohesion_psi": drawdown.get("cohesion_psi"),
        "sanding_risk": drawdown.get("sanding_risk"),
        # Gravel volume
        "gravel_volume_bbl": volume.get("gravel_volume_bbl"),
        "effective_hole_id_in": volume.get("effective_hole_id_in"),
        # Skin components
        "skin_total": skin.get("skin_total"),
        "skin_perforation": skin.get("skin_perforation"),
        "skin_gravel": skin.get("skin_gravel"),
        "skin_damage": skin.get("skin_damage"),
        # Completion type recommendation + scores
        "recommended_completion": completion.get("recommended"),
        **{f"score_{k}": v for k, v in method_scores.items()},
    }


BASE_FLAT = _flatten(_run())


def _check(test_id: str, **overrides):
    """Assert that changing the override(s) produces at least one different output."""
    alt_flat = _flatten(_run(**overrides))
    diffs = {k: (BASE_FLAT[k], alt_flat[k]) for k in BASE_FLAT if BASE_FLAT[k] != alt_flat[k]}
    assert diffs, (
        f"{test_id} CAMPO FANTASMA — ningún output cambió al modificar {list(overrides.keys())}"
    )


# ── Grupo A: Granulometría ────────────────────────────────────────────────────

def test_SC01_sieve_sizes():
    """Tamices más finos → D10/D50/D90 bajan, gravel mesh cambia, slot baja."""
    _check("SC-01",
           sieve_sizes_mm=[1.0, 0.5, 0.25, 0.125, 0.063, 0.031],
           cumulative_passing_pct=[100, 95, 70, 40, 15, 2])


def test_SC02_cumulative_passing():
    """Más finos retenidos → curva PSD se desplaza, D50/Cu cambian."""
    _check("SC-02", cumulative_passing_pct=[100, 98, 90, 60, 30, 5])


# ── Grupo B: Geometría ────────────────────────────────────────────────────────

def test_SC03_hole_diameter():
    """Hoyo más grande → volumen anular sube ((Dh²-OD²)×L), gravel vol. sube."""
    _check("SC-03", hole_id=12.25)


def test_SC04_screen_od():
    """Screen más pequeño → espacio anular mayor → gravel vol. sube."""
    _check("SC-04", screen_od=3.5)


def test_SC05_interval_length():
    """Intervalo ×2 → gravel vol. ×2, gravel weight ×2."""
    _check("SC-05", interval_length=100)


def test_SC06_wellbore_radius():
    """Radio pozo menor → todos los ln(r_x/rw) en skin cambian."""
    _check("SC-06", wellbore_radius_ft=0.25)


# ── Grupo C: Geomecánica ──────────────────────────────────────────────────────

def test_SC07_ucs():
    """UCS ×4 → cohesión sube → critical drawdown sube → riesgo puede bajar."""
    _check("SC-07", ucs_psi=2000)


def test_SC08_friction_angle():
    """Ángulo fricción 30°→45° → Mohr-Coulomb: C0 cambia, drawdown cambia."""
    _check("SC-08", friction_angle_deg=45)


def test_SC09_reservoir_pressure():
    """P reservorio baja → σ_v_eff sube → drawdown cambia."""
    _check("SC-09", reservoir_pressure_psi=2000)


def test_SC10_overburden_stress():
    """Sobrecarga ÷2 → σ_v baja → σ_H, σ_h bajan (Kirsch) → drawdown cambia."""
    _check("SC-10", overburden_stress_psi=5000)


# ── Grupo D: Permeabilidad y Skin ─────────────────────────────────────────────

def test_SC11_formation_permeability():
    """k_form 500→10 mD → ratios k_form/k_gravel cambian, completion scores cambian."""
    _check("SC-11", formation_permeability_md=10)


def test_SC12_gravel_permeability():
    """k_grava 80000→20000 mD → S_gravel = (k_form/k_grava - 1)×ln(...) cambia."""
    _check("SC-12", gravel_permeability_md=20000)


# ── Grupo E: Factores Operacionales ──────────────────────────────────────────

def test_SC13_pack_factor():
    """Factor empaque 1.4→1.0 → gravel vol. = ann_vol × factor baja."""
    _check("SC-13", pack_factor=1.0)


def test_SC14_washout_factor():
    """Factor lavado 1.1→1.5 → D_eff = D_hole×√(washout) sube → vol. sube."""
    _check("SC-14", washout_factor=1.5)


# ── Grupo F: Tipo Completación ────────────────────────────────────────────────

def test_SC15_wellbore_type():
    """
    Entubado→Descubierto:
    - screen_type: wire_wrap → premium_mesh
    - skin_perforation: S_perf=0 (no perforaciones en hoyo abierto)
    - completion scores: OHGP +3, CHGP -3
    """
    _check("SC-15", wellbore_type="openhole")
