"""
Workover Hydraulics Calculation Engine

Coiled tubing (CT) and workover hydraulics calculations including pressure losses,
snubbing forces, weight/drag in wellbore, and maximum CT reach estimation.

References:
- ICoTA Coiled Tubing Manual
- Bourgoyne et al.: Applied Drilling Engineering
- Reutilizes HydraulicsEngine.pressure_loss_bingham() for pipe/annular pressure loss
"""
import math
from typing import List, Dict, Any, Optional


class WorkoverHydraulicsEngine:
    """
    Implements workover/CT hydraulic calculations.
    All methods are @staticmethod — no external dependencies beyond math.
    """

    # Common CT sizes (OD inches): 1.25, 1.5, 1.75, 2.0, 2.375, 2.625, 2.875, 3.5
    STEEL_DENSITY = 490.0        # lb/ft³
    STEEL_WEIGHT_WATER = 65.5    # ppg equivalent
    GRAVITY = 32.174             # ft/s²

    @staticmethod
    def calculate_ct_dimensions(
        ct_od: float,
        wall_thickness: float
    ) -> Dict[str, Any]:
        """
        Calculate coiled tubing geometric properties.

        Args:
            ct_od: CT outer diameter (inches)
            wall_thickness: CT wall thickness (inches)

        Returns:
            Dict with ct_id, cross_section_area, inner_area, metal_area, weight_per_ft
        """
        ct_id = ct_od - 2 * wall_thickness
        if ct_id <= 0 or ct_od <= 0:
            return {"error": "Invalid CT dimensions"}

        outer_area = math.pi / 4.0 * ct_od ** 2       # in²
        inner_area = math.pi / 4.0 * ct_id ** 2        # in²
        metal_area = outer_area - inner_area            # in²

        # Weight per foot: steel density × metal area / 144 (in²→ft²)
        weight_per_ft = WorkoverHydraulicsEngine.STEEL_DENSITY * metal_area / 144.0  # lb/ft

        return {
            "ct_od_in": ct_od,
            "ct_id_in": round(ct_id, 3),
            "wall_thickness_in": wall_thickness,
            "outer_area_in2": round(outer_area, 4),
            "inner_area_in2": round(inner_area, 4),
            "metal_area_in2": round(metal_area, 4),
            "weight_per_ft_lb": round(weight_per_ft, 3)
        }

    @staticmethod
    def calculate_ct_pressure_loss(
        flow_rate: float,
        mud_weight: float,
        pv: float,
        yp: float,
        ct_od: float,
        ct_id: float,
        ct_length: float,
        hole_id: float,
        annular_length: float
    ) -> Dict[str, Any]:
        """
        Calculate CT pressure losses through pipe and annulus using Bingham Plastic model.
        Adapts standard hydraulics for small CT diameters (1.5"-3.5").

        Args:
            flow_rate: pump rate (gpm) — typical CT: 0.5-4 bpm (21-168 gpm)
            mud_weight: fluid density (ppg)
            pv: plastic viscosity (cP)
            yp: yield point (lb/100ft²)
            ct_od: coiled tubing OD (inches)
            ct_id: coiled tubing ID (inches)
            ct_length: total CT length (ft)
            hole_id: wellbore/casing ID (inches)
            annular_length: annular length (ft)

        Returns:
            Dict with pipe_loss, annular_loss, total_loss, velocities, regime
        """
        if flow_rate <= 0 or ct_length <= 0:
            return {
                "pipe_loss_psi": 0.0, "annular_loss_psi": 0.0,
                "total_loss_psi": 0.0, "pipe_velocity_ftmin": 0.0,
                "annular_velocity_ftmin": 0.0, "pipe_regime": "none",
                "annular_regime": "none"
            }

        # --- Pipe flow (inside CT) ---
        d_eff_pipe = ct_id
        if d_eff_pipe <= 0:
            v_pipe = 0.0
            dp_pipe = 0.0
            re_pipe = 0.0
            regime_pipe = "none"
        else:
            v_pipe = 24.5 * flow_rate / (d_eff_pipe ** 2)
            re_pipe = 928.0 * mud_weight * v_pipe * d_eff_pipe / pv if pv > 0 else 99999
            he_pipe = 37100.0 * mud_weight * yp * d_eff_pipe ** 2 / (pv ** 2) if pv > 0 else 0
            re_crit_pipe = 2100.0 + 7.3 * (he_pipe ** 0.58) if he_pipe > 0 else 2100.0

            regime_pipe = "laminar" if re_pipe < re_crit_pipe else "turbulent"

            if regime_pipe == "laminar":
                dp_pipe = (pv * v_pipe * ct_length) / (1500.0 * d_eff_pipe ** 2) + \
                          (yp * ct_length) / (225.0 * d_eff_pipe)
            else:
                f = 0.0791 / (re_pipe ** 0.25) if re_pipe > 0 else 0.01
                v_pipe_fps = v_pipe / 60.0  # Convert ft/min to ft/s for Bourgoyne formula
                dp_pipe = (f * mud_weight * v_pipe_fps ** 2 * ct_length) / (25.8 * d_eff_pipe)

        # --- Annular flow (CT in wellbore) ---
        d_eff_ann = hole_id - ct_od
        if d_eff_ann <= 0 or annular_length <= 0:
            v_ann = 0.0
            dp_ann = 0.0
            re_ann = 0.0
            regime_ann = "none"
        else:
            v_ann = 24.5 * flow_rate / (hole_id ** 2 - ct_od ** 2)
            re_ann = 757.0 * mud_weight * v_ann * d_eff_ann / pv if pv > 0 else 99999
            he_ann = 37100.0 * mud_weight * yp * d_eff_ann ** 2 / (pv ** 2) if pv > 0 else 0
            re_crit_ann = 2100.0 + 7.3 * (he_ann ** 0.58) if he_ann > 0 else 2100.0

            regime_ann = "laminar" if re_ann < re_crit_ann else "turbulent"

            if regime_ann == "laminar":
                dp_ann = (pv * v_ann * annular_length) / (1000.0 * d_eff_ann ** 2) + \
                         (yp * annular_length) / (200.0 * d_eff_ann)
            else:
                f = 0.0791 / (re_ann ** 0.25) if re_ann > 0 else 0.01
                v_ann_fps = v_ann / 60.0  # Convert ft/min to ft/s for Bourgoyne formula
                dp_ann = (f * mud_weight * v_ann_fps ** 2 * annular_length) / (21.1 * d_eff_ann)

        total_loss = dp_pipe + dp_ann

        return {
            "pipe_loss_psi": round(dp_pipe, 1),
            "annular_loss_psi": round(dp_ann, 1),
            "total_loss_psi": round(total_loss, 1),
            "pipe_velocity_ftmin": round(v_pipe, 1),
            "annular_velocity_ftmin": round(v_ann, 1),
            "pipe_reynolds": round(re_pipe, 0),
            "annular_reynolds": round(re_ann, 0),
            "pipe_regime": regime_pipe,
            "annular_regime": regime_ann
        }

    @staticmethod
    def calculate_ct_buoyed_weight(
        weight_per_ft: float,
        length: float,
        mud_weight: float,
        inclination: float = 0.0
    ) -> Dict[str, Any]:
        """
        Calculate buoyed CT string weight considering inclination.

        Args:
            weight_per_ft: CT weight (lb/ft)
            length: CT length in hole (ft)
            mud_weight: fluid density (ppg)
            inclination: average inclination (degrees)

        Returns:
            Dict with air_weight, buoyancy_factor, buoyed_weight, axial_component
        """
        if length <= 0 or weight_per_ft <= 0:
            return {
                "air_weight_lb": 0.0, "buoyancy_factor": 1.0,
                "buoyed_weight_lb": 0.0, "axial_component_lb": 0.0
            }

        bf = 1.0 - (mud_weight / WorkoverHydraulicsEngine.STEEL_WEIGHT_WATER)
        bf = max(bf, 0.0)

        air_weight = weight_per_ft * length
        buoyed_weight = air_weight * bf

        # Axial component (weight contributing to tension/compression)
        incl_rad = math.radians(inclination)
        axial_component = buoyed_weight * math.cos(incl_rad)

        return {
            "air_weight_lb": round(air_weight, 0),
            "buoyancy_factor": round(bf, 4),
            "buoyed_weight_lb": round(buoyed_weight, 0),
            "axial_component_lb": round(axial_component, 0)
        }

    @staticmethod
    def calculate_ct_drag(
        buoyed_weight: float,
        inclination: float,
        friction_factor: float = 0.25
    ) -> Dict[str, Any]:
        """
        Calculate CT drag force in wellbore.

        F_drag = mu * W_buoyed * sin(incl)

        Args:
            buoyed_weight: buoyed CT weight (lb)
            inclination: average inclination (degrees)
            friction_factor: wellbore friction coefficient (0.15-0.40)

        Returns:
            Dict with drag_force, normal_force, friction_factor
        """
        incl_rad = math.radians(inclination)
        normal_force = buoyed_weight * math.sin(incl_rad)
        drag_force = friction_factor * normal_force

        return {
            "drag_force_lb": round(drag_force, 0),
            "normal_force_lb": round(normal_force, 0),
            "friction_factor": friction_factor
        }

    @staticmethod
    def calculate_snubbing_force(
        wellhead_pressure: float,
        ct_od: float,
        buoyed_weight: float,
        ct_length_in_hole: float,
        weight_per_ft: float,
        mud_weight: float
    ) -> Dict[str, Any]:
        """
        Calculate snubbing force for CT operations under pressure.

        F_snub = P_wellhead × A_pipe - W_buoyed
        Light point: when F_snub = 0 (pipe weight = pressure force)

        Args:
            wellhead_pressure: surface pressure (psi)
            ct_od: CT outer diameter (inches)
            buoyed_weight: total buoyed weight in hole (lb)
            ct_length_in_hole: CT length in hole (ft)
            weight_per_ft: CT weight (lb/ft)
            mud_weight: fluid density (ppg)

        Returns:
            Dict with snubbing_force, pipe_light status, light_heavy_point
        """
        # Wellhead force pushing pipe out
        pipe_area = math.pi / 4.0 * ct_od ** 2
        pressure_force = wellhead_pressure * pipe_area

        # Net snubbing force (positive = must push pipe in)
        snubbing_force = pressure_force - buoyed_weight

        pipe_light = snubbing_force > 0

        # Light/Heavy point: depth where buoyed weight = pressure force
        bf = 1.0 - (mud_weight / WorkoverHydraulicsEngine.STEEL_WEIGHT_WATER)
        buoyed_weight_per_ft = weight_per_ft * max(bf, 0.01)

        light_heavy_depth = 0.0
        if buoyed_weight_per_ft > 0:
            light_heavy_depth = pressure_force / buoyed_weight_per_ft

        return {
            "snubbing_force_lb": round(snubbing_force, 0),
            "pressure_force_lb": round(pressure_force, 0),
            "buoyed_weight_lb": round(buoyed_weight, 0),
            "pipe_light": pipe_light,
            "light_heavy_depth_ft": round(light_heavy_depth, 0),
            "wellhead_pressure_psi": wellhead_pressure
        }

    @staticmethod
    def calculate_max_reach(
        ct_od: float,
        ct_id: float,
        wall_thickness: float,
        weight_per_ft: float,
        mud_weight: float,
        inclination: float,
        friction_factor: float,
        wellhead_pressure: float = 0.0,
        yield_strength_psi: float = 80000.0
    ) -> Dict[str, Any]:
        """
        Estimate maximum CT reach based on helical buckling and yield limits.

        The CT will buckle when compressive force exceeds critical buckling load,
        limiting how far the CT can be pushed into a horizontal section.

        Args:
            ct_od: CT OD (inches)
            ct_id: CT ID (inches)
            wall_thickness: CT wall (inches)
            weight_per_ft: CT weight (lb/ft)
            mud_weight: fluid density (ppg)
            inclination: wellbore inclination (degrees)
            friction_factor: friction coefficient
            wellhead_pressure: surface pressure (psi)
            yield_strength_psi: CT yield strength (psi, typically 70-110 ksi)

        Returns:
            Dict with max_reach estimates and limiting factors
        """
        bf = 1.0 - (mud_weight / WorkoverHydraulicsEngine.STEEL_WEIGHT_WATER)
        buoyed_wt_per_ft = weight_per_ft * max(bf, 0.01)

        # Moment of inertia
        I = math.pi / 64.0 * (ct_od ** 4 - ct_id ** 4)  # in⁴

        # Metal cross-section area
        A_s = math.pi / 4.0 * (ct_od ** 2 - ct_id ** 2)  # in²

        # Young's modulus for steel
        E = 30e6  # psi

        # Radial clearance (assume 7" casing for typical CT ops)
        r_clearance = (7.0 - ct_od) / 2.0  # inches
        if r_clearance <= 0:
            r_clearance = 1.0  # minimum guess

        incl_rad = math.radians(inclination)

        # --- Helical buckling limit ---
        # Paslay-Dawson: F_hb = sqrt(8 * E * I * w * sin(incl) / r)
        w_n = buoyed_wt_per_ft * math.sin(incl_rad) / 12.0  # lb/in (normal component)

        if w_n > 0 and r_clearance > 0:
            F_hb = math.sqrt(8.0 * E * I * w_n / r_clearance)
        else:
            F_hb = yield_strength_psi * A_s  # fallback to yield

        # --- Yield limit ---
        F_yield = yield_strength_psi * A_s

        # --- Pressure force at surface ---
        pipe_area = math.pi / 4.0 * ct_od ** 2
        F_pressure = wellhead_pressure * pipe_area

        # --- Maximum push force available ---
        # In horizontal section, the weight axial component is near zero
        # Max force = weight of vertical/build section - drag losses
        # Simplified: max push ≈ buoyed weight of vertical section - drag
        max_push = max(F_hb, 0)

        # Max horizontal reach: L = F_push / (mu * w_n * 12)
        friction_per_ft = friction_factor * buoyed_wt_per_ft * math.sin(incl_rad) if inclination > 5 else buoyed_wt_per_ft * friction_factor * 0.1
        if friction_per_ft > 0:
            max_reach_ft = max_push / friction_per_ft
        else:
            max_reach_ft = 50000.0  # essentially unlimited in vertical

        # Cap at practical limit
        max_reach_ft = min(max_reach_ft, 35000.0)

        limiting_factor = "Helical Buckling"
        if F_yield < F_hb:
            limiting_factor = "CT Yield Strength"
            max_reach_ft = min(max_reach_ft, F_yield / max(friction_per_ft, 0.01))

        return {
            "max_reach_ft": round(max_reach_ft, 0),
            "helical_buckling_load_lb": round(F_hb, 0),
            "yield_load_lb": round(F_yield, 0),
            "pressure_force_lb": round(F_pressure, 0),
            "limiting_factor": limiting_factor,
            "buoyed_wt_per_ft": round(buoyed_wt_per_ft, 3),
            "moment_of_inertia_in4": round(I, 6)
        }

    @staticmethod
    def calculate_workover_kill(
        reservoir_pressure: float,
        tvd: float,
        current_mud_weight: float,
        safety_margin_ppg: float = 0.3
    ) -> Dict[str, Any]:
        """
        Calculate kill fluid requirements for workover operations.

        Kill weight = (P_reservoir / (0.052 × TVD)) + safety_margin

        Args:
            reservoir_pressure: formation/reservoir pressure (psi)
            tvd: true vertical depth (ft)
            current_mud_weight: current fluid weight (ppg)
            safety_margin_ppg: overbalance safety margin (ppg)

        Returns:
            Dict with kill_weight, hydrostatic, overbalance
        """
        if tvd <= 0:
            return {
                "kill_weight_ppg": current_mud_weight,
                "required_bhp_psi": reservoir_pressure,
                "current_bhp_psi": 0.0,
                "overbalance_psi": 0.0,
                "status": "Error: Zero TVD"
            }

        # Required kill weight
        kill_weight = (reservoir_pressure / (0.052 * tvd)) + safety_margin_ppg

        # Current hydrostatic
        current_bhp = 0.052 * current_mud_weight * tvd
        required_bhp = 0.052 * kill_weight * tvd

        overbalance = required_bhp - reservoir_pressure

        status = "Overbalanced"
        if current_bhp < reservoir_pressure:
            status = "UNDERBALANCED — Kill required"
        elif current_bhp >= reservoir_pressure and current_mud_weight < kill_weight:
            status = "Marginal — Weight up recommended"

        return {
            "kill_weight_ppg": round(kill_weight, 2),
            "required_bhp_psi": round(required_bhp, 0),
            "current_bhp_psi": round(current_bhp, 0),
            "reservoir_pressure_psi": reservoir_pressure,
            "overbalance_psi": round(overbalance, 0),
            "safety_margin_ppg": safety_margin_ppg,
            "status": status
        }

    @staticmethod
    def calculate_ct_elongation(
        ct_od: float,
        ct_id: float,
        ct_length: float,
        weight_per_ft: float,
        mud_weight: float,
        delta_p_internal: float = 0.0,
        delta_t: float = 0.0,
        wellhead_pressure: float = 0.0,
        annular_pressure: float = 0.0
    ) -> Dict[str, Any]:
        """
        Calculate CT elongation/shortening from four physical mechanisms.

        Components:
        1. Weight (Hooke's triangular load): dL_weight = W * L / (2 * E * A_s)
        2. Temperature: dL_temp = alpha * delta_T * L
        3. Ballooning (Poisson effect): dL_balloon = -2*nu * (Pi*Ai - Po*Ao) * L / (E * A_s)
        4. Bourdon (internal pressure end force): dL_bourdon = delta_P * Ai * L / (E * A_s)

        Parameters:
        - ct_od, ct_id: CT dimensions (inches)
        - ct_length: CT length in hole (ft)
        - weight_per_ft: CT weight (lb/ft)
        - mud_weight: fluid density (ppg) — for buoyancy
        - delta_p_internal: differential internal pressure above hydrostatic (psi)
        - delta_t: average temperature change from surface condition (°F, positive = hotter)
        - wellhead_pressure: surface treating pressure (psi)
        - annular_pressure: annular surface pressure (psi)

        Returns:
        - Individual elongation components and total (ft)
        """
        if ct_od <= 0 or ct_id <= 0 or ct_length <= 0:
            return {
                "dL_weight_ft": 0.0, "dL_temperature_ft": 0.0,
                "dL_ballooning_ft": 0.0, "dL_bourdon_ft": 0.0,
                "dL_total_ft": 0.0, "depth_correction_ft": 0.0
            }

        # Steel properties
        E = 30e6           # Young's modulus, psi
        alpha = 6.9e-6     # Thermal expansion coefficient, 1/°F (steel)
        nu = 0.30           # Poisson's ratio (steel)

        # Cross-section areas (in²)
        A_o = math.pi / 4.0 * ct_od**2   # Outer area
        A_i = math.pi / 4.0 * ct_id**2   # Inner area
        A_s = A_o - A_i                    # Metal (steel) area

        if A_s <= 0:
            return {
                "dL_weight_ft": 0.0, "dL_temperature_ft": 0.0,
                "dL_ballooning_ft": 0.0, "dL_bourdon_ft": 0.0,
                "dL_total_ft": 0.0, "depth_correction_ft": 0.0
            }

        # Buoyed weight of entire CT string (lb)
        bf = max(1.0 - (mud_weight / 65.5), 0.0)
        W_buoyed = weight_per_ft * bf * ct_length

        # 1. Weight elongation (triangular load — CG at L/2)
        # dL = W * L / (2 * E * A_s)  — W in lb, L in inches
        L_in = ct_length * 12.0  # convert to inches
        dL_weight_in = W_buoyed * L_in / (2.0 * E * A_s)
        dL_weight_ft = dL_weight_in / 12.0

        # 2. Temperature elongation
        dL_temp_ft = alpha * delta_t * ct_length

        # 3. Ballooning (Poisson shortening from internal/external pressure)
        # Pressure at surface: internal = wellhead_pressure, external = annular_pressure
        # dL_balloon = -2*nu * (Pi*Ai - Po*Ao) * L / (E * A_s)
        Pi = wellhead_pressure + delta_p_internal  # Average internal pressure (simplified)
        Po = annular_pressure                        # Average external pressure
        dL_balloon_in = -2.0 * nu * (Pi * A_i - Po * A_o) * L_in / (E * A_s)
        dL_balloon_ft = dL_balloon_in / 12.0

        # 4. Bourdon effect (pressure end-force on closed end)
        # dL_bourdon = delta_P * Ai * L / (E * A_s)
        delta_P_net = Pi - Po
        dL_bourdon_in = delta_P_net * A_i * L_in / (E * A_s)
        dL_bourdon_ft = dL_bourdon_in / 12.0

        # Total elongation
        dL_total_ft = dL_weight_ft + dL_temp_ft + dL_balloon_ft + dL_bourdon_ft

        return {
            "dL_weight_ft": round(dL_weight_ft, 4),
            "dL_temperature_ft": round(dL_temp_ft, 4),
            "dL_ballooning_ft": round(dL_balloon_ft, 4),
            "dL_bourdon_ft": round(dL_bourdon_ft, 4),
            "dL_total_ft": round(dL_total_ft, 4),
            "depth_correction_ft": round(-dL_total_ft, 4),
            "ct_length_ft": ct_length,
            "metal_area_in2": round(A_s, 4),
            "buoyed_weight_lb": round(W_buoyed, 0)
        }

    @staticmethod
    def calculate_ct_fatigue(
        ct_od: float,
        wall_thickness: float,
        reel_diameter: float,
        internal_pressure: float = 0.0,
        yield_strength_psi: float = 80000.0,
        trips_history: Optional[List[Dict[str, float]]] = None
    ) -> Dict[str, Any]:
        """
        Calculate CT fatigue life based on bending/pressure strains and Miner's rule.

        Based on API RP 5C7 low-cycle fatigue methodology:
        1. Bending strain on reel: eps_bend = OD / (2 * R_reel)
        2. Pressure strain: eps_pressure = P * ID / (2 * wall * E)
        3. Total strain: eps_total = eps_bend + eps_pressure
        4. Cycles to failure: N_f = C / eps_total^m  (S-N curve parameters)
        5. Miner's rule: D = sum(n_i / N_f_i), failure at D >= 1.0

        Parameters:
        - ct_od: CT outer diameter (inches)
        - wall_thickness: CT wall thickness (inches)
        - reel_diameter: guide arch / reel core diameter (inches, typical 72"-120")
        - internal_pressure: treating pressure during bending (psi)
        - yield_strength_psi: CT yield strength (psi)
        - trips_history: list of {pressure_psi, cycles} for accumulated damage
                         (each entry = one set of bending trips at a given pressure)

        Returns:
        - Strain components, cycles to failure, remaining life
        """
        ct_id = ct_od - 2.0 * wall_thickness
        if ct_od <= 0 or wall_thickness <= 0 or ct_id <= 0 or reel_diameter <= 0:
            return {
                "error": "Invalid CT or reel dimensions",
                "strain_bending_pct": 0.0, "strain_pressure_pct": 0.0,
                "strain_total_pct": 0.0, "cycles_to_failure": 0,
                "remaining_life_pct": 0.0
            }

        E = 30e6  # psi

        # 1. Bending strain (from winding/unwinding CT on reel)
        R_reel = reel_diameter / 2.0  # inches
        eps_bending = ct_od / (2.0 * R_reel)

        # 2. Pressure strain (hoop stress contribution to axial strain via Poisson)
        # Simplified: eps_pressure = P * ct_id / (2 * wall * E)
        eps_pressure = 0.0
        if internal_pressure > 0 and wall_thickness > 0:
            eps_pressure = internal_pressure * ct_id / (2.0 * wall_thickness * E)

        # Total strain per cycle
        eps_total = eps_bending + eps_pressure

        # 3. S-N curve parameters (API RP 5C7 typical for CT-80/CT-90 steel)
        # N_f = C / eps_total^m
        # Higher grade steel is stronger but more fatigue-sensitive under cyclic bending.
        # m is kept constant (material-class dependent), C decreases with grade.
        # Conservative values for planning:
        m = 2.5  # Exponent for all CT grades (API RP 5C7 typical)
        if yield_strength_psi >= 110000:
            C = 0.020    # Higher grade → more brittle, fewer cycles
        elif yield_strength_psi >= 90000:
            C = 0.028
        else:
            C = 0.038    # CT-80 baseline (most ductile)

        # Cycles to failure at current conditions
        if eps_total > 0:
            N_f = C / (eps_total ** m)
            N_f = max(int(N_f), 1)
        else:
            N_f = 999999

        # 4. Miner's rule — accumulated damage from history
        damage_accumulated = 0.0
        damage_breakdown = []

        if trips_history:
            for entry in trips_history:
                p_hist = entry.get("pressure_psi", 0.0)
                n_cycles = entry.get("cycles", 0)

                # Recalculate strain at historical pressure
                eps_p_hist = 0.0
                if p_hist > 0 and wall_thickness > 0:
                    eps_p_hist = p_hist * ct_id / (2.0 * wall_thickness * E)
                eps_hist = eps_bending + eps_p_hist

                if eps_hist > 0:
                    N_f_hist = C / (eps_hist ** m)
                    N_f_hist = max(N_f_hist, 1.0)
                    damage_i = n_cycles / N_f_hist
                else:
                    damage_i = 0.0

                damage_accumulated += damage_i
                damage_breakdown.append({
                    "pressure_psi": p_hist,
                    "cycles": n_cycles,
                    "strain_pct": round(eps_hist * 100, 4),
                    "Nf": int(max(N_f_hist, 1)) if eps_hist > 0 else 999999,
                    "damage_fraction": round(damage_i, 6)
                })

        # Remaining life
        remaining_life_pct = max((1.0 - damage_accumulated) * 100.0, 0.0)

        # Remaining cycles at current pressure
        if N_f > 0 and damage_accumulated < 1.0:
            remaining_cycles = int(N_f * (1.0 - damage_accumulated))
        else:
            remaining_cycles = 0

        return {
            "strain_bending_pct": round(eps_bending * 100, 4),
            "strain_pressure_pct": round(eps_pressure * 100, 4),
            "strain_total_pct": round(eps_total * 100, 4),
            "cycles_to_failure": N_f,
            "remaining_life_pct": round(remaining_life_pct, 2),
            "remaining_cycles_at_current_pressure": remaining_cycles,
            "damage_accumulated": round(damage_accumulated, 6),
            "damage_breakdown": damage_breakdown,
            "sn_parameters": {"C": C, "m": m, "grade_class": "CT-80" if yield_strength_psi < 90000 else "CT-90+" },
            "reel_diameter_in": reel_diameter,
            "internal_pressure_psi": internal_pressure
        }

    @staticmethod
    def calculate_full_workover(
        flow_rate: float,
        mud_weight: float,
        pv: float,
        yp: float,
        ct_od: float,
        wall_thickness: float,
        ct_length: float,
        hole_id: float,
        tvd: float,
        inclination: float = 0.0,
        friction_factor: float = 0.25,
        wellhead_pressure: float = 0.0,
        reservoir_pressure: float = 0.0,
        yield_strength_psi: float = 80000.0
    ) -> Dict[str, Any]:
        """
        Complete workover hydraulics analysis combining all calculations.

        Returns:
            Dict with summary, force_analysis, hydraulics, kill_data, alerts
        """
        eng = WorkoverHydraulicsEngine

        # CT dimensions
        dims = eng.calculate_ct_dimensions(ct_od, wall_thickness)
        if "error" in dims:
            return {"summary": {}, "alerts": [dims["error"]]}

        ct_id = dims["ct_id_in"]
        weight_per_ft = dims["weight_per_ft_lb"]

        # Hydraulics
        hydraulics = eng.calculate_ct_pressure_loss(
            flow_rate, mud_weight, pv, yp,
            ct_od, ct_id, ct_length, hole_id, ct_length
        )

        # Buoyed weight
        weight_data = eng.calculate_ct_buoyed_weight(
            weight_per_ft, ct_length, mud_weight, inclination
        )

        # Drag
        drag_data = eng.calculate_ct_drag(
            weight_data["buoyed_weight_lb"], inclination, friction_factor
        )

        # Snubbing
        snubbing = eng.calculate_snubbing_force(
            wellhead_pressure, ct_od,
            weight_data["buoyed_weight_lb"], ct_length,
            weight_per_ft, mud_weight
        )

        # Max reach
        reach = eng.calculate_max_reach(
            ct_od, ct_id, wall_thickness, weight_per_ft,
            mud_weight, inclination, friction_factor,
            wellhead_pressure, yield_strength_psi
        )

        # Kill calculation
        kill_data = eng.calculate_workover_kill(
            reservoir_pressure, tvd, mud_weight
        )

        # CT Elongation
        elongation = eng.calculate_ct_elongation(
            ct_od=ct_od, ct_id=ct_id, ct_length=ct_length,
            weight_per_ft=weight_per_ft, mud_weight=mud_weight,
            delta_p_internal=hydraulics["pipe_loss_psi"],
            delta_t=0.0,  # Default — caller can override
            wellhead_pressure=wellhead_pressure,
            annular_pressure=0.0
        )

        # Alerts
        alerts = []
        if snubbing["pipe_light"]:
            alerts.append(f"CT is pipe-light! Snubbing force: {snubbing['snubbing_force_lb']:.0f} lb. Use snubbing unit.")
        if hydraulics["total_loss_psi"] > 5000:
            alerts.append(f"High total pressure loss: {hydraulics['total_loss_psi']:.0f} psi — verify CT pressure rating")
        if ct_length > reach["max_reach_ft"]:
            alerts.append(f"CT length {ct_length:.0f} ft exceeds max reach {reach['max_reach_ft']:.0f} ft — risk of helical buckling")
        if kill_data["status"].startswith("UNDERBALANCED"):
            alerts.append(f"Well is underbalanced! Kill weight required: {kill_data['kill_weight_ppg']:.2f} ppg")
        if hydraulics["pipe_velocity_ftmin"] > 600:
            alerts.append(f"High pipe velocity {hydraulics['pipe_velocity_ftmin']:.0f} ft/min — erosion risk in CT")
        if drag_data["drag_force_lb"] > weight_data["buoyed_weight_lb"] * 0.5:
            alerts.append("Drag force exceeds 50% of buoyed weight — consider friction reducer")

        summary = {
            "total_pressure_loss_psi": hydraulics["total_loss_psi"],
            "pipe_loss_psi": hydraulics["pipe_loss_psi"],
            "annular_loss_psi": hydraulics["annular_loss_psi"],
            "buoyed_weight_lb": weight_data["buoyed_weight_lb"],
            "drag_force_lb": drag_data["drag_force_lb"],
            "snubbing_force_lb": snubbing["snubbing_force_lb"],
            "pipe_light": snubbing["pipe_light"],
            "max_reach_ft": reach["max_reach_ft"],
            "kill_weight_ppg": kill_data["kill_weight_ppg"],
            "limiting_factor": reach["limiting_factor"],
            "alerts": alerts
        }

        # Elongation alert
        if abs(elongation.get("dL_total_ft", 0)) > 5.0:
            alerts.append(f"Significant CT elongation: {elongation['dL_total_ft']:.2f} ft — adjust depth tags")

        return {
            "summary": summary,
            "hydraulics": hydraulics,
            "ct_dimensions": dims,
            "weight_analysis": weight_data,
            "drag_analysis": drag_data,
            "snubbing": snubbing,
            "max_reach": reach,
            "kill_data": kill_data,
            "elongation": elongation,
            "parameters": {
                "flow_rate_gpm": flow_rate,
                "mud_weight_ppg": mud_weight,
                "pv_cp": pv,
                "yp_lb100ft2": yp,
                "ct_od_in": ct_od,
                "wall_thickness_in": wall_thickness,
                "ct_length_ft": ct_length,
                "hole_id_in": hole_id,
                "tvd_ft": tvd,
                "inclination_deg": inclination,
                "friction_factor": friction_factor,
                "wellhead_pressure_psi": wellhead_pressure,
                "reservoir_pressure_psi": reservoir_pressure,
                "yield_strength_psi": yield_strength_psi
            },
            "alerts": alerts
        }
