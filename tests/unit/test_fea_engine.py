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
