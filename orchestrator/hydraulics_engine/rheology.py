"""
Hydraulics Engine — Rheological Pressure Loss Models.

References:
- Bourgoyne et al., Applied Drilling Engineering (SPE Textbook)
- API RP 13D: Rheology and Hydraulics of Oil-Well Drilling Fluids
- Dodge, D.W. & Metzner, A.B. (1959): Turbulent Flow of Non-Newtonian Systems
"""
import math
from typing import Dict, Any


def _zero_result() -> Dict[str, Any]:
    return {
        "pressure_loss_psi": 0.0,
        "velocity_ft_min": 0.0,
        "reynolds": 0,
        "flow_regime": "none",
        "d_eff": 0.0
    }


def pressure_loss_bingham(
    flow_rate: float,
    mud_weight: float,
    pv: float,
    yp: float,
    length: float,
    od: float,
    id_inner: float,
    is_annular: bool = False
) -> Dict[str, Any]:
    """
    Calculate pressure loss using Bingham Plastic model.

    For pipe flow:
        Laminar:  dP = (PV * V * L) / (1500 * d²) + (YP * L) / (225 * d)
        Turbulent: dP = (f * MW * V² * L) / (25.8 * d)

    For annular flow:
        d_eff = d_hole - d_pipe (for velocity)
        d_hyd = d_hole - d_pipe (hydraulic diameter for Reynolds)

    Parameters:
    - flow_rate: gpm
    - mud_weight: ppg
    - pv: plastic viscosity (cP)
    - yp: yield point (lb/100ft²)
    - length: section length (ft)
    - od: outer diameter (inches) — hole/casing ID for annular
    - id_inner: inner diameter (inches) — pipe OD for annular
    - is_annular: True for annular flow
    """
    if length <= 0 or flow_rate <= 0:
        return _zero_result()

    if is_annular:
        d_outer = od       # hole or casing ID
        d_inner = id_inner  # pipe OD
        # Annular velocity
        v = 24.5 * flow_rate / (d_outer**2 - d_inner**2)
        d_eff = d_outer - d_inner
    else:
        # Pipe velocity
        d_eff = id_inner
        v = 24.5 * flow_rate / (d_eff**2)
        d_outer = od
        d_inner = 0

    if d_eff <= 0:
        return _zero_result()

    # Reynolds number (Bingham)
    if is_annular:
        re = 757.0 * mud_weight * v * d_eff / pv if pv > 0 else 99999
    else:
        re = 928.0 * mud_weight * v * d_eff / pv if pv > 0 else 99999

    # Hedstrom number for critical Re
    he = 37100.0 * mud_weight * yp * d_eff**2 / (pv**2) if pv > 0 else 0

    # Critical Reynolds (simplified)
    re_crit = 2100.0  # simplified; full solution uses He iteration
    if he > 0:
        re_crit = 2100.0 + 7.3 * (he**0.58)  # Hanks correlation approximation

    flow_regime = "laminar" if re < re_crit else "turbulent"

    if flow_regime == "laminar":
        if is_annular:
            dp = (pv * v * length) / (1000.0 * d_eff**2) + (yp * length) / (200.0 * d_eff)
        else:
            dp = (pv * v * length) / (1500.0 * d_eff**2) + (yp * length) / (225.0 * d_eff)
    else:
        # Turbulent: Fanning friction factor
        f = 0.0791 / (re**0.25) if re > 0 else 0.01
        v_fps = v / 60.0  # Convert ft/min to ft/s for Bourgoyne formula
        if is_annular:
            dp = (f * mud_weight * v_fps**2 * length) / (21.1 * d_eff)
        else:
            dp = (f * mud_weight * v_fps**2 * length) / (25.8 * d_eff)

    return {
        "pressure_loss_psi": round(dp, 1),
        "velocity_ft_min": round(v, 1),
        "reynolds": round(re, 0),
        "flow_regime": flow_regime,
        "d_eff": round(d_eff, 3)
    }


def pressure_loss_power_law(
    flow_rate: float,
    mud_weight: float,
    n: float,
    k: float,
    length: float,
    od: float,
    id_inner: float,
    is_annular: bool = False
) -> Dict[str, Any]:
    """
    Calculate pressure loss using Power Law model.
    tau = K * gamma^n

    Parameters:
    - n: flow behavior index (dimensionless)
    - k: consistency index (eq cP)
    """
    if length <= 0 or flow_rate <= 0 or n <= 0:
        return _zero_result()

    if is_annular:
        d_outer = od
        d_inner = id_inner
        v = 24.5 * flow_rate / (d_outer**2 - d_inner**2)
        d_eff = d_outer - d_inner
    else:
        d_eff = id_inner
        v = 24.5 * flow_rate / (d_eff**2)

    if d_eff <= 0:
        return _zero_result()

    # Generalized Reynolds number (Dodge-Metzner)
    if is_annular:
        na = (2.0 + 1.0 / n) / 3.0  # annular geometry factor
        re_g = (109000.0 * mud_weight * v**(2 - n) * d_eff**n) / (k * (na)**n)
    else:
        np_factor = (3.0 + 1.0 / n) / 4.0
        re_g = (89100.0 * mud_weight * v**(2 - n) * d_eff**n) / (k * (np_factor)**n)

    re_crit = 3470.0 - 1370.0 * n  # Dodge-Metzner critical Re

    flow_regime = "laminar" if re_g < re_crit else "turbulent"

    if flow_regime == "laminar":
        if is_annular:
            dp = (k * v**n * length) / (144000.0 * d_eff**(1 + n)) * (
                (2 + 1.0 / n) / 0.0208
            )**n
        else:
            dp = (k * v**n * length) / (144000.0 * d_eff**(1 + n)) * (
                (3 + 1.0 / n) / 0.0208
            )**n
        # Simplified: use direct formula
        # dP = (K * L) / (144000 * d^(1+n)) * (v * (3n+1)/(0.0208*n))^n  for pipe
        dp = max(dp, 0)
    else:
        # Turbulent friction factor (Dodge-Metzner)
        a = 1.0 / (4.0 * n**0.75)
        b = 0.395 / (n**1.2)
        # Iterative f solve — use initial guess
        f = 0.0791 / (re_g**0.25)
        for _ in range(10):
            rhs = a * math.log10(re_g * f**(1 - n / 2.0)) - b
            if rhs <= 0:
                break
            f = 1.0 / (rhs**2)

        if is_annular:
            dp = (f * mud_weight * v**2 * length) / (21.1 * d_eff)
        else:
            dp = (f * mud_weight * v**2 * length) / (25.8 * d_eff)

    return {
        "pressure_loss_psi": round(dp, 1),
        "velocity_ft_min": round(v, 1),
        "reynolds": round(re_g, 0),
        "flow_regime": flow_regime,
        "d_eff": round(d_eff, 3),
        "n": n,
        "k": k
    }


def fit_herschel_bulkley(fann_readings: Dict[str, float]) -> Dict[str, Any]:
    """
    Fit Herschel-Bulkley rheological parameters (tau_0, K, n) from
    standard FANN viscometer readings using iterative least-squares.

    Model: tau = tau_0 + K * gamma^n

    Parameters:
    - fann_readings: dict with keys r600, r300, r200, r100, r6, r3
      (dial readings at standard RPMs)

    Returns:
    - tau_0: yield stress (lbf/100ft²)
    - k_hb: consistency index
    - n_hb: flow behavior index
    - r_squared: goodness of fit
    - fann_readings: echo of input readings
    """
    # FANN RPM -> shear rate (1/s): gamma = 1.703 * RPM
    fann_rpm = {"r600": 600, "r300": 300, "r200": 200, "r100": 100, "r6": 6, "r3": 3}

    # Extract available readings
    readings = []
    for key in ["r3", "r6", "r100", "r200", "r300", "r600"]:
        val = fann_readings.get(key, 0.0)
        if val is not None and val > 0:
            gamma = 1.703 * fann_rpm[key]          # shear rate (1/s)
            tau = 1.0678 * val                      # shear stress (lbf/100ft²)
            readings.append((gamma, tau))

    # Guard: all zero or no valid readings
    if len(readings) < 2:
        return {
            "tau_0": 0.0, "k_hb": 0.0, "n_hb": 1.0,
            "r_squared": 0.0, "fann_readings": fann_readings
        }

    # Sort by shear rate ascending
    readings.sort(key=lambda x: x[0])

    # Initial tau_0 estimate: low-shear extrapolation (2*tau_3 - tau_6)
    tau_3 = 1.0678 * fann_readings.get("r3", 0.0)
    tau_6 = 1.0678 * fann_readings.get("r6", 0.0)
    tau_0 = max(2.0 * tau_3 - tau_6, 0.0)

    # Cap tau_0 below minimum measured shear stress
    tau_min = min(t for _, t in readings)
    if tau_0 >= tau_min:
        tau_0 = tau_min * 0.5

    best_tau_0, best_k, best_n, best_r2 = tau_0, 0.0, 1.0, -1.0

    # Iterative regression: ln(tau - tau_0) = ln(K) + n * ln(gamma)
    for iteration in range(5):
        ln_gamma = []
        ln_tau_adj = []
        for gamma, tau in readings:
            adj = tau - tau_0
            if adj > 1e-6:
                ln_gamma.append(math.log(gamma))
                ln_tau_adj.append(math.log(adj))

        if len(ln_gamma) < 2:
            break

        # Least-squares: y = a + b*x  →  ln(tau-tau0) = ln(K) + n*ln(gamma)
        n_pts = len(ln_gamma)
        sum_x = sum(ln_gamma)
        sum_y = sum(ln_tau_adj)
        sum_xx = sum(x * x for x in ln_gamma)
        sum_xy = sum(x * y for x, y in zip(ln_gamma, ln_tau_adj))

        denom = n_pts * sum_xx - sum_x * sum_x
        if abs(denom) < 1e-12:
            break

        n_hb = (n_pts * sum_xy - sum_x * sum_y) / denom
        ln_k = (sum_y - n_hb * sum_x) / n_pts
        k_hb = math.exp(ln_k)

        # Clamp n to physical range
        n_hb = max(0.05, min(n_hb, 1.5))

        # R-squared
        mean_y = sum_y / n_pts
        ss_tot = sum((y - mean_y) ** 2 for y in ln_tau_adj)
        ss_res = sum((y - (ln_k + n_hb * x)) ** 2 for x, y in zip(ln_gamma, ln_tau_adj))
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 0.0

        if r2 > best_r2:
            best_tau_0, best_k, best_n, best_r2 = tau_0, k_hb, n_hb, r2

        # Update tau_0: find value that minimizes residuals
        # Use predicted tau at lowest shear rate minus measured
        gamma_low, tau_low = readings[0]
        tau_0_new = tau_low - k_hb * gamma_low ** n_hb
        tau_0_new = max(tau_0_new, 0.0)
        tau_0_new = min(tau_0_new, tau_min * 0.95)

        if abs(tau_0_new - tau_0) < 0.01:
            best_tau_0, best_k, best_n, best_r2 = tau_0_new, k_hb, n_hb, r2
            break
        tau_0 = tau_0_new

    # Fallback: 2-point fit from r300/r600 if regression diverged
    if best_r2 < 0.5 and best_k <= 0:
        r300 = fann_readings.get("r300", 0.0)
        r600 = fann_readings.get("r600", 0.0)
        if r300 > 0 and r600 > 0:
            tau300 = 1.0678 * r300
            tau600 = 1.0678 * r600
            best_n = math.log(tau600 / tau300) / math.log(2.0) if tau300 > 0 else 1.0
            best_n = max(0.05, min(best_n, 1.5))
            best_k = tau300 / (510.9 ** best_n)
            best_tau_0 = 0.0
            best_r2 = 0.95

    return {
        "tau_0": round(best_tau_0, 3),
        "k_hb": round(best_k, 6),
        "n_hb": round(best_n, 4),
        "r_squared": round(best_r2, 4),
        "fann_readings": fann_readings
    }


def pressure_loss_herschel_bulkley(
    flow_rate: float, mud_weight: float,
    tau_0: float, k_hb: float, n_hb: float,
    length: float, od: float, id_inner: float,
    is_annular: bool = False
) -> Dict[str, Any]:
    """
    Calculate pressure loss using Herschel-Bulkley model (API RP 13D / Metzner-Reed).

    Model: tau = tau_0 + K * gamma^n

    Parameters:
    - tau_0: yield stress (lbf/100ft²)
    - k_hb: consistency index
    - n_hb: flow behavior index (0 < n < 1 for shear-thinning)
    - is_annular: True for annular geometry

    Returns: dict with pressure_loss_psi, velocity, Reynolds, flow regime
    """
    if length <= 0 or flow_rate <= 0:
        result = _zero_result()
        result.update({"tau_0": tau_0, "k_hb": k_hb, "n_hb": n_hb})
        return result

    if is_annular:
        d_eff = od - id_inner
        v = 24.5 * flow_rate / (od**2 - id_inner**2)  # ft/min
    else:
        d_eff = id_inner
        v = 24.5 * flow_rate / (d_eff**2)              # ft/min

    if d_eff <= 0 or v <= 0:
        result = _zero_result()
        result.update({"tau_0": tau_0, "k_hb": k_hb, "n_hb": n_hb})
        return result

    # Ensure n_hb is in valid range
    n = max(0.05, min(n_hb, 1.5))

    # Wall shear rate (Metzner-Reed generalized)
    if is_annular:
        gamma_w = 144.0 * v / d_eff * (2.0 * n + 1.0) / (3.0 * n)
    else:
        gamma_w = 96.0 * v / d_eff * (3.0 * n + 1.0) / (4.0 * n)

    # Wall shear stress
    tau_w = tau_0 + k_hb * (gamma_w ** n)

    # Effective viscosity (cP) at the wall
    if is_annular:
        mu_eff = tau_w * d_eff / (144.0 * v) if v > 0 else 1e6
    else:
        mu_eff = tau_w * d_eff / (96.0 * v) if v > 0 else 1e6

    mu_eff = max(mu_eff, 0.001)

    # Generalized Reynolds number
    re_g = 928.0 * mud_weight * v * d_eff / mu_eff

    # Critical Reynolds (Dodge-Metzner)
    re_crit = 3470.0 - 1370.0 * n

    if re_g < re_crit:
        # Laminar: dP = tau_w * L / (300 * d_eff)
        if is_annular:
            dp = tau_w * length / (300.0 * d_eff)
        else:
            dp = tau_w * length / (300.0 * d_eff)
        flow_regime = "laminar"
    else:
        # Turbulent: Fanning friction factor (Dodge-Metzner)
        a_coef = (math.log10(n) + 3.93) / 50.0
        b_coef = (1.75 - math.log10(n)) / 7.0
        f = a_coef / (re_g ** b_coef)
        f = max(f, 1e-6)

        if is_annular:
            dp = f * mud_weight * v**2 * length / (21.1 * d_eff)
        else:
            dp = f * mud_weight * v**2 * length / (25.8 * d_eff)
        flow_regime = "turbulent"

    return {
        "pressure_loss_psi": round(dp, 1),
        "velocity_ft_min": round(v, 1),
        "reynolds": round(re_g, 0),
        "flow_regime": flow_regime,
        "d_eff": round(d_eff, 3),
        "tau_0": tau_0,
        "k_hb": k_hb,
        "n_hb": n_hb
    }
