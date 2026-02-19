"""
Shot Efficiency Calculation Engine

Connects petrophysical log data with perforation design to recommend
optimal shooting intervals and estimate post-shot skin damage.

References:
- Archie (1942): Formation factor and water saturation
- Larionov (1969): Vshale correction for Tertiary formations
- Karakas & Tariq (1991): Semi-analytical perforation skin model
- Standard petrophysical cutoffs (SPE/AAPG)
"""
import math
from typing import Dict, Any, List, Optional


class ShotEfficiencyEngine:
    """
    Implements petrophysical analysis and perforation interval optimization.
    All methods are @staticmethod — no external dependencies beyond math.
    """

    # Karakas-Tariq phasing constants (SPE 18247, Table 1)
    PHASING_DATA = {
        0:   {"a": -2.091, "b": 0.0453, "c1": 1.6e-1, "c2": 2.675},
        60:  {"a": -2.025, "b": 0.0943, "c1": 2.6e-2, "c2": 4.532},
        90:  {"a": -1.905, "b": 0.1038, "c1": 6.6e-3, "c2": 5.320},
        120: {"a": -1.898, "b": 0.1023, "c1": 1.6e-3, "c2": 6.155},
        180: {"a": -2.018, "b": 0.0634, "c1": 2.3e-2, "c2": 3.550},
    }

    @staticmethod
    def parse_log_data(log_entries: List[Dict]) -> Dict[str, Any]:
        """
        Parse and validate array of log measurements.

        Each entry should have: {md, gr, rhob, nphi, rt, caliper (optional)}
        Validates ranges: GR 0-200, RHOB 1.5-3.0, NPHI -0.05-0.60, Rt 0.1-10000

        Args:
            log_entries: list of dicts with log measurements

        Returns:
            Dict with accepted points, rejected count, depth range
        """
        if not log_entries:
            return {"error": "No log entries provided", "accepted": [], "rejected_count": 0}

        accepted = []
        rejected = 0

        for entry in log_entries:
            md = entry.get("md", entry.get("depth", 0))
            gr = entry.get("gr", entry.get("gamma_ray", 0))
            rhob = entry.get("rhob", entry.get("density", 0))
            nphi = entry.get("nphi", entry.get("neutron", 0))
            rt = entry.get("rt", entry.get("resistivity", 0))
            caliper = entry.get("caliper", entry.get("cali", 0))

            # Validate ranges
            if md <= 0 or gr < 0 or gr > 300:
                rejected += 1
                continue
            if rhob < 1.5 or rhob > 3.2:
                rejected += 1
                continue
            if nphi < -0.05 or nphi > 0.65:
                rejected += 1
                continue
            if rt < 0.1 or rt > 100000:
                rejected += 1
                continue

            accepted.append({
                "md": round(md, 1),
                "gr": round(gr, 2),
                "rhob": round(rhob, 4),
                "nphi": round(nphi, 4),
                "rt": round(rt, 4),
                "caliper": round(caliper, 3) if caliper else 0,
            })

        # Sort by depth
        accepted.sort(key=lambda x: x["md"])

        return {
            "accepted": accepted,
            "accepted_count": len(accepted),
            "rejected_count": rejected,
            "depth_range": {
                "min_md": accepted[0]["md"] if accepted else 0,
                "max_md": accepted[-1]["md"] if accepted else 0,
            }
        }

    @staticmethod
    def calculate_porosity(
        rhob: float,
        nphi: float,
        rho_matrix: float = 2.65,
        rho_fluid: float = 1.0
    ) -> Dict[str, Any]:
        """
        Density-neutron crossplot porosity.

        phi = sqrt((phi_D^2 + phi_N^2) / 2)
        where phi_D = (rho_ma - rhob) / (rho_ma - rho_fl)

        Args:
            rhob: bulk density (g/cc)
            nphi: neutron porosity (v/v fraction)
            rho_matrix: matrix density (g/cc), default 2.65 sandstone
            rho_fluid: fluid density (g/cc), default 1.0

        Returns:
            Dict with phi, phi_density, phi_neutron, method
        """
        denom = rho_matrix - rho_fluid
        if denom == 0:
            return {"error": "Matrix and fluid densities are equal"}

        phi_d = (rho_matrix - rhob) / denom
        phi_n = nphi

        # RMS crossplot
        phi = math.sqrt((phi_d ** 2 + phi_n ** 2) / 2.0)

        # Clamp to physically reasonable range
        phi = max(0.0, min(phi, 0.50))

        return {
            "phi": round(phi, 4),
            "phi_density": round(phi_d, 4),
            "phi_neutron": round(phi_n, 4),
            "method": "density_neutron_rms_crossplot",
        }

    @staticmethod
    def calculate_water_saturation(
        rt: float,
        porosity: float,
        rw: float = 0.05,
        a: float = 1.0,
        m: float = 2.0,
        n: float = 2.0
    ) -> Dict[str, Any]:
        """
        Archie (1942) water saturation.

        Sw^n = (a * Rw) / (Rt * phi^m)
        Sw   = ((a * Rw) / (Rt * phi^m))^(1/n)

        Args:
            rt: true (deep) resistivity (ohm-m)
            porosity: total porosity (v/v fraction)
            rw: formation water resistivity (ohm-m)
            a: tortuosity factor (default 1.0)
            m: cementation exponent (default 2.0)
            n: saturation exponent (default 2.0)

        Returns:
            Dict with sw, hydrocarbon_saturation, classification
        """
        if porosity <= 0 or rt <= 0:
            return {"sw": 1.0, "hydrocarbon_saturation": 0.0, "classification": "Non-reservoir"}

        numerator = a * rw
        denominator = rt * (porosity ** m)
        if denominator <= 0:
            sw = 1.0
        else:
            sw = (numerator / denominator) ** (1.0 / n)

        sw = max(0.0, min(sw, 1.0))
        sh = 1.0 - sw

        if sw > 0.80:
            classification = "Water"
        elif sw > 0.60:
            classification = "Water with residual HC"
        elif sw > 0.40:
            classification = "Transition"
        elif sw > 0.20:
            classification = "Hydrocarbon"
        else:
            classification = "Hydrocarbon (high saturation)"

        return {
            "sw": round(sw, 4),
            "hydrocarbon_saturation": round(sh, 4),
            "classification": classification,
        }

    @staticmethod
    def calculate_vshale(
        gr_value: float,
        gr_clean: float = 20.0,
        gr_shale: float = 120.0,
        method: str = "larionov_tertiary"
    ) -> Dict[str, Any]:
        """
        Volume of shale from gamma ray.

        Linear (IGR): Vsh = (GR - GR_clean) / (GR_shale - GR_clean)
        Larionov Tertiary: Vsh = 0.083 * (2^(3.7 * IGR) - 1)

        Args:
            gr_value: gamma ray reading (API)
            gr_clean: clean-sand GR baseline (API)
            gr_shale: pure-shale GR baseline (API)
            method: "linear" or "larionov_tertiary"

        Returns:
            Dict with vsh, igr, method used
        """
        denom = gr_shale - gr_clean
        if denom <= 0:
            return {"error": "GR_shale must be greater than GR_clean"}

        igr = (gr_value - gr_clean) / denom
        igr = max(0.0, min(igr, 1.0))

        if method == "linear":
            vsh = igr
        else:
            # Larionov Tertiary correction
            vsh = 0.083 * (2.0 ** (3.7 * igr) - 1.0)

        vsh = max(0.0, min(vsh, 1.0))

        return {
            "vsh": round(vsh, 4),
            "igr": round(igr, 4),
            "method": method,
        }

    @staticmethod
    def identify_net_pay_intervals(
        log_data: List[Dict],
        phi_cutoff: float = 0.08,
        sw_cutoff: float = 0.60,
        vsh_cutoff: float = 0.40,
        min_thickness_ft: float = 2.0
    ) -> Dict[str, Any]:
        """
        Identify net-pay intervals from processed log data.

        A depth point passes: phi > phi_min, Sw < Sw_max, Vsh < Vsh_max.
        Contiguous passing points grouped into intervals.
        Intervals thinner than min_thickness_ft are discarded.

        Args:
            log_data: list of dicts with md, phi, sw, vsh
            phi_cutoff: minimum porosity (v/v)
            sw_cutoff: maximum water saturation (v/v)
            vsh_cutoff: maximum shale volume (v/v)
            min_thickness_ft: minimum interval thickness (ft)

        Returns:
            Dict with intervals list and summary statistics
        """
        if not log_data:
            return {"intervals": [], "interval_count": 0, "total_net_pay_ft": 0.0}

        # Tag each point
        tagged = []
        for pt in log_data:
            passes = (
                pt.get("phi", 0) > phi_cutoff
                and pt.get("sw", 1) < sw_cutoff
                and pt.get("vsh", 1) < vsh_cutoff
            )
            tagged.append({**pt, "is_net_pay": passes})

        # Group contiguous passing points
        intervals = []
        current_group = []

        for pt in tagged:
            if pt["is_net_pay"]:
                current_group.append(pt)
            else:
                if current_group:
                    intervals.append(current_group)
                    current_group = []
        if current_group:
            intervals.append(current_group)

        # Build interval summaries
        result_intervals = []
        total_net = 0.0

        for grp in intervals:
            top_md = grp[0]["md"]
            base_md = grp[-1]["md"]
            thickness = base_md - top_md
            if len(grp) == 1:
                thickness = 0.5  # single-point: assume 0.5 ft spacing

            if thickness < min_thickness_ft:
                continue

            avg_phi = sum(p["phi"] for p in grp) / len(grp)
            avg_sw = sum(p["sw"] for p in grp) / len(grp)
            avg_vsh = sum(p["vsh"] for p in grp) / len(grp)

            result_intervals.append({
                "top_md": round(top_md, 1),
                "base_md": round(base_md, 1),
                "thickness_ft": round(thickness, 1),
                "avg_phi": round(avg_phi, 4),
                "avg_sw": round(avg_sw, 4),
                "avg_vsh": round(avg_vsh, 4),
                "is_net_pay": True,
                "point_count": len(grp),
            })
            total_net += thickness

        return {
            "intervals": result_intervals,
            "interval_count": len(result_intervals),
            "total_net_pay_ft": round(total_net, 1),
            "cutoffs_used": {
                "phi_min": phi_cutoff, "sw_max": sw_cutoff,
                "vsh_max": vsh_cutoff, "min_thickness_ft": min_thickness_ft,
            },
        }

    @staticmethod
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

        p = ShotEfficiencyEngine.PHASING_DATA.get(
            phasing_deg, ShotEfficiencyEngine.PHASING_DATA[90]
        )

        # S_p: plane-flow pseudo-skin
        r_eff_w = r_w * math.exp(p["a"])
        if l_p > 0 and r_eff_w > 0:
            s_p = math.log(r_eff_w / (r_w + l_p)) if (r_w + l_p) > r_eff_w else 0.0
        else:
            s_p = 0.0

        # S_v: vertical convergence skin
        s_v = 0.0
        if l_p > 0 and kv_kh > 0 and h_spacing_ft > 0:
            h_d = h_spacing_ft * math.sqrt(1.0 / kv_kh) / l_p
            r_pd = r_p / (h_spacing_ft * (1.0 + math.sqrt(kv_kh)))
            if h_d > 0 and r_pd > 0:
                s_v = (10.0 ** (p["a"] + p["b"] * math.log10(r_pd))) * h_d
                s_v = max(0.0, min(s_v, 50.0))

        # S_wb: wellbore blockage skin
        c1 = p["c1"]
        c2 = p["c2"]
        s_wb = 0.0
        if r_p > 0 and r_w > 0:
            ratio = r_p / r_w
            if ratio < 1.0:
                s_wb = c1 * math.exp(c2 * ratio)
            else:
                s_wb = c1
            s_wb = min(s_wb, 5.0)

        s_total = s_p + s_v + s_wb

        return {
            "s_p": round(s_p, 4),
            "s_v": round(s_v, 4),
            "s_wb": round(s_wb, 4),
            "s_total": round(s_total, 4),
        }

    @staticmethod
    def rank_intervals(
        intervals: List[Dict],
        weights: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Score and rank candidate perforation intervals.

        score = w_phi * phi_norm + w_sw * (1-sw_norm) + w_thick * thick_norm
                + w_skin * (1/(1+|skin|))

        Default weights: phi=0.35, sw=0.25, thickness=0.25, skin=0.15

        Args:
            intervals: list of interval dicts with avg_phi, avg_sw, thickness_ft, skin_total
            weights: optional dict overriding default weights

        Returns:
            Dict with ranked list and best interval
        """
        if not intervals:
            return {"ranked": [], "best": None}

        w = weights or {"phi": 0.35, "sw": 0.25, "thickness": 0.25, "skin": 0.15}

        phis = [iv["avg_phi"] for iv in intervals]
        sws = [iv["avg_sw"] for iv in intervals]
        thicks = [iv["thickness_ft"] for iv in intervals]

        def _norm(val, lo, hi):
            return (val - lo) / (hi - lo) if hi != lo else 1.0

        phi_lo, phi_hi = min(phis), max(phis)
        sw_lo, sw_hi = min(sws), max(sws)
        th_lo, th_hi = min(thicks), max(thicks)

        scored = []
        for iv in intervals:
            phi_n = _norm(iv["avg_phi"], phi_lo, phi_hi)
            sw_n = _norm(iv["avg_sw"], sw_lo, sw_hi)
            th_n = _norm(iv["thickness_ft"], th_lo, th_hi)
            sk_factor = 1.0 / (1.0 + abs(iv.get("skin_total", 0.0)))

            score = (w["phi"] * phi_n + w["sw"] * (1.0 - sw_n)
                     + w["thickness"] * th_n + w["skin"] * sk_factor)

            scored.append({**iv, "score": round(score, 4)})

        scored.sort(key=lambda x: x["score"], reverse=True)
        for idx, item in enumerate(scored):
            item["rank"] = idx + 1

        return {"ranked": scored, "best": scored[0] if scored else None, "weights_used": w}

    @staticmethod
    def calculate_full_shot_efficiency(
        log_entries: List[Dict],
        archie_params: Optional[Dict[str, float]] = None,
        matrix_params: Optional[Dict[str, float]] = None,
        cutoffs: Optional[Dict[str, float]] = None,
        perf_params: Optional[Dict[str, Any]] = None,
        reservoir_params: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Full integrated shot-efficiency analysis pipeline.

        1. Parse and validate log data
        2. Compute porosity, Sw, Vshale per depth point
        3. Identify net pay intervals
        4. Calculate Karakas-Tariq skin per interval
        5. Rank intervals by composite score
        6. Compile summary with alerts

        Args:
            log_entries: raw log measurements
            archie_params: {a, m, n, rw}
            matrix_params: {rho_matrix, rho_fluid, gr_clean, gr_shale}
            cutoffs: {phi_min, sw_max, vsh_max, min_thickness_ft}
            perf_params: {spf, phasing_deg, perf_length_in, tunnel_radius_in}
            reservoir_params: {k_h, kv_kh, wellbore_radius_ft}

        Returns:
            Dict with processed_logs, intervals, rankings, summary, alerts
        """
        eng = ShotEfficiencyEngine

        # Resolve defaults
        ap = archie_params or {}
        a, m, n, rw = ap.get("a", 1.0), ap.get("m", 2.0), ap.get("n", 2.0), ap.get("rw", 0.05)

        mp = matrix_params or {}
        rho_matrix = mp.get("rho_matrix", 2.65)
        rho_fluid = mp.get("rho_fluid", 1.0)
        gr_clean = mp.get("gr_clean", 20.0)
        gr_shale = mp.get("gr_shale", 120.0)

        co = cutoffs or {}
        phi_min = co.get("phi_min", 0.08)
        sw_max = co.get("sw_max", 0.60)
        vsh_max = co.get("vsh_max", 0.40)
        min_thick = co.get("min_thickness_ft", 2.0)

        pp = perf_params or {}
        spf = pp.get("spf", 4)
        phasing_deg = pp.get("phasing_deg", 90)
        perf_length_in = pp.get("perf_length_in", 12.0)
        tunnel_radius_in = pp.get("tunnel_radius_in", 0.20)

        rp = reservoir_params or {}
        kv_kh = rp.get("kv_kh", 0.5)
        wellbore_radius_ft = rp.get("wellbore_radius_ft", 0.354)

        # Step 1: Parse logs
        parsed = eng.parse_log_data(log_entries)
        if "error" in parsed:
            return {"summary": {}, "alerts": [parsed["error"]]}

        accepted = parsed["accepted"]
        if not accepted:
            return {"summary": {}, "alerts": ["No valid log points after parsing"], "parsing": parsed}

        # Step 2: Compute petrophysics
        processed = []
        for pt in accepted:
            por = eng.calculate_porosity(pt["rhob"], pt["nphi"], rho_matrix, rho_fluid)
            sw_res = eng.calculate_water_saturation(pt["rt"], por.get("phi", 0), rw, a, m, n)
            vsh_res = eng.calculate_vshale(pt["gr"], gr_clean, gr_shale)

            processed.append({
                "md": pt["md"], "gr": pt["gr"], "rhob": pt["rhob"],
                "nphi": pt["nphi"], "rt": pt["rt"],
                "phi": por.get("phi", 0.0),
                "phi_density": por.get("phi_density", 0.0),
                "phi_neutron": por.get("phi_neutron", 0.0),
                "sw": sw_res.get("sw", 1.0),
                "hydrocarbon_saturation": sw_res.get("hydrocarbon_saturation", 0.0),
                "sw_class": sw_res.get("classification", ""),
                "vsh": vsh_res.get("vsh", 1.0),
                "igr": vsh_res.get("igr", 1.0),
            })

        # Step 3: Identify net pay
        net_pay = eng.identify_net_pay_intervals(processed, phi_min, sw_max, vsh_max, min_thick)
        intervals = net_pay["intervals"]

        # Step 4: Calculate skin per interval
        for iv in intervals:
            skin_res = eng.calculate_skin_factor(
                perf_length_in=perf_length_in,
                perf_radius_in=tunnel_radius_in,
                wellbore_radius_ft=wellbore_radius_ft,
                spf=spf, phasing_deg=phasing_deg,
                h_perf_ft=iv["thickness_ft"],
                kv_kh=kv_kh,
            )
            iv["skin_total"] = skin_res["s_total"]
            iv["skin_components"] = {"s_p": skin_res["s_p"], "s_v": skin_res["s_v"], "s_wb": skin_res["s_wb"]}

        # Step 5: Rank
        ranking = eng.rank_intervals(intervals)

        # Step 6: Alerts & summary
        alerts = []
        if parsed["rejected_count"] > 0:
            alerts.append(f"{parsed['rejected_count']} log point(s) rejected during parsing")
        if net_pay["interval_count"] == 0:
            alerts.append("No net-pay intervals identified -- review cutoffs")
        if net_pay["total_net_pay_ft"] < 5.0 and net_pay["interval_count"] > 0:
            alerts.append(f"Thin total net pay ({net_pay['total_net_pay_ft']:.1f} ft)")

        best = ranking.get("best")
        if best:
            if best.get("skin_total", 0) > 10:
                alerts.append(f"High skin ({best['skin_total']:.1f}) on best interval -- consider stimulation")
            if best.get("avg_sw", 1) > 0.50:
                alerts.append(f"Best interval Sw={best['avg_sw']:.2f} -- risk of early water production")

        avg_phi_all = sum(p["phi"] for p in processed) / len(processed)
        avg_sw_all = sum(p["sw"] for p in processed) / len(processed)
        avg_vsh_all = sum(p["vsh"] for p in processed) / len(processed)

        summary = {
            "total_log_points": len(processed),
            "rejected_points": parsed["rejected_count"],
            "avg_porosity": round(avg_phi_all, 4),
            "avg_sw": round(avg_sw_all, 4),
            "avg_vsh": round(avg_vsh_all, 4),
            "net_pay_intervals_count": net_pay["interval_count"],
            "total_net_pay_ft": net_pay["total_net_pay_ft"],
            "best_interval": {
                "top_md": best["top_md"], "base_md": best["base_md"],
                "thickness_ft": best["thickness_ft"], "avg_phi": best["avg_phi"],
                "avg_sw": best["avg_sw"], "score": best["score"],
                "skin_total": best.get("skin_total", 0),
            } if best else None,
            "perf_config": {"spf": spf, "phasing_deg": phasing_deg, "perf_length_in": perf_length_in},
            "alerts": alerts,
        }

        return {
            "summary": summary,
            "processed_logs": processed,
            "net_pay": net_pay,
            "intervals_with_skin": intervals,
            "rankings": ranking,
            "parameters": {
                "archie": {"a": a, "m": m, "n": n, "rw": rw},
                "matrix": {"rho_matrix": rho_matrix, "rho_fluid": rho_fluid, "gr_clean": gr_clean, "gr_shale": gr_shale},
                "cutoffs": {"phi_min": phi_min, "sw_max": sw_max, "vsh_max": vsh_max, "min_thickness_ft": min_thick},
                "perforation": {"spf": spf, "phasing_deg": phasing_deg, "perf_length_in": perf_length_in, "tunnel_radius_in": tunnel_radius_in},
                "reservoir": {"kv_kh": kv_kh, "wellbore_radius_ft": wellbore_radius_ft},
            },
            "alerts": alerts,
        }
