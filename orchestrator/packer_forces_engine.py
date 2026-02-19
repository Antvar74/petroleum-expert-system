"""
Packer Forces Calculation Engine

Calculates forces acting on packers and tubing in completion/workover operations.
References:
- Lubinski, A. (1962): Helical Buckling of Tubing Sealed in Packers
- Mitchell, R. & Samuel, R. (2009): How Good Is the Thin Shell Approximation
- Halliburton Red Book, Baker Hughes Completion Engineering Guide
"""
import math
from typing import Dict, Any, Optional


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
