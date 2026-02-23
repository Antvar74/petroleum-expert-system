"""
Advanced Petrophysics Engine

Extends basic petrophysical analysis with:
- LAS 2.0/3.0 file parsing via lasio library
- Waxman-Smits (1968) shaly-sand water saturation model
- Dual-Water model (Clavier et al., 1984) for high-clay formations
- Pickett plot generation with iso-Sw lines
- Density-Neutron crossplot with lithology lines
- Advanced permeability: Timur (1968), Coates-Dumanoir (1974)

References:
- Archie, G.E. (1942): Formation Factor and Water Saturation
- Waxman, M.H. & Smits, L.J.M. (1968): Electrical Conductivities in Shaly Sands
- Clavier, C., Coates, G. & Dumanoir, J. (1984): Dual-Water Model
- Timur, A. (1968): Permeability from Logs
- Coates, G.R. & Dumanoir, J.L. (1974): Permeability Estimation
"""
import math
import os
from typing import Dict, Any, List, Optional

try:
    import lasio
    HAS_LASIO = True
except ImportError:
    HAS_LASIO = False


class PetrophysicsEngine:
    """
    Advanced petrophysical analysis engine.
    All methods are @staticmethod — no external state.
    """

    # Common LAS mnemonic mapping to standard names
    MNEMONIC_MAP = {
        "DEPT": "md", "DEPTH": "md", "MD": "md", "TDEP": "md",
        "GR": "gr", "SGR": "gr", "CGR": "gr", "ECGR": "gr",
        "RHOB": "rhob", "RHOZ": "rhob", "DEN": "rhob", "DENSITY": "rhob",
        "NPHI": "nphi", "TNPH": "nphi", "PHIN": "nphi", "NEU": "nphi", "CNPHI": "nphi",
        "RT": "rt", "ILD": "rt", "LLD": "rt", "MSFL": "rt", "RILM": "rt",
        "RESD": "rt", "RD": "rt", "AT90": "rt", "HDRS": "rt",
        "DT": "dt", "DTC": "dt", "DTCO": "dt", "SONIC": "dt",
        "CALI": "caliper", "CAL": "caliper", "HCAL": "caliper",
        "SP": "sp",
        "DRHO": "drho", "DPHI": "dphi",
        "PE": "pe", "PEF": "pe",
    }

    # Lithology matrix parameters for crossplots
    LITHOLOGY = {
        "sandstone":  {"rho_ma": 2.65, "nphi_ma": -0.02, "dt_ma": 55.5},
        "limestone":  {"rho_ma": 2.71, "nphi_ma": 0.00, "dt_ma": 47.5},
        "dolomite":   {"rho_ma": 2.87, "nphi_ma": 0.02, "dt_ma": 43.5},
    }

    # ─────────────────────────────────────────────────────────────
    # LAS File Parsing (using lasio)
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def parse_las_file(file_path: str) -> Dict[str, Any]:
        """
        Parse LAS 2.0/3.0 file using lasio library.

        Args:
            file_path: path to .las file

        Returns:
            Dict with well_info, curves (list of mnemonic names),
            data (list of dicts with standardized keys), units, stats
        """
        if not HAS_LASIO:
            return {"error": "lasio library not installed. Run: pip install lasio"}

        if not os.path.exists(file_path):
            return {"error": f"File not found: {file_path}"}

        try:
            las = lasio.read(file_path)
        except Exception as e:
            return {"error": f"Cannot parse LAS file: {str(e)}"}

        return PetrophysicsEngine._process_lasio_object(las)

    @staticmethod
    def parse_las_content(content: str) -> Dict[str, Any]:
        """
        Parse LAS content from string (for frontend upload without file).

        Args:
            content: LAS file content as string

        Returns:
            Same structure as parse_las_file
        """
        if not HAS_LASIO:
            return {"error": "lasio library not installed. Run: pip install lasio"}

        if not content or not content.strip():
            return {"error": "Empty LAS content"}

        try:
            import io
            las = lasio.read(io.StringIO(content))
        except Exception as e:
            return {"error": f"Cannot parse LAS content: {str(e)}"}

        return PetrophysicsEngine._process_lasio_object(las)

    @staticmethod
    def _process_lasio_object(las) -> Dict[str, Any]:
        """Process a lasio.LASFile object into standardized output."""
        # Extract well info
        well_info = {}
        for item in las.well:
            well_info[item.mnemonic] = item.value

        # Extract curve info and map mnemonics
        curves = []
        curve_mapping = {}
        units = {}
        for curve in las.curves:
            mnem = curve.mnemonic.upper().strip()
            std_name = PetrophysicsEngine.MNEMONIC_MAP.get(mnem, mnem.lower())
            curves.append(mnem)
            curve_mapping[mnem] = std_name
            units[std_name] = curve.unit

        # Extract data rows
        data = []
        null_val = las.well.NULL.value if hasattr(las.well, 'NULL') else -999.25
        try:
            null_val = float(null_val)
        except (ValueError, TypeError):
            null_val = -999.25

        for i in range(len(las[las.curves[0].mnemonic])):
            row = {}
            for curve in las.curves:
                mnem = curve.mnemonic.upper().strip()
                std_name = curve_mapping.get(mnem, mnem.lower())
                val = float(las[curve.mnemonic][i])
                # Replace null values and NaN with None
                if math.isnan(val) or abs(val - null_val) < 0.01:
                    row[std_name] = None
                else:
                    row[std_name] = round(val, 6)
            data.append(row)

        # Compute basic stats per curve
        stats = {}
        for curve in las.curves:
            mnem = curve.mnemonic.upper().strip()
            std_name = curve_mapping.get(mnem, mnem.lower())
            valid_vals = [d[std_name] for d in data if d.get(std_name) is not None]
            if valid_vals:
                stats[std_name] = {
                    "min": round(min(valid_vals), 4),
                    "max": round(max(valid_vals), 4),
                    "mean": round(sum(valid_vals) / len(valid_vals), 4),
                    "count": len(valid_vals),
                }

        return {
            "well_info": well_info,
            "curves": curves,
            "curve_mapping": curve_mapping,
            "units": units,
            "data": data,
            "stats": stats,
            "depth_range": {
                "min": data[0].get("md") if data else None,
                "max": data[-1].get("md") if data else None,
                "points": len(data),
            },
        }

    # ─────────────────────────────────────────────────────────────
    # Advanced Water Saturation Models
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def calculate_water_saturation_advanced(
        phi: float, rt: float, rw: float, vsh: float = 0.0, rsh: float = 2.0,
        a: float = 1.0, m: float = 2.0, n: float = 2.0,
        method: str = "auto",
    ) -> Dict[str, Any]:
        """
        Calculate water saturation with auto-model selection.

        Models:
        - Archie (1942): clean sands, Vsh < 0.15
        - Waxman-Smits (1968): moderate clay, 0.15 <= Vsh < 0.40
        - Dual-Water (Clavier 1984): high clay, Vsh >= 0.40

        Args:
            phi: total porosity (fractional, 0-1)
            rt: true resistivity (ohm-m)
            rw: formation water resistivity (ohm-m)
            vsh: volume of shale (fractional, 0-1)
            rsh: shale resistivity (ohm-m)
            a, m, n: Archie cementation parameters
            method: "auto", "archie", "waxman_smits", "dual_water"

        Returns:
            Dict with sw, model_used, details
        """
        # Validate inputs
        phi = max(0.01, min(phi, 0.50))
        rt = max(0.1, rt)
        rw = max(0.001, rw)
        vsh = max(0.0, min(vsh, 1.0))

        # Auto-select model
        if method == "auto":
            if vsh < 0.15:
                method = "archie"
            elif vsh < 0.40:
                method = "waxman_smits"
            else:
                method = "dual_water"

        if method == "archie":
            sw = PetrophysicsEngine._archie_sw(phi, rt, rw, a, m, n)
            return {"sw": sw, "model_used": "archie", "vsh": vsh,
                    "details": "Clean sand model (Archie 1942)"}

        elif method == "waxman_smits":
            sw = PetrophysicsEngine._waxman_smits_sw(phi, rt, rw, vsh, rsh, a, m, n)
            return {"sw": sw, "model_used": "waxman_smits", "vsh": vsh,
                    "details": "Shaly sand model (Waxman-Smits 1968)"}

        elif method == "dual_water":
            sw = PetrophysicsEngine._dual_water_sw(phi, rt, rw, vsh, rsh, a, m, n)
            return {"sw": sw, "model_used": "dual_water", "vsh": vsh,
                    "details": "High-clay model (Clavier et al. 1984)"}

        else:
            return {"error": f"Unknown method: {method}"}

    @staticmethod
    def _archie_sw(phi: float, rt: float, rw: float, a: float, m: float, n: float) -> float:
        """Archie (1942): Sw = [(a * Rw) / (Rt * phi^m)]^(1/n)"""
        sw = ((a * rw) / (rt * (phi ** m))) ** (1.0 / n)
        return max(0.0, min(sw, 1.0))

    @staticmethod
    def _waxman_smits_sw(
        phi: float, rt: float, rw: float, vsh: float, rsh: float,
        a: float, m: float, n: float,
    ) -> float:
        """
        Waxman-Smits (1968): accounts for clay-bound water conductivity.

        Qv (CEC per unit pore volume) estimated from Vsh:
            Qv ≈ Vsh * rho_sh * CEC_sh / phi
        Simplified: Qv ≈ 0.6 * Vsh / phi (typical for Gulf Coast shales)

        1/Rt = Sw^n * phi^m / (a*Rw) + B*Qv*Sw^(n-1) * phi^m / a
        where B ≈ 4.6 * (1 - 0.6*exp(-0.77/Rw)) — equivalent conductance
        """
        qv = 0.6 * vsh / max(phi, 0.01)
        b_coeff = 4.6 * (1.0 - 0.6 * math.exp(-0.77 / max(rw, 0.001)))

        # Iterative solution: start with Archie as initial guess
        sw = PetrophysicsEngine._archie_sw(phi, rt, rw, a, m, n)

        for _ in range(20):
            # 1/Rt = Sw^n * phi^m/(a*Rw) + B*Qv*Sw^(n-1)*phi^m/a
            term1 = (sw ** n) * (phi ** m) / (a * rw)
            term2 = b_coeff * qv * (sw ** max(n - 1, 0.1)) * (phi ** m) / a
            rt_calc = 1.0 / max(term1 + term2, 1e-10)

            if abs(rt_calc - rt) < 0.01 * rt:
                break

            # Adjust Sw
            if rt_calc > rt:
                sw *= 1.02
            else:
                sw *= 0.98
            sw = max(0.01, min(sw, 1.0))

        return round(sw, 4)

    @staticmethod
    def _dual_water_sw(
        phi: float, rt: float, rw: float, vsh: float, rsh: float,
        a: float, m: float, n: float,
    ) -> float:
        """
        Dual-Water Model (Clavier et al., 1984).

        Distinguishes bound water (Swb) from free water (Swf).
        phi_t = phi_e + Vsh * phi_sh
        Ct = (phi_t^m / a) * [Swt^n * Cw + (Swb - Swt*Swb) * Cwb]

        Simplified iterative approach.
        """
        phi_sh = 0.30  # typical shale porosity
        phi_t = phi + vsh * phi_sh * (1.0 - phi)
        phi_t = max(0.01, min(phi_t, 0.50))

        swb = vsh * phi_sh / phi_t  # bound water saturation
        swb = min(swb, 0.99)

        cw = 1.0 / max(rw, 0.001)
        cwb = 1.0 / max(rsh * 0.3, 0.01)  # bound water conductivity
        ct = 1.0 / max(rt, 0.1)

        # Solve for Swt: Ct = (phi_t^m / a) * Swt^n * [Cw + (Swb/Swt)*(Cwb - Cw)]
        swt = PetrophysicsEngine._archie_sw(phi_t, rt, rw, a, m, n)

        for _ in range(30):
            if swt < 0.01:
                swt = 0.01
            cw_eff = cw + (swb / max(swt, 0.01)) * (cwb - cw)
            cw_eff = max(cw_eff, cw * 0.5)
            ct_calc = (phi_t ** m / a) * (swt ** n) * cw_eff

            if abs(ct_calc - ct) < 0.005 * ct:
                break

            ratio = (ct / max(ct_calc, 1e-10)) ** (1.0 / n)
            swt = swt * ratio
            swt = max(0.01, min(swt, 1.0))

        # Free water saturation
        sw_free = max(swt - swb, 0.0)

        return round(swt, 4)

    # ─────────────────────────────────────────────────────────────
    # Pickett Plot
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def generate_pickett_plot(
        log_data: List[Dict], rw: float = 0.05,
        a: float = 1.0, m: float = 2.0, n: float = 2.0,
    ) -> Dict[str, Any]:
        """
        Generate Pickett plot data (log10(Rt) vs log10(phi)).

        Includes iso-Sw lines for Sw = 0.2, 0.4, 0.6, 0.8, 1.0.

        Args:
            log_data: list of dicts with phi, rt, and optionally sw
            rw: formation water resistivity
            a, m, n: Archie parameters

        Returns:
            Dict with points, iso_sw_lines, regression
        """
        points = []
        for entry in log_data:
            phi = entry.get("phi", 0)
            rt = entry.get("rt", 0)
            if phi > 0.01 and rt > 0.1:
                points.append({
                    "phi": phi,
                    "rt": rt,
                    "log_phi": round(math.log10(phi), 4),
                    "log_rt": round(math.log10(rt), 4),
                    "sw": entry.get("sw"),
                })

        # Generate iso-Sw lines
        iso_sw_lines = {}
        phi_range = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40]
        for sw in [0.20, 0.40, 0.60, 0.80, 1.00]:
            line_points = []
            for phi in phi_range:
                # Rt = a * Rw / (phi^m * Sw^n)
                rt_val = a * rw / ((phi ** m) * (sw ** n))
                line_points.append({
                    "log_phi": round(math.log10(phi), 4),
                    "log_rt": round(math.log10(rt_val), 4),
                })
            iso_sw_lines[f"Sw={sw:.0%}"] = line_points

        # Simple linear regression on log-log for m estimation
        regression = {}
        if len(points) >= 3:
            x = [p["log_phi"] for p in points]
            y = [p["log_rt"] for p in points]
            n_pts = len(x)
            sum_x = sum(x)
            sum_y = sum(y)
            sum_xy = sum(xi * yi for xi, yi in zip(x, y))
            sum_xx = sum(xi ** 2 for xi in x)
            denom = n_pts * sum_xx - sum_x ** 2
            if abs(denom) > 1e-10:
                slope = (n_pts * sum_xy - sum_x * sum_y) / denom
                intercept = (sum_y - slope * sum_x) / n_pts
                regression = {
                    "slope": round(slope, 3),
                    "intercept": round(intercept, 3),
                    "estimated_m": round(-slope, 3),
                    "note": "Slope of Pickett plot ≈ -m (cementation exponent)",
                }

        return {
            "points": points,
            "iso_sw_lines": iso_sw_lines,
            "regression": regression,
        }

    # ─────────────────────────────────────────────────────────────
    # Density-Neutron Crossplot
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def crossplot_density_neutron(
        log_data: List[Dict],
        rho_fluid: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Generate Density-Neutron crossplot data with lithology lines.

        Args:
            log_data: list of dicts with rhob, nphi
            rho_fluid: fluid density (g/cc), default 1.0 for water

        Returns:
            Dict with data_points, lithology_lines, gas_flag zones
        """
        points = []
        for entry in log_data:
            rhob = entry.get("rhob", 0)
            nphi = entry.get("nphi", 0)
            if 1.5 < rhob < 3.2 and -0.05 < nphi < 0.60:
                # Compute density porosity
                rho_ma = 2.65  # assume sandstone
                phi_d = (rho_ma - rhob) / (rho_ma - rho_fluid)
                phi_d = max(0, min(phi_d, 0.50))

                # Gas flag: neutron reads low, density reads high porosity
                gas_flag = nphi < phi_d - 0.04

                points.append({
                    "rhob": round(rhob, 4),
                    "nphi": round(nphi, 4),
                    "phi_density": round(phi_d, 4),
                    "gas_flag": gas_flag,
                    "md": entry.get("md"),
                })

        # Lithology lines (matrix → fluid point)
        lithology_lines = {}
        for lith, params in PetrophysicsEngine.LITHOLOGY.items():
            lithology_lines[lith] = {
                "matrix_point": {"rhob": params["rho_ma"], "nphi": params["nphi_ma"]},
                "fluid_point": {"rhob": rho_fluid, "nphi": 1.0},
                "line": [
                    {"rhob": params["rho_ma"], "nphi": params["nphi_ma"]},
                    {"rhob": round(params["rho_ma"] * 0.6 + rho_fluid * 0.4, 3),
                     "nphi": round(params["nphi_ma"] * 0.6 + 0.4, 3)},
                ],
            }

        return {
            "points": points,
            "lithology_lines": lithology_lines,
            "gas_count": sum(1 for p in points if p["gas_flag"]),
            "total_points": len(points),
        }

    # ─────────────────────────────────────────────────────────────
    # Advanced Permeability
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def calculate_permeability_advanced(
        phi: float, sw_irr: float = 0.20, method: str = "timur",
    ) -> Dict[str, Any]:
        """
        Estimate permeability from porosity and irreducible water saturation.

        Methods:
        - Timur (1968): k = 8.58e4 * phi^4.4 / Sw_irr^2
        - Coates (1974): k = [(100*phi)^2 * (1-Sw_irr)/Sw_irr]^2 / 10000

        Args:
            phi: porosity (fractional)
            sw_irr: irreducible water saturation (fractional)
            method: "timur" or "coates"

        Returns:
            Dict with k_md, method, inputs
        """
        phi = max(0.01, min(phi, 0.50))
        sw_irr = max(0.05, min(sw_irr, 0.95))

        if method == "timur":
            k = 8.58e4 * (phi ** 4.4) / (sw_irr ** 2)
        elif method == "coates":
            k = ((100 * phi) ** 2 * (1 - sw_irr) / sw_irr) ** 2 / 10000
        else:
            return {"error": f"Unknown method: {method}"}

        return {
            "k_md": round(k, 2),
            "k_darcy": round(k / 1000, 4),
            "method": method,
            "phi": phi,
            "sw_irr": sw_irr,
            "quality": (
                "Excellent" if k > 1000 else
                "Good" if k > 100 else
                "Moderate" if k > 10 else
                "Poor" if k > 1 else
                "Tight"
            ),
        }

    # ─────────────────────────────────────────────────────────────
    # Full Petrophysical Evaluation
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def run_full_evaluation(
        log_data: List[Dict],
        archie_params: Optional[Dict] = None,
        matrix_params: Optional[Dict] = None,
        cutoffs: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Run complete petrophysical evaluation on log data.

        Computes Vsh, porosity, Sw (auto-model), permeability, net pay for each depth.

        Args:
            log_data: list of dicts with md, gr, rhob, nphi, rt (+ optional dt)
            archie_params: {a, m, n, rw}
            matrix_params: {rho_matrix, rho_fluid, gr_clean, gr_shale}
            cutoffs: {phi_min, sw_max, vsh_max}

        Returns:
            Dict with evaluated_data, summary, net_pay_intervals
        """
        ap = archie_params or {"a": 1.0, "m": 2.0, "n": 2.0, "rw": 0.05}
        mp = matrix_params or {"rho_matrix": 2.65, "rho_fluid": 1.0, "gr_clean": 20, "gr_shale": 120}
        co = cutoffs or {"phi_min": 0.08, "sw_max": 0.60, "vsh_max": 0.40}

        evaluated = []
        for entry in log_data:
            md = entry.get("md", 0)
            gr = entry.get("gr")
            rhob = entry.get("rhob")
            nphi = entry.get("nphi")
            rt = entry.get("rt")

            if gr is None or rhob is None or nphi is None or rt is None:
                continue

            # Vshale (linear)
            gr_range = mp["gr_shale"] - mp["gr_clean"]
            vsh = (gr - mp["gr_clean"]) / max(gr_range, 1) if gr_range > 0 else 0
            vsh = max(0.0, min(vsh, 1.0))

            # Porosity (density-neutron RMS crossplot)
            phi_d = (mp["rho_matrix"] - rhob) / (mp["rho_matrix"] - mp["rho_fluid"])
            phi_d = max(0.0, min(phi_d, 0.50))
            phi = math.sqrt((phi_d ** 2 + nphi ** 2) / 2)
            phi = max(0.0, min(phi, 0.50))

            # Effective porosity
            phi_e = phi * (1.0 - vsh)
            phi_e = max(0.0, phi_e)

            # Water saturation (auto-model)
            sw_result = PetrophysicsEngine.calculate_water_saturation_advanced(
                phi=max(phi_e, 0.01), rt=rt, rw=ap["rw"], vsh=vsh,
                rsh=2.0, a=ap["a"], m=ap["m"], n=ap["n"],
            )
            sw = sw_result.get("sw", 1.0)

            # Permeability
            sw_irr = min(sw, 0.50)
            perm = PetrophysicsEngine.calculate_permeability_advanced(phi_e, sw_irr, "timur")

            # Net pay flag
            is_pay = phi_e >= co["phi_min"] and sw <= co["sw_max"] and vsh <= co["vsh_max"]

            evaluated.append({
                "md": md,
                "gr": gr, "rhob": rhob, "nphi": nphi, "rt": rt,
                "vsh": round(vsh, 4),
                "phi_total": round(phi, 4),
                "phi_effective": round(phi_e, 4),
                "sw": round(sw, 4),
                "sw_model": sw_result.get("model_used", "archie"),
                "k_md": perm.get("k_md", 0),
                "is_pay": is_pay,
                "hc_saturation": round(1.0 - sw, 4),
            })

        # Identify net pay intervals
        intervals = PetrophysicsEngine._identify_intervals(evaluated, co)

        # Summary statistics
        pay_points = [e for e in evaluated if e["is_pay"]]
        summary = {
            "total_points": len(evaluated),
            "pay_points": len(pay_points),
            "net_pay_ft": round(len(pay_points) * 0.5, 1) if pay_points else 0,
            "avg_phi_pay": round(sum(p["phi_effective"] for p in pay_points) / len(pay_points), 4) if pay_points else 0,
            "avg_sw_pay": round(sum(p["sw"] for p in pay_points) / len(pay_points), 4) if pay_points else 0,
            "avg_perm_pay": round(sum(p["k_md"] for p in pay_points) / len(pay_points), 2) if pay_points else 0,
        }

        return {
            "evaluated_data": evaluated,
            "summary": summary,
            "intervals": intervals,
        }

    @staticmethod
    def _identify_intervals(evaluated: List[Dict], cutoffs: Dict) -> List[Dict]:
        """Group consecutive pay points into intervals."""
        intervals = []
        current = None

        for pt in evaluated:
            if pt["is_pay"]:
                if current is None:
                    current = {
                        "top_md": pt["md"],
                        "base_md": pt["md"],
                        "points": [pt],
                    }
                else:
                    current["base_md"] = pt["md"]
                    current["points"].append(pt)
            else:
                if current is not None:
                    thickness = current["base_md"] - current["top_md"]
                    if thickness >= cutoffs.get("min_thickness_ft", 0):
                        pts = current["points"]
                        intervals.append({
                            "top_md": current["top_md"],
                            "base_md": current["base_md"],
                            "thickness_ft": round(thickness, 1),
                            "avg_phi": round(sum(p["phi_effective"] for p in pts) / len(pts), 4),
                            "avg_sw": round(sum(p["sw"] for p in pts) / len(pts), 4),
                            "avg_perm_md": round(sum(p["k_md"] for p in pts) / len(pts), 2),
                        })
                    current = None

        # Close last interval
        if current is not None:
            thickness = current["base_md"] - current["top_md"]
            pts = current["points"]
            if thickness >= cutoffs.get("min_thickness_ft", 0):
                intervals.append({
                    "top_md": current["top_md"],
                    "base_md": current["base_md"],
                    "thickness_ft": round(thickness, 1),
                    "avg_phi": round(sum(p["phi_effective"] for p in pts) / len(pts), 4),
                    "avg_sw": round(sum(p["sw"] for p in pts) / len(pts), 4),
                    "avg_perm_md": round(sum(p["k_md"] for p in pts) / len(pts), 2),
                })

        return intervals
