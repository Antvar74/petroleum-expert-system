# FEA Vibrations Module Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a Finite Element Analysis (FEA) solver for BHA lateral vibrations with Mode Shape Plot and Campbell Diagram to bring PetroExpert to Tier-1 level.

**Architecture:** New `fea.py` module in `orchestrator/vibrations_engine/` implements Euler-Bernoulli beam FEM with [K], [Kg], [M] matrices, solved via `scipy.linalg.eigh`. Two new API routes (`/vibrations/fea`, `/vibrations/campbell`). Frontend adds BHA editor, Mode Shape Plot, and Campbell Diagram as Recharts charts.

**Tech Stack:** Python (numpy, scipy), FastAPI, Pydantic, React/TypeScript, Recharts

**Design Doc:** `Docs/plans/2026-02-25-fea-vibrations-design.md`

---

## Task 1: FEA Element Matrices — Test + Implementation

**Files:**
- Create: `tests/unit/test_fea_engine.py`
- Create: `orchestrator/vibrations_engine/fea.py`

**Step 1: Write the failing test for element matrices**

Create `tests/unit/test_fea_engine.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system && python3 -m pytest tests/unit/test_fea_engine.py::TestBeamElementMatrices -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'orchestrator.vibrations_engine.fea'`

**Step 3: Write element matrices implementation**

Create `orchestrator/vibrations_engine/fea.py`:

```python
"""Finite Element Analysis (FEA) solver for BHA lateral vibrations.

Euler-Bernoulli beam formulation with 4 DOF per element (2 nodes x [y, theta]).
Supports:
  - Assembled stiffness [K], geometric stiffness [Kg], consistent mass [M]
  - Eigenvalue solve for natural frequencies and mode shapes
  - Forced response with Rayleigh damping
  - Campbell diagram generation

References:
  - Cook et al. (2002): Concepts and Applications of Finite Element Analysis
  - Jansen (1991): Nonlinear Dynamics of Oilwell Drillstrings
"""
import math
from typing import Dict, Any, List, Optional, Tuple

import numpy as np
from numpy.typing import NDArray

# Steel constants (consistent with critical_speeds.py)
STEEL_E = 30e6          # Young's modulus (psi)
STEEL_DENSITY = 490.0   # lb/ft^3
GRAVITY = 32.174        # ft/s^2


def beam_element_matrices(
    length_in: float,
    EI: float,
    rhoA: float,
    P: float = 0.0,
) -> Tuple[NDArray, NDArray, NDArray]:
    """Build 4x4 Euler-Bernoulli beam element matrices.

    DOFs per element: [y1, theta1, y2, theta2]
      y = lateral deflection (in)
      theta = rotation (rad)

    Args:
        length_in: Element length (inches).
        EI: Bending stiffness E*I (lb*in^2).
        rhoA: Mass per unit length (slug/in).
        P: Axial compressive load (lbs). Positive = compression.

    Returns:
        (Ke, Kge, Me) — stiffness, geometric stiffness, consistent mass.
    """
    L = length_in
    L2 = L * L
    L3 = L2 * L

    # -- Stiffness matrix [Ke] (Euler-Bernoulli) --
    c = EI / L3
    Ke = c * np.array([
        [ 12,     6*L,   -12,     6*L   ],
        [  6*L,   4*L2,   -6*L,   2*L2  ],
        [-12,    -6*L,    12,    -6*L   ],
        [  6*L,   2*L2,   -6*L,   4*L2  ],
    ], dtype=np.float64)

    # -- Geometric stiffness [Kge] (axial pre-stress) --
    if abs(P) < 1e-12:
        Kge = np.zeros((4, 4), dtype=np.float64)
    else:
        g = P / (30.0 * L)
        Kge = g * np.array([
            [ 36,     3*L,   -36,     3*L   ],
            [  3*L,   4*L2,   -3*L,  -L2    ],
            [-36,    -3*L,    36,    -3*L   ],
            [  3*L,  -L2,    -3*L,   4*L2   ],
        ], dtype=np.float64)

    # -- Consistent mass matrix [Me] --
    m = rhoA * L / 420.0
    Me = m * np.array([
        [156,     22*L,    54,    -13*L  ],
        [ 22*L,    4*L2,   13*L,   -3*L2 ],
        [ 54,     13*L,   156,    -22*L  ],
        [-13*L,   -3*L2,  -22*L,    4*L2 ],
    ], dtype=np.float64)

    return Ke, Kge, Me
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system && python3 -m pytest tests/unit/test_fea_engine.py::TestBeamElementMatrices -v`
Expected: All 6 tests PASS

**Step 5: Commit**

```bash
git add tests/unit/test_fea_engine.py orchestrator/vibrations_engine/fea.py
git commit -m "feat(fea): add beam element matrices [K], [Kg], [M] with tests

Euler-Bernoulli 4-DOF element formulation for BHA lateral vibration FEA.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 2: Global Matrix Assembly

**Files:**
- Modify: `tests/unit/test_fea_engine.py`
- Modify: `orchestrator/vibrations_engine/fea.py`

**Step 1: Write the failing test for assembly**

Append to `tests/unit/test_fea_engine.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system && python3 -m pytest tests/unit/test_fea_engine.py::TestGlobalAssembly -v`
Expected: FAIL — `ImportError: cannot import name 'assemble_global_matrices'`

**Step 3: Write assembly implementation**

Append to `orchestrator/vibrations_engine/fea.py`:

```python
def assemble_global_matrices(
    bha_components: List[Dict[str, Any]],
    mud_weight_ppg: float = 10.0,
    wob_klb: float = 0.0,
    stabilizer_nodes: Optional[List[int]] = None,
    stabilizer_stiffness: float = 1e8,
) -> Tuple[NDArray, NDArray, NDArray, List[float]]:
    """Assemble global [K], [Kg], [M] from BHA component list.

    Each component becomes one beam element.  Nodes numbered 0..N where
    node 0 = bit end, node N = top of BHA.

    Args:
        bha_components: List of dicts with keys:
            od (float): outer diameter (in)
            id_inner (float): inner diameter (in)
            length_ft (float): segment length (ft)
            weight_ppf (float): weight per foot (lb/ft)
            type (str): component type (collar, dp, hwdp, stabilizer, motor, MWD)
        mud_weight_ppg: Mud weight (ppg) for buoyancy.
        wob_klb: Weight on bit (klbs) — axial compressive load.
        stabilizer_nodes: Node indices where stabilizers constrain y≈0.
        stabilizer_stiffness: Spring constant for stabilizer (lb/in).

    Returns:
        (K_global, Kg_global, M_global, node_positions_ft)
    """
    n_elements = len(bha_components)
    n_nodes = n_elements + 1
    n_dof = n_nodes * 2  # 2 DOF per node (y, theta)

    K_global = np.zeros((n_dof, n_dof), dtype=np.float64)
    Kg_global = np.zeros((n_dof, n_dof), dtype=np.float64)
    M_global = np.zeros((n_dof, n_dof), dtype=np.float64)

    # Buoyancy factor
    bf = max(0.01, 1.0 - mud_weight_ppg / 65.5)

    # WOB in lbs (axial compression)
    P_lbs = wob_klb * 1000.0

    # Track node positions for mode shape plotting
    node_positions_ft: List[float] = [0.0]
    cumulative_ft = 0.0

    for i, comp in enumerate(bha_components):
        od = comp.get("od", 6.75)
        id_in = comp.get("id_inner", 2.813)
        length_ft = comp.get("length_ft", 30.0)
        weight_ppf = comp.get("weight_ppf", 83.0)

        length_in = length_ft * 12.0
        cumulative_ft += length_ft
        node_positions_ft.append(cumulative_ft)

        # Section properties
        I_moment = math.pi * (od**4 - id_in**4) / 64.0  # in^4
        EI = STEEL_E * I_moment  # lb*in^2

        # Mass per unit length (slug/in)
        # weight_ppf is lb/ft → mass = weight / g → slug/ft → /12 → slug/in
        mass_per_ft = weight_ppf * bf / GRAVITY  # slug/ft
        rhoA = mass_per_ft / 12.0  # slug/in

        # Element matrices
        Ke, Kge, Me = beam_element_matrices(length_in, EI, rhoA, P_lbs)

        # Assemble into global (standard FEM overlap at shared node)
        dof_start = i * 2  # each element starts 2 DOF after previous
        idx = slice(dof_start, dof_start + 4)

        K_global[idx, idx] += Ke
        Kg_global[idx, idx] += Kge
        M_global[idx, idx] += Me

    # Apply stabilizer springs (add to K diagonal at y-DOF)
    if stabilizer_nodes:
        for node_idx in stabilizer_nodes:
            dof_y = node_idx * 2  # y-DOF for this node
            if 0 <= dof_y < n_dof:
                K_global[dof_y, dof_y] += stabilizer_stiffness

    return K_global, Kg_global, M_global, node_positions_ft
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system && python3 -m pytest tests/unit/test_fea_engine.py::TestGlobalAssembly -v`
Expected: All 4 tests PASS

**Step 5: Commit**

```bash
git add tests/unit/test_fea_engine.py orchestrator/vibrations_engine/fea.py
git commit -m "feat(fea): add global matrix assembly with stabilizer support

Standard FEM assembly overlapping shared DOFs. Stabilizers as spring constraints.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 3: Eigenvalue Solver — Natural Frequencies + Mode Shapes

**Files:**
- Modify: `tests/unit/test_fea_engine.py`
- Modify: `orchestrator/vibrations_engine/fea.py`

**Step 1: Write the failing test for eigenvalue solver**

Append to `tests/unit/test_fea_engine.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system && python3 -m pytest tests/unit/test_fea_engine.py::TestEigenvalueSolver -v`
Expected: FAIL — `ImportError: cannot import name 'solve_eigenvalue'`

**Step 3: Write eigenvalue solver implementation**

Append to `orchestrator/vibrations_engine/fea.py`:

```python
def solve_eigenvalue(
    K: NDArray,
    Kg: NDArray,
    M: NDArray,
    bc: str = "pinned-pinned",
    n_modes: int = 5,
) -> Dict[str, Any]:
    """Solve generalized eigenvalue problem for natural frequencies and mode shapes.

    Solves: (K - P*Kg) * phi = omega^2 * M * phi
    Since Kg is already scaled by P during assembly, we solve:
        (K - Kg) * phi = omega^2 * M * phi

    Boundary conditions are applied by eliminating constrained DOFs.

    Args:
        K: Global stiffness matrix.
        Kg: Global geometric stiffness (already P-scaled).
        M: Global mass matrix.
        bc: Boundary conditions — 'pinned-pinned', 'fixed-pinned', 'fixed-free'.
        n_modes: Number of modes to return.

    Returns:
        Dict with frequencies_hz, critical_rpms, mode_shapes (deflection-only at nodes).
    """
    from scipy.linalg import eigh

    n_dof = K.shape[0]
    n_nodes = n_dof // 2

    # Identify constrained DOFs based on boundary conditions
    # Node 0 = bit end, Node N-1 = top end
    constrained_dofs: List[int] = []
    if bc == "pinned-pinned":
        constrained_dofs = [0, (n_nodes - 1) * 2]  # y=0 at both ends
    elif bc == "fixed-pinned":
        constrained_dofs = [0, 1, (n_nodes - 1) * 2]  # y=0, theta=0 at bit; y=0 at top
    elif bc == "fixed-free":
        constrained_dofs = [0, 1]  # y=0, theta=0 at bit; top is free
    else:
        constrained_dofs = [0, (n_nodes - 1) * 2]  # default pinned-pinned

    # Free DOFs (not constrained)
    all_dofs = list(range(n_dof))
    free_dofs = [d for d in all_dofs if d not in constrained_dofs]
    n_free = len(free_dofs)

    if n_free < 1:
        return {"frequencies_hz": [], "critical_rpms": [], "mode_shapes": [], "error": "No free DOFs"}

    # Extract sub-matrices for free DOFs
    ix = np.ix_(free_dofs, free_dofs)
    K_eff = K[ix] - Kg[ix]  # Effective stiffness including geometric effects
    M_free = M[ix]

    # Solve generalized eigenvalue problem: K_eff * phi = lambda * M_free * phi
    # eigh returns eigenvalues in ascending order
    n_solve = min(n_modes, n_free)
    eigenvalues, eigenvectors = eigh(K_eff, M_free, subset_by_index=[0, n_solve - 1])

    # Convert eigenvalues to frequencies
    frequencies_hz: List[float] = []
    critical_rpms: List[float] = []
    mode_shapes_raw: List[NDArray] = []

    for i in range(n_solve):
        lam = eigenvalues[i]
        if lam > 0:
            omega = math.sqrt(lam)
            freq_hz = omega / (2.0 * math.pi)
            frequencies_hz.append(round(freq_hz, 4))
            critical_rpms.append(round(freq_hz * 60.0, 1))
        else:
            frequencies_hz.append(0.0)
            critical_rpms.append(0.0)

        # Reconstruct full mode shape from free DOFs
        phi_full = np.zeros(n_dof, dtype=np.float64)
        phi_full[free_dofs] = eigenvectors[:, i]
        mode_shapes_raw.append(phi_full)

    # Extract deflection-only (y at each node) and normalize
    mode_shapes: List[List[float]] = []
    for phi in mode_shapes_raw:
        deflections = [phi[node * 2] for node in range(n_nodes)]
        max_abs = max(abs(d) for d in deflections) if deflections else 1.0
        if max_abs > 1e-15:
            deflections = [d / max_abs for d in deflections]
        mode_shapes.append(deflections)

    return {
        "frequencies_hz": frequencies_hz,
        "critical_rpms": critical_rpms,
        "mode_shapes": mode_shapes,
        "n_nodes": n_nodes,
        "n_free_dofs": n_free,
        "boundary_conditions": bc,
    }
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system && python3 -m pytest tests/unit/test_fea_engine.py::TestEigenvalueSolver -v`
Expected: All 7 tests PASS

**Step 5: Commit**

```bash
git add tests/unit/test_fea_engine.py orchestrator/vibrations_engine/fea.py
git commit -m "feat(fea): add eigenvalue solver for natural frequencies and mode shapes

Generalized symmetric eigenproblem via scipy.linalg.eigh with boundary condition
elimination. Validated against analytical pinned-pinned uniform beam (<5% error).

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 4: Forced Response + Campbell Diagram Engine

**Files:**
- Modify: `tests/unit/test_fea_engine.py`
- Modify: `orchestrator/vibrations_engine/fea.py`

**Step 1: Write the failing tests**

Append to `tests/unit/test_fea_engine.py`:

```python
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
        K, Kg, M, _ = assemble_global_matrices(uniform_bha, mud_weight_ppg=10.0, wob_klb=20.0)
        eigen = solve_eigenvalue(K, Kg, M, bc="pinned-pinned", n_modes=3)
        result = solve_forced_response(
            K=K, Kg=Kg, M=M, bc="pinned-pinned",
            excitation_freq_hz=eigen["frequencies_hz"][0] * 0.5,  # off-resonance
            excitation_node=0,
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
        K, Kg, M, _ = assemble_global_matrices(uniform_bha, mud_weight_ppg=10.0, wob_klb=20.0)
        eigen = solve_eigenvalue(K, Kg, M, bc="pinned-pinned", n_modes=3)
        f1 = eigen["frequencies_hz"][0]

        off_res = solve_forced_response(
            K=K, Kg=Kg, M=M, bc="pinned-pinned",
            excitation_freq_hz=f1 * 0.3, excitation_node=0, force_lbs=100.0,
            mud_weight_ppg=10.0,
        )
        near_res = solve_forced_response(
            K=K, Kg=Kg, M=M, bc="pinned-pinned",
            excitation_freq_hz=f1 * 0.95, excitation_node=0, force_lbs=100.0,
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
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system && python3 -m pytest tests/unit/test_fea_engine.py::TestForcedResponse tests/unit/test_fea_engine.py::TestCampbellDiagram -v`
Expected: FAIL — `ImportError: cannot import name 'solve_forced_response'`

**Step 3: Write forced response + Campbell implementation**

Append to `orchestrator/vibrations_engine/fea.py`:

```python
def solve_forced_response(
    K: NDArray,
    Kg: NDArray,
    M: NDArray,
    bc: str = "pinned-pinned",
    excitation_freq_hz: float = 2.0,
    excitation_node: int = 0,
    force_lbs: float = 100.0,
    mud_weight_ppg: float = 10.0,
    alpha: Optional[float] = None,
    beta: float = 0.01,
) -> Dict[str, Any]:
    """Solve forced harmonic response at a given frequency.

    Equation: (K_eff + i*omega*C - omega^2*M) * U = F
    With Rayleigh damping: C = alpha*M + beta*K

    Args:
        K, Kg, M: Global matrices.
        bc: Boundary conditions.
        excitation_freq_hz: Forcing frequency (Hz).
        excitation_node: Node where force is applied (0 = bit).
        force_lbs: Force magnitude (lbs).
        mud_weight_ppg: For damping estimation.
        alpha: Mass-proportional damping. If None, estimated from mud weight.
        beta: Stiffness-proportional damping (default 0.01).

    Returns:
        Dict with amplitudes (per node), max_amplitude_in, phase angles.
    """
    n_dof = K.shape[0]
    n_nodes = n_dof // 2

    # Damping: alpha estimated from mud interaction
    if alpha is None:
        alpha = 0.5 + mud_weight_ppg * 0.05  # heuristic: heavier mud = more damping

    # Rayleigh damping matrix
    C = alpha * M + beta * K

    # Boundary condition DOF elimination
    constrained_dofs: List[int] = []
    if bc == "pinned-pinned":
        constrained_dofs = [0, (n_nodes - 1) * 2]
    elif bc == "fixed-pinned":
        constrained_dofs = [0, 1, (n_nodes - 1) * 2]
    elif bc == "fixed-free":
        constrained_dofs = [0, 1]
    else:
        constrained_dofs = [0, (n_nodes - 1) * 2]

    free_dofs = [d for d in range(n_dof) if d not in constrained_dofs]
    ix = np.ix_(free_dofs, free_dofs)

    K_eff_free = (K[ix] - Kg[ix])
    M_free = M[ix]
    C_free = C[ix]

    omega = 2.0 * math.pi * excitation_freq_hz

    # Dynamic stiffness: Z = K_eff + i*omega*C - omega^2*M
    Z = K_eff_free + 1j * omega * C_free - omega**2 * M_free

    # Force vector (at excitation node y-DOF)
    F_full = np.zeros(n_dof, dtype=np.complex128)
    force_dof = excitation_node * 2  # y-DOF of excitation node
    F_full[force_dof] = force_lbs
    F_free = F_full[free_dofs]

    # Solve
    try:
        U_free = np.linalg.solve(Z, F_free)
    except np.linalg.LinAlgError:
        return {"amplitudes": [0.0] * n_nodes, "max_amplitude_in": 0.0, "error": "Singular matrix"}

    # Reconstruct full displacement
    U_full = np.zeros(n_dof, dtype=np.complex128)
    U_full[free_dofs] = U_free

    # Extract deflection amplitudes at each node
    amplitudes = [float(abs(U_full[node * 2])) for node in range(n_nodes)]
    max_amp = max(amplitudes) if amplitudes else 0.0

    return {
        "amplitudes": amplitudes,
        "max_amplitude_in": round(max_amp, 6),
        "excitation_freq_hz": excitation_freq_hz,
    }


def generate_campbell_diagram(
    bha_components: List[Dict[str, Any]],
    wob_klb: float = 20.0,
    mud_weight_ppg: float = 10.0,
    hole_diameter_in: float = 8.5,
    bc: str = "pinned-pinned",
    rpm_min: float = 20.0,
    rpm_max: float = 300.0,
    rpm_step: float = 5.0,
    n_modes: int = 5,
    n_blades: Optional[int] = None,
) -> Dict[str, Any]:
    """Generate Campbell diagram data: natural frequencies vs RPM.

    At each RPM point the eigenvalue problem is solved (WOB effect constant).
    Excitation lines: 1x, 2x, 3x RPM. Crossings flag resonance hazards.

    Returns:
        Dict with rpm_values, natural_freq_curves, excitation_lines, crossings.
    """
    rpm_values: List[float] = []
    rpm = rpm_min
    while rpm <= rpm_max + 0.001:
        rpm_values.append(round(rpm, 1))
        rpm += rpm_step

    # Assemble once (WOB is constant in standard Campbell)
    K, Kg, M, node_positions = assemble_global_matrices(
        bha_components, mud_weight_ppg, wob_klb,
    )

    # Solve eigenvalue at each RPM (frequencies don't change with RPM in linear analysis,
    # but we keep the loop for future nonlinear extension)
    eigen_result = solve_eigenvalue(K, Kg, M, bc=bc, n_modes=n_modes)
    base_freqs = eigen_result["frequencies_hz"]

    # Natural frequency curves (currently constant vs RPM for linear analysis)
    natural_freq_curves: Dict[str, List[float]] = {}
    for mode_idx in range(len(base_freqs)):
        key = f"mode_{mode_idx + 1}"
        natural_freq_curves[key] = [base_freqs[mode_idx]] * len(rpm_values)

    # Excitation lines: f = n * RPM / 60
    excitation_lines: Dict[str, List[float]] = {
        "1x": [r / 60.0 for r in rpm_values],
        "2x": [2.0 * r / 60.0 for r in rpm_values],
        "3x": [3.0 * r / 60.0 for r in rpm_values],
    }

    # Blade-pass excitation line
    if n_blades and n_blades > 0:
        excitation_lines[f"{n_blades}x_blade"] = [n_blades * r / 60.0 for r in rpm_values]

    # Detect crossings (resonances)
    crossings: List[Dict[str, Any]] = []
    threshold_hz = 0.3  # Hz tolerance for crossing detection

    for exc_name, exc_freqs in excitation_lines.items():
        for mode_name, mode_freqs in natural_freq_curves.items():
            for i, rpm_val in enumerate(rpm_values):
                if abs(exc_freqs[i] - mode_freqs[i]) < threshold_hz:
                    crossings.append({
                        "rpm": rpm_val,
                        "frequency_hz": round(mode_freqs[i], 2),
                        "excitation": exc_name,
                        "mode": mode_name,
                        "risk": "critical" if exc_name == "1x" else "high",
                    })

    return {
        "rpm_values": rpm_values,
        "natural_freq_curves": natural_freq_curves,
        "excitation_lines": excitation_lines,
        "crossings": crossings,
        "node_positions_ft": node_positions,
        "mode_shapes": eigen_result["mode_shapes"],
        "frequencies_hz": base_freqs,
    }
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system && python3 -m pytest tests/unit/test_fea_engine.py::TestForcedResponse tests/unit/test_fea_engine.py::TestCampbellDiagram -v`
Expected: All 5 tests PASS

**Step 5: Commit**

```bash
git add tests/unit/test_fea_engine.py orchestrator/vibrations_engine/fea.py
git commit -m "feat(fea): add forced response solver and Campbell diagram generator

Rayleigh damping, harmonic excitation at bit node, resonance crossing detection.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 5: High-Level `run_fea_analysis()` Orchestrator

**Files:**
- Modify: `tests/unit/test_fea_engine.py`
- Modify: `orchestrator/vibrations_engine/fea.py`

**Step 1: Write the failing test**

Append to `tests/unit/test_fea_engine.py`:

```python
# ---------------------------------------------------------------------------
# Task 5: run_fea_analysis orchestrator
# ---------------------------------------------------------------------------
class TestRunFEAAnalysis:
    """Verify the high-level FEA analysis function."""

    @pytest.fixture
    def standard_bha(self):
        return [
            {"type": "collar", "od": 8.0, "id_inner": 2.813, "length_ft": 30.0, "weight_ppf": 147.0},
            {"type": "collar", "od": 6.75, "id_inner": 2.813, "length_ft": 60.0, "weight_ppf": 83.0},
            {"type": "collar", "od": 6.75, "id_inner": 2.813, "length_ft": 60.0, "weight_ppf": 83.0},
            {"type": "hwdp", "od": 5.0, "id_inner": 3.0, "length_ft": 90.0, "weight_ppf": 49.3},
            {"type": "dp", "od": 5.0, "id_inner": 4.276, "length_ft": 60.0, "weight_ppf": 19.5},
        ]

    def test_returns_all_expected_keys(self, standard_bha):
        """run_fea_analysis must return frequencies, mode_shapes, campbell, forced_response."""
        from orchestrator.vibrations_engine.fea import run_fea_analysis
        result = run_fea_analysis(
            bha_components=standard_bha,
            wob_klb=25.0, rpm=120.0, mud_weight_ppg=10.0,
            hole_diameter_in=8.5, bc="pinned-pinned", n_modes=3,
        )
        assert "eigenvalue" in result
        assert "campbell" in result
        assert "forced_response" in result
        assert "node_positions_ft" in result
        assert "summary" in result

    def test_summary_has_critical_rpms(self, standard_bha):
        """Summary must include critical RPMs and stability assessment."""
        from orchestrator.vibrations_engine.fea import run_fea_analysis
        result = run_fea_analysis(
            bha_components=standard_bha,
            wob_klb=25.0, rpm=120.0, mud_weight_ppg=10.0,
            hole_diameter_in=8.5, bc="pinned-pinned", n_modes=3,
        )
        summary = result["summary"]
        assert "mode_1_freq_hz" in summary
        assert "mode_1_critical_rpm" in summary
        assert "resonance_warnings" in summary
        assert "fea_method" in summary
        assert summary["fea_method"] == "Euler-Bernoulli FEM"

    def test_mixed_bha_works(self, standard_bha):
        """Mixed component BHA (collars + HWDP + DP) should compute without error."""
        from orchestrator.vibrations_engine.fea import run_fea_analysis
        result = run_fea_analysis(
            bha_components=standard_bha,
            wob_klb=20.0, rpm=100.0, mud_weight_ppg=12.0,
            hole_diameter_in=8.5, bc="pinned-pinned", n_modes=5,
        )
        assert len(result["eigenvalue"]["frequencies_hz"]) == 5
        assert len(result["eigenvalue"]["mode_shapes"]) == 5
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system && python3 -m pytest tests/unit/test_fea_engine.py::TestRunFEAAnalysis -v`
Expected: FAIL — `ImportError: cannot import name 'run_fea_analysis'`

**Step 3: Write orchestrator implementation**

Append to `orchestrator/vibrations_engine/fea.py`:

```python
def run_fea_analysis(
    bha_components: List[Dict[str, Any]],
    wob_klb: float = 20.0,
    rpm: float = 120.0,
    mud_weight_ppg: float = 10.0,
    hole_diameter_in: float = 8.5,
    bc: str = "pinned-pinned",
    n_modes: int = 5,
    include_forced_response: bool = True,
    include_campbell: bool = True,
    n_blades: Optional[int] = None,
    rpm_min: float = 20.0,
    rpm_max: float = 300.0,
    rpm_step: float = 5.0,
) -> Dict[str, Any]:
    """Run complete FEA analysis on BHA: eigenvalue + forced response + Campbell.

    This is the main entry point for the FEA module.

    Args:
        bha_components: BHA component list (see assemble_global_matrices).
        wob_klb: Weight on bit (klbs).
        rpm: Operating RPM.
        mud_weight_ppg: Mud weight (ppg).
        hole_diameter_in: Hole diameter (in).
        bc: Boundary conditions.
        n_modes: Number of modes.
        include_forced_response: Calculate forced response amplitudes.
        include_campbell: Generate Campbell diagram.
        n_blades: PDC blade count for blade-pass excitation.
        rpm_min, rpm_max, rpm_step: Campbell diagram RPM sweep range.

    Returns:
        Dict with eigenvalue, forced_response, campbell, node_positions_ft, summary.
    """
    # 1. Assemble
    K, Kg, M, node_positions = assemble_global_matrices(
        bha_components, mud_weight_ppg, wob_klb,
    )

    # 2. Eigenvalue analysis
    eigen = solve_eigenvalue(K, Kg, M, bc=bc, n_modes=n_modes)

    # 3. Forced response (at 1x RPM excitation)
    forced = None
    if include_forced_response and eigen["frequencies_hz"]:
        excitation_freq = rpm / 60.0  # 1x RPM in Hz
        forced = solve_forced_response(
            K=K, Kg=Kg, M=M, bc=bc,
            excitation_freq_hz=excitation_freq,
            excitation_node=0,  # bit node
            force_lbs=wob_klb * 50.0,  # rough imbalance force estimate
            mud_weight_ppg=mud_weight_ppg,
        )

    # 4. Campbell diagram
    campbell = None
    if include_campbell:
        campbell = generate_campbell_diagram(
            bha_components=bha_components,
            wob_klb=wob_klb,
            mud_weight_ppg=mud_weight_ppg,
            hole_diameter_in=hole_diameter_in,
            bc=bc,
            rpm_min=rpm_min, rpm_max=rpm_max, rpm_step=rpm_step,
            n_modes=n_modes,
            n_blades=n_blades,
        )

    # 5. Resonance warnings
    warnings: List[str] = []
    operating_freq = rpm / 60.0
    for i, freq in enumerate(eigen["frequencies_hz"]):
        ratio = operating_freq / freq if freq > 0 else 0
        if 0.85 < ratio < 1.15:
            warnings.append(
                f"1x RPM ({rpm}) near Mode {i+1} ({freq:.2f} Hz / {freq*60:.0f} RPM) — resonance risk"
            )
        if 0.85 < 2 * operating_freq / freq < 1.15:
            warnings.append(
                f"2x RPM near Mode {i+1} ({freq:.2f} Hz) — secondary resonance"
            )

    # 6. Summary
    summary: Dict[str, Any] = {
        "fea_method": "Euler-Bernoulli FEM",
        "n_elements": len(bha_components),
        "n_nodes": len(node_positions),
        "n_dof": len(node_positions) * 2,
        "boundary_conditions": bc,
        "wob_klb": wob_klb,
        "operating_rpm": rpm,
        "resonance_warnings": warnings,
    }
    # Add per-mode info
    for i, (freq, crit_rpm) in enumerate(
        zip(eigen["frequencies_hz"], eigen["critical_rpms"])
    ):
        summary[f"mode_{i+1}_freq_hz"] = freq
        summary[f"mode_{i+1}_critical_rpm"] = crit_rpm

    if forced:
        summary["max_vibration_amplitude_in"] = forced["max_amplitude_in"]

    return {
        "eigenvalue": eigen,
        "forced_response": forced,
        "campbell": campbell,
        "node_positions_ft": node_positions,
        "summary": summary,
    }
```

**Step 4: Run ALL FEA tests to verify everything passes**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system && python3 -m pytest tests/unit/test_fea_engine.py -v`
Expected: All 22 tests PASS

**Step 5: Commit**

```bash
git add tests/unit/test_fea_engine.py orchestrator/vibrations_engine/fea.py
git commit -m "feat(fea): add run_fea_analysis orchestrator with summary and warnings

Complete FEA pipeline: assemble → eigenvalue → forced response → Campbell → warnings.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 6: Wire FEA into Facade + Schemas + Routes

**Files:**
- Modify: `orchestrator/vibrations_engine/__init__.py:22-63`
- Modify: `schemas/vibrations.py:57-70`
- Modify: `routes/modules/vibrations.py:16-18,128-143`

**Step 1: Run existing vibrations tests to ensure green baseline**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system && python3 -m pytest tests/unit/test_vibrations_engine.py -v`
Expected: All existing tests PASS

**Step 2: Update facade (`__init__.py`)**

Add to `orchestrator/vibrations_engine/__init__.py` after line 24 (`from .fatigue ...`):

```python
from .fea import run_fea_analysis, generate_campbell_diagram
```

Add to the `VibrationsEngine` class after line 60 (`calculate_fatigue_damage`):

```python
    # fea
    run_fea_analysis = staticmethod(run_fea_analysis)
    generate_campbell_diagram = staticmethod(generate_campbell_diagram)
```

**Step 3: Add Pydantic schemas**

Append to `schemas/vibrations.py` after the `FatigueRequest` class (after line 69):

```python


class FEARequest(BaseModel):
    """Body for ``POST /vibrations/fea``."""

    bha_components: List[Dict[str, Any]] = Field(..., description="BHA component list")
    wob_klb: float = Field(default=20, description="Weight on bit (klbs)")
    rpm: float = Field(default=120, description="Operating RPM")
    mud_weight_ppg: float = Field(default=10, description="Mud weight (ppg)")
    hole_diameter_in: float = Field(default=8.5, description="Hole diameter (in)")
    boundary_conditions: str = Field(default="pinned-pinned", description="BC: pinned-pinned, fixed-pinned, fixed-free")
    n_modes: int = Field(default=5, description="Number of modes to compute")
    include_forced_response: bool = Field(default=True, description="Include forced response analysis")
    include_campbell: bool = Field(default=True, description="Include Campbell diagram")
    n_blades: Optional[int] = Field(default=None, description="PDC blade count for blade-pass excitation")


class CampbellRequest(BaseModel):
    """Body for ``POST /vibrations/campbell``."""

    bha_components: List[Dict[str, Any]] = Field(..., description="BHA component list")
    wob_klb: float = Field(default=20, description="Weight on bit (klbs)")
    mud_weight_ppg: float = Field(default=10, description="Mud weight (ppg)")
    hole_diameter_in: float = Field(default=8.5, description="Hole diameter (in)")
    boundary_conditions: str = Field(default="pinned-pinned", description="Boundary conditions")
    rpm_min: float = Field(default=20, description="Campbell RPM sweep start")
    rpm_max: float = Field(default=300, description="Campbell RPM sweep end")
    rpm_step: float = Field(default=5, description="Campbell RPM step")
    n_modes: int = Field(default=5, description="Number of modes")
    n_blades: Optional[int] = Field(default=None, description="PDC blade count")
```

**Step 4: Add API routes**

In `routes/modules/vibrations.py`:

Update imports (line 16-18) to add the new schemas:
```python
from schemas.vibrations import (
    VibrationsCalcRequest, Vibrations3DMapRequest, BHAModalRequest, FatigueRequest,
    FEARequest, CampbellRequest,
)
```

Append two new endpoints after line 142:

```python


@router.post("/vibrations/fea")
def calculate_fea(data: FEARequest):
    """Finite Element Analysis of BHA lateral vibrations."""
    return VibrationsEngine.run_fea_analysis(
        bha_components=data.bha_components,
        wob_klb=data.wob_klb,
        rpm=data.rpm,
        mud_weight_ppg=data.mud_weight_ppg,
        hole_diameter_in=data.hole_diameter_in,
        bc=data.boundary_conditions,
        n_modes=data.n_modes,
        include_forced_response=data.include_forced_response,
        include_campbell=data.include_campbell,
        n_blades=data.n_blades,
    )


@router.post("/vibrations/campbell")
def calculate_campbell(data: CampbellRequest):
    """Generate Campbell diagram data for BHA."""
    return VibrationsEngine.generate_campbell_diagram(
        bha_components=data.bha_components,
        wob_klb=data.wob_klb,
        mud_weight_ppg=data.mud_weight_ppg,
        hole_diameter_in=data.hole_diameter_in,
        bc=data.boundary_conditions,
        rpm_min=data.rpm_min,
        rpm_max=data.rpm_max,
        rpm_step=data.rpm_step,
        n_modes=data.n_modes,
        n_blades=data.n_blades,
    )
```

**Step 5: Run all tests to verify nothing broke**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system && python3 -m pytest tests/unit/test_vibrations_engine.py tests/unit/test_fea_engine.py -v`
Expected: All tests PASS (both existing and new)

**Step 6: Commit**

```bash
git add orchestrator/vibrations_engine/__init__.py schemas/vibrations.py routes/modules/vibrations.py
git commit -m "feat(fea): wire FEA into facade, Pydantic schemas, and API routes

POST /vibrations/fea and POST /vibrations/campbell endpoints added.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 7: Frontend — BHA Editor Component

**Files:**
- Create: `frontend/src/components/charts/vb/BHAEditor.tsx`

**Step 1: Create the BHA editor**

Create `frontend/src/components/charts/vb/BHAEditor.tsx`:

```tsx
/**
 * BHAEditor.tsx — Interactive multi-component BHA editor for FEA analysis.
 * Allows adding, removing, reordering BHA components (collar, dp, hwdp, etc.)
 */
import React from 'react';
import { Plus, Trash2, ChevronUp, ChevronDown } from 'lucide-react';

export interface BHAComponent {
  type: string;
  od: number;
  id_inner: number;
  length_ft: number;
  weight_ppf: number;
}

interface BHAEditorProps {
  components: BHAComponent[];
  onChange: (components: BHAComponent[]) => void;
}

const COMPONENT_TYPES = ['collar', 'dp', 'hwdp', 'stabilizer', 'motor', 'MWD'];

const DEFAULT_BY_TYPE: Record<string, Partial<BHAComponent>> = {
  collar:     { od: 6.75, id_inner: 2.813, weight_ppf: 83.0, length_ft: 30 },
  dp:         { od: 5.0,  id_inner: 4.276, weight_ppf: 19.5, length_ft: 30 },
  hwdp:       { od: 5.0,  id_inner: 3.0,   weight_ppf: 49.3, length_ft: 30 },
  stabilizer: { od: 8.25, id_inner: 2.813, weight_ppf: 95.0, length_ft: 5 },
  motor:      { od: 6.75, id_inner: 3.5,   weight_ppf: 90.0, length_ft: 25 },
  MWD:        { od: 6.75, id_inner: 3.25,  weight_ppf: 85.0, length_ft: 10 },
};

const BHA_PRESETS: Record<string, BHAComponent[]> = {
  'Standard Rotary': [
    { type: 'collar', od: 8.0, id_inner: 2.813, length_ft: 30, weight_ppf: 147 },
    { type: 'collar', od: 6.75, id_inner: 2.813, length_ft: 60, weight_ppf: 83 },
    { type: 'collar', od: 6.75, id_inner: 2.813, length_ft: 60, weight_ppf: 83 },
    { type: 'hwdp', od: 5.0, id_inner: 3.0, length_ft: 90, weight_ppf: 49.3 },
    { type: 'dp', od: 5.0, id_inner: 4.276, length_ft: 60, weight_ppf: 19.5 },
  ],
  'Motor BHA': [
    { type: 'stabilizer', od: 8.25, id_inner: 2.813, length_ft: 5, weight_ppf: 95 },
    { type: 'motor', od: 6.75, id_inner: 3.5, length_ft: 25, weight_ppf: 90 },
    { type: 'MWD', od: 6.75, id_inner: 3.25, length_ft: 10, weight_ppf: 85 },
    { type: 'collar', od: 6.75, id_inner: 2.813, length_ft: 90, weight_ppf: 83 },
    { type: 'hwdp', od: 5.0, id_inner: 3.0, length_ft: 90, weight_ppf: 49.3 },
    { type: 'dp', od: 5.0, id_inner: 4.276, length_ft: 60, weight_ppf: 19.5 },
  ],
  'RSS BHA': [
    { type: 'stabilizer', od: 8.25, id_inner: 2.813, length_ft: 3, weight_ppf: 95 },
    { type: 'collar', od: 6.75, id_inner: 2.813, length_ft: 15, weight_ppf: 83 },
    { type: 'MWD', od: 6.75, id_inner: 3.25, length_ft: 10, weight_ppf: 85 },
    { type: 'collar', od: 6.75, id_inner: 2.813, length_ft: 120, weight_ppf: 83 },
    { type: 'hwdp', od: 5.0, id_inner: 3.0, length_ft: 90, weight_ppf: 49.3 },
    { type: 'dp', od: 5.0, id_inner: 4.276, length_ft: 60, weight_ppf: 19.5 },
  ],
};

const TYPE_COLORS: Record<string, string> = {
  collar: 'bg-rose-500/20 text-rose-300',
  dp: 'bg-blue-500/20 text-blue-300',
  hwdp: 'bg-amber-500/20 text-amber-300',
  stabilizer: 'bg-green-500/20 text-green-300',
  motor: 'bg-purple-500/20 text-purple-300',
  MWD: 'bg-cyan-500/20 text-cyan-300',
};

const BHAEditor: React.FC<BHAEditorProps> = ({ components, onChange }) => {

  const addComponent = () => {
    const defaults = DEFAULT_BY_TYPE['collar'];
    onChange([...components, { type: 'collar', ...defaults } as BHAComponent]);
  };

  const removeComponent = (index: number) => {
    onChange(components.filter((_, i) => i !== index));
  };

  const updateComponent = (index: number, field: keyof BHAComponent, value: string | number) => {
    const updated = [...components];
    if (field === 'type') {
      const newType = value as string;
      const defaults = DEFAULT_BY_TYPE[newType] || {};
      updated[index] = { ...updated[index], ...defaults, type: newType };
    } else {
      updated[index] = { ...updated[index], [field]: typeof value === 'string' ? parseFloat(value) || 0 : value };
    }
    onChange(updated);
  };

  const moveComponent = (index: number, direction: 'up' | 'down') => {
    const newIdx = direction === 'up' ? index - 1 : index + 1;
    if (newIdx < 0 || newIdx >= components.length) return;
    const updated = [...components];
    [updated[index], updated[newIdx]] = [updated[newIdx], updated[index]];
    onChange(updated);
  };

  const totalLength = components.reduce((sum, c) => sum + c.length_ft, 0);

  return (
    <div className="space-y-3">
      {/* Presets */}
      <div className="flex flex-wrap gap-2">
        {Object.keys(BHA_PRESETS).map(name => (
          <button key={name} type="button"
            onClick={() => onChange([...BHA_PRESETS[name]])}
            className="px-3 py-1 text-xs rounded-md border bg-white/5 border-white/10 text-gray-400 hover:border-rose-500/40 hover:text-rose-300 transition-colors"
          >
            {name}
          </button>
        ))}
      </div>

      {/* Component Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-gray-500 text-xs border-b border-white/10">
              <th className="text-left py-2 px-1 w-8">#</th>
              <th className="text-left py-2 px-1">Type</th>
              <th className="text-right py-2 px-1">OD (in)</th>
              <th className="text-right py-2 px-1">ID (in)</th>
              <th className="text-right py-2 px-1">Length (ft)</th>
              <th className="text-right py-2 px-1">Weight (lb/ft)</th>
              <th className="py-2 px-1 w-24"></th>
            </tr>
          </thead>
          <tbody>
            {components.map((comp, i) => (
              <tr key={i} className="border-b border-white/5 hover:bg-white/[0.02]">
                <td className="py-1 px-1 text-gray-600">{i + 1}</td>
                <td className="py-1 px-1">
                  <select value={comp.type}
                    onChange={e => updateComponent(i, 'type', e.target.value)}
                    className={`bg-transparent border border-white/10 rounded px-2 py-1 text-xs ${TYPE_COLORS[comp.type] || 'text-gray-300'}`}>
                    {COMPONENT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </td>
                {(['od', 'id_inner', 'length_ft', 'weight_ppf'] as const).map(field => (
                  <td key={field} className="py-1 px-1">
                    <input type="number"
                      value={comp[field]}
                      step={field === 'length_ft' ? '5' : '0.125'}
                      onChange={e => updateComponent(i, field, e.target.value)}
                      className="w-full text-right bg-white/5 border border-white/10 rounded px-2 py-1 text-xs focus:border-rose-500 focus:outline-none"
                    />
                  </td>
                ))}
                <td className="py-1 px-1">
                  <div className="flex gap-1 justify-end">
                    <button onClick={() => moveComponent(i, 'up')} disabled={i === 0}
                      className="p-1 text-gray-500 hover:text-gray-300 disabled:opacity-20"><ChevronUp size={14} /></button>
                    <button onClick={() => moveComponent(i, 'down')} disabled={i === components.length - 1}
                      className="p-1 text-gray-500 hover:text-gray-300 disabled:opacity-20"><ChevronDown size={14} /></button>
                    <button onClick={() => removeComponent(i)}
                      className="p-1 text-gray-500 hover:text-red-400"><Trash2 size={14} /></button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Footer */}
      <div className="flex justify-between items-center">
        <button onClick={addComponent} type="button"
          className="flex items-center gap-1 px-3 py-1.5 text-xs rounded-lg border border-dashed border-white/20 text-gray-400 hover:border-rose-500/40 hover:text-rose-300 transition-colors">
          <Plus size={14} /> Add Component
        </button>
        <span className="text-xs text-gray-500">
          {components.length} components &middot; Total: {totalLength.toFixed(0)} ft
        </span>
      </div>
    </div>
  );
};

export default BHAEditor;
```

**Step 2: Verify TypeScript compiles**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system/frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: No errors related to BHAEditor.tsx

**Step 3: Commit**

```bash
git add frontend/src/components/charts/vb/BHAEditor.tsx
git commit -m "feat(fea): add BHA editor component with presets and reordering

Interactive table for multi-component BHA definition (collar, dp, hwdp, stabilizer,
motor, MWD). Includes Standard Rotary, Motor BHA, and RSS BHA presets.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 8: Frontend — Mode Shape Plot Chart

**Files:**
- Create: `frontend/src/components/charts/vb/ModeShapePlot.tsx`

**Step 1: Create Mode Shape Plot component**

Create `frontend/src/components/charts/vb/ModeShapePlot.tsx`:

```tsx
/**
 * ModeShapePlot.tsx — Vertical mode shape visualization.
 * Shows BHA deflection profile for each vibration mode.
 * Y-axis = depth (reversed, bit at bottom), X-axis = normalized deflection.
 */
import React, { useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';
import ChartContainer, { DarkTooltip } from '../ChartContainer';
import { CHART_DEFAULTS } from '../ChartTheme';
import { Waves } from 'lucide-react';

interface ModeShapePlotProps {
  nodePositions: number[];
  modeShapes: number[][];
  frequenciesHz: number[];
  height?: number;
}

const MODE_COLORS = ['#3b82f6', '#22c55e', '#f97316', '#a855f7', '#06b6d4'];

const ModeShapePlot: React.FC<ModeShapePlotProps> = ({
  nodePositions,
  modeShapes,
  frequenciesHz,
  height = 450,
}) => {
  const [visibleModes, setVisibleModes] = useState<Set<number>>(new Set([0, 1, 2]));

  if (!nodePositions?.length || !modeShapes?.length) return null;

  // Build data: each row = { depth, mode_0, mode_1, mode_2, ... }
  const data = nodePositions.map((depth, i) => {
    const row: Record<string, number> = { depth };
    modeShapes.forEach((shape, modeIdx) => {
      if (shape[i] !== undefined) {
        row[`mode_${modeIdx}`] = shape[i];
      }
    });
    return row;
  });

  const toggleMode = (idx: number) => {
    setVisibleModes(prev => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  return (
    <ChartContainer title="Mode Shapes (FEA)" icon={Waves} height={height}>
      <LineChart data={data} layout="vertical" margin={{ top: 10, right: 30, bottom: 10, left: 60 }}>
        <CartesianGrid stroke={CHART_DEFAULTS.gridColor} />
        <YAxis
          dataKey="depth"
          type="number"
          reversed
          domain={['dataMin', 'dataMax']}
          tick={{ fill: CHART_DEFAULTS.labelColor, fontSize: 11 }}
          label={{ value: 'MD (ft)', angle: -90, position: 'insideLeft', fill: CHART_DEFAULTS.labelColor, fontSize: 12 }}
        />
        <XAxis
          type="number"
          domain={[-1.1, 1.1]}
          tick={{ fill: CHART_DEFAULTS.labelColor, fontSize: 11 }}
          label={{ value: 'Deflection (normalized)', position: 'insideBottom', fill: CHART_DEFAULTS.labelColor, fontSize: 12, offset: -5 }}
        />
        <Tooltip content={<DarkTooltip />} />
        <Legend
          onClick={(e: any) => {
            const idx = parseInt(e.dataKey?.replace('mode_', '') || '0');
            toggleMode(idx);
          }}
          wrapperStyle={{ cursor: 'pointer' }}
        />
        {modeShapes.map((_, modeIdx) => (
          visibleModes.has(modeIdx) && (
            <Line
              key={`mode_${modeIdx}`}
              dataKey={`mode_${modeIdx}`}
              name={`Mode ${modeIdx + 1} (${frequenciesHz[modeIdx]?.toFixed(2)} Hz)`}
              stroke={MODE_COLORS[modeIdx % MODE_COLORS.length]}
              strokeWidth={2}
              dot={false}
              type="monotone"
            />
          )
        ))}
      </LineChart>
    </ChartContainer>
  );
};

export default ModeShapePlot;
```

**Step 2: Verify TypeScript compiles**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system/frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: No errors

**Step 3: Commit**

```bash
git add frontend/src/components/charts/vb/ModeShapePlot.tsx
git commit -m "feat(fea): add Mode Shape Plot chart with vertical depth layout

Recharts vertical LineChart showing normalized deflection vs depth for up to 5 modes.
Toggle visibility per mode via legend click.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 9: Frontend — Campbell Diagram Chart

**Files:**
- Create: `frontend/src/components/charts/vb/CampbellDiagram.tsx`

**Step 1: Create Campbell Diagram component**

Create `frontend/src/components/charts/vb/CampbellDiagram.tsx`:

```tsx
/**
 * CampbellDiagram.tsx — Natural frequency vs RPM with excitation lines.
 * Crossings indicate resonance hazards.
 */
import React from 'react';
import {
  ComposedChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  Scatter, ReferenceArea,
} from 'recharts';
import ChartContainer, { DarkTooltip } from '../ChartContainer';
import { CHART_DEFAULTS } from '../ChartTheme';
import { Activity } from 'lucide-react';

interface CampbellDiagramProps {
  rpmValues: number[];
  naturalFreqCurves: Record<string, number[]>;
  excitationLines: Record<string, number[]>;
  crossings: Array<{
    rpm: number;
    frequency_hz: number;
    excitation: string;
    mode: string;
    risk: string;
  }>;
  operatingRpm?: number;
  height?: number;
}

const MODE_COLORS = ['#3b82f6', '#22c55e', '#a855f7', '#06b6d4', '#f59e0b'];
const EXC_COLORS: Record<string, string> = {
  '1x': '#ef4444',
  '2x': '#f97316',
  '3x': '#eab308',
};

const CampbellDiagram: React.FC<CampbellDiagramProps> = ({
  rpmValues,
  naturalFreqCurves,
  excitationLines,
  crossings,
  operatingRpm,
  height = 450,
}) => {
  if (!rpmValues?.length) return null;

  // Build merged data array: { rpm, mode_1, mode_2, ..., exc_1x, exc_2x, ... }
  const data = rpmValues.map((rpm, i) => {
    const row: Record<string, number> = { rpm };
    Object.entries(naturalFreqCurves).forEach(([key, vals]) => {
      row[key] = vals[i];
    });
    Object.entries(excitationLines).forEach(([key, vals]) => {
      row[`exc_${key}`] = vals[i];
    });
    return row;
  });

  // Crossing scatter data
  const crossingData = crossings.map(c => ({
    rpm: c.rpm,
    frequency_hz: c.frequency_hz,
    label: `${c.mode} x ${c.excitation}`,
    risk: c.risk,
  }));

  const modeKeys = Object.keys(naturalFreqCurves);
  const excKeys = Object.keys(excitationLines);

  return (
    <ChartContainer title="Campbell Diagram (FEA)" icon={Activity} height={height}>
      <ComposedChart data={data} margin={{ top: 10, right: 30, bottom: 10, left: 10 }}>
        <CartesianGrid stroke={CHART_DEFAULTS.gridColor} />
        <XAxis
          dataKey="rpm"
          type="number"
          tick={{ fill: CHART_DEFAULTS.labelColor, fontSize: 11 }}
          label={{ value: 'RPM', position: 'insideBottom', fill: CHART_DEFAULTS.labelColor, fontSize: 12, offset: -5 }}
        />
        <YAxis
          type="number"
          tick={{ fill: CHART_DEFAULTS.labelColor, fontSize: 11 }}
          label={{ value: 'Frequency (Hz)', angle: -90, position: 'insideLeft', fill: CHART_DEFAULTS.labelColor, fontSize: 12 }}
        />
        <Tooltip content={<DarkTooltip />} />
        <Legend />

        {/* Operating RPM band */}
        {operatingRpm && (
          <ReferenceArea
            x1={operatingRpm - 10}
            x2={operatingRpm + 10}
            fill="#f43f5e"
            fillOpacity={0.08}
            label={{ value: `${operatingRpm} RPM`, fill: '#f43f5e', fontSize: 10 }}
          />
        )}

        {/* Natural frequency curves (solid) */}
        {modeKeys.map((key, i) => (
          <Line
            key={key}
            dataKey={key}
            name={`${key.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase())}`}
            stroke={MODE_COLORS[i % MODE_COLORS.length]}
            strokeWidth={2}
            dot={false}
            type="monotone"
          />
        ))}

        {/* Excitation lines (dashed) */}
        {excKeys.map(key => (
          <Line
            key={`exc_${key}`}
            dataKey={`exc_${key}`}
            name={`${key} RPM`}
            stroke={EXC_COLORS[key] || '#888'}
            strokeWidth={1.5}
            strokeDasharray="6 3"
            dot={false}
            type="linear"
          />
        ))}

        {/* Resonance crossing markers */}
        {crossingData.length > 0 && (
          <Scatter
            data={crossingData}
            dataKey="frequency_hz"
            fill="#ef4444"
            name="Resonance"
            shape="diamond"
          />
        )}
      </ComposedChart>
    </ChartContainer>
  );
};

export default CampbellDiagram;
```

**Step 2: Verify TypeScript compiles**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system/frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: No errors

**Step 3: Commit**

```bash
git add frontend/src/components/charts/vb/CampbellDiagram.tsx
git commit -m "feat(fea): add Campbell Diagram chart with resonance crossing markers

Composed Recharts chart: natural frequency curves, 1x/2x/3x excitation dashed lines,
operating RPM band, resonance diamond markers.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 10: Integrate FEA into VibrationsModule.tsx

**Files:**
- Modify: `frontend/src/components/VibrationsModule.tsx`

**Step 1: Add FEA state, BHA editor, and chart integration**

In `frontend/src/components/VibrationsModule.tsx`:

Add imports after existing chart imports (after line 9):
```tsx
import BHAEditor, { type BHAComponent } from './charts/vb/BHAEditor';
import ModeShapePlot from './charts/vb/ModeShapePlot';
import CampbellDiagram from './charts/vb/CampbellDiagram';
import { Wrench } from 'lucide-react';
```

Add FEA state after line 48 (`const [result, setResult] = ...`):
```tsx
  const [bhaComponents, setBhaComponents] = useState<BHAComponent[]>([]);
  const [feaResult, setFeaResult] = useState<Record<string, any> | null>(null);
  const [feaLoading, setFeaLoading] = useState(false);
  const [showBhaEditor, setShowBhaEditor] = useState(false);
```

Add FEA calculation function after the `calculate` callback (after line 90):
```tsx
  const calculateFEA = useCallback(async () => {
    if (bhaComponents.length < 2) {
      addToast('Add at least 2 BHA components for FEA analysis', 'error');
      return;
    }
    setFeaLoading(true);
    try {
      const res = await api.post('/vibrations/fea', {
        bha_components: bhaComponents,
        wob_klb: params.wob_klb || 20,
        rpm: params.rpm || 120,
        mud_weight_ppg: params.mud_weight_ppg || 10,
        hole_diameter_in: params.hole_diameter_in || 8.5,
        boundary_conditions: 'pinned-pinned',
        n_modes: 5,
        include_forced_response: true,
        include_campbell: true,
        n_blades: params.n_blades || undefined,
      });
      setFeaResult(res.data);
      setActiveTab('results');
    } catch (e: unknown) {
      addToast('FEA Error: ' + ((e as APIError).response?.data?.detail || (e as APIError).message), 'error');
    }
    setFeaLoading(false);
  }, [bhaComponents, params, addToast]);
```

Add BHA Editor section in the Input tab, after the BHA Configuration section (after line 208, the closing `</div>` of BHA Configuration):
```tsx
              {/* FEA — BHA Detailed Editor */}
              <div>
                <button
                  type="button"
                  onClick={() => setShowBhaEditor(!showBhaEditor)}
                  className="flex items-center gap-2 text-lg font-bold mb-3 hover:text-rose-400 transition-colors"
                >
                  <Wrench size={18} />
                  BHA Detallado (FEA)
                  <span className="text-xs font-normal text-gray-500 ml-2">
                    {showBhaEditor ? '▼' : '▶'} {bhaComponents.length > 0 ? `${bhaComponents.length} components` : 'Click to expand'}
                  </span>
                </button>
                {showBhaEditor && (
                  <div className="glass-panel p-4 rounded-xl border border-white/5">
                    <BHAEditor components={bhaComponents} onChange={setBhaComponents} />
                    {bhaComponents.length >= 2 && (
                      <button onClick={calculateFEA} disabled={feaLoading}
                        className="mt-4 flex items-center gap-2 px-5 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-lg text-sm font-medium transition-colors disabled:opacity-50">
                        {feaLoading ? <RefreshCw size={14} className="animate-spin" /> : <Wrench size={14} />}
                        {feaLoading ? 'Running FEA...' : 'Run FEA Analysis'}
                      </button>
                    )}
                  </div>
                )}
              </div>
```

Add FEA results section in the Results tab, after the Charts grid (after line 340, before `{/* AI Analysis */}`):
```tsx
            {/* FEA Results */}
            {feaResult && (
              <>
                {/* FEA Summary */}
                <div className="glass-panel p-6 rounded-2xl border border-indigo-500/20">
                  <h3 className="text-lg font-bold text-indigo-400 mb-3">FEA Analysis (Euler-Bernoulli FEM)</h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    {feaResult.eigenvalue?.frequencies_hz?.slice(0, 4).map((freq: number, i: number) => (
                      <div key={i} className="text-center">
                        <div className="text-xs text-gray-500">Mode {i + 1}</div>
                        <div className="font-bold text-indigo-300">{freq.toFixed(2)} Hz</div>
                        <div className="text-xs text-gray-500">{(freq * 60).toFixed(0)} RPM</div>
                      </div>
                    ))}
                  </div>
                  {feaResult.summary?.resonance_warnings?.length > 0 && (
                    <div className="mt-3 space-y-1">
                      {feaResult.summary.resonance_warnings.map((w: string, i: number) => (
                        <p key={i} className="text-xs text-red-400">⚠ {w}</p>
                      ))}
                    </div>
                  )}
                </div>

                {/* FEA Charts */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <ModeShapePlot
                    nodePositions={feaResult.node_positions_ft || []}
                    modeShapes={feaResult.eigenvalue?.mode_shapes || []}
                    frequenciesHz={feaResult.eigenvalue?.frequencies_hz || []}
                  />
                  {feaResult.campbell && (
                    <CampbellDiagram
                      rpmValues={feaResult.campbell.rpm_values || []}
                      naturalFreqCurves={feaResult.campbell.natural_freq_curves || {}}
                      excitationLines={feaResult.campbell.excitation_lines || {}}
                      crossings={feaResult.campbell.crossings || []}
                      operatingRpm={params.rpm as number}
                    />
                  )}
                </div>
              </>
            )}
```

**Step 2: Verify TypeScript compiles and build succeeds**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system/frontend && npx tsc --noEmit && npm run build`
Expected: No errors, build succeeds

**Step 3: Commit**

```bash
git add frontend/src/components/VibrationsModule.tsx
git commit -m "feat(fea): integrate BHA editor and FEA charts into VibrationsModule

Collapsible BHA editor with FEA button, mode shape plot, Campbell diagram,
and FEA summary cards in the results tab.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 11: Verify Full Stack — Integration Test

**Files:** None (verification only)

**Step 1: Run ALL backend tests**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system && python3 -m pytest tests/unit/test_fea_engine.py tests/unit/test_vibrations_engine.py -v`
Expected: All tests PASS (FEA + existing vibrations)

**Step 2: Verify frontend builds**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system/frontend && npx tsc --noEmit && npm run build`
Expected: No errors

**Step 3: Quick API smoke test**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system && python3 -c "
from orchestrator.vibrations_engine import VibrationsEngine

bha = [
    {'type': 'collar', 'od': 8.0, 'id_inner': 2.813, 'length_ft': 30, 'weight_ppf': 147},
    {'type': 'collar', 'od': 6.75, 'id_inner': 2.813, 'length_ft': 60, 'weight_ppf': 83},
    {'type': 'collar', 'od': 6.75, 'id_inner': 2.813, 'length_ft': 60, 'weight_ppf': 83},
    {'type': 'hwdp', 'od': 5.0, 'id_inner': 3.0, 'length_ft': 90, 'weight_ppf': 49.3},
    {'type': 'dp', 'od': 5.0, 'id_inner': 4.276, 'length_ft': 60, 'weight_ppf': 19.5},
]

result = VibrationsEngine.run_fea_analysis(
    bha_components=bha, wob_klb=25, rpm=120, mud_weight_ppg=10, hole_diameter_in=8.5,
)
print('FEA OK')
print(f'Modes: {len(result[\"eigenvalue\"][\"frequencies_hz\"])}')
print(f'Frequencies: {result[\"eigenvalue\"][\"frequencies_hz\"]}')
print(f'Campbell crossings: {len(result[\"campbell\"][\"crossings\"])}')
print(f'Warnings: {result[\"summary\"][\"resonance_warnings\"]}')
print(f'Max amplitude: {result[\"forced_response\"][\"max_amplitude_in\"]}')
"`
Expected: Prints FEA results without errors

**Step 4: Final commit tag**

```bash
git add -A
git commit -m "feat(fea): complete FEA vibrations module implementation

Full Euler-Bernoulli FEM solver with eigenvalue analysis, forced response,
Campbell diagram generation, BHA editor component, Mode Shape Plot, and
Campbell Diagram chart. 22 unit tests, 2 new API endpoints.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Summary

| Task | Description | Files | Tests |
|------|-------------|-------|-------|
| 1 | Element matrices [K], [Kg], [M] | fea.py + test | 6 |
| 2 | Global assembly with stabilizers | fea.py + test | 4 |
| 3 | Eigenvalue solver (natural freq + mode shapes) | fea.py + test | 7 |
| 4 | Forced response + Campbell engine | fea.py + test | 5 |
| 5 | `run_fea_analysis()` orchestrator | fea.py + test | 3 |
| 6 | Facade + schemas + routes | 3 files modified | 0 (integration) |
| 7 | BHA Editor component | BHAEditor.tsx | 0 (UI) |
| 8 | Mode Shape Plot chart | ModeShapePlot.tsx | 0 (UI) |
| 9 | Campbell Diagram chart | CampbellDiagram.tsx | 0 (UI) |
| 10 | Integrate into VibrationsModule | VibrationsModule.tsx | 0 (UI) |
| 11 | Full stack verification | none | smoke test |

**Total: 25 unit tests, 4 new backend files, 3 new frontend files, 3 modified files, 11 commits.**
