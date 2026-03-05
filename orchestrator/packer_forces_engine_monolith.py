"""
Packer Forces Calculation Engine

Calculates forces acting on packers and tubing in completion/workover operations.

Elite enhancements (Phase 8):
- APB (Annular Pressure Buildup) model for HPHT/subsea
- Packer type classification (free/anchored/limited movement)
- Temperature profile variable with depth (integral approach)
- Buckling length calculation (sinusoidal/helicoidal)
- Landing force and initial conditions

References:
- Lubinski, A. (1962): Helical Buckling of Tubing Sealed in Packers
- Mitchell, R. & Samuel, R. (2009): How Good Is the Thin Shell Approximation
- Halliburton Red Book, Baker Hughes Completion Engineering Guide
- API TR 5C3: Casing and Tubing Buckling in Wellbores
- Adams, A.J. & MacEachran, A. (1994): Impact on Casing Design of Thermal Expansion
"""
import math
from typing import Dict, Any, List, Optional, Tuple


class PackerForcesEngine:
    """
    Calculates piston, ballooning, temperature, and buckling forces
    on tubing-packer systems. All methods are @staticmethod.
    """

    # Steel properties (defaults)
    STEEL_E = 30e6         # Young's modulus (psi)
    STEEL_POISSON = 0.30   # Poisson's ratio
    STEEL_ALPHA = 6.9e-6   # Thermal expansion coefficient (1/°F)

    @staticmethod
    def calculate_tubing_areas(od: float, id_inner: float) -> Dict[str, float]:
        """
        Calculate tubing cross-sectional areas.

        Args:
            od: tubing outer diameter (inches)
            id_inner: tubing inner diameter (inches)

        Returns:
            Dict with ao, ai, as (outer, inner, steel areas in in²)
        """
        ao = math.pi * (od / 2.0) ** 2
        ai = math.pi * (id_inner / 2.0) ** 2
        a_steel = ao - ai
        return {
            "ao_in2": round(ao, 4),
            "ai_in2": round(ai, 4),
            "as_in2": round(a_steel, 4)
        }

    @staticmethod
    def calculate_piston_force(
        pressure_below: float,
        pressure_above: float,
        seal_bore_area: float,
        tubing_ao: float,
        tubing_ai: float
    ) -> float:
        """
        Piston effect force on packer.
        F_piston = P_below * (A_seal - A_i) - P_above * (A_seal - A_o)

        For PBR (polished bore receptacle):
        F = (P_below - P_above) * A_seal approximately

        Args:
            pressure_below: pressure below packer (psi)
            pressure_above: pressure above packer (psi)
            seal_bore_area: packer seal bore area (in²)
            tubing_ao: tubing outer area (in²)
            tubing_ai: tubing inner area (in²)

        Returns:
            Piston force (lbs). Positive = tension, Negative = compression.
        """
        f_piston = (pressure_below * (seal_bore_area - tubing_ai)
                    - pressure_above * (seal_bore_area - tubing_ao))
        return round(f_piston, 1)

    @staticmethod
    def calculate_ballooning_force(
        delta_pi: float,
        delta_po: float,
        tubing_ai: float,
        tubing_ao: float,
        poisson_ratio: float = 0.30
    ) -> float:
        """
        Ballooning/reverse-ballooning force due to pressure changes.
        F_balloon = -2ν × (ΔP_i × A_i - ΔP_o × A_o)

        Args:
            delta_pi: change in internal pressure (psi) (final - initial)
            delta_po: change in external pressure (psi) (final - initial)
            tubing_ai: tubing inner area (in²)
            tubing_ao: tubing outer area (in²)
            poisson_ratio: Poisson's ratio (default 0.30)

        Returns:
            Ballooning force (lbs). Positive = tension.
        """
        f_balloon = -2.0 * poisson_ratio * (delta_pi * tubing_ai - delta_po * tubing_ao)
        return round(f_balloon, 1)

    @staticmethod
    def calculate_temperature_force(
        delta_t: float,
        tubing_as: float,
        youngs_modulus: float = 30e6,
        thermal_expansion: float = 6.9e-6
    ) -> float:
        """
        Temperature effect force.
        F_temp = -E × A_s × α × ΔT

        Args:
            delta_t: average temperature change (°F) (final - initial)
            tubing_as: tubing steel cross-sectional area (in²)
            youngs_modulus: Young's modulus (psi)
            thermal_expansion: thermal expansion coefficient (1/°F)

        Returns:
            Temperature force (lbs). Heating → compression (negative).
        """
        f_temp = -youngs_modulus * tubing_as * thermal_expansion * delta_t
        return round(f_temp, 1)

    @staticmethod
    def calculate_buckling_force(
        tubing_ai: float,
        tubing_ao: float,
        pressure_internal: float,
        pressure_external: float
    ) -> float:
        """
        Buckling force (fictitious force concept — Lubinski).
        F_f = P_i × A_i - P_o × A_o

        If actual force at packer < -F_f, the string will buckle.

        Args:
            tubing_ai: tubing inner area (in²)
            tubing_ao: tubing outer area (in²)
            pressure_internal: internal pressure at packer (psi)
            pressure_external: external/annular pressure at packer (psi)

        Returns:
            Fictitious buckling force (lbs)
        """
        f_f = pressure_internal * tubing_ai - pressure_external * tubing_ao
        return round(f_f, 1)

    @staticmethod
    def calculate_tubing_movement(
        force: float,
        tubing_length: float,
        tubing_as: float,
        youngs_modulus: float = 30e6
    ) -> float:
        """
        Calculate tubing length change due to a force (Hooke's law).
        ΔL = F × L / (E × A_s)

        Args:
            force: applied force (lbs)
            tubing_length: tubing length (ft)
            tubing_as: steel cross-sectional area (in²)
            youngs_modulus: Young's modulus (psi)

        Returns:
            Length change (inches). Positive = elongation.
        """
        if tubing_as <= 0 or youngs_modulus <= 0:
            return 0.0
        # Convert length to inches for consistent units
        delta_l = force * (tubing_length * 12.0) / (youngs_modulus * tubing_as)
        return round(delta_l, 3)

    @staticmethod
    def calculate_helical_buckling_load(
        tubing_od: float,
        tubing_id: float,
        tubing_weight: float,
        casing_id: float,
        inclination: float = 0.0
    ) -> float:
        """
        Critical helical buckling load (Lubinski/Paslay-Dawson).

        For vertical: F_cr = 2 * sqrt(E * I * w / r)
        For inclined: F_cr = 2 * sqrt(E * I * w * sin(θ) / r)

        Args:
            tubing_od: tubing OD (inches)
            tubing_id: tubing ID (inches)
            tubing_weight: buoyed weight per foot (lb/ft)
            casing_id: casing ID (inches)
            inclination: wellbore inclination (degrees)

        Returns:
            Critical buckling load (lbs). Compression exceeding this → helical buckling.
        """
        # Moment of inertia
        i_moment = math.pi * (tubing_od ** 4 - tubing_id ** 4) / 64.0

        # Radial clearance
        r_clear = (casing_id - tubing_od) / 2.0
        if r_clear <= 0:
            return float('inf')

        w = abs(tubing_weight)
        if w <= 0:
            return float('inf')

        e = PackerForcesEngine.STEEL_E

        inc_rad = math.radians(inclination)
        sin_factor = math.sin(inc_rad) if inclination > 5 else 1.0

        f_cr = 2.0 * math.sqrt(e * i_moment * w * sin_factor / r_clear)
        return round(f_cr, 0)

    @staticmethod
    def calculate_total_packer_force(
        tubing_od: float,
        tubing_id: float,
        tubing_weight: float,
        tubing_length: float,
        seal_bore_id: float,
        initial_tubing_pressure: float,
        final_tubing_pressure: float,
        initial_annulus_pressure: float,
        final_annulus_pressure: float,
        initial_temperature: float,
        final_temperature: float,
        packer_depth_tvd: float,
        mud_weight_tubing: float = 8.34,
        mud_weight_annulus: float = 8.34,
        poisson_ratio: float = 0.30,
        thermal_expansion: float = 6.9e-6
    ) -> Dict[str, Any]:
        """
        Complete packer force analysis — combines all effects.

        Returns:
            Dict with force components, movements, total force, buckling check.
        """
        eng = PackerForcesEngine

        # Areas
        areas = eng.calculate_tubing_areas(tubing_od, tubing_id)
        ao = areas["ao_in2"]
        ai = areas["ai_in2"]
        a_steel = areas["as_in2"]

        seal_area = math.pi * (seal_bore_id / 2.0) ** 2

        # Hydrostatic pressures at packer
        # P = surface_P + 0.052 * MW * TVD
        p_below_initial = initial_tubing_pressure + 0.052 * mud_weight_tubing * packer_depth_tvd
        p_below_final = final_tubing_pressure + 0.052 * mud_weight_tubing * packer_depth_tvd
        p_above_initial = initial_annulus_pressure + 0.052 * mud_weight_annulus * packer_depth_tvd
        p_above_final = final_annulus_pressure + 0.052 * mud_weight_annulus * packer_depth_tvd

        # 1. Piston force (change from initial to final)
        f_piston_initial = eng.calculate_piston_force(
            p_below_initial, p_above_initial, seal_area, ao, ai
        )
        f_piston_final = eng.calculate_piston_force(
            p_below_final, p_above_final, seal_area, ao, ai
        )
        delta_f_piston = f_piston_final - f_piston_initial

        # 2. Ballooning force
        delta_pi = (final_tubing_pressure - initial_tubing_pressure)
        delta_po = (final_annulus_pressure - initial_annulus_pressure)
        f_ballooning = eng.calculate_ballooning_force(delta_pi, delta_po, ai, ao, poisson_ratio)

        # 3. Temperature force
        delta_t = final_temperature - initial_temperature
        f_temperature = eng.calculate_temperature_force(delta_t, a_steel, thermal_expansion=thermal_expansion)

        # Total force change
        total_force = delta_f_piston + f_ballooning + f_temperature

        # Movements (if packer allows motion)
        dl_piston = eng.calculate_tubing_movement(delta_f_piston, tubing_length, a_steel)
        dl_balloon = eng.calculate_tubing_movement(f_ballooning, tubing_length, a_steel)
        dl_temp_free = -thermal_expansion * delta_t * tubing_length * 12.0  # free thermal expansion (inches)
        dl_total = dl_piston + dl_balloon + dl_temp_free

        # Buckling check
        buoyed_weight = tubing_weight * (1.0 - mud_weight_annulus / 65.5)  # steel = 65.5 ppg
        f_buckling_critical = eng.calculate_helical_buckling_load(
            tubing_od, tubing_id, buoyed_weight, seal_bore_id
        )

        buckling_status = "OK"
        if total_force < 0 and abs(total_force) > f_buckling_critical:
            buckling_status = "Helical Buckling"
        elif total_force < 0 and abs(total_force) > f_buckling_critical * 0.5:
            buckling_status = "Sinusoidal Buckling"

        # Alerts
        alerts = []
        if buckling_status != "OK":
            alerts.append(f"{buckling_status} predicted — compressive force {abs(total_force):.0f} lbs exceeds critical {f_buckling_critical:.0f} lbs")
        if abs(dl_total) > 6.0:
            alerts.append(f"Large tubing movement {dl_total:.2f} inches — verify seal stroke length")
        if total_force > 0 and total_force > 0.6 * 80000 * a_steel:  # 80 ksi yield approx
            alerts.append(f"High tension {total_force:.0f} lbs — verify tubing connection rating")
        if delta_t > 100:
            alerts.append(f"Large temperature change ΔT={delta_t:.0f}°F — significant thermal effects")

        summary = {
            "total_force_lbs": round(total_force, 0),
            "force_direction": "Tension" if total_force > 0 else "Compression",
            "piston_force_lbs": round(delta_f_piston, 0),
            "ballooning_force_lbs": round(f_ballooning, 0),
            "temperature_force_lbs": round(f_temperature, 0),
            "total_movement_inches": round(dl_total, 3),
            "movement_piston_in": round(dl_piston, 3),
            "movement_balloon_in": round(dl_balloon, 3),
            "movement_thermal_in": round(dl_temp_free, 3),
            "buckling_status": buckling_status,
            "buckling_critical_load_lbs": round(f_buckling_critical, 0),
            "alerts": alerts
        }

        return {
            "summary": summary,
            "force_components": {
                "piston": round(delta_f_piston, 0),
                "ballooning": round(f_ballooning, 0),
                "temperature": round(f_temperature, 0),
                "total": round(total_force, 0)
            },
            "movements": {
                "piston_in": round(dl_piston, 3),
                "ballooning_in": round(dl_balloon, 3),
                "thermal_in": round(dl_temp_free, 3),
                "total_in": round(dl_total, 3)
            },
            "parameters": {
                "tubing_od_in": tubing_od,
                "tubing_id_in": tubing_id,
                "tubing_weight_lbft": tubing_weight,
                "tubing_length_ft": tubing_length,
                "seal_bore_id_in": seal_bore_id,
                "packer_depth_tvd_ft": packer_depth_tvd,
                "delta_t_f": delta_t,
                "delta_pi_psi": delta_pi,
                "delta_po_psi": delta_po
            },
            "alerts": alerts
        }

    # =====================================================================
    # Phase 8 Elite — APB, Packer Type, T-Profile, Buckling Length, Landing
    # =====================================================================

    @staticmethod
    def calculate_apb(
        annular_fluid_type: str = "WBM",
        delta_t_avg: float = 100.0,
        annular_volume_bbl: float = 200.0,
        casing_od: float = 9.625,
        casing_id: float = 8.681,
        tubing_od: float = 3.5,
        tubing_id: float = 2.992,
        annular_length_ft: float = 10000.0,
        initial_pressure_psi: float = 0.0
    ) -> Dict[str, Any]:
        """
        Calculate Annular Pressure Buildup (APB) for trapped annulus.

        APB = alpha_f * delta_T * V / (C_f * V + C_casing + C_tubing)

        Where:
            alpha_f = thermal expansion coefficient of fluid
            C_f = fluid compressibility
            C_casing = casing compliance (radial expansion capacity)
            C_tubing = tubing compliance (radial compression capacity)

        Critical for HPHT and subsea wells where annuli are sealed.

        Args:
            annular_fluid_type: 'WBM', 'OBM', 'brine', 'completion_fluid'
            delta_t_avg: average temperature increase (deg F)
            annular_volume_bbl: total annular volume (bbl)
            casing_od, casing_id: casing dimensions (in)
            tubing_od, tubing_id: tubing dimensions (in)
            annular_length_ft: length of sealed annulus (ft)
            initial_pressure_psi: initial trapped pressure (psi)

        Returns:
            Dict with APB pressure, SF checks, mitigation recommendations.
        """
        # Fluid properties by type
        fluid_props = {
            "WBM":               {"alpha": 2.0e-4, "C_f": 3.0e-6},
            "OBM":               {"alpha": 3.5e-4, "C_f": 5.0e-6},
            "brine":             {"alpha": 2.5e-4, "C_f": 3.2e-6},
            "completion_fluid":  {"alpha": 2.8e-4, "C_f": 4.0e-6},
        }
        props = fluid_props.get(annular_fluid_type, fluid_props["WBM"])
        alpha_f = props["alpha"]  # 1/deg F
        c_f = props["C_f"]       # 1/psi

        e = PackerForcesEngine.STEEL_E

        # Volume in cubic inches
        v_ann_in3 = annular_volume_bbl * 9702.0  # 1 bbl = 9702 in3

        # Casing compliance: dV/dP for casing expanding outward
        casing_wall = (casing_od - casing_id) / 2.0
        if casing_wall > 0:
            c_casing = math.pi * casing_id ** 2 * (annular_length_ft * 12.0) / (2.0 * e * casing_wall)
        else:
            c_casing = 0

        # Tubing compliance: dV/dP for tubing compressing inward
        tubing_wall = (tubing_od - tubing_id) / 2.0
        if tubing_wall > 0:
            c_tubing = math.pi * tubing_od ** 2 * (annular_length_ft * 12.0) / (2.0 * e * tubing_wall)
        else:
            c_tubing = 0

        # APB calculation
        denominator = c_f * v_ann_in3 + c_casing + c_tubing
        if denominator > 0:
            apb_psi = alpha_f * delta_t_avg * v_ann_in3 / denominator
        else:
            apb_psi = 0

        total_pressure = initial_pressure_psi + apb_psi

        # Safety factor checks (simplified burst/collapse ratings)
        casing_burst_approx = 0.875 * 2 * 80000 * casing_wall / casing_od if casing_od > 0 else 99999
        casing_burst_sf = casing_burst_approx / total_pressure if total_pressure > 0 else 99

        tubing_collapse_approx = 2 * 80000 * tubing_wall / tubing_od if tubing_od > 0 else 99999
        tubing_collapse_sf = tubing_collapse_approx / total_pressure if total_pressure > 0 else 99

        # Mitigation
        mitigation_needed = total_pressure > 0.8 * casing_burst_approx
        recommendations = []
        if mitigation_needed:
            recommendations.append("Consider nitrogen-foamed spacer to reduce APB")
            recommendations.append("Evaluate crushable foam inserts for annular volume compensation")
            recommendations.append("Consider rupture disk or pressure relief sub")

        return {
            "apb_psi": round(apb_psi, 0),
            "total_annular_pressure_psi": round(total_pressure, 0),
            "casing_burst_sf": round(casing_burst_sf, 2),
            "tubing_collapse_sf": round(tubing_collapse_sf, 2),
            "thermal_expansion_coeff": alpha_f,
            "fluid_compressibility": c_f,
            "casing_compliance_in3_psi": round(c_casing, 4),
            "tubing_compliance_in3_psi": round(c_tubing, 4),
            "annular_fluid_type": annular_fluid_type,
            "delta_t_avg_f": delta_t_avg,
            "mitigation_needed": mitigation_needed,
            "recommendations": recommendations,
        }

    @staticmethod
    def calculate_apb_mitigation(
        apb_psi: float,
        foam_volume_pct: float = 0.0,
        crushable_spacer_vol_bbl: float = 0.0,
        annular_volume_bbl: float = 200.0,
        fluid_compressibility: float = 3.0e-6
    ) -> Dict[str, Any]:
        """
        Calculate APB after mitigation measures (foam, crushable spacers).

        Nitrogen foam increases effective compressibility of annular fluid.
        Crushable spacers provide additional compliance volume.

        Args:
            apb_psi: original APB pressure (psi)
            foam_volume_pct: percentage of annular volume filled with foam (0-50%)
            crushable_spacer_vol_bbl: volume of crushable spacer (bbl)
            annular_volume_bbl: total annular volume (bbl)
            fluid_compressibility: base fluid compressibility (1/psi)

        Returns:
            Dict with mitigated APB, reduction percentage.
        """
        if apb_psi <= 0:
            return {
                "apb_original_psi": 0,
                "apb_mitigated_psi": 0,
                "reduction_pct": 0,
                "foam_reduction_factor": 1.0,
                "crush_reduction_factor": 1.0,
            }

        # Foam effect: nitrogen compressibility ~100x higher than liquid
        foam_frac = min(0.50, max(0, foam_volume_pct / 100.0))
        c_foam = 1.0e-4  # 1/psi (nitrogen at typical downhole conditions)
        c_effective = (1.0 - foam_frac) * fluid_compressibility + foam_frac * c_foam
        foam_reduction_factor = fluid_compressibility / c_effective if c_effective > 0 else 1.0

        # Crushable spacer: provides additional compliance
        v_ann = annular_volume_bbl * 9702.0  # in3
        v_crush = crushable_spacer_vol_bbl * 9702.0
        crush_factor = v_ann / (v_ann + v_crush) if (v_ann + v_crush) > 0 else 1.0

        apb_mitigated = apb_psi * foam_reduction_factor * crush_factor
        reduction_pct = (1.0 - apb_mitigated / apb_psi) * 100 if apb_psi > 0 else 0

        return {
            "apb_original_psi": round(apb_psi, 0),
            "apb_mitigated_psi": round(apb_mitigated, 0),
            "reduction_pct": round(reduction_pct, 1),
            "foam_reduction_factor": round(foam_reduction_factor, 4),
            "crush_reduction_factor": round(crush_factor, 4),
            "effective_compressibility": round(c_effective, 8),
            "foam_volume_pct": foam_volume_pct,
            "crushable_spacer_bbl": crushable_spacer_vol_bbl,
        }

    @staticmethod
    def calculate_packer_force_by_type(
        packer_type: str,
        total_force_if_anchored: float,
        tubing_movement_if_free_in: float,
        stroke_in: float = 0.0,
        tubing_length_ft: float = 10000.0,
        tubing_as: float = 3.0,
        youngs_modulus: float = 30e6
    ) -> Dict[str, Any]:
        """
        Calculate force/displacement based on packer type classification.

        Free (polished bore): tubing moves freely, force on packer = 0
        Anchored: no movement allowed, all force absorbed by packer
        Limited movement: hybrid -- free until stroke exhausted, then anchored

        Args:
            packer_type: 'free', 'anchored', 'limited'
            total_force_if_anchored: force that would act if fully anchored (lbs)
            tubing_movement_if_free_in: movement that would occur if free (in)
            stroke_in: available stroke for limited-movement packer (in)
            tubing_length_ft: tubing length (ft)
            tubing_as: tubing steel area (in2)
            youngs_modulus: Young's modulus (psi)

        Returns:
            Dict with force_on_packer, tubing_displacement, packer_status.
        """
        pt = packer_type.lower().strip()

        if pt == "free":
            return {
                "packer_type": "free",
                "force_on_packer_lbs": 0.0,
                "tubing_displacement_in": round(tubing_movement_if_free_in, 3),
                "packer_status": "Free movement -- tubing moved",
                "seal_engagement": abs(tubing_movement_if_free_in) < 48.0,
                "remaining_stroke_in": None,
            }

        elif pt == "anchored":
            return {
                "packer_type": "anchored",
                "force_on_packer_lbs": round(total_force_if_anchored, 0),
                "tubing_displacement_in": 0.0,
                "packer_status": "Anchored -- full force absorbed by packer",
                "seal_engagement": True,
                "remaining_stroke_in": None,
            }

        elif pt == "limited":
            if abs(tubing_movement_if_free_in) <= stroke_in:
                return {
                    "packer_type": "limited",
                    "force_on_packer_lbs": 0.0,
                    "tubing_displacement_in": round(tubing_movement_if_free_in, 3),
                    "packer_status": "Limited -- within stroke (free behavior)",
                    "seal_engagement": True,
                    "remaining_stroke_in": round(stroke_in - abs(tubing_movement_if_free_in), 3),
                }
            else:
                excess_in = abs(tubing_movement_if_free_in) - stroke_in
                stiffness = youngs_modulus * tubing_as / (tubing_length_ft * 12.0) if tubing_length_ft > 0 else 1e6
                excess_force = stiffness * excess_in
                if tubing_movement_if_free_in < 0:
                    excess_force = -excess_force

                actual_displacement = math.copysign(stroke_in, tubing_movement_if_free_in)

                return {
                    "packer_type": "limited",
                    "force_on_packer_lbs": round(excess_force, 0),
                    "tubing_displacement_in": round(actual_displacement, 3),
                    "packer_status": "Limited -- stroke exhausted (partially anchored)",
                    "seal_engagement": True,
                    "remaining_stroke_in": 0.0,
                }
        else:
            return {"error": f"Unknown packer type: {packer_type}. Use 'free', 'anchored', or 'limited'."}

    @staticmethod
    def calculate_temperature_force_profile(
        initial_t_profile: List[Dict[str, float]],
        production_t_profile: List[Dict[str, float]],
        tubing_od: float = 3.5,
        tubing_id: float = 2.992,
        youngs_modulus: float = 30e6,
        thermal_expansion: float = 6.9e-6
    ) -> Dict[str, Any]:
        """
        Calculate temperature force using depth-varying temperature profile
        instead of uniform delta-T.

        F_temp = E * A_s * alpha * integral(delta_T(z))dz / L

        The integral captures depth-varying temperature difference, which is
        more accurate than a single average delta-T for deviated wells and
        production scenarios.

        Args:
            initial_t_profile: list of {depth_ft, temperature_f} -- initial state
            production_t_profile: list of {depth_ft, temperature_f} -- final state
            tubing_od, tubing_id: tubing dimensions (in)
            youngs_modulus: Young's modulus (psi)
            thermal_expansion: thermal expansion coefficient (1/deg F)

        Returns:
            Dict with force, delta-T profile, average delta-T, max delta-T.
        """
        if not initial_t_profile or not production_t_profile:
            return {"error": "Temperature profiles must be provided"}

        a_steel = math.pi * (tubing_od ** 2 - tubing_id ** 2) / 4.0

        delta_t_profile = []
        dt_integral = 0.0
        max_dt = -1e9
        min_dt = 1e9

        for i, prod_pt in enumerate(production_t_profile):
            depth = prod_pt.get("depth_ft", 0)
            t_prod = prod_pt.get("temperature_f", 0)

            # Linear interpolation in initial profile
            t_init = 0
            if initial_t_profile:
                for j in range(len(initial_t_profile) - 1):
                    d1 = initial_t_profile[j].get("depth_ft", 0)
                    d2 = initial_t_profile[j + 1].get("depth_ft", 0)
                    if d1 <= depth <= d2 and d2 > d1:
                        frac = (depth - d1) / (d2 - d1)
                        t1 = initial_t_profile[j].get("temperature_f", 0)
                        t2 = initial_t_profile[j + 1].get("temperature_f", 0)
                        t_init = t1 + frac * (t2 - t1)
                        break
                else:
                    if depth <= initial_t_profile[0].get("depth_ft", 0):
                        t_init = initial_t_profile[0].get("temperature_f", 0)
                    else:
                        t_init = initial_t_profile[-1].get("temperature_f", 0)

            dt = t_prod - t_init
            delta_t_profile.append({
                "depth_ft": depth,
                "t_initial_f": round(t_init, 1),
                "t_production_f": round(t_prod, 1),
                "delta_t_f": round(dt, 1),
            })
            max_dt = max(max_dt, dt)
            min_dt = min(min_dt, dt)

            # Trapezoidal integration
            if i > 0:
                d_prev = production_t_profile[i - 1].get("depth_ft", 0)
                dt_prev = delta_t_profile[i - 1]["delta_t_f"]
                dz = (depth - d_prev) * 12.0  # inches
                dt_integral += 0.5 * (dt_prev + dt) * dz

        # Total tubing length
        if len(production_t_profile) >= 2:
            total_length_ft = production_t_profile[-1].get("depth_ft", 0) - production_t_profile[0].get("depth_ft", 0)
        else:
            total_length_ft = 0

        total_length_in = total_length_ft * 12.0
        delta_t_avg = dt_integral / total_length_in if total_length_in > 0 else 0

        # Force: F = -E * A_s * alpha * delta_T_avg (for anchored packer)
        force_temp = -youngs_modulus * a_steel * thermal_expansion * delta_t_avg

        # Free thermal expansion
        free_expansion_in = thermal_expansion * delta_t_avg * total_length_in

        return {
            "force_temperature_lbs": round(force_temp, 0),
            "delta_t_avg_f": round(delta_t_avg, 1),
            "delta_t_max_f": round(max_dt, 1),
            "delta_t_min_f": round(min_dt, 1),
            "free_expansion_in": round(free_expansion_in, 3),
            "tubing_length_ft": round(total_length_ft, 1),
            "delta_t_profile": delta_t_profile,
            "method": "Depth-varying temperature integral",
        }

    @staticmethod
    def calculate_buckling_length(
        axial_force: float,
        tubing_od: float = 3.5,
        tubing_id: float = 2.992,
        tubing_weight_ppf: float = 9.3,
        casing_id: float = 6.276,
        inclination_deg: float = 0.0,
        mud_weight_ppg: float = 8.34
    ) -> Dict[str, Any]:
        """
        Calculate length of buckled tubing and associated effects.

        Sinusoidal: L_buckled = F / (w * sin(inc))
        Helicoidal: L_helix = sqrt(8 * EI * F) / (w * sin(inc) * r)
        Shortening: dL = F^2 * r^2 / (8 * EI * w * sin(inc))

        Args:
            axial_force: compressive force at packer (lbs, negative = compression)
            tubing_od, tubing_id: tubing dimensions (in)
            tubing_weight_ppf: buoyed weight per foot (lb/ft)
            casing_id: casing ID for clearance (in)
            inclination_deg: wellbore inclination (degrees)
            mud_weight_ppg: mud weight (ppg)

        Returns:
            Dict with buckled length, type, shortening, contact force.
        """
        e = PackerForcesEngine.STEEL_E
        i_moment = math.pi * (tubing_od ** 4 - tubing_id ** 4) / 64.0
        ei = e * i_moment

        r_clearance = (casing_id - tubing_od) / 2.0
        if r_clearance <= 0:
            return {"error": "Casing ID must be larger than tubing OD"}

        bf = max(0.01, 1.0 - mud_weight_ppg / 65.5)
        w = abs(tubing_weight_ppf * bf)  # lb/ft buoyed
        w_in = w / 12.0  # lb/in

        inc_rad = math.radians(inclination_deg)
        sin_inc = max(math.sin(inc_rad), 0.05)  # Avoid singularity

        f_comp = abs(axial_force)

        # Critical buckling loads
        f_cr_sin = math.sqrt(2.0 * ei * w_in * sin_inc / r_clearance) if r_clearance > 0 else float("inf")
        f_cr_hel = 2.0 * f_cr_sin

        if f_comp < f_cr_sin:
            buckling_type = "None"
            buckled_length = 0
            shortening = 0
            contact_force = 0
            max_bending_stress = 0
        elif f_comp < f_cr_hel:
            buckling_type = "Sinusoidal"
            buckled_length = f_comp / (w * sin_inc) if w * sin_inc > 0 else 0
            shortening = (f_comp ** 2 * r_clearance ** 2) / (8.0 * ei * w_in * sin_inc) / 12.0 if ei > 0 else 0
            contact_force = f_comp ** 2 / (4.0 * ei / r_clearance) / 12.0 if ei > 0 else 0
            max_bending_stress = r_clearance * (tubing_od / 2.0) * f_comp / (4.0 * i_moment) if i_moment > 0 else 0
        else:
            buckling_type = "Helicoidal"
            buckled_length = f_comp / (w * sin_inc) if w * sin_inc > 0 else 0
            shortening = (f_comp ** 2 * r_clearance ** 2) / (4.0 * ei * w_in * sin_inc) / 12.0 if ei > 0 else 0
            contact_force = f_comp ** 2 * r_clearance / (4.0 * ei) / 12.0 if ei > 0 else 0
            max_bending_stress = f_comp * r_clearance * (tubing_od / 2.0) / (4.0 * i_moment) if i_moment > 0 else 0

        return {
            "buckling_type": buckling_type,
            "buckled_length_ft": round(buckled_length, 1),
            "shortening_in": round(shortening, 3),
            "contact_force_lbf_per_ft": round(contact_force, 1),
            "max_bending_stress_psi": round(max_bending_stress, 0),
            "critical_load_sinusoidal_lbs": round(f_cr_sin, 0),
            "critical_load_helicoidal_lbs": round(f_cr_hel, 0),
            "axial_force_lbs": round(axial_force, 0),
            "radial_clearance_in": round(r_clearance, 3),
            "inclination_deg": inclination_deg,
        }

    @staticmethod
    def calculate_landing_conditions(
        tubing_sections: List[Dict[str, Any]],
        survey_stations: Optional[List[Dict[str, float]]] = None,
        mud_weight_ppg: float = 8.34,
        friction_factor: float = 0.30,
        packer_depth_tvd_ft: float = 10000.0,
        set_down_weight_lbs: float = 5000.0
    ) -> Dict[str, Any]:
        """
        Calculate tubing weight at packer (landing conditions) and initial forces.

        Accounts for buoyancy, drag in deviated wells, and set-down weight.
        Landing conditions define the baseline from which all subsequent
        force changes (pressure, temperature) are calculated.

        Args:
            tubing_sections: list of {od, id_inner, length_ft, weight_ppf}
            survey_stations: list of {md_ft, inclination_deg} (optional for drag)
            mud_weight_ppg: mud weight (ppg)
            friction_factor: friction coefficient for drag (0.15-0.40)
            packer_depth_tvd_ft: packer TVD (ft)
            set_down_weight_lbs: additional weight for packer setting (lbs)

        Returns:
            Dict with tubing_weight_at_packer, buoyancy, drag, set_down_weight.
        """
        if not tubing_sections:
            return {"error": "No tubing sections provided"}

        bf = max(0.01, 1.0 - mud_weight_ppg / 65.5)

        total_weight_air = 0.0
        total_weight_buoyed = 0.0
        total_length_ft = 0.0

        for section in tubing_sections:
            w_ppf = section.get("weight_ppf", 9.3)
            l_ft = section.get("length_ft", 0)
            section_weight = w_ppf * l_ft
            total_weight_air += section_weight
            total_weight_buoyed += section_weight * bf
            total_length_ft += l_ft

        # Drag calculation
        total_drag = 0.0
        if survey_stations and len(survey_stations) > 1:
            for i in range(1, len(survey_stations)):
                md_prev = survey_stations[i - 1].get("md_ft", 0)
                md_curr = survey_stations[i].get("md_ft", 0)
                inc_prev = survey_stations[i - 1].get("inclination_deg", 0)
                inc_curr = survey_stations[i].get("inclination_deg", 0)

                dl = md_curr - md_prev
                inc_avg = math.radians((inc_prev + inc_curr) / 2.0)

                avg_ppf = total_weight_buoyed / total_length_ft if total_length_ft > 0 else 9.0
                w_segment = avg_ppf * dl

                drag_segment = friction_factor * abs(w_segment * math.sin(inc_avg))
                total_drag += drag_segment
        else:
            avg_inc = math.atan(0.3) if packer_depth_tvd_ft > 0 else 0
            total_drag = friction_factor * total_weight_buoyed * abs(math.sin(avg_inc)) * 0.3

        weight_at_packer = total_weight_buoyed - total_drag
        landing_force = weight_at_packer + set_down_weight_lbs

        min_set_down = {
            "typical_mechanical": 5000,
            "hydraulic_set": 0,
            "permanent": 10000,
        }

        return {
            "tubing_weight_air_lbs": round(total_weight_air, 0),
            "tubing_weight_buoyed_lbs": round(total_weight_buoyed, 0),
            "buoyancy_factor": round(bf, 4),
            "drag_force_lbs": round(total_drag, 0),
            "weight_at_packer_lbs": round(weight_at_packer, 0),
            "set_down_weight_lbs": round(set_down_weight_lbs, 0),
            "total_landing_force_lbs": round(landing_force, 0),
            "total_tubing_length_ft": round(total_length_ft, 1),
            "packer_depth_tvd_ft": packer_depth_tvd_ft,
            "friction_factor": friction_factor,
            "min_set_down_recommendations": min_set_down,
        }
