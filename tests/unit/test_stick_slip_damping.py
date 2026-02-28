"""Tests for Stribeck + viscous damping in stick-slip model."""
from orchestrator.vibrations_engine.stick_slip import calculate_stick_slip_severity


def test_stribeck_higher_rpm_reduces_severity():
    """At 160 RPM, Stribeck friction is lower than at 40 RPM."""
    common = dict(
        wob_klb=20, torque_ftlb=15000, bit_diameter_in=8.5,
        bha_length_ft=300, bha_od_in=6.75, bha_id_in=2.813,
        mud_weight_ppg=10.0, friction_factor=0.25,
    )
    low_rpm = calculate_stick_slip_severity(surface_rpm=40, **common)
    high_rpm = calculate_stick_slip_severity(surface_rpm=160, **common)
    assert high_rpm["severity_index"] < low_rpm["severity_index"], (
        f"160 RPM severity ({high_rpm['severity_index']}) should be < 40 RPM ({low_rpm['severity_index']})"
    )


def test_stribeck_very_high_rpm_approaches_dynamic_friction():
    """At 250+ RPM, severity should be ~60% of the static value."""
    common = dict(
        wob_klb=15, torque_ftlb=10000, bit_diameter_in=8.5,
        bha_length_ft=300, bha_od_in=6.75, bha_id_in=2.813,
        mud_weight_ppg=10.0, friction_factor=0.25,
    )
    low = calculate_stick_slip_severity(surface_rpm=5, **common)
    high = calculate_stick_slip_severity(surface_rpm=250, **common)
    ratio = high["severity_index"] / low["severity_index"] if low["severity_index"] > 0 else 1.0
    assert 0.3 <= ratio <= 0.8, f"Ratio {ratio:.3f} not in [0.3, 0.8]"


def test_viscous_damping_with_pv():
    """Higher plastic viscosity -> more damping (lower damping_factor)."""
    common = dict(
        surface_rpm=100, wob_klb=20, torque_ftlb=15000, bit_diameter_in=8.5,
        bha_length_ft=300, bha_od_in=6.75, bha_id_in=2.813,
        mud_weight_ppg=12.0, friction_factor=0.25,
        hole_diameter_in=8.5,
    )
    no_pv = calculate_stick_slip_severity(**common)  # PV estimated from MW
    high_pv = calculate_stick_slip_severity(pv_cp=45, **common)
    # Higher PV → lower damping factor (more energy dissipated)
    assert high_pv["damping_factor"] < no_pv["damping_factor"], (
        f"PV=45 damping ({high_pv['damping_factor']}) should be < default ({no_pv['damping_factor']})"
    )


def test_damped_output_includes_damping_fields():
    """Result dict should include Stribeck and damping metadata."""
    result = calculate_stick_slip_severity(
        surface_rpm=120, wob_klb=20, torque_ftlb=15000,
        bit_diameter_in=8.5, bha_length_ft=300,
        bha_od_in=6.75, bha_id_in=2.813,
        mud_weight_ppg=10.0, friction_factor=0.25,
        pv_cp=30, hole_diameter_in=8.5,
    )
    assert "stribeck_friction_factor" in result
    assert "damping_factor" in result
    assert "severity_undamped" in result
    assert result["stribeck_friction_factor"] <= 0.25
    assert 0 < result["damping_factor"] <= 1.0


def test_backward_compatible_without_new_params():
    """Without pv_cp/hole_diameter_in, damping still works with defaults."""
    result = calculate_stick_slip_severity(
        surface_rpm=120, wob_klb=20, torque_ftlb=15000,
        bit_diameter_in=8.5, bha_length_ft=300,
        bha_od_in=6.75, bha_id_in=2.813,
    )
    assert result["severity_index"] > 0
    assert "stribeck_friction_factor" in result
