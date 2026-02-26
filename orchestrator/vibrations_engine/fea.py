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


def solve_eigenvalue(
    K: NDArray,
    Kg: NDArray,
    M: NDArray,
    bc: str = "pinned-pinned",
    n_modes: int = 5,
) -> Dict[str, Any]:
    """Solve generalized eigenvalue problem for natural frequencies and mode shapes.

    Solves: (K - Kg) * phi = omega^2 * M * phi

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
