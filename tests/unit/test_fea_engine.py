"""
Unit tests for FEA beam element solver -- BHA lateral vibration analysis.

Covers element matrices, assembly, eigenvalue solve, forced response, Campbell.
"""
import math
import pytest
import numpy as np


# ---------------------------------------------------------------------------
# Task 1: Element matrices
# ---------------------------------------------------------------------------
class TestBeamElementMatrices:
    """Verify 4x4 Euler-Bernoulli beam element [K], [Kg], [M] matrices."""

    def test_stiffness_matrix_shape_and_symmetry(self):
        """Ke must be 4x4 and symmetric."""
        from orchestrator.vibrations_engine.fea import beam_element_matrices
        Ke, Kge, Me = beam_element_matrices(
            length_in=360.0, EI=1e9, rhoA=0.5, P=0.0
        )
        assert Ke.shape == (4, 4)
        np.testing.assert_allclose(Ke, Ke.T, atol=1e-10)

    def test_mass_matrix_shape_and_symmetry(self):
        """Me must be 4x4 and symmetric."""
        from orchestrator.vibrations_engine.fea import beam_element_matrices
        Ke, Kge, Me = beam_element_matrices(
            length_in=360.0, EI=1e9, rhoA=0.5, P=0.0
        )
        assert Me.shape == (4, 4)
        np.testing.assert_allclose(Me, Me.T, atol=1e-10)

    def test_geometric_stiffness_zero_when_no_axial_load(self):
        """With P=0, Kge should be all zeros."""
        from orchestrator.vibrations_engine.fea import beam_element_matrices
        Ke, Kge, Me = beam_element_matrices(
            length_in=360.0, EI=1e9, rhoA=0.5, P=0.0
        )
        np.testing.assert_allclose(Kge, np.zeros((4, 4)), atol=1e-15)

    def test_geometric_stiffness_nonzero_with_axial_load(self):
        """With P>0, Kge must have non-zero entries."""
        from orchestrator.vibrations_engine.fea import beam_element_matrices
        Ke, Kge, Me = beam_element_matrices(
            length_in=360.0, EI=1e9, rhoA=0.5, P=10000.0
        )
        assert np.any(np.abs(Kge) > 0)
        np.testing.assert_allclose(Kge, Kge.T, atol=1e-10)

    def test_stiffness_k11_value(self):
        """K[0,0] = 12*EI/L^3 for Euler-Bernoulli beam."""
        from orchestrator.vibrations_engine.fea import beam_element_matrices
        L = 120.0  # inches
        EI = 2e9
        Ke, _, _ = beam_element_matrices(length_in=L, EI=EI, rhoA=0.5, P=0.0)
        expected_k11 = 12.0 * EI / L**3
        assert abs(Ke[0, 0] - expected_k11) < 1e-3

    def test_mass_m11_value(self):
        """M[0,0] = 156*rhoA*L/420 for consistent mass."""
        from orchestrator.vibrations_engine.fea import beam_element_matrices
        L = 120.0
        rhoA = 0.5
        _, _, Me = beam_element_matrices(length_in=L, EI=2e9, rhoA=rhoA, P=0.0)
        expected_m11 = 156.0 * rhoA * L / 420.0
        assert abs(Me[0, 0] - expected_m11) < 1e-6


# ---------------------------------------------------------------------------
# Task 2: Global assembly
# ---------------------------------------------------------------------------
class TestGlobalAssembly:
    """Verify global matrix assembly from BHA component list."""

    @pytest.fixture
    def two_collar_bha(self):
        """Simple BHA: two 30-ft drill collars."""
        return [
            {"type": "collar", "od": 6.75, "id_inner": 2.813, "length_ft": 30.0, "weight_ppf": 83.0},
            {"type": "collar", "od": 6.75, "id_inner": 2.813, "length_ft": 30.0, "weight_ppf": 83.0},
        ]

    def test_assembly_matrix_sizes(self, two_collar_bha):
        """Two 30-ft elements → 3 nodes → 6x6 global matrices."""
        from orchestrator.vibrations_engine.fea import assemble_global_matrices
        K, Kg, M, node_positions = assemble_global_matrices(
            bha_components=two_collar_bha,
            mud_weight_ppg=10.0,
            wob_klb=20.0,
        )
        # 2 elements → 3 nodes → 6 DOF
        assert K.shape == (6, 6)
        assert Kg.shape == (6, 6)
        assert M.shape == (6, 6)
        assert len(node_positions) == 3

    def test_assembly_symmetry(self, two_collar_bha):
        """Global K, M must remain symmetric after assembly."""
        from orchestrator.vibrations_engine.fea import assemble_global_matrices
        K, Kg, M, _ = assemble_global_matrices(
            bha_components=two_collar_bha,
            mud_weight_ppg=10.0,
            wob_klb=20.0,
        )
        np.testing.assert_allclose(K, K.T, atol=1e-8)
        np.testing.assert_allclose(M, M.T, atol=1e-8)

    def test_node_positions_cumulative(self, two_collar_bha):
        """Node positions must accumulate element lengths (in feet)."""
        from orchestrator.vibrations_engine.fea import assemble_global_matrices
        _, _, _, node_positions = assemble_global_matrices(
            bha_components=two_collar_bha,
            mud_weight_ppg=10.0,
            wob_klb=20.0,
        )
        np.testing.assert_allclose(node_positions, [0.0, 30.0, 60.0], atol=1e-6)

    def test_assembly_single_element(self):
        """Single component → 2 nodes → 4x4 matrices (same as element)."""
        from orchestrator.vibrations_engine.fea import assemble_global_matrices
        bha = [{"type": "collar", "od": 6.75, "id_inner": 2.813, "length_ft": 30.0, "weight_ppf": 83.0}]
        K, Kg, M, _ = assemble_global_matrices(bha, mud_weight_ppg=10.0, wob_klb=0.0)
        assert K.shape == (4, 4)


# ---------------------------------------------------------------------------
# Task 3: Eigenvalue solver
# ---------------------------------------------------------------------------
class TestEigenvalueSolver:
    """Verify FEA eigenvalue solution for natural frequencies and mode shapes."""

    @pytest.fixture
    def uniform_bha(self):
        """10-element uniform BHA for reasonable frequency resolution."""
        return [
            {"type": "collar", "od": 6.75, "id_inner": 2.813, "length_ft": 30.0, "weight_ppf": 83.0}
            for _ in range(10)
        ]

    def test_returns_correct_number_of_modes(self, uniform_bha):
        """Should return requested number of modes."""
        from orchestrator.vibrations_engine.fea import assemble_global_matrices, solve_eigenvalue
        K, Kg, M, _ = assemble_global_matrices(uniform_bha, mud_weight_ppg=10.0, wob_klb=0.0)
        result = solve_eigenvalue(K, Kg, M, bc="pinned-pinned", n_modes=3)
        assert len(result["frequencies_hz"]) == 3
        assert len(result["critical_rpms"]) == 3
        assert len(result["mode_shapes"]) == 3

    def test_frequencies_are_positive_and_ascending(self, uniform_bha):
        """Natural frequencies must be positive and in ascending order."""
        from orchestrator.vibrations_engine.fea import assemble_global_matrices, solve_eigenvalue
        K, Kg, M, _ = assemble_global_matrices(uniform_bha, mud_weight_ppg=10.0, wob_klb=0.0)
        result = solve_eigenvalue(K, Kg, M, bc="pinned-pinned", n_modes=5)
        freqs = result["frequencies_hz"]
        assert all(f > 0 for f in freqs)
        for i in range(len(freqs) - 1):
            assert freqs[i] <= freqs[i + 1]

    def test_mode_shapes_are_normalized(self, uniform_bha):
        """Each mode shape vector should have max abs deflection = 1.0."""
        from orchestrator.vibrations_engine.fea import assemble_global_matrices, solve_eigenvalue
        K, Kg, M, _ = assemble_global_matrices(uniform_bha, mud_weight_ppg=10.0, wob_klb=0.0)
        result = solve_eigenvalue(K, Kg, M, bc="pinned-pinned", n_modes=3)
        for shape in result["mode_shapes"]:
            assert abs(max(abs(d) for d in shape) - 1.0) < 1e-6

    def test_pinned_pinned_bc_zero_at_ends(self, uniform_bha):
        """For pinned-pinned, deflection at both ends should be zero (BC enforced)."""
        from orchestrator.vibrations_engine.fea import assemble_global_matrices, solve_eigenvalue
        K, Kg, M, _ = assemble_global_matrices(uniform_bha, mud_weight_ppg=10.0, wob_klb=0.0)
        result = solve_eigenvalue(K, Kg, M, bc="pinned-pinned", n_modes=3)
        for shape in result["mode_shapes"]:
            # First and last entries are y-deflections at end nodes
            assert abs(shape[0]) < 1e-6   # bit end
            assert abs(shape[-1]) < 1e-6  # top end

    def test_wob_reduces_natural_frequencies(self, uniform_bha):
        """Axial compression (WOB) should reduce natural frequencies."""
        from orchestrator.vibrations_engine.fea import assemble_global_matrices, solve_eigenvalue
        K0, Kg0, M0, _ = assemble_global_matrices(uniform_bha, mud_weight_ppg=10.0, wob_klb=0.0)
        r0 = solve_eigenvalue(K0, Kg0, M0, bc="pinned-pinned", n_modes=3)

        K1, Kg1, M1, _ = assemble_global_matrices(uniform_bha, mud_weight_ppg=10.0, wob_klb=30.0)
        r1 = solve_eigenvalue(K1, Kg1, M1, bc="pinned-pinned", n_modes=3)

        # With WOB, frequencies should be lower
        for f0, f1 in zip(r0["frequencies_hz"], r1["frequencies_hz"]):
            assert f1 < f0

    def test_analytical_pinned_pinned_uniform_beam(self, uniform_bha):
        """Compare mode-1 frequency against analytical: f1 = (pi/L^2)*sqrt(EI/rhoA)."""
        from orchestrator.vibrations_engine.fea import assemble_global_matrices, solve_eigenvalue
        K, Kg, M, _ = assemble_global_matrices(uniform_bha, mud_weight_ppg=10.0, wob_klb=0.0)
        result = solve_eigenvalue(K, Kg, M, bc="pinned-pinned", n_modes=1)

        # Analytical first mode for pinned-pinned: omega_1 = pi^2 * sqrt(EI / (rhoA * L^4))
        od, id_in = 6.75, 2.813
        I_mom = math.pi * (od**4 - id_in**4) / 64.0
        EI = 30e6 * I_mom
        bf = 1.0 - 10.0 / 65.5
        rhoA = (83.0 * bf / 32.174) / 12.0  # slug/in
        L_total = 300.0 * 12.0  # 300 ft in inches

        omega_analytical = (math.pi**2) * math.sqrt(EI / (rhoA * L_total**4))
        f_analytical = omega_analytical / (2.0 * math.pi)

        # FEA should be within 5% of analytical for 10 elements
        error_pct = abs(result["frequencies_hz"][0] - f_analytical) / f_analytical * 100
        assert error_pct < 5.0, f"FEA f1={result['frequencies_hz'][0]:.4f}, analytical={f_analytical:.4f}, error={error_pct:.1f}%"


# ---------------------------------------------------------------------------
# Task 4: Forced response and Campbell diagram
# ---------------------------------------------------------------------------
class TestForcedResponse:
    """Verify forced response amplitude calculation."""

    @pytest.fixture
    def uniform_bha(self):
        return [
            {"type": "collar", "od": 6.75, "id_inner": 2.813, "length_ft": 30.0, "weight_ppf": 83.0}
            for _ in range(10)
        ]

    def test_forced_response_returns_amplitudes(self, uniform_bha):
        """Forced response should return amplitude array."""
        from orchestrator.vibrations_engine.fea import (
            assemble_global_matrices, solve_eigenvalue, solve_forced_response,
        )
        # WOB=0 to avoid near-buckling on 300ft uniform BHA
        K, Kg, M, _ = assemble_global_matrices(uniform_bha, mud_weight_ppg=10.0, wob_klb=0.0)
        eigen = solve_eigenvalue(K, Kg, M, bc="pinned-pinned", n_modes=3)
        result = solve_forced_response(
            K=K, Kg=Kg, M=M, bc="pinned-pinned",
            excitation_freq_hz=eigen["frequencies_hz"][0] * 0.5,
            excitation_node=5,  # mid-BHA node (interior, not constrained)
            force_lbs=100.0,
            mud_weight_ppg=10.0,
        )
        assert "amplitudes" in result
        assert "max_amplitude_in" in result
        assert result["max_amplitude_in"] > 0

    def test_amplitude_peaks_near_resonance(self, uniform_bha):
        """Amplitude should be much larger near a natural frequency."""
        from orchestrator.vibrations_engine.fea import (
            assemble_global_matrices, solve_eigenvalue, solve_forced_response,
        )
        K, Kg, M, _ = assemble_global_matrices(uniform_bha, mud_weight_ppg=10.0, wob_klb=0.0)
        eigen = solve_eigenvalue(K, Kg, M, bc="pinned-pinned", n_modes=3)
        f1 = eigen["frequencies_hz"][0]

        off_res = solve_forced_response(
            K=K, Kg=Kg, M=M, bc="pinned-pinned",
            excitation_freq_hz=f1 * 0.3, excitation_node=5, force_lbs=100.0,
            mud_weight_ppg=10.0,
        )
        near_res = solve_forced_response(
            K=K, Kg=Kg, M=M, bc="pinned-pinned",
            excitation_freq_hz=f1 * 0.95, excitation_node=5, force_lbs=100.0,
            mud_weight_ppg=10.0,
        )
        assert near_res["max_amplitude_in"] > off_res["max_amplitude_in"] * 2


class TestCampbellDiagram:
    """Verify Campbell diagram data generation."""

    @pytest.fixture
    def uniform_bha(self):
        return [
            {"type": "collar", "od": 6.75, "id_inner": 2.813, "length_ft": 30.0, "weight_ppf": 83.0}
            for _ in range(10)
        ]

    def test_campbell_returns_expected_keys(self, uniform_bha):
        """Campbell must return rpm_values, natural_freq_curves, excitation_lines, crossings."""
        from orchestrator.vibrations_engine.fea import generate_campbell_diagram
        result = generate_campbell_diagram(
            bha_components=uniform_bha,
            wob_klb=20.0, mud_weight_ppg=10.0,
            hole_diameter_in=8.5, bc="pinned-pinned",
            rpm_min=40, rpm_max=200, rpm_step=20, n_modes=3,
        )
        assert "rpm_values" in result
        assert "natural_freq_curves" in result
        assert "excitation_lines" in result
        assert "crossings" in result

    def test_campbell_rpm_range(self, uniform_bha):
        """RPM values should match requested range."""
        from orchestrator.vibrations_engine.fea import generate_campbell_diagram
        result = generate_campbell_diagram(
            bha_components=uniform_bha,
            wob_klb=20.0, mud_weight_ppg=10.0,
            hole_diameter_in=8.5, bc="pinned-pinned",
            rpm_min=60, rpm_max=180, rpm_step=30, n_modes=2,
        )
        rpms = result["rpm_values"]
        assert rpms[0] == 60
        assert rpms[-1] == 180

    def test_campbell_excitation_lines(self, uniform_bha):
        """Should have 1x, 2x, 3x excitation lines."""
        from orchestrator.vibrations_engine.fea import generate_campbell_diagram
        result = generate_campbell_diagram(
            bha_components=uniform_bha,
            wob_klb=20.0, mud_weight_ppg=10.0,
            hole_diameter_in=8.5, bc="pinned-pinned",
            rpm_min=60, rpm_max=180, rpm_step=30, n_modes=2,
        )
        lines = result["excitation_lines"]
        assert "1x" in lines
        assert "2x" in lines
        assert "3x" in lines
        # 1x at 120 RPM = 2 Hz
        assert abs(lines["1x"][2] - 120.0 / 60.0) < 0.01
