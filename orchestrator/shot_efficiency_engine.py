"""
Shot Efficiency Calculation Engine

Connects petrophysical log data with perforation design to recommend
optimal shooting intervals and estimate post-shot skin damage.

Elite enhancements (Phase 7):
- Shaly-sand Sw: Simandoux (1963), Indonesia/Poupon-Leveaux (1971)
- Permeability from logs: Timur (1968), Coates-Dumanoir
- Sonic porosity: Wyllie, Raymer-Hunt-Gardner
- LAS 2.0 parser: read log files directly
- HC typing: density-neutron separation, MHI, BVW crossplots
- Karakas-Tariq deduplication: delegate to CompletionDesignEngine

References:
- Archie (1942): Formation factor and water saturation
- Simandoux (1963): Shaly-sand water saturation model
- Poupon & Leveaux (1971): Indonesia Sw model for high Vsh
- Timur (1968): Permeability from logs (phi, Swirr)
- Coates & Dumanoir (1974): Permeability estimation
- Wyllie et al. (1956): Time-average sonic porosity
- Raymer, Hunt & Gardner (1980): Improved sonic porosity
- Larionov (1969): Vshale correction for Tertiary formations
- Karakas & Tariq (1991): Semi-analytical perforation skin model
- Standard petrophysical cutoffs (SPE/AAPG)
"""
import math
import os
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

    # ─────────────────────────────────────────────────────────────
    # Phase 7 Elite: Shaly-Sand Sw Models
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def calculate_sw_simandoux(
        rt: float,
        porosity: float,
        rw: float = 0.05,
        vsh: float = 0.0,
        rsh: float = 5.0,
        a: float = 1.0,
        m: float = 2.0,
        n: float = 2.0
    ) -> Dict[str, Any]:
        """
        Simandoux (1963) shaly-sand water saturation model.

        1/Rt = Sw^n × phi^m / (a × Rw) + Vsh × Sw / Rsh

        Solves quadratic for Sw (linearized for n=2):
        Rearranged: (phi^m/(a×Rw))×Sw^2 + (Vsh/Rsh)×Sw - 1/Rt = 0

        Args:
            rt: true resistivity (ohm-m)
            porosity: total porosity (v/v)
            rw: water resistivity (ohm-m)
            vsh: volume of shale (v/v)
            rsh: shale resistivity (ohm-m)
            a, m, n: Archie parameters

        Returns:
            Dict with sw, method, comparison with Archie
        """
        if porosity <= 0 or rt <= 0 or rw <= 0:
            return {"sw": 1.0, "method": "simandoux",
                    "hydrocarbon_saturation": 0.0, "classification": "Non-reservoir"}

        # Quadratic coefficients (for n≈2): A×Sw² + B×Sw + C = 0
        A_coeff = (porosity ** m) / (a * rw)
        B_coeff = vsh / rsh if rsh > 0 else 0.0
        C_coeff = -1.0 / rt

        # Solve quadratic: Sw = (-B + sqrt(B² - 4AC)) / (2A)
        discriminant = B_coeff ** 2 - 4.0 * A_coeff * C_coeff
        if discriminant < 0 or A_coeff <= 0:
            sw = 1.0
        else:
            sw = (-B_coeff + math.sqrt(discriminant)) / (2.0 * A_coeff)

        sw = max(0.0, min(sw, 1.0))

        # Archie comparison
        sw_archie = ((a * rw) / (rt * porosity ** m)) ** (1.0 / n)
        sw_archie = max(0.0, min(sw_archie, 1.0))

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
            "hydrocarbon_saturation": round(1.0 - sw, 4),
            "classification": classification,
            "sw_archie": round(sw_archie, 4),
            "sw_difference": round(sw - sw_archie, 4),
            "vsh_used": round(vsh, 4),
            "method": "simandoux",
        }

    @staticmethod
    def calculate_sw_indonesia(
        rt: float,
        porosity: float,
        rw: float = 0.05,
        vsh: float = 0.0,
        rsh: float = 5.0,
        a: float = 1.0,
        m: float = 2.0,
        n: float = 2.0
    ) -> Dict[str, Any]:
        """
        Indonesia / Poupon-Leveaux (1971) shaly-sand Sw model.

        1/sqrt(Rt) = sqrt(phi^m/(a×Rw)) × Sw^(n/2) + Vsh^(1-Vsh/2)/sqrt(Rsh) × Sw

        Better for high-Vsh formations (>30%). Iterative solution.

        Args:
            rt: true resistivity (ohm-m)
            porosity: total porosity (v/v)
            rw: water resistivity (ohm-m)
            vsh: volume of shale (v/v)
            rsh: shale resistivity (ohm-m)
            a, m, n: Archie parameters

        Returns:
            Dict with sw, method, iterations
        """
        if porosity <= 0 or rt <= 0 or rw <= 0:
            return {"sw": 1.0, "method": "indonesia",
                    "hydrocarbon_saturation": 0.0, "classification": "Non-reservoir"}

        # Target: 1/sqrt(Rt)
        target = 1.0 / math.sqrt(rt)

        # Clean-sand term coefficient
        clean_coeff = math.sqrt(porosity ** m / (a * rw))
        # Shale term coefficient
        vsh_exp = max(0.0, 1.0 - vsh / 2.0)
        shale_coeff = (vsh ** vsh_exp) / math.sqrt(rsh) if rsh > 0 else 0.0

        # Iterative: F(Sw) = clean_coeff × Sw^(n/2) + shale_coeff × Sw - target = 0
        # Newton-Raphson
        sw = 0.5  # initial guess
        for iteration in range(20):
            f = clean_coeff * sw ** (n / 2.0) + shale_coeff * sw - target
            df = clean_coeff * (n / 2.0) * sw ** (n / 2.0 - 1.0) + shale_coeff if sw > 0 else shale_coeff + 1.0
            if abs(df) < 1e-15:
                break
            sw_new = sw - f / df
            sw_new = max(0.01, min(sw_new, 1.0))
            if abs(sw_new - sw) < 1e-6:
                sw = sw_new
                break
            sw = sw_new

        sw = max(0.0, min(sw, 1.0))

        # Archie comparison
        sw_archie = ((a * rw) / (rt * porosity ** m)) ** (1.0 / n)
        sw_archie = max(0.0, min(sw_archie, 1.0))

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
            "hydrocarbon_saturation": round(1.0 - sw, 4),
            "classification": classification,
            "sw_archie": round(sw_archie, 4),
            "sw_difference": round(sw - sw_archie, 4),
            "vsh_used": round(vsh, 4),
            "method": "indonesia",
        }

    @staticmethod
    def calculate_sw_auto(
        rt: float,
        porosity: float,
        rw: float = 0.05,
        vsh: float = 0.0,
        rsh: float = 5.0,
        a: float = 1.0,
        m: float = 2.0,
        n: float = 2.0
    ) -> Dict[str, Any]:
        """
        Auto-select Sw model based on Vsh content.

        - Vsh < 0.15: Archie (clean sand)
        - 0.15 <= Vsh < 0.40: Simandoux
        - Vsh >= 0.40: Indonesia (Poupon-Leveaux)

        Returns:
            Dict with sw, method selected, selection_reason
        """
        eng = ShotEfficiencyEngine

        if vsh < 0.15:
            result = eng.calculate_water_saturation(rt, porosity, rw, a, m, n)
            result["method"] = "archie"
            result["selection_reason"] = f"Vsh={vsh:.3f} < 0.15 → clean sand (Archie)"
        elif vsh < 0.40:
            result = eng.calculate_sw_simandoux(rt, porosity, rw, vsh, rsh, a, m, n)
            result["selection_reason"] = f"0.15 <= Vsh={vsh:.3f} < 0.40 → moderately shaly (Simandoux)"
        else:
            result = eng.calculate_sw_indonesia(rt, porosity, rw, vsh, rsh, a, m, n)
            result["selection_reason"] = f"Vsh={vsh:.3f} >= 0.40 → highly shaly (Indonesia)"

        return result

    # ─────────────────────────────────────────────────────────────
    # Phase 7 Elite: Permeability from Logs
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def calculate_permeability_timur(
        porosity: float,
        sw_irreducible: float
    ) -> Dict[str, Any]:
        """
        Timur (1968) permeability from porosity and irreducible Sw.

        k = 0.136 × phi^4.4 / Swirr^2  (mD)

        Best for sandstones.

        Args:
            porosity: total porosity (v/v fraction)
            sw_irreducible: irreducible water saturation (v/v fraction)

        Returns:
            Dict with k_md, method
        """
        if porosity <= 0 or sw_irreducible <= 0:
            return {"k_md": 0.0, "method": "timur",
                    "note": "Invalid inputs — zero permeability"}

        # Timur formula (phi in fraction)
        k = 0.136 * (porosity ** 4.4) / (sw_irreducible ** 2)
        # Convert: original formula uses phi in %, so scale
        # Actually Timur (1968) with phi in fraction: k = 8.58e4 * phi^4.4 / Swirr^2
        k = 8.58e4 * (porosity ** 4.4) / (sw_irreducible ** 2)

        # Classify
        if k > 1000:
            perm_class = "Very High"
        elif k > 100:
            perm_class = "High"
        elif k > 10:
            perm_class = "Moderate"
        elif k > 1:
            perm_class = "Low"
        else:
            perm_class = "Very Low / Tight"

        return {
            "k_md": round(k, 3),
            "perm_class": perm_class,
            "porosity": round(porosity, 4),
            "sw_irreducible": round(sw_irreducible, 4),
            "method": "timur",
        }

    @staticmethod
    def calculate_permeability_coates(
        porosity: float,
        sw_irreducible: float
    ) -> Dict[str, Any]:
        """
        Coates-Dumanoir permeability estimation.

        k = [(100×phi)^2 × (1-Swirr)/Swirr]^2 / 10000  (mD)

        Good for carbonates and mixed lithologies.

        Args:
            porosity: total porosity (v/v fraction)
            sw_irreducible: irreducible water saturation (v/v fraction)

        Returns:
            Dict with k_md, method
        """
        if porosity <= 0 or sw_irreducible <= 0 or sw_irreducible >= 1.0:
            return {"k_md": 0.0, "method": "coates",
                    "note": "Invalid inputs — zero permeability"}

        ratio = (1.0 - sw_irreducible) / sw_irreducible
        k = ((100.0 * porosity) ** 2 * ratio) ** 2 / 10000.0

        if k > 1000:
            perm_class = "Very High"
        elif k > 100:
            perm_class = "High"
        elif k > 10:
            perm_class = "Moderate"
        elif k > 1:
            perm_class = "Low"
        else:
            perm_class = "Very Low / Tight"

        return {
            "k_md": round(k, 3),
            "perm_class": perm_class,
            "porosity": round(porosity, 4),
            "sw_irreducible": round(sw_irreducible, 4),
            "method": "coates",
        }

    # ─────────────────────────────────────────────────────────────
    # Phase 7 Elite: Sonic Porosity
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def calculate_porosity_sonic(
        dt_log: float,
        dt_matrix: float = 55.5,
        dt_fluid: float = 189.0,
        method: str = "raymer"
    ) -> Dict[str, Any]:
        """
        Sonic porosity from compressional slowness log.

        Wyllie: phi = (DT_log - DT_ma) / (DT_fl - DT_ma)
        Raymer-Hunt-Gardner: phi = 0.625 × (DT_log - DT_ma) / DT_log

        Typical DT_matrix values:
        - Sandstone: 55.5 us/ft
        - Limestone: 47.5 us/ft
        - Dolomite: 43.5 us/ft

        Args:
            dt_log: interval transit time from log (us/ft)
            dt_matrix: matrix transit time (us/ft)
            dt_fluid: fluid transit time (us/ft), ~189 freshwater
            method: "wyllie" or "raymer" (default)

        Returns:
            Dict with phi_sonic, method used
        """
        if dt_log <= 0 or dt_matrix <= 0:
            return {"phi_sonic": 0.0, "method": method,
                    "note": "Invalid DT values"}

        if method.lower() == "wyllie":
            denom = dt_fluid - dt_matrix
            if denom <= 0:
                return {"phi_sonic": 0.0, "method": "wyllie",
                        "note": "DT_fluid must be > DT_matrix"}
            phi = (dt_log - dt_matrix) / denom
        else:
            # Raymer-Hunt-Gardner (empirical, preferred)
            if dt_log <= 0:
                phi = 0.0
            else:
                phi = 0.625 * (dt_log - dt_matrix) / dt_log

        phi = max(0.0, min(phi, 0.50))

        return {
            "phi_sonic": round(phi, 4),
            "dt_log": dt_log,
            "dt_matrix": dt_matrix,
            "dt_fluid": dt_fluid,
            "method": f"sonic_{method.lower()}",
        }

    # ─────────────────────────────────────────────────────────────
    # Phase 7 Elite: LAS 2.0 Parser
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def parse_las_file(file_path: str) -> Dict[str, Any]:
        """
        Parse LAS 2.0 file and extract well info + curve data.

        Recognizes common mnemonics: GR, RHOB, NPHI, RT/ILD/LLD, DT, CALI, SP, DEPT

        Args:
            file_path: path to .las file

        Returns:
            Dict with well_info, curve_info, data as list of dicts, curve_mapping
        """
        if not os.path.exists(file_path):
            return {"error": f"File not found: {file_path}"}

        try:
            with open(file_path, 'r', errors='replace') as f:
                lines = f.readlines()
        except Exception as e:
            return {"error": f"Cannot read file: {str(e)}"}

        well_info = {}
        curve_info = []
        curve_names = []
        data_rows = []
        current_section = None
        null_value = -999.25

        # Common mnemonic mapping
        mnemonic_map = {
            "DEPT": "md", "DEPTH": "md", "MD": "md",
            "GR": "gr", "SGR": "gr", "CGR": "gr",
            "RHOB": "rhob", "RHOZ": "rhob", "DEN": "rhob", "DENSITY": "rhob",
            "NPHI": "nphi", "TNPH": "nphi", "PHIN": "nphi", "NEU": "nphi",
            "RT": "rt", "ILD": "rt", "LLD": "rt", "MSFL": "rt", "RILM": "rt",
            "RESD": "rt", "RD": "rt", "AT90": "rt",
            "DT": "dt", "DTC": "dt", "DTCO": "dt", "SONIC": "dt",
            "CALI": "caliper", "CAL": "caliper", "HCAL": "caliper",
            "SP": "sp",
        }

        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            # Section headers
            if line.startswith('~W'):
                current_section = 'well'
                continue
            elif line.startswith('~C'):
                current_section = 'curve'
                continue
            elif line.startswith('~A'):
                current_section = 'data'
                continue
            elif line.startswith('~V'):
                current_section = 'version'
                continue
            elif line.startswith('~P'):
                current_section = 'parameter'
                continue
            elif line.startswith('~O'):
                current_section = 'other'
                continue

            if current_section == 'well':
                # Parse well header: MNEM.UNIT VALUE : DESCRIPTION
                if '.' in line:
                    parts = line.split('.', 1)
                    mnem = parts[0].strip()
                    rest = parts[1] if len(parts) > 1 else ""
                    if ':' in rest:
                        val_part, desc = rest.rsplit(':', 1)
                    else:
                        val_part, desc = rest, ""
                    # Extract unit and value
                    val_parts = val_part.strip().split(None, 1)
                    unit = val_parts[0] if val_parts else ""
                    value = val_parts[1].strip() if len(val_parts) > 1 else unit
                    well_info[mnem] = {"value": value, "unit": unit, "description": desc.strip()}
                    if mnem == "NULL":
                        try:
                            null_value = float(value)
                        except ValueError:
                            pass

            elif current_section == 'curve':
                # Parse curve info
                if '.' in line:
                    parts = line.split('.', 1)
                    mnem = parts[0].strip().upper()
                    rest = parts[1] if len(parts) > 1 else ""
                    if ':' in rest:
                        unit_val, desc = rest.rsplit(':', 1)
                    else:
                        unit_val, desc = rest, ""
                    unit = unit_val.strip().split()[0] if unit_val.strip() else ""
                    curve_names.append(mnem)
                    mapped = mnemonic_map.get(mnem, mnem.lower())
                    curve_info.append({
                        "mnemonic": mnem,
                        "unit": unit,
                        "description": desc.strip(),
                        "mapped_to": mapped,
                    })

            elif current_section == 'data':
                # Parse data values
                values = line.split()
                if len(values) == len(curve_names):
                    row = {}
                    for ci, val_str in zip(curve_info, values):
                        try:
                            val = float(val_str)
                            if abs(val - null_value) < 0.01:
                                val = None
                            row[ci["mapped_to"]] = val
                        except ValueError:
                            row[ci["mapped_to"]] = None
                    data_rows.append(row)

        # Build curve_mapping summary
        curve_mapping = {}
        for ci in curve_info:
            curve_mapping[ci["mnemonic"]] = ci["mapped_to"]

        return {
            "well_info": well_info,
            "curve_info": curve_info,
            "curve_mapping": curve_mapping,
            "data": data_rows,
            "data_points": len(data_rows),
            "curves_found": [ci["mnemonic"] for ci in curve_info],
            "null_value": null_value,
            "file_path": file_path,
        }

    # ─────────────────────────────────────────────────────────────
    # Phase 7 Elite: HC Typing
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def classify_hydrocarbon_type(
        phi_density: float,
        phi_neutron: float,
        rt: float,
        rxo: float = 0.0,
        sw: float = 0.5,
        sxo: float = 0.7
    ) -> Dict[str, Any]:
        """
        Discriminate oil vs gas vs water using crossplot indicators.

        Key indicators:
        - Density-neutron separation: gas pulls neutron left, density right
        - Moveable HC Index (MHI): phi × (1 - Sw/Sxo)
        - Bulk Volume Water (BVW): phi × Sw

        Args:
            phi_density: density-derived porosity (v/v)
            phi_neutron: neutron porosity (v/v)
            rt: deep resistivity (ohm-m)
            rxo: shallow/flushed resistivity (ohm-m), 0 = not available
            sw: water saturation (v/v)
            sxo: flushed zone water saturation (v/v)

        Returns:
            Dict with type classification, confidence, MHI, BVW
        """
        phi_avg = (phi_density + phi_neutron) / 2.0 if (phi_density + phi_neutron) > 0 else 0.01

        # Density-neutron separation (gas effect)
        dn_separation = phi_density - phi_neutron

        # MHI: Moveable Hydrocarbon Index
        if sxo > 0 and phi_avg > 0:
            MHI = phi_avg * (1.0 - sw / sxo) if sw <= sxo else 0.0
        else:
            MHI = 0.0
        MHI = max(0.0, MHI)

        # BVW: Bulk Volume Water
        BVW = phi_avg * sw

        # Classification logic
        confidence = 0.0
        hc_type = "water"

        if sw > 0.80:
            hc_type = "water"
            confidence = min(1.0, sw)
        elif dn_separation > 0.04 and phi_neutron < phi_density:
            # Gas: neutron reads lower than density (gas pulls neutron down)
            hc_type = "gas"
            confidence = min(1.0, dn_separation / 0.10)
            if sw < 0.40:
                confidence = min(1.0, confidence + 0.2)
        elif sw < 0.60:
            hc_type = "oil"
            confidence = min(1.0, (0.60 - sw) / 0.40 + 0.3)
            if MHI > 0.02:
                confidence = min(1.0, confidence + 0.15)
        else:
            hc_type = "water_with_hc"
            confidence = 0.5

        # Resistivity ratio check (if Rxo available)
        if rxo > 0 and rt > 0:
            ri_ratio = rt / rxo
            if ri_ratio > 2.0 and hc_type in ("oil", "gas"):
                confidence = min(1.0, confidence + 0.1)

        return {
            "type": hc_type,
            "confidence": round(confidence, 3),
            "MHI": round(MHI, 4),
            "BVW": round(BVW, 4),
            "dn_separation": round(dn_separation, 4),
            "phi_density": round(phi_density, 4),
            "phi_neutron": round(phi_neutron, 4),
            "sw": round(sw, 4),
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
                + w_skin * (1/(1+|skin|)) [+ w_kh * kh_norm if available]

        Default weights: phi=0.30, sw=0.25, thickness=0.20, skin=0.10, kh=0.15

        Args:
            intervals: list of interval dicts with avg_phi, avg_sw, thickness_ft, skin_total
                       optionally: k_md, kh_md (from permeability estimation)
            weights: optional dict overriding default weights

        Returns:
            Dict with ranked list and best interval
        """
        if not intervals:
            return {"ranked": [], "best": None}

        has_kh = any("kh_md_ft" in iv or "k_md" in iv for iv in intervals)

        if has_kh:
            w = weights or {"phi": 0.25, "sw": 0.20, "thickness": 0.15, "skin": 0.10, "kh": 0.30}
        else:
            w = weights or {"phi": 0.35, "sw": 0.25, "thickness": 0.25, "skin": 0.15}

        phis = [iv["avg_phi"] for iv in intervals]
        sws = [iv["avg_sw"] for iv in intervals]
        thicks = [iv["thickness_ft"] for iv in intervals]

        def _norm(val, lo, hi):
            return (val - lo) / (hi - lo) if hi != lo else 1.0

        phi_lo, phi_hi = min(phis), max(phis)
        sw_lo, sw_hi = min(sws), max(sws)
        th_lo, th_hi = min(thicks), max(thicks)

        kh_lo, kh_hi = 0.0, 1.0
        if has_kh:
            kh_values = [iv.get("kh_md_ft", iv.get("k_md", 0) * iv.get("thickness_ft", 1)) for iv in intervals]
            kh_lo = min(kh_values) if kh_values else 0.0
            kh_hi = max(kh_values) if kh_values else 1.0

        scored = []
        for iv in intervals:
            phi_n = _norm(iv["avg_phi"], phi_lo, phi_hi)
            sw_n = _norm(iv["avg_sw"], sw_lo, sw_hi)
            th_n = _norm(iv["thickness_ft"], th_lo, th_hi)
            sk_factor = 1.0 / (1.0 + abs(iv.get("skin_total", 0.0)))

            score = (w.get("phi", 0.35) * phi_n + w.get("sw", 0.25) * (1.0 - sw_n)
                     + w.get("thickness", 0.25) * th_n + w.get("skin", 0.15) * sk_factor)

            if has_kh and "kh" in w:
                kh_val = iv.get("kh_md_ft", iv.get("k_md", 0) * iv.get("thickness_ft", 1))
                kh_n = _norm(kh_val, kh_lo, kh_hi)
                score += w["kh"] * kh_n

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
        reservoir_params: Optional[Dict[str, float]] = None,
        sw_model: str = "auto",
        rsh: float = 5.0,
        estimate_permeability: bool = False,
        sw_irreducible: float = 0.25
    ) -> Dict[str, Any]:
        """
        Full integrated shot-efficiency analysis pipeline.

        1. Parse and validate log data
        2. Compute porosity, Sw (auto/archie/simandoux/indonesia), Vshale per point
        3. Optionally estimate permeability (Timur) and compute kh
        4. Identify net pay intervals
        5. Calculate Karakas-Tariq skin per interval
        6. Classify HC type per interval
        7. Rank intervals by composite score (with kh if available)
        8. Compile summary with alerts

        Args:
            log_entries: raw log measurements
            archie_params: {a, m, n, rw}
            matrix_params: {rho_matrix, rho_fluid, gr_clean, gr_shale}
            cutoffs: {phi_min, sw_max, vsh_max, min_thickness_ft}
            perf_params: {spf, phasing_deg, perf_length_in, tunnel_radius_in}
            reservoir_params: {k_h, kv_kh, wellbore_radius_ft}
            sw_model: "auto", "archie", "simandoux", "indonesia" (default auto)
            rsh: shale resistivity for shaly-sand models (ohm-m)
            estimate_permeability: if True, estimate k from Timur and include kh in ranking
            sw_irreducible: irreducible Sw for permeability estimation (v/v)

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

        # Step 2: Compute petrophysics with selected Sw model
        processed = []
        for pt in accepted:
            por = eng.calculate_porosity(pt["rhob"], pt["nphi"], rho_matrix, rho_fluid)
            vsh_res = eng.calculate_vshale(pt["gr"], gr_clean, gr_shale)
            phi_val = por.get("phi", 0.0)
            vsh_val = vsh_res.get("vsh", 1.0)

            # Sw model selection
            if sw_model == "auto":
                sw_res = eng.calculate_sw_auto(pt["rt"], phi_val, rw, vsh_val, rsh, a, m, n)
            elif sw_model == "simandoux":
                sw_res = eng.calculate_sw_simandoux(pt["rt"], phi_val, rw, vsh_val, rsh, a, m, n)
            elif sw_model == "indonesia":
                sw_res = eng.calculate_sw_indonesia(pt["rt"], phi_val, rw, vsh_val, rsh, a, m, n)
            else:
                sw_res = eng.calculate_water_saturation(pt["rt"], phi_val, rw, a, m, n)

            row = {
                "md": pt["md"], "gr": pt["gr"], "rhob": pt["rhob"],
                "nphi": pt["nphi"], "rt": pt["rt"],
                "phi": phi_val,
                "phi_density": por.get("phi_density", 0.0),
                "phi_neutron": por.get("phi_neutron", 0.0),
                "sw": sw_res.get("sw", 1.0),
                "hydrocarbon_saturation": sw_res.get("hydrocarbon_saturation", 0.0),
                "sw_class": sw_res.get("classification", ""),
                "sw_model": sw_res.get("method", "archie"),
                "vsh": vsh_val,
                "igr": vsh_res.get("igr", 1.0),
            }

            # Permeability estimation
            if estimate_permeability and phi_val > 0 and sw_irreducible > 0:
                k_res = eng.calculate_permeability_timur(phi_val, sw_irreducible)
                row["k_md"] = k_res.get("k_md", 0.0)

            # HC type classification
            hc_res = eng.classify_hydrocarbon_type(
                por.get("phi_density", 0.0), por.get("phi_neutron", 0.0),
                pt["rt"], 0.0, sw_res.get("sw", 1.0), 0.7
            )
            row["hc_type"] = hc_res.get("type", "water")

            processed.append(row)

        # Step 3: Identify net pay
        net_pay = eng.identify_net_pay_intervals(processed, phi_min, sw_max, vsh_max, min_thick)
        intervals = net_pay["intervals"]

        # Step 4: Calculate skin per interval + add kh if permeability estimated
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

            # Aggregate kh per interval
            if estimate_permeability:
                interval_pts = [p for p in processed
                                if iv["top_md"] <= p["md"] <= iv["base_md"] and "k_md" in p]
                if interval_pts:
                    avg_k = sum(p["k_md"] for p in interval_pts) / len(interval_pts)
                    iv["k_md"] = round(avg_k, 3)
                    iv["kh_md_ft"] = round(avg_k * iv["thickness_ft"], 1)

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
            "sw_model_used": sw_model,
            "permeability_estimated": estimate_permeability,
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
                "sw_model": sw_model,
                "rsh": rsh,
                "estimate_permeability": estimate_permeability,
                "sw_irreducible": sw_irreducible,
            },
            "alerts": alerts,
        }
