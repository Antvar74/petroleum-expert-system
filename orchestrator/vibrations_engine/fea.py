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


MAX_ELEMENT_LENGTH_FT = 100.0  # Max element length before auto-meshing (ft)

# Component types that form the BHA (analyzed for lateral vibrations).
# Drill pipe is excluded — it's too flexible for lateral FEA and is only
# relevant for torsional (stick-slip) analysis.
_BHA_TYPES = {"collar", "hwdp", "stabilizer", "motor", "mwd"}


def _auto_mesh(
    bha_components: List[Dict[str, Any]],
    max_length_ft: float = MAX_ELEMENT_LENGTH_FT,
) -> List[Dict[str, Any]]:
    """Subdivide long components into smaller equal-length elements.

    Any component with length_ft > max_length_ft is split into N sub-elements
    of equal length, each inheriting the same OD, ID, and weight_ppf.
    This prevents numerical singularity in the Euler-Bernoulli stiffness
    matrix where EI/L^3 approaches zero for very long elements.

    Args:
        bha_components: Original component list from BHA Editor.
        max_length_ft: Maximum element length (ft). Default 30 ft.

    Returns:
        Meshed component list (may be larger than input).
    """
    meshed: List[Dict[str, Any]] = []
    for comp in bha_components:
        length_ft = comp.get("length_ft", 30.0)
        if length_ft <= max_length_ft:
            meshed.append(comp)
        else:
            n_sub = math.ceil(length_ft / max_length_ft)
            sub_length = length_ft / n_sub
            for _ in range(n_sub):
                meshed.append({**comp, "length_ft": sub_length})
    return meshed


_DP_FEA_MAX_LENGTH_FT = 500.0  # DP sections longer than this are excluded from lateral FEA


def _filter_bha_for_fea(
    bha_components: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Filter components for lateral FEA — exclude long drill pipe sections.

    Short DP (< 500 ft, typical BHA tail section) is kept in the model.
    Long DP (> 500 ft, e.g. 14,665 ft) is excluded because:
    - Lateral FEA of a 15,000 ft beam produces ill-conditioned matrices
      (condition number > 1e15) and eigenvalues near machine precision.
    - Physically, lateral vibration analysis targets the BHA — the DP section
      above is relevant only for torsional (stick-slip) analysis.

    If filtering removes all components, returns original list unchanged.
    """
    filtered = [
        c for c in bha_components
        if c.get("type", "").lower() in _BHA_TYPES
        or c.get("length_ft", 0) <= _DP_FEA_MAX_LENGTH_FT
    ]
    if not filtered:
        return bha_components  # fallback: use all if nothing passes filter
    return filtered


def assemble_global_matrices(
    bha_components: List[Dict[str, Any]],
    mud_weight_ppg: float = 10.0,
    wob_klb: float = 0.0,
    stabilizer_nodes: Optional[List[int]] = None,
    stabilizer_stiffness: float = 1e8,
) -> Tuple[NDArray, NDArray, NDArray, List[float]]:
    """Assemble global [K], [Kg], [M] from BHA component list.

    Components are automatically meshed (subdivided) before assembly.
    Any component longer than MAX_ELEMENT_LENGTH_FT (30 ft) is split into
    smaller equal-length sub-elements to prevent numerical instability.

    Nodes numbered 0..N where node 0 = bit end, node N = top of BHA.

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
    # Auto-mesh: subdivide long elements to prevent L^3 singularity
    elements = _auto_mesh(bha_components)

    n_elements = len(elements)
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

    for i, comp in enumerate(elements):
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


def _get_constrained_dofs(bc: str, n_nodes: int) -> List[int]:
    """Return list of constrained DOF indices for given boundary conditions."""
    if bc == "pinned-pinned":
        return [0, (n_nodes - 1) * 2]
    elif bc == "fixed-pinned":
        return [0, 1, (n_nodes - 1) * 2]
    elif bc == "fixed-free":
        return [0, 1]
    return [0, (n_nodes - 1) * 2]


def _compute_damping_alpha(
    mud_weight_ppg: float = 10.0,
    pv_cp: Optional[float] = None,
    yp_lbf_100ft2: Optional[float] = None,
) -> float:
    """Compute mass-proportional Rayleigh damping coefficient.

    When PV and YP are available, uses a rheology-based model:
        alpha = 0.005 + MW * 0.001 + PV * 0.0008 + YP * 0.0003

    When only MW is available, uses the legacy empirical formula:
        alpha = 0.01 + MW * 0.002

    The rheology-based model accounts for:
    - Mud weight: buoyant mass effect on damping
    - Plastic viscosity: viscous shear dissipation around BHA
    - Yield point: gel structure dissipation at low shear rates

    Returns:
        alpha: Mass-proportional damping coefficient (dimensionless).
    """
    if pv_cp is not None and yp_lbf_100ft2 is not None:
        return 0.005 + mud_weight_ppg * 0.001 + pv_cp * 0.0008 + yp_lbf_100ft2 * 0.0003
    return 0.01 + mud_weight_ppg * 0.002


def solve_forced_response(
    K: NDArray,
    Kg: NDArray,
    M: NDArray,
    bc: str = "pinned-pinned",
    excitation_freq_hz: float = 2.0,
    excitation_node: int = 0,
    force_lbs: float = 100.0,
    mud_weight_ppg: float = 10.0,
    pv_cp: Optional[float] = None,
    yp_lbf_100ft2: Optional[float] = None,
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
        pv_cp: Plastic viscosity (cP). Improves damping model when available.
        yp_lbf_100ft2: Yield point (lbf/100ft2). Improves damping model when available.
        alpha: Mass-proportional damping. If None, estimated from mud weight and rheology.
        beta: Stiffness-proportional damping (default 0.01).

    Returns:
        Dict with amplitudes (per node), max_amplitude_in, phase angles.
    """
    n_dof = K.shape[0]
    n_nodes = n_dof // 2

    if alpha is None:
        alpha = _compute_damping_alpha(mud_weight_ppg, pv_cp, yp_lbf_100ft2)

    C = alpha * M + beta * K

    constrained_dofs = _get_constrained_dofs(bc, n_nodes)
    free_dofs = [d for d in range(n_dof) if d not in constrained_dofs]
    ix = np.ix_(free_dofs, free_dofs)

    K_eff_free = K[ix] - Kg[ix]
    M_free = M[ix]
    C_free = C[ix]

    omega = 2.0 * math.pi * excitation_freq_hz

    Z = K_eff_free + 1j * omega * C_free - omega**2 * M_free

    F_full = np.zeros(n_dof, dtype=np.complex128)
    force_dof = excitation_node * 2
    # If requested DOF is constrained, apply at nearest free y-DOF
    if force_dof in constrained_dofs:
        for node in range(n_nodes):
            candidate = node * 2
            if candidate not in constrained_dofs:
                force_dof = candidate
                break
    F_full[force_dof] = force_lbs
    F_free = F_full[free_dofs]

    try:
        U_free = np.linalg.solve(Z, F_free)
    except np.linalg.LinAlgError:
        return {"amplitudes": [0.0] * n_nodes, "max_amplitude_in": 0.0, "error": "Singular matrix"}

    U_full = np.zeros(n_dof, dtype=np.complex128)
    U_full[free_dofs] = U_free

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

    K, Kg, M, node_positions = assemble_global_matrices(
        bha_components, mud_weight_ppg, wob_klb,
    )

    eigen_result = solve_eigenvalue(K, Kg, M, bc=bc, n_modes=n_modes)
    base_freqs = eigen_result["frequencies_hz"]

    natural_freq_curves: Dict[str, List[float]] = {}
    for mode_idx in range(len(base_freqs)):
        key = f"mode_{mode_idx + 1}"
        natural_freq_curves[key] = [base_freqs[mode_idx]] * len(rpm_values)

    excitation_lines: Dict[str, List[float]] = {
        "1x": [r / 60.0 for r in rpm_values],
        "2x": [2.0 * r / 60.0 for r in rpm_values],
        "3x": [3.0 * r / 60.0 for r in rpm_values],
    }

    if n_blades and n_blades > 0:
        excitation_lines[f"{n_blades}x_blade"] = [n_blades * r / 60.0 for r in rpm_values]

    crossings: List[Dict[str, Any]] = []
    threshold_hz = 0.3

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


def run_fea_analysis(
    bha_components: List[Dict[str, Any]],
    wob_klb: float = 20.0,
    rpm: float = 120.0,
    mud_weight_ppg: float = 10.0,
    pv_cp: Optional[float] = None,
    yp_lbf_100ft2: Optional[float] = None,
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
        pv_cp: Plastic viscosity (cP). Improves damping model when available.
        yp_lbf_100ft2: Yield point (lbf/100ft2). Improves damping model when available.
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
    # 0. Filter: only BHA components for lateral FEA (exclude DP)
    fea_components = _filter_bha_for_fea(bha_components)

    # 1. Assemble
    K, Kg, M, node_positions = assemble_global_matrices(
        fea_components, mud_weight_ppg, wob_klb,
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
            pv_cp=pv_cp,
            yp_lbf_100ft2=yp_lbf_100ft2,
        )

    # 4. Campbell diagram
    campbell = None
    if include_campbell:
        campbell = generate_campbell_diagram(
            bha_components=fea_components,
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
        if freq <= 0:
            continue
        ratio = operating_freq / freq
        if 0.85 < ratio < 1.15:
            warnings.append(
                f"1x RPM ({rpm}) near Mode {i+1} ({freq:.2f} Hz / {freq*60:.0f} RPM) — resonance risk"
            )
        if freq > 0 and 0.85 < 2 * operating_freq / freq < 1.15:
            warnings.append(
                f"2x RPM near Mode {i+1} ({freq:.2f} Hz) — secondary resonance"
            )

    # 6. Summary
    summary: Dict[str, Any] = {
        "fea_method": "Euler-Bernoulli FEM (auto-meshed)",
        "n_components_input": len(bha_components),
        "n_components_fea": len(fea_components),
        "n_elements": len(node_positions) - 1,
        "n_nodes": len(node_positions),
        "n_dof": len(node_positions) * 2,
        "boundary_conditions": bc,
        "wob_klb": wob_klb,
        "operating_rpm": rpm,
        "resonance_warnings": warnings,
    }
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
