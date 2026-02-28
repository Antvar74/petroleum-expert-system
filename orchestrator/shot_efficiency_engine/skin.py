"""Karakas & Tariq (1991) perforation skin model (SPE 18247)."""
import math
from typing import Dict, Any


# Karakas-Tariq phasing constants (SPE 18247, Table 1)
#
# S_H  = ln(r'_w / (r_w + l_p))  where  r'_w = r_w * exp(alpha)
# S_V  = 10^(a1 + a2*log10(r_pD)) * h_D^(b1 + b2*log10(r_pD))
#        Note: a1 = alpha for all phasing angles per SPE 18247.
# S_wb = c1 * exp(c2 * r_wb)
#
# Keys: alpha = alpha_theta (also a1 for S_V),
#        a2   = second coefficient for S_V exponent A,
#        b1   = first coefficient for S_V exponent B (h_D power),
#        b2   = second coefficient for S_V exponent B,
#        c1   = S_wb coefficient,
#        c2   = S_wb exponent coefficient.
PHASING_DATA = {
    0:   {"alpha": -2.091, "a2": 0.0453, "b1": 5.1313, "b2": 1.8672, "c1": 1.6e-1, "c2": 2.675},
    60:  {"alpha": -2.025, "a2": 0.0943, "b1": 3.0373, "b2": 1.8115, "c1": 2.6e-2, "c2": 4.532},
    90:  {"alpha": -1.905, "a2": 0.1038, "b1": 1.8672, "b2": 1.6392, "c1": 6.6e-3, "c2": 5.320},
    120: {"alpha": -1.898, "a2": 0.1023, "b1": 1.3654, "b2": 1.6490, "c1": 1.6e-3, "c2": 6.155},
    180: {"alpha": -2.018, "a2": 0.0634, "b1": 1.6136, "b2": 1.7770, "c1": 2.3e-2, "c2": 3.550},
}


def calculate_skin_factor(
    perf_length_in: float,
    perf_radius_in: float,
    wellbore_radius_ft: float,
    spf: int,
    phasing_deg: int,
    h_perf_ft: float,
    kv_kh: float = 1.0
) -> Dict[str, Any]:
    """
    Karakas & Tariq (1991) perforation skin model.
    S_total = S_p + S_v + S_wb

    Note: This is the canonical implementation. CompletionDesignEngine's
    calculate_productivity_ratio() uses an equivalent implementation inline.
    Both share the same PHASING_DATA constants and K&T formulations.

    Args:
        perf_length_in: perforation tunnel length (inches)
        perf_radius_in: perforation tunnel radius (inches)
        wellbore_radius_ft: wellbore radius (ft)
        spf: shots per foot
        phasing_deg: gun phasing angle (0, 60, 90, 120, 180)
        h_perf_ft: interval thickness (ft)
        kv_kh: vertical-to-horizontal permeability ratio

    Returns:
        Dict with s_p, s_v, s_wb, s_total
    """
    r_w = wellbore_radius_ft
    l_p = perf_length_in / 12.0
    r_p = perf_radius_in / 12.0

    h_spacing_ft = 1.0 / spf if spf > 0 else h_perf_ft

    p = PHASING_DATA.get(
        phasing_deg, PHASING_DATA[90]
    )

    # S_p: plane-flow pseudo-skin
    r_eff_w = r_w * math.exp(p["alpha"])
    if l_p > 0 and r_eff_w > 0:
        s_p = math.log(r_eff_w / (r_w + l_p)) if (r_w + l_p) > r_eff_w else 0.0
    else:
        s_p = 0.0

    # S_v: vertical convergence skin
    # S_v = 10^A * h_D^B  where A = a1 + a2*log10(r_pD), B = b1 + b2*log10(r_pD)
    s_v = 0.0
    if l_p > 0 and kv_kh > 0 and h_spacing_ft > 0:
        h_d = h_spacing_ft * math.sqrt(1.0 / kv_kh) / l_p
        r_pd = r_p / (h_spacing_ft * (1.0 + math.sqrt(kv_kh)))
        if h_d > 0 and r_pd > 0:
            log_rpd = math.log10(r_pd)
            a_exp = p["alpha"] + p["a2"] * log_rpd
            b_exp = p["b1"] + p["b2"] * log_rpd
            s_v = (10.0 ** a_exp) * (h_d ** b_exp)
            s_v = max(0.0, min(s_v, 50.0))

    # S_wb: wellbore blockage skin
    # r_wD = r_w / (r_w + l_p) — dimensionless wellbore radius per SPE 18247
    c1 = p["c1"]
    c2 = p["c2"]
    s_wb = 0.0
    if r_w > 0 and l_p > 0:
        r_wD = r_w / (r_w + l_p)
        s_wb = c1 * math.exp(c2 * r_wD)
        s_wb = min(s_wb, 5.0)

    s_p = round(s_p, 4)
    s_v = round(s_v, 4)
    s_wb = round(s_wb, 4)
    s_total = round(s_p + s_v + s_wb, 4)

    return {
        "s_p": s_p,
        "s_v": s_v,
        "s_wb": s_wb,
        "s_total": s_total,
    }
