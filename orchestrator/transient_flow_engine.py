"""
TransientFlowEngine — Kick migration and kill circulation simulation.

Models:
- Gas kick migration (rising gas in closed wellbore)
- Kill circulation step-by-step (Driller's Method & Wait-and-Weight)
- Surge/swab transient pressure estimation

Uses DAK Z-factor from WellControlEngine for real gas behavior.
"""
import math
from typing import Dict, Any, List, Optional


class TransientFlowEngine:
    """Transient flow simulation for well control scenarios."""

    # Default gas properties
    DEFAULT_GAS_GRAVITY = 0.65
    DEFAULT_TEMPERATURE_GRADIENT = 1.5  # °F per 100 ft (geothermal)
    DEFAULT_SURFACE_TEMP = 80.0  # °F
    DEFAULT_GAS_MIGRATION_RATE = 1000.0  # ft/hr (typical gas migration in mud)

    # ── Z-factor (standalone, avoids circular import) ──────────────

    @staticmethod
    def _z_factor_dak(pressure_psia: float, temperature_f: float, gas_gravity: float = 0.65) -> float:
        """
        DAK Z-factor correlation (simplified Newton-Raphson).
        Standalone implementation to avoid importing WellControlEngine.
        """
        if pressure_psia <= 0 or gas_gravity <= 0:
            return 1.0

        sg = gas_gravity
        t_pc = 168.0 + 325.0 * sg - 12.5 * sg ** 2
        p_pc = 677.0 + 15.0 * sg - 37.5 * sg ** 2

        t_pr = max((temperature_f + 460.0) / t_pc, 1.05)
        p_pr = pressure_psia / p_pc

        # DAK coefficients
        A1, A2, A3, A4, A5 = 0.3265, -1.0700, -0.5339, 0.01569, -0.05165
        A6, A7, A8 = 0.5475, -0.7361, 0.1844
        A9, A10, A11 = 0.1056, 0.6134, 0.7210

        z = 1.0
        for _ in range(20):
            rho_r = 0.27 * p_pr / (z * t_pr)

            c1 = A1 + A2 / t_pr + A3 / t_pr ** 3 + A4 / t_pr ** 4 + A5 / t_pr ** 5
            c2 = A6 + A7 / t_pr + A8 / t_pr ** 2
            c3 = A9 * (A7 / t_pr + A8 / t_pr ** 2)
            c4_exp = -A11 * rho_r ** 2
            c4 = A10 * (1.0 + A11 * rho_r ** 2) * (rho_r ** 2 / t_pr ** 3) * math.exp(c4_exp)

            f_z = z - (1.0 + c1 * rho_r + c2 * rho_r ** 2 - c3 * rho_r ** 5 + c4)

            d_rho_dz = -rho_r / z
            dc4_drho = (
                A10 * rho_r / t_pr ** 3
                * (2.0 * (1.0 + A11 * rho_r ** 2) + 2.0 * A11 * rho_r ** 2)
                * math.exp(c4_exp)
                + A10 * (1.0 + A11 * rho_r ** 2) * (rho_r ** 2 / t_pr ** 3) * math.exp(c4_exp) * (-2.0 * A11 * rho_r)
            )

            df_dz = 1.0 - (c1 + 2.0 * c2 * rho_r - 5.0 * c3 * rho_r ** 4 + dc4_drho) * d_rho_dz

            if abs(df_dz) < 1e-15:
                break

            z_new = max(0.05, min(z - f_z / df_dz, 3.0))
            if abs(z_new - z) < 1e-6:
                z = z_new
                break
            z = z_new

        return z

    # ── Gas Kick Migration Simulation ──────────────────────────────

    @staticmethod
    def simulate_kick_migration(
        well_depth_tvd: float,
        mud_weight: float,
        kick_volume_bbl: float,
        kick_gradient: float,
        sidpp: float,
        sicp: float,
        annular_capacity_bbl_ft: float,
        time_steps_min: int = 60,
        gas_gravity: float = 0.65,
        migration_rate_ft_hr: float = 1000.0,
        surface_temp_f: float = 80.0,
        temp_gradient_f_per_100ft: float = 1.5,
    ) -> Dict[str, Any]:
        """
        Simulate gas kick migration in a shut-in well.

        As gas migrates upward:
        - It moves to lower-pressure zones
        - Z-factor changes → gas expands
        - Both SIDPP and SICP increase if well is kept shut-in

        Parameters:
        - well_depth_tvd: TVD in ft
        - mud_weight: current mud weight in ppg
        - kick_volume_bbl: initial kick volume in bbl
        - kick_gradient: kick fluid pressure gradient (psi/ft), ~0.1 for gas
        - sidpp: shut-in drill pipe pressure (psi)
        - sicp: shut-in casing pressure (psi)
        - annular_capacity_bbl_ft: annular capacity (bbl/ft)
        - time_steps_min: total simulation time in minutes
        - gas_gravity: specific gravity of gas
        - migration_rate_ft_hr: gas migration rate (ft/hr)
        - surface_temp_f: surface temperature (°F)
        - temp_gradient_f_per_100ft: geothermal gradient

        Returns:
            {
                "time_series": [{"time_min", "kick_top_tvd", "kick_bottom_tvd",
                                 "kick_volume_bbl", "casing_pressure_psi",
                                 "drillpipe_pressure_psi", "z_factor"}],
                "max_casing_pressure": float,
                "surface_arrival_min": float or None,
            }
        """
        # Hydrostatic gradient
        mud_gradient = mud_weight * 0.052  # psi/ft

        # Initial kick position (bottom of well)
        kick_height_ft = kick_volume_bbl / annular_capacity_bbl_ft
        kick_bottom_tvd = well_depth_tvd
        kick_top_tvd = well_depth_tvd - kick_height_ft

        # Initial conditions
        # Bottom-hole pressure
        bhp = mud_gradient * well_depth_tvd + sidpp

        # Temperature at kick top
        temp_at_kick_top = surface_temp_f + (kick_top_tvd / 100.0) * temp_gradient_f_per_100ft

        # Pressure at kick top (hydrostatic above + casing pressure)
        pressure_at_kick_top = mud_gradient * kick_top_tvd + sicp

        # Z-factor at initial conditions
        z_initial = TransientFlowEngine._z_factor_dak(
            pressure_at_kick_top + 14.7, temp_at_kick_top, gas_gravity
        )

        # Track initial PV/ZT for real gas law
        t_initial_r = temp_at_kick_top + 460.0  # Rankine
        # PV = ZnRT, so nR = PV/(ZT) = const
        pv_zt_const = (pressure_at_kick_top + 14.7) * kick_volume_bbl / (z_initial * t_initial_r)

        time_series = []
        max_cp = sicp
        surface_arrival_min = None

        for t_min in range(0, time_steps_min + 1):
            # Migration distance
            migration_ft = migration_rate_ft_hr * (t_min / 60.0)

            # New kick top position
            new_kick_top = max(0.0, kick_top_tvd - migration_ft)

            # Temperature at new kick top
            temp_new = surface_temp_f + (new_kick_top / 100.0) * temp_gradient_f_per_100ft
            t_new_r = temp_new + 460.0

            # In a shut-in well, BHP stays constant (formation pressure)
            # Pressure at kick top = BHP - hydrostatic from kick top to bottom
            # But as gas migrates, the mud column above kick changes
            # Simplified: casing pressure increases to maintain BHP
            mud_above_kick = mud_gradient * new_kick_top

            # Pressure at kick top = mud_above_kick + new_casing_pressure
            # Gas column pressure contribution
            gas_height = kick_height_ft  # will update
            gas_hydrostatic = kick_gradient * gas_height

            # BHP must equal formation pressure (constant in shut-in well)
            # BHP = CP_new + mud_gradient * new_kick_top + kick_gradient * gas_height
            #       + mud_gradient * (well_depth_tvd - new_kick_top - gas_height)
            # Rearranging for CP_new:
            mud_below_kick = mud_gradient * (well_depth_tvd - new_kick_top - gas_height)
            cp_new = bhp - mud_above_kick - gas_hydrostatic - mud_below_kick

            # Ensure CP doesn't go below initial
            cp_new = max(cp_new, sicp)

            # Pressure at kick top for Z-factor
            p_kick_top = mud_above_kick + cp_new + 14.7

            # Z-factor at new conditions
            z_new = TransientFlowEngine._z_factor_dak(p_kick_top, temp_new, gas_gravity)

            # New gas volume from real gas law: V2 = nR * Z2 * T2 / P2
            v_new = pv_zt_const * z_new * t_new_r / p_kick_top if p_kick_top > 0 else kick_volume_bbl

            # Update kick height
            kick_height_ft = v_new / annular_capacity_bbl_ft if annular_capacity_bbl_ft > 0 else kick_height_ft

            # New bottom position
            new_kick_bottom = new_kick_top + kick_height_ft

            # Recalculate CP with updated gas height
            gas_hydrostatic = kick_gradient * kick_height_ft
            mud_below_kick = mud_gradient * max(0, well_depth_tvd - new_kick_top - kick_height_ft)
            cp_recalc = bhp - mud_above_kick - gas_hydrostatic - mud_below_kick
            cp_recalc = max(cp_recalc, sicp)

            # SIDPP also increases (same BHP, less hydrostatic due to gas expansion)
            dpp_new = bhp - mud_gradient * well_depth_tvd
            dpp_new = max(dpp_new, sidpp)

            max_cp = max(max_cp, cp_recalc)

            # Check surface arrival
            if new_kick_top <= 0 and surface_arrival_min is None:
                surface_arrival_min = t_min

            time_series.append({
                "time_min": t_min,
                "kick_top_tvd": round(new_kick_top, 1),
                "kick_bottom_tvd": round(min(new_kick_bottom, well_depth_tvd), 1),
                "kick_volume_bbl": round(v_new, 2),
                "casing_pressure_psi": round(cp_recalc, 1),
                "drillpipe_pressure_psi": round(dpp_new, 1),
                "z_factor": round(z_new, 4),
            })

        return {
            "time_series": time_series,
            "max_casing_pressure": round(max_cp, 1),
            "surface_arrival_min": surface_arrival_min,
        }

    # ── Kill Circulation Simulation ────────────────────────────────

    @staticmethod
    def simulate_kill_circulation(
        well_depth_tvd: float,
        mud_weight: float,
        kill_mud_weight: float,
        sidpp: float,
        scr: float,
        strokes_to_bit: int,
        strokes_bit_to_surface: int,
        method: str = "drillers",
        step_size: int = 50,
    ) -> Dict[str, Any]:
        """
        Simulate kill circulation step-by-step.

        Driller's Method:
        - 1st circulation: pump original mud, displace kick
          DPP starts at ICP, stays constant until kick out
        - 2nd circulation: pump kill mud
          DPP linearly decreases from ICP to FCP as kill mud fills drillstring

        Wait-and-Weight:
        - Single circulation with kill mud
          DPP linearly decreases from ICP to FCP as kill mud reaches bit
          Then FCP maintained as kill mud fills annulus

        Parameters:
        - well_depth_tvd: TVD in ft
        - mud_weight: original mud weight (ppg)
        - kill_mud_weight: kill mud weight (ppg)
        - sidpp: shut-in drill pipe pressure (psi)
        - scr: slow circulating rate pressure loss (psi)
        - strokes_to_bit: pump strokes from surface to bit
        - strokes_bit_to_surface: pump strokes from bit to surface
        - method: "drillers" or "wait_weight"
        - step_size: stroke interval for output points

        Returns:
            {
                "drill_pipe_pressure": [{"stroke", "pressure_psi"}],
                "casing_pressure": [{"stroke", "pressure_psi"}],
                "method": str,
                "icp": float,
                "fcp": float,
                "total_strokes": int,
            }
        """
        icp = sidpp + scr
        fcp = scr * (kill_mud_weight / mud_weight) if mud_weight > 0 else scr

        dpp_schedule = []
        cp_schedule = []

        if method == "drillers":
            # 1st circulation: displace kick with original mud
            total_first = strokes_to_bit + strokes_bit_to_surface
            for stroke in range(0, total_first + 1, step_size):
                # DPP stays at ICP during 1st circulation
                dpp_schedule.append({"stroke": stroke, "pressure_psi": round(icp, 1)})

                # CP varies as kick is displaced
                # Simplified: CP starts at sicp + scr, decreases as kick exits
                fraction_displaced = min(stroke / total_first, 1.0)
                # CP decreases as gas exits
                cp_val = icp - (icp - fcp) * fraction_displaced * 0.3
                cp_schedule.append({"stroke": stroke, "pressure_psi": round(cp_val, 1)})

            # 2nd circulation: pump kill mud
            for stroke in range(0, strokes_to_bit + strokes_bit_to_surface + 1, step_size):
                total_stroke = total_first + stroke
                if stroke <= strokes_to_bit:
                    # DPP linearly decreases from ICP to FCP as kill mud fills DP
                    fraction = stroke / strokes_to_bit if strokes_to_bit > 0 else 1.0
                    dpp = icp - (icp - fcp) * fraction
                else:
                    # Kill mud in annulus: DPP stays at FCP
                    dpp = fcp

                dpp_schedule.append({"stroke": total_stroke, "pressure_psi": round(dpp, 1)})

                # CP during 2nd circ decreases as heavy mud fills annulus
                fraction_annulus = max(0, stroke - strokes_to_bit) / strokes_bit_to_surface if strokes_bit_to_surface > 0 else 0
                cp_val = fcp * (1.0 - fraction_annulus * 0.3)
                cp_schedule.append({"stroke": total_stroke, "pressure_psi": round(max(cp_val, 0), 1)})

            total_strokes = total_first + strokes_to_bit + strokes_bit_to_surface

        else:  # wait_weight
            total_strokes = strokes_to_bit + strokes_bit_to_surface

            for stroke in range(0, total_strokes + 1, step_size):
                if stroke <= strokes_to_bit:
                    # DPP linearly from ICP to FCP
                    fraction = stroke / strokes_to_bit if strokes_to_bit > 0 else 1.0
                    dpp = icp - (icp - fcp) * fraction
                else:
                    # Kill mud in annulus: maintain FCP
                    dpp = fcp

                dpp_schedule.append({"stroke": stroke, "pressure_psi": round(dpp, 1)})

                # CP: decreases as kill mud displaces gas
                if stroke <= strokes_to_bit:
                    cp_val = icp - (icp - fcp) * (stroke / strokes_to_bit) * 0.5
                else:
                    frac = (stroke - strokes_to_bit) / strokes_bit_to_surface if strokes_bit_to_surface > 0 else 1.0
                    cp_val = fcp * (1.0 - frac * 0.4)
                cp_schedule.append({"stroke": stroke, "pressure_psi": round(max(cp_val, 0), 1)})

        return {
            "drill_pipe_pressure": dpp_schedule,
            "casing_pressure": cp_schedule,
            "method": method,
            "icp": round(icp, 1),
            "fcp": round(fcp, 1),
            "total_strokes": total_strokes,
        }

    # ── Surge/Swab Transient Estimation ────────────────────────────

    @staticmethod
    def estimate_surge_swab(
        trip_speed_ft_min: float,
        pipe_od: float,
        hole_id: float,
        mud_weight: float,
        pv: float,
        yp: float,
        pipe_length_ft: float,
        is_surge: bool = True,
    ) -> Dict[str, Any]:
        """
        Estimate surge or swab pressure from tripping operations.

        Uses Burkhardt's clinging factor approach:
        ΔP = f(v_pipe, annular_geometry, mud_rheology) * pipe_length

        Parameters:
        - trip_speed_ft_min: tripping speed (ft/min)
        - pipe_od: pipe outer diameter (inches)
        - hole_id: hole or casing inner diameter (inches)
        - mud_weight: mud weight (ppg)
        - pv: plastic viscosity (cP)
        - yp: yield point (lb/100ft²)
        - pipe_length_ft: length of pipe being tripped
        - is_surge: True for surge (running in), False for swab (pulling out)

        Returns:
            {"delta_p_psi", "ecd_ppg", "type"}
        """
        # Annular area ratio
        r_ratio = (pipe_od / hole_id) ** 2 if hole_id > 0 else 0

        # Clinging factor (Burkhardt)
        k_clinging = 0.45 * r_ratio + 0.21 * r_ratio ** 2

        # Effective annular velocity
        annular_area = (math.pi / 4.0) * ((hole_id / 12.0) ** 2 - (pipe_od / 12.0) ** 2)
        pipe_area = (math.pi / 4.0) * (pipe_od / 12.0) ** 2

        # Displaced fluid velocity in annulus
        v_annular = trip_speed_ft_min * (pipe_area / annular_area) if annular_area > 0 else 0
        v_eff = v_annular * (1.0 + k_clinging)

        # Annular pressure loss (Bingham Plastic, simplified)
        d_hyd = hole_id - pipe_od  # hydraulic diameter (inches)
        if d_hyd <= 0:
            return {"delta_p_psi": 0, "ecd_ppg": mud_weight, "type": "surge" if is_surge else "swab"}

        # Simplified Bingham annular ΔP/1000ft
        dp_per_1000 = (pv * v_eff) / (60000.0 * d_hyd ** 2) * 1000 + yp / (200.0 * d_hyd) * 1000

        delta_p = dp_per_1000 * pipe_length_ft / 1000.0

        # ECD equivalent
        if is_surge:
            ecd = mud_weight + delta_p / (0.052 * pipe_length_ft) if pipe_length_ft > 0 else mud_weight
        else:
            ecd = mud_weight - delta_p / (0.052 * pipe_length_ft) if pipe_length_ft > 0 else mud_weight

        return {
            "delta_p_psi": round(delta_p, 1),
            "ecd_ppg": round(ecd, 2),
            "type": "surge" if is_surge else "swab",
            "effective_velocity_ft_min": round(v_eff, 1),
            "clinging_factor": round(k_clinging, 4),
        }

    # ── Multiphase Drift-Flux Kick Migration ───────────────────────

    @staticmethod
    def simulate_kick_migration_multiphase(
        well_depth_tvd: float,
        mud_weight: float,
        kick_volume_bbl: float,
        sidpp: float,
        sicp: float,
        annular_id_in: float,
        pipe_od_in: float,
        gas_gravity: float = 0.65,
        time_steps_min: int = 120,
        dt_sec: float = 60.0,
        surface_temp_f: float = 80.0,
        temp_gradient: float = 1.5,
        n_cells: int = 50,
    ) -> Dict[str, Any]:
        """
        Multiphase kick migration using Zuber-Findlay drift-flux model.

        Discretizes the annulus into n_cells. Each cell tracks gas holdup,
        pressure, temperature, and mixture density. Gas velocity includes
        slip (drift) between gas and liquid phases.

        Zuber-Findlay: v_gas = C0 * v_mixture + v_drift
        where v_drift = 0.35 * sqrt(g * D_hyd * delta_rho / rho_liquid)
        """
        # Constants
        G_FT_S2 = 32.174
        C0 = 1.2
        BBL_TO_FT3 = 5.6146

        # Geometry
        d_hyd_in = annular_id_in - pipe_od_in
        d_hyd_ft = d_hyd_in / 12.0
        ann_area_ft2 = (math.pi / 4.0) * ((annular_id_in / 12.0) ** 2 - (pipe_od_in / 12.0) ** 2)

        # Cell setup
        cell_height_ft = well_depth_tvd / n_cells
        cell_volume_ft3 = ann_area_ft2 * cell_height_ft
        cell_volume_bbl = cell_volume_ft3 / BBL_TO_FT3

        # Mud properties
        mud_gradient = mud_weight * 0.052
        rho_mud_lbft3 = mud_weight * 7.48052

        # BHP (constant in shut-in well)
        bhp = mud_gradient * well_depth_tvd + sidpp

        # Initialize cells: [0] = surface, [n_cells-1] = TD
        cell_depths = [(i + 0.5) * cell_height_ft for i in range(n_cells)]
        gas_holdup = [0.0] * n_cells

        # Place initial kick at bottom
        kick_vol_ft3 = kick_volume_bbl * BBL_TO_FT3
        remaining = kick_vol_ft3
        for i in range(n_cells - 1, -1, -1):
            if remaining <= 0:
                break
            fill = min(remaining, cell_volume_ft3)
            gas_holdup[i] = fill / cell_volume_ft3
            remaining -= fill

        # Time loop
        n_time_steps = int(time_steps_min * 60 / dt_sec) + 1
        time_series = []
        max_cp = sicp
        surface_arrival_min = None

        for t_idx in range(n_time_steps):
            t_min = t_idx * dt_sec / 60.0

            # ── Compute pressure profile (top-down) ──
            pressures = [0.0] * n_cells
            cp_current = sicp
            for trial in range(3):
                pressures[0] = cp_current + 0.5 * cell_height_ft * (
                    rho_mud_lbft3 * (1 - gas_holdup[0]) * 0.006944
                )
                for i in range(1, n_cells):
                    temp_i = surface_temp_f + cell_depths[i] / 100.0 * temp_gradient
                    p_above = pressures[i - 1]

                    z_i = TransientFlowEngine._z_factor_dak(p_above + 14.7, temp_i, gas_gravity)
                    m_gas = 28.97 * gas_gravity
                    t_rankine = temp_i + 460.0
                    rho_gas = (p_above + 14.7) * m_gas / (z_i * 10.73 * t_rankine) if z_i > 0 else 0.1

                    rho_mix = rho_mud_lbft3 * (1 - gas_holdup[i]) + rho_gas * gas_holdup[i]
                    dp = rho_mix / 144.0 * cell_height_ft
                    pressures[i] = p_above + dp

                bhp_calc = pressures[n_cells - 1]
                cp_current += (bhp - bhp_calc) * 0.5
                cp_current = max(cp_current, 0)

            max_cp = max(max_cp, cp_current)

            # ── Compute gas velocities and advance holdup ──
            total_gas_vol_ft3 = 0.0
            max_gas_vel = 0.0
            max_hup = 0.0
            density_profile = []

            for i in range(n_cells):
                temp_i = surface_temp_f + cell_depths[i] / 100.0 * temp_gradient
                z_i = TransientFlowEngine._z_factor_dak(pressures[i] + 14.7, temp_i, gas_gravity)
                m_gas = 28.97 * gas_gravity
                t_rankine = temp_i + 460.0
                rho_gas = (pressures[i] + 14.7) * m_gas / (z_i * 10.73 * t_rankine) if z_i > 0 else 0.1

                rho_mix = rho_mud_lbft3 * (1 - gas_holdup[i]) + rho_gas * gas_holdup[i]
                density_profile.append(round(rho_mix, 2))

                total_gas_vol_ft3 += gas_holdup[i] * cell_volume_ft3
                max_hup = max(max_hup, gas_holdup[i])

                if gas_holdup[i] > 1e-6:
                    delta_rho = max(rho_mud_lbft3 - rho_gas, 0.1)
                    v_drift = 0.35 * math.sqrt(G_FT_S2 * d_hyd_ft * delta_rho / rho_mud_lbft3)
                    v_gas = C0 * 0.0 + v_drift
                    v_gas_ft_min = v_gas * 60.0
                    max_gas_vel = max(max_gas_vel, v_gas_ft_min)

            # ── Advance gas holdup (upward transport) ──
            if t_idx < n_time_steps - 1:
                new_holdup = [0.0] * n_cells
                for i in range(n_cells):
                    if gas_holdup[i] < 1e-10:
                        continue

                    temp_i = surface_temp_f + cell_depths[i] / 100.0 * temp_gradient
                    z_i = TransientFlowEngine._z_factor_dak(pressures[i] + 14.7, temp_i, gas_gravity)
                    m_gas = 28.97 * gas_gravity
                    t_rankine = temp_i + 460.0
                    rho_gas = (pressures[i] + 14.7) * m_gas / (z_i * 10.73 * t_rankine) if z_i > 0 else 0.1

                    delta_rho = max(rho_mud_lbft3 - rho_gas, 0.1)
                    v_drift = 0.35 * math.sqrt(G_FT_S2 * d_hyd_ft * delta_rho / rho_mud_lbft3)
                    v_gas = v_drift

                    dist_ft = v_gas * dt_sec
                    cells_moved = dist_ft / cell_height_ft

                    frac_move = min(cells_moved, 1.0)
                    gas_staying = gas_holdup[i] * (1.0 - frac_move)
                    gas_leaving = gas_holdup[i] * frac_move

                    new_holdup[i] += gas_staying
                    if i > 0:
                        target = i - 1
                        if pressures[target] > 0 and pressures[i] > 0:
                            expansion = pressures[i] / pressures[target] if pressures[target] > 0 else 1.0
                            z_target = TransientFlowEngine._z_factor_dak(
                                pressures[target] + 14.7,
                                surface_temp_f + cell_depths[target] / 100.0 * temp_gradient,
                                gas_gravity,
                            )
                            expansion *= (z_target / z_i) if z_i > 0 else 1.0
                        else:
                            expansion = 1.0
                        expanded_holdup = gas_leaving * expansion
                        new_holdup[target] += min(expanded_holdup, 1.0 - new_holdup[target])

                gas_holdup = [min(h, 0.99) for h in new_holdup]

            # ── Detect surface arrival ──
            if gas_holdup[0] > 0.01 and surface_arrival_min is None:
                surface_arrival_min = round(t_min, 1)

            # ── Compute kick top TVD ──
            kick_top_tvd = well_depth_tvd
            for i in range(n_cells):
                if gas_holdup[i] > 0.001:
                    kick_top_tvd = cell_depths[i] - cell_height_ft / 2
                    break

            # Gas mass proxy
            gas_mass_proxy = 0.0
            for i in range(n_cells):
                if gas_holdup[i] > 1e-10:
                    temp_i = surface_temp_f + cell_depths[i] / 100.0 * temp_gradient
                    z_i = TransientFlowEngine._z_factor_dak(pressures[i] + 14.7, temp_i, gas_gravity)
                    t_r = temp_i + 460.0
                    gas_mass_proxy += gas_holdup[i] * cell_volume_ft3 * (pressures[i] + 14.7) / (z_i * t_r) if z_i > 0 else 0

            # Record time step
            if t_idx % max(1, int(60 / dt_sec)) == 0 or t_idx == n_time_steps - 1:
                time_series.append({
                    "time_min": round(t_min, 1),
                    "casing_pressure_psi": round(cp_current, 1),
                    "drillpipe_pressure_psi": round(bhp - mud_gradient * well_depth_tvd, 1),
                    "kick_top_tvd": round(kick_top_tvd, 1),
                    "kick_volume_bbl": round(total_gas_vol_ft3 / BBL_TO_FT3, 2),
                    "max_gas_velocity_ft_min": round(max_gas_vel, 1),
                    "max_holdup": round(max_hup, 4),
                    "mixture_density_profile": density_profile,
                    "gas_mass_proxy": round(gas_mass_proxy, 4),
                })

        return {
            "time_series": time_series,
            "max_casing_pressure": round(max_cp, 1),
            "surface_arrival_min": surface_arrival_min,
            "model": "zuber_findlay_drift_flux",
            "parameters": {
                "C0": C0,
                "n_cells": n_cells,
                "dt_sec": dt_sec,
                "gas_gravity": gas_gravity,
            },
        }
