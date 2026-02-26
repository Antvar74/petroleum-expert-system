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
