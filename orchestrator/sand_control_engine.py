"""
Sand Control Calculation Engine

Grain size analysis, gravel pack design, screen selection, critical drawdown,
and completion type evaluation for sand control applications.

References:
- Penberthy & Shaughnessy: Sand Control (SPE Series)
- Saucier (1974): Gravel sizing criteria
- API RP 19C: Procedures for Testing Sand Control Screens
- Mohr-Coulomb failure criterion for sanding prediction
"""
import math
from typing import List, Dict, Any, Optional


class SandControlEngine:
    """
    Implements sand control engineering calculations.
    All methods are @staticmethod — no external dependencies beyond math.
    """

    # Standard sieve sizes (mm) for PSD analysis
    SIEVE_SIZES_MM = [4.75, 2.0, 0.85, 0.425, 0.25, 0.15, 0.075, 0.045]

    # Gravel pack factor (1.3-1.5x annular volume)
    DEFAULT_PACK_FACTOR = 1.4

    @staticmethod
    def analyze_grain_distribution(
        sieve_sizes_mm: List[float],
        cumulative_passing_pct: List[float]
    ) -> Dict[str, Any]:
        """
        Analyze particle/grain size distribution from sieve analysis.

        Uses linear interpolation on cumulative passing curve to determine
        D10, D40, D50, D60, D90 and uniformity coefficient.

        Args:
            sieve_sizes_mm: sieve opening sizes in mm (descending order)
            cumulative_passing_pct: cumulative weight % passing each sieve

        Returns:
            Dict with D10, D40, D50, D60, D90, Cu, sorting description
        """
        if len(sieve_sizes_mm) < 3 or len(sieve_sizes_mm) != len(cumulative_passing_pct):
            return {"error": "Insufficient or mismatched sieve data"}

        # Ensure data is in descending sieve size order
        paired = sorted(zip(sieve_sizes_mm, cumulative_passing_pct), reverse=True)
        sizes = [p[0] for p in paired]
        passing = [p[1] for p in paired]

        def interpolate_d(target_pct: float) -> float:
            """Interpolate grain size at a given cumulative passing percentage."""
            for i in range(len(passing) - 1):
                if (passing[i] <= target_pct <= passing[i + 1]) or \
                   (passing[i] >= target_pct >= passing[i + 1]):
                    # Linear interpolation on log scale
                    if passing[i + 1] == passing[i]:
                        return sizes[i]
                    ratio = (target_pct - passing[i]) / (passing[i + 1] - passing[i])
                    if sizes[i] > 0 and sizes[i + 1] > 0:
                        log_d = math.log10(sizes[i]) + ratio * (math.log10(sizes[i + 1]) - math.log10(sizes[i]))
                        return 10 ** log_d
                    return sizes[i] + ratio * (sizes[i + 1] - sizes[i])
            # Extrapolate if outside range
            if target_pct <= min(passing):
                return max(sizes)
            return min(sizes)

        d10 = interpolate_d(10.0)
        d40 = interpolate_d(40.0)
        d50 = interpolate_d(50.0)
        d60 = interpolate_d(60.0)
        d90 = interpolate_d(90.0)

        # Uniformity coefficient (Hazen)
        cu = d60 / d10 if d10 > 0 else 0.0

        # Sorting classification
        if cu < 2:
            sorting = "Very Well Sorted"
        elif cu < 3:
            sorting = "Well Sorted"
        elif cu < 5:
            sorting = "Moderately Sorted"
        elif cu < 10:
            sorting = "Poorly Sorted"
        else:
            sorting = "Very Poorly Sorted"

        return {
            "d10_mm": round(d10, 4),
            "d40_mm": round(d40, 4),
            "d50_mm": round(d50, 4),
            "d60_mm": round(d60, 4),
            "d90_mm": round(d90, 4),
            "uniformity_coefficient": round(cu, 2),
            "sorting": sorting,
            "sieve_count": len(sieve_sizes_mm)
        }

    @staticmethod
    def select_gravel_size(
        d50_mm: float,
        d10_mm: float,
        d90_mm: float,
        uniformity_coefficient: float
    ) -> Dict[str, Any]:
        """
        Select optimal gravel size using Saucier criterion.

        Saucier (1974): D_gravel = 5-6 × D50 of formation sand.
        For poorly sorted sands, use D40 instead of D50.

        Args:
            d50_mm: median grain size (mm)
            d10_mm: 10th percentile grain size (mm)
            d90_mm: 90th percentile grain size (mm)
            uniformity_coefficient: Cu = D60/D10

        Returns:
            Dict with recommended gravel size range and standard mesh sizes
        """
        # Saucier criterion
        if uniformity_coefficient > 5:
            # Poorly sorted: use more conservative sizing
            reference_d = (d50_mm + d10_mm) / 2.0  # conservative
            multiplier_low = 5.0
            multiplier_high = 6.0
        else:
            reference_d = d50_mm
            multiplier_low = 5.0
            multiplier_high = 6.0

        gravel_min_mm = reference_d * multiplier_low
        gravel_max_mm = reference_d * multiplier_high

        # Map to standard mesh sizes
        # Common gravel packs: 20/40, 40/60, 16/30, 12/20
        standard_packs = [
            {"name": "12/20", "min_mm": 0.85, "max_mm": 1.70},
            {"name": "16/30", "min_mm": 0.60, "max_mm": 1.18},
            {"name": "20/40", "min_mm": 0.425, "max_mm": 0.85},
            {"name": "40/60", "min_mm": 0.25, "max_mm": 0.425},
            {"name": "50/70", "min_mm": 0.212, "max_mm": 0.30},
        ]

        recommended_pack = "Custom"
        for pack in standard_packs:
            if pack["min_mm"] <= gravel_min_mm <= pack["max_mm"] or \
               pack["min_mm"] <= gravel_max_mm <= pack["max_mm"]:
                recommended_pack = pack["name"]
                break

        # If no overlap, find closest
        if recommended_pack == "Custom":
            target_mid = (gravel_min_mm + gravel_max_mm) / 2.0
            best_diff = float('inf')
            for pack in standard_packs:
                mid = (pack["min_mm"] + pack["max_mm"]) / 2.0
                diff = abs(mid - target_mid)
                if diff < best_diff:
                    best_diff = diff
                    recommended_pack = pack["name"]

        return {
            "gravel_min_mm": round(gravel_min_mm, 3),
            "gravel_max_mm": round(gravel_max_mm, 3),
            "recommended_pack": recommended_pack,
            "saucier_multiplier_low": multiplier_low,
            "saucier_multiplier_high": multiplier_high,
            "reference_d_mm": round(reference_d, 4),
            "criterion": "Saucier (1974)"
        }

    @staticmethod
    def select_screen_slot(
        d10_mm: float,
        d50_mm: float,
        screen_type: str = "wire_wrap"
    ) -> Dict[str, Any]:
        """
        Select screen slot size based on grain size distribution.

        Wire wrap: slot ≈ 2 × D10 (retains 90% of formation sand)
        Premium mesh: slot ≈ D10

        Args:
            d10_mm: 10th percentile grain size (mm)
            d50_mm: 50th percentile grain size (mm)
            screen_type: 'wire_wrap' or 'premium_mesh'

        Returns:
            Dict with slot_size_mm, slot_size_inches, gauge
        """
        if screen_type == "premium_mesh":
            slot_mm = d10_mm
        else:  # wire_wrap
            slot_mm = 2.0 * d10_mm

        # Convert to thousandths of an inch (gauge)
        slot_in = slot_mm / 25.4
        gauge = round(slot_in * 1000, 0)

        # Standard slot sizes
        standard_slots = [0.006, 0.008, 0.010, 0.012, 0.015, 0.018, 0.020, 0.025, 0.030]
        closest_slot = min(standard_slots, key=lambda s: abs(s - slot_in))

        retention_estimate = 90.0 if screen_type == "wire_wrap" else 95.0

        return {
            "slot_size_mm": round(slot_mm, 3),
            "slot_size_in": round(slot_in, 4),
            "gauge_thou": gauge,
            "recommended_standard_slot_in": closest_slot,
            "screen_type": screen_type,
            "estimated_retention_pct": retention_estimate
        }

    @staticmethod
    def calculate_critical_drawdown(
        ucs_psi: float,
        friction_angle_deg: float,
        reservoir_pressure_psi: float,
        overburden_stress_psi: float,
        poisson_ratio: float = 0.25,
        biot_coefficient: float = 1.0
    ) -> Dict[str, Any]:
        """
        Calculate critical drawdown pressure for sanding using simplified Mohr-Coulomb.

        ΔP_crit is the maximum allowable drawdown before formation failure.

        Args:
            ucs_psi: unconfined compressive strength (psi)
            friction_angle_deg: internal friction angle (degrees)
            reservoir_pressure_psi: pore pressure (psi)
            overburden_stress_psi: overburden stress (psi)
            poisson_ratio: Poisson's ratio (dimensionless)
            biot_coefficient: Biot's poroelastic coefficient (0-1)

        Returns:
            Dict with critical_drawdown, max_flow_rate, sanding_risk
        """
        phi_rad = math.radians(friction_angle_deg)

        # Effective stress coefficient
        sigma_v_eff = overburden_stress_psi - biot_coefficient * reservoir_pressure_psi

        # Horizontal stress estimate (uniaxial strain)
        k0 = poisson_ratio / (1.0 - poisson_ratio)
        sigma_h_eff = k0 * sigma_v_eff

        # Mohr-Coulomb critical drawdown
        # Simplified: ΔP_crit = (UCS + (σ_h_eff) * (1 - sin(φ))) / (1 + sin(φ))
        sin_phi = math.sin(phi_rad)

        if (1 + sin_phi) == 0:
            dp_crit = ucs_psi
        else:
            dp_crit = (ucs_psi + sigma_h_eff * (1 - sin_phi)) / (1 + sin_phi)

        dp_crit = max(dp_crit, 0)

        # Sanding risk assessment
        if dp_crit < 200:
            risk = "Very High"
            recommendation = "Sand control required — OHGP or SAS recommended"
        elif dp_crit < 500:
            risk = "High"
            recommendation = "Sand control recommended — consider OHGP"
        elif dp_crit < 1000:
            risk = "Moderate"
            recommendation = "Monitor sand production — rate-restricted completion"
        elif dp_crit < 2000:
            risk = "Low"
            recommendation = "Oriented perforating may be sufficient"
        else:
            risk = "Very Low"
            recommendation = "Sand-free completion likely — no sand control needed"

        return {
            "critical_drawdown_psi": round(dp_crit, 0),
            "effective_overburden_psi": round(sigma_v_eff, 0),
            "effective_horizontal_psi": round(sigma_h_eff, 0),
            "sanding_risk": risk,
            "recommendation": recommendation,
            "ucs_psi": ucs_psi,
            "friction_angle_deg": friction_angle_deg
        }

    @staticmethod
    def calculate_gravel_volume(
        hole_id: float,
        screen_od: float,
        interval_length: float,
        pack_factor: float = 1.4,
        washout_factor: float = 1.1
    ) -> Dict[str, Any]:
        """
        Calculate gravel volume required for packing.

        V = annular_volume × pack_factor × washout_factor

        Args:
            hole_id: open hole or casing ID (inches)
            screen_od: screen OD (inches)
            interval_length: completion interval length (ft)
            pack_factor: overfill factor (typically 1.3-1.5)
            washout_factor: hole enlargement factor (1.0 = gauge hole)

        Returns:
            Dict with gravel volume in bbl, ft³, lb
        """
        if hole_id <= screen_od:
            return {"error": "Hole ID must be larger than screen OD"}

        # Effective hole diameter (with washout)
        effective_hole_id = hole_id * math.sqrt(washout_factor)

        # Annular volume
        annular_area_in2 = math.pi / 4.0 * (effective_hole_id ** 2 - screen_od ** 2)
        annular_vol_ft3 = annular_area_in2 * interval_length / 144.0  # in²×ft / 144 = ft³

        # Apply pack factor
        gravel_vol_ft3 = annular_vol_ft3 * pack_factor
        gravel_vol_bbl = gravel_vol_ft3 / 5.615  # ft³ to bbl

        # Weight (gravel density ≈ 165 lb/ft³ packed)
        gravel_weight_lb = gravel_vol_ft3 * 165.0

        # Annular volume per foot
        ann_vol_per_ft_bbl = (annular_area_in2 / 144.0) / 5.615

        return {
            "gravel_volume_bbl": round(gravel_vol_bbl, 1),
            "gravel_volume_ft3": round(gravel_vol_ft3, 1),
            "gravel_weight_lb": round(gravel_weight_lb, 0),
            "annular_volume_bbl": round(annular_vol_ft3 / 5.615, 1),
            "annular_vol_per_ft_bbl": round(ann_vol_per_ft_bbl, 4),
            "effective_hole_id_in": round(effective_hole_id, 3),
            "pack_factor": pack_factor,
            "washout_factor": washout_factor,
            "interval_length_ft": interval_length
        }

    @staticmethod
    def calculate_skin_factor(
        perforation_length: float,
        perforation_diameter: float,
        gravel_permeability_md: float,
        formation_permeability_md: float,
        wellbore_radius: float,
        damaged_zone_radius: float = 0.0,
        damaged_zone_perm_md: float = 0.0
    ) -> Dict[str, Any]:
        """
        Calculate completion skin factor including gravel pack contribution.

        S_total = S_perf + S_gravel + S_damage

        Args:
            perforation_length: perforation tunnel length (inches)
            perforation_diameter: perforation tunnel diameter (inches)
            gravel_permeability_md: gravel pack permeability (mD)
            formation_permeability_md: formation permeability (mD)
            wellbore_radius: wellbore radius (ft)
            damaged_zone_radius: damaged zone extent (ft), 0 = no damage
            damaged_zone_perm_md: damaged zone permeability (mD)

        Returns:
            Dict with S_total and components
        """
        if formation_permeability_md <= 0 or wellbore_radius <= 0:
            return {"error": "Invalid permeability or wellbore radius"}

        # Perforation tunnel converted to feet
        l_perf_ft = perforation_length / 12.0
        d_perf_ft = perforation_diameter / 12.0

        # Gravel-filled perforation skin
        s_gravel = 0.0
        if gravel_permeability_md > 0 and l_perf_ft > 0 and d_perf_ft > 0:
            r_perf = d_perf_ft / 2.0
            if r_perf > 0:
                s_gravel = (formation_permeability_md / gravel_permeability_md - 1.0) * \
                           math.log((wellbore_radius + l_perf_ft) / wellbore_radius)

        # Perforation pseudo-skin (simplified Karakas-Tariq)
        s_perf = 0.0
        if l_perf_ft > 0:
            r_d = l_perf_ft / wellbore_radius
            if r_d > 0:
                s_perf = math.log(1.0 / r_d) if r_d < 1 else -math.log(r_d)

        # Damage skin
        s_damage = 0.0
        if damaged_zone_radius > wellbore_radius and damaged_zone_perm_md > 0:
            s_damage = (formation_permeability_md / damaged_zone_perm_md - 1.0) * \
                       math.log(damaged_zone_radius / wellbore_radius)

        s_total = s_perf + s_gravel + s_damage

        return {
            "skin_total": round(s_total, 2),
            "skin_perforation": round(s_perf, 2),
            "skin_gravel": round(s_gravel, 2),
            "skin_damage": round(s_damage, 2),
            "formation_perm_md": formation_permeability_md,
            "gravel_perm_md": gravel_permeability_md
        }

    @staticmethod
    def evaluate_completion_type(
        d50_mm: float,
        uniformity_coefficient: float,
        ucs_psi: float,
        reservoir_pressure_psi: float,
        formation_permeability_md: float,
        wellbore_type: str = "cased"
    ) -> Dict[str, Any]:
        """
        Evaluate and recommend completion/sand control method.

        Decision matrix comparing OHGP, Cased-Hole GP, SAS, Frac-Pack.

        Args:
            d50_mm: median grain size (mm)
            uniformity_coefficient: Cu = D60/D10
            ucs_psi: unconfined compressive strength (psi)
            reservoir_pressure_psi: reservoir pressure (psi)
            formation_permeability_md: formation permeability (mD)
            wellbore_type: 'openhole' or 'cased'

        Returns:
            Dict with recommended method, alternatives, scoring
        """
        methods = []

        # --- Open Hole Gravel Pack (OHGP) ---
        ohgp_score = 0
        if wellbore_type == "openhole":
            ohgp_score += 3
        if d50_mm < 0.15:  # fine sand
            ohgp_score += 2
        if uniformity_coefficient < 5:
            ohgp_score += 2
        if formation_permeability_md > 500:
            ohgp_score += 2
        if ucs_psi < 500:
            ohgp_score += 1
        methods.append({"method": "Open Hole Gravel Pack (OHGP)", "score": ohgp_score,
                        "pro": "Best sand retention, low skin", "con": "Requires open hole"})

        # --- Cased Hole Gravel Pack (CHGP) ---
        chgp_score = 0
        if wellbore_type == "cased":
            chgp_score += 3
        if d50_mm < 0.20:
            chgp_score += 2
        if uniformity_coefficient < 5:
            chgp_score += 1
        if formation_permeability_md > 200:
            chgp_score += 2
        if ucs_psi < 1000:
            chgp_score += 1
        methods.append({"method": "Cased Hole Gravel Pack (CHGP)", "score": chgp_score,
                        "pro": "Works with cased completions", "con": "Higher skin than OHGP"})

        # --- Standalone Screen (SAS) ---
        sas_score = 0
        if uniformity_coefficient < 3:
            sas_score += 3
        if d50_mm > 0.15:
            sas_score += 2
        if formation_permeability_md > 1000:
            sas_score += 2
        if ucs_psi > 500:
            sas_score += 1
        methods.append({"method": "Standalone Screen (SAS)", "score": sas_score,
                        "pro": "Simple, cost-effective", "con": "Poor for fines, no gravel backup"})

        # --- Frac-Pack ---
        fp_score = 0
        if formation_permeability_md < 200:
            fp_score += 3
        if d50_mm < 0.10:  # very fine sand
            fp_score += 2
        if ucs_psi < 300:
            fp_score += 2
        if reservoir_pressure_psi > 5000:
            fp_score += 1
        methods.append({"method": "Frac-Pack", "score": fp_score,
                        "pro": "Best for low-perm + sanding", "con": "Complex, expensive"})

        # Sort by score descending
        methods.sort(key=lambda m: m["score"], reverse=True)
        recommended = methods[0]["method"]

        return {
            "recommended": recommended,
            "methods": methods,
            "formation_d50_mm": d50_mm,
            "uniformity_coefficient": uniformity_coefficient,
            "ucs_psi": ucs_psi,
            "wellbore_type": wellbore_type
        }

    @staticmethod
    def calculate_full_sand_control(
        sieve_sizes_mm: List[float],
        cumulative_passing_pct: List[float],
        hole_id: float,
        screen_od: float,
        interval_length: float,
        ucs_psi: float,
        friction_angle_deg: float,
        reservoir_pressure_psi: float,
        overburden_stress_psi: float,
        formation_permeability_md: float,
        wellbore_radius_ft: float = 0.354,
        wellbore_type: str = "cased",
        gravel_permeability_md: float = 80000.0,
        pack_factor: float = 1.4,
        washout_factor: float = 1.1
    ) -> Dict[str, Any]:
        """
        Complete sand control analysis combining all calculations.

        Returns:
            Dict with summary, psd, gravel, screen, drawdown, volume, skin, completion, alerts
        """
        eng = SandControlEngine

        # PSD Analysis
        psd = eng.analyze_grain_distribution(sieve_sizes_mm, cumulative_passing_pct)
        if "error" in psd:
            return {"summary": {}, "alerts": [psd["error"]]}

        # Gravel selection
        gravel = eng.select_gravel_size(
            psd["d50_mm"], psd["d10_mm"], psd["d90_mm"],
            psd["uniformity_coefficient"]
        )

        # Screen selection
        screen = eng.select_screen_slot(psd["d10_mm"], psd["d50_mm"])

        # Critical drawdown
        drawdown = eng.calculate_critical_drawdown(
            ucs_psi, friction_angle_deg,
            reservoir_pressure_psi, overburden_stress_psi
        )

        # Gravel volume
        volume = eng.calculate_gravel_volume(
            hole_id, screen_od, interval_length,
            pack_factor, washout_factor
        )

        # Skin factor
        skin = eng.calculate_skin_factor(
            perforation_length=12.0,  # typical 12" perf
            perforation_diameter=0.5,  # typical 0.5" tunnel
            gravel_permeability_md=gravel_permeability_md,
            formation_permeability_md=formation_permeability_md,
            wellbore_radius=wellbore_radius_ft
        )

        # Completion type evaluation
        completion = eng.evaluate_completion_type(
            psd["d50_mm"], psd["uniformity_coefficient"],
            ucs_psi, reservoir_pressure_psi,
            formation_permeability_md, wellbore_type
        )

        # Alerts
        alerts = []
        if psd["uniformity_coefficient"] > 10:
            alerts.append(f"Very poorly sorted sand (Cu={psd['uniformity_coefficient']:.1f}) — premium screen recommended")
        if drawdown["sanding_risk"] in ["Very High", "High"]:
            alerts.append(f"Sanding risk: {drawdown['sanding_risk']} — sand control required")
        if drawdown["critical_drawdown_psi"] < 200:
            alerts.append(f"Critical drawdown only {drawdown['critical_drawdown_psi']:.0f} psi — very weak formation")
        if skin["skin_total"] > 10:
            alerts.append(f"High completion skin {skin['skin_total']:.1f} — consider productivity optimization")
        if psd["d50_mm"] < 0.05:
            alerts.append("Very fine sand — consider frac-pack instead of conventional gravel pack")
        if volume.get("gravel_volume_bbl", 0) > 100:
            alerts.append(f"Large gravel volume required: {volume['gravel_volume_bbl']:.0f} bbl — verify logistics")

        summary = {
            "d50_mm": psd["d50_mm"],
            "uniformity_coefficient": psd["uniformity_coefficient"],
            "sorting": psd["sorting"],
            "recommended_gravel": gravel["recommended_pack"],
            "screen_slot_in": screen["recommended_standard_slot_in"],
            "critical_drawdown_psi": drawdown["critical_drawdown_psi"],
            "sanding_risk": drawdown["sanding_risk"],
            "gravel_volume_bbl": volume.get("gravel_volume_bbl", 0),
            "skin_total": skin["skin_total"],
            "recommended_completion": completion["recommended"],
            "alerts": alerts
        }

        return {
            "summary": summary,
            "psd": psd,
            "gravel": gravel,
            "screen": screen,
            "drawdown": drawdown,
            "volume": volume,
            "skin": skin,
            "completion": completion,
            "parameters": {
                "hole_id_in": hole_id,
                "screen_od_in": screen_od,
                "interval_length_ft": interval_length,
                "ucs_psi": ucs_psi,
                "friction_angle_deg": friction_angle_deg,
                "reservoir_pressure_psi": reservoir_pressure_psi,
                "overburden_stress_psi": overburden_stress_psi,
                "formation_permeability_md": formation_permeability_md,
                "wellbore_type": wellbore_type,
                "pack_factor": pack_factor,
                "washout_factor": washout_factor
            },
            "alerts": alerts
        }
