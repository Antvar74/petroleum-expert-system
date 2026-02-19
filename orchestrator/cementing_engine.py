"""
Cementing Simulation Calculation Engine

Displacement mechanics, multi-fluid ECD, free-fall, U-tube equilibrium,
BHP schedule, and lift pressure for primary cementing operations.

References:
- Nelson & Guillot: Well Cementing (2nd Edition, Schlumberger)
- API Spec 10A: Cements and Materials for Well Cementing
- API Spec 10B: Recommended Practice for Testing Well Cements
- API RP 65-Part 2: Isolating Potential Flow Zones During Well Construction
- Bourgoyne et al.: Applied Drilling Engineering, Ch. 3 (hydraulics basis)
"""
import math
from typing import List, Dict, Any, Optional


class CementingEngine:
    """
    Primary cementing simulation engine.
    Calculates fluid volumes, displacement tracking, multi-fluid ECD,
    free-fall height, U-tube effect, BHP schedule, and lift pressure.
    All methods are @staticmethod.
    """

    # -------------------------------------------------------------------
    # Typical cement densities (ppg) — reference table
    # -------------------------------------------------------------------
    CEMENT_CLASSES = {
        "A":  {"density_range": (15.0, 16.0), "depth_ft": 6000,  "use": "Surface / Conductor"},
        "B":  {"density_range": (15.0, 16.0), "depth_ft": 6000,  "use": "Surface / Conductor"},
        "C":  {"density_range": (14.0, 15.0), "depth_ft": 6000,  "use": "High early strength"},
        "G":  {"density_range": (15.6, 16.4), "depth_ft": 8000,  "use": "General purpose (most common)"},
        "H":  {"density_range": (16.0, 16.5), "depth_ft": 8000,  "use": "General purpose"},
    }

    # Typical spacer / wash densities
    DEFAULT_SPACER_DENSITY = 10.0  # ppg (water-based spacer)
    DEFAULT_WASH_VOLUME_BBL_PER_1000FT = 5.0  # rule of thumb

    # ===================================================================
    # 1. Fluid Volumes
    # ===================================================================
    @staticmethod
    def calculate_fluid_volumes(
        casing_od_in: float,
        casing_id_in: float,
        hole_id_in: float,
        casing_shoe_md_ft: float,
        toc_md_ft: float,
        float_collar_md_ft: float,
        lead_cement_density_ppg: float = 13.5,
        tail_cement_density_ppg: float = 16.0,
        tail_length_ft: float = 500.0,
        spacer_volume_bbl: float = 25.0,
        excess_pct: float = 50.0,
        rat_hole_ft: float = 50.0,
    ) -> Dict[str, Any]:
        """
        Calculate volumes of each fluid in the cementing job.

        Geometry:
          annular_capacity = (hole_id^2 - casing_od^2) / 1029.4   [bbl/ft]
          casing_capacity  = casing_id^2 / 1029.4                   [bbl/ft]

        Parameters:
        - casing_od_in / casing_id_in: casing dimensions
        - hole_id_in: open-hole diameter
        - casing_shoe_md_ft: measured depth of casing shoe
        - toc_md_ft: depth of top of cement (measured from surface)
        - float_collar_md_ft: depth of float collar
        - lead_cement_density_ppg / tail_cement_density_ppg: slurry densities
        - tail_length_ft: length of tail cement above shoe
        - spacer_volume_bbl: spacer volume
        - excess_pct: percentage excess cement for washouts (e.g., 50 = +50%)
        - rat_hole_ft: length below shoe (open hole below casing)
        """
        # Capacities [bbl/ft]
        ann_cap = (hole_id_in ** 2 - casing_od_in ** 2) / 1029.4
        csg_cap = casing_id_in ** 2 / 1029.4

        if ann_cap <= 0 or csg_cap <= 0:
            return {"error": "Invalid geometry: check hole_id > casing_od and casing_id > 0"}

        # Cement heights in annulus
        cement_top_to_shoe = casing_shoe_md_ft - toc_md_ft
        if cement_top_to_shoe < 0:
            cement_top_to_shoe = 0.0

        tail_annular_length = min(tail_length_ft, cement_top_to_shoe)
        lead_annular_length = cement_top_to_shoe - tail_annular_length

        # Annular volumes (gauge + excess)
        excess_factor = 1.0 + excess_pct / 100.0
        lead_annular_bbl = lead_annular_length * ann_cap * excess_factor
        tail_annular_bbl = tail_annular_length * ann_cap * excess_factor
        rat_hole_bbl = rat_hole_ft * ann_cap * excess_factor  # below shoe

        # Cement inside casing (shoe to float collar)
        shoe_to_float = casing_shoe_md_ft - float_collar_md_ft
        if shoe_to_float < 0:
            shoe_to_float = 0.0
        tail_inside_bbl = shoe_to_float * csg_cap  # tail fills shoe track

        # Total cement volumes
        total_lead_bbl = lead_annular_bbl
        total_tail_bbl = tail_annular_bbl + tail_inside_bbl + rat_hole_bbl
        total_cement_bbl = total_lead_bbl + total_tail_bbl

        # Displacement volume (from surface to float collar)
        displacement_bbl = float_collar_md_ft * csg_cap

        # Lead cement in sacks (1 sack Class G ≈ 1.15 ft³; 1 bbl = 5.615 ft³)
        lead_sacks = total_lead_bbl * 5.615 / 1.15 if total_lead_bbl > 0 else 0
        tail_sacks = total_tail_bbl * 5.615 / 1.15 if total_tail_bbl > 0 else 0

        # Total job volume (pump sequence)
        total_pump_bbl = spacer_volume_bbl + total_cement_bbl + displacement_bbl

        return {
            "annular_capacity_bbl_ft": round(ann_cap, 4),
            "casing_capacity_bbl_ft": round(csg_cap, 4),
            "lead_cement_bbl": round(total_lead_bbl, 1),
            "tail_cement_bbl": round(total_tail_bbl, 1),
            "total_cement_bbl": round(total_cement_bbl, 1),
            "lead_cement_sacks": round(lead_sacks, 0),
            "tail_cement_sacks": round(tail_sacks, 0),
            "spacer_volume_bbl": round(spacer_volume_bbl, 1),
            "displacement_volume_bbl": round(displacement_bbl, 1),
            "total_pump_volume_bbl": round(total_pump_bbl, 1),
            "lead_annular_length_ft": round(lead_annular_length, 0),
            "tail_annular_length_ft": round(tail_annular_length, 0),
            "shoe_track_length_ft": round(shoe_to_float, 0),
            "excess_pct": excess_pct,
            "lead_density_ppg": lead_cement_density_ppg,
            "tail_density_ppg": tail_cement_density_ppg,
        }

    # ===================================================================
    # 2. Displacement Schedule — fluid interface tracking
    # ===================================================================
    @staticmethod
    def calculate_displacement_schedule(
        spacer_volume_bbl: float,
        lead_cement_bbl: float,
        tail_cement_bbl: float,
        displacement_volume_bbl: float,
        pump_rate_bbl_min: float = 5.0,
        num_points: int = 30,
        pump_schedule: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Track fluid interfaces vs. cumulative barrels pumped.

        Returns schedule with key events:
          - Spacer away (spacer done pumping)
          - Lead away
          - Tail away
          - Plug bump (displacement complete)

        Parameters:
        - pump_rate_bbl_min: average pump rate (used when pump_schedule is None)
        - num_points: resolution of schedule curve
        - pump_schedule: optional variable rate schedule
          [{rate_bpm, volume_bbl, stage_name}] — multi-stage pumping
        """
        if pump_schedule is not None and len(pump_schedule) > 0:
            # Variable pump rate mode
            return CementingEngine._displacement_variable_rate(
                spacer_volume_bbl, lead_cement_bbl, tail_cement_bbl,
                displacement_volume_bbl, pump_schedule, num_points
            )

        if pump_rate_bbl_min <= 0:
            return {"error": "Pump rate must be > 0"}

        # Cumulative volume milestones
        v_spacer_end = spacer_volume_bbl
        v_lead_end = v_spacer_end + lead_cement_bbl
        v_tail_end = v_lead_end + tail_cement_bbl
        v_plug_bump = v_tail_end + displacement_volume_bbl
        total_volume = v_plug_bump

        if total_volume <= 0:
            return {"error": "Total pump volume is zero"}

        # Generate schedule points
        schedule = []
        step = total_volume / max(num_points - 1, 1)
        for i in range(num_points):
            v_cum = min(i * step, total_volume)
            t_min = v_cum / pump_rate_bbl_min

            # Determine current fluid being pumped
            if v_cum <= v_spacer_end:
                current_fluid = "Spacer"
                pct_complete = (v_cum / v_spacer_end * 100) if v_spacer_end > 0 else 100
            elif v_cum <= v_lead_end:
                current_fluid = "Lead Cement"
                pct_complete = ((v_cum - v_spacer_end) / lead_cement_bbl * 100) if lead_cement_bbl > 0 else 100
            elif v_cum <= v_tail_end:
                current_fluid = "Tail Cement"
                pct_complete = ((v_cum - v_lead_end) / tail_cement_bbl * 100) if tail_cement_bbl > 0 else 100
            else:
                current_fluid = "Displacement (Mud)"
                pct_complete = ((v_cum - v_tail_end) / displacement_volume_bbl * 100) if displacement_volume_bbl > 0 else 100

            schedule.append({
                "cumulative_bbl": round(v_cum, 1),
                "time_min": round(t_min, 1),
                "current_fluid": current_fluid,
                "fluid_pct_complete": round(min(pct_complete, 100), 1),
                "job_pct_complete": round(v_cum / total_volume * 100, 1),
            })

        # Key events
        events = [
            {"event": "Spacer Away", "volume_bbl": round(v_spacer_end, 1),
             "time_min": round(v_spacer_end / pump_rate_bbl_min, 1)},
            {"event": "Lead Cement Away", "volume_bbl": round(v_lead_end, 1),
             "time_min": round(v_lead_end / pump_rate_bbl_min, 1)},
            {"event": "Tail Cement Away", "volume_bbl": round(v_tail_end, 1),
             "time_min": round(v_tail_end / pump_rate_bbl_min, 1)},
            {"event": "Plug Bump / End Displacement", "volume_bbl": round(v_plug_bump, 1),
             "time_min": round(v_plug_bump / pump_rate_bbl_min, 1)},
        ]

        total_time_min = v_plug_bump / pump_rate_bbl_min

        return {
            "schedule": schedule,
            "events": events,
            "total_volume_bbl": round(total_volume, 1),
            "total_time_min": round(total_time_min, 1),
            "total_time_hrs": round(total_time_min / 60, 2),
            "pump_rate_bbl_min": pump_rate_bbl_min,
        }

    @staticmethod
    def _displacement_variable_rate(
        spacer_volume_bbl: float,
        lead_cement_bbl: float,
        tail_cement_bbl: float,
        displacement_volume_bbl: float,
        pump_schedule: List[Dict[str, Any]],
        num_points: int = 30,
    ) -> Dict[str, Any]:
        """
        Displacement schedule with variable pump rates (multi-stage).

        pump_schedule: [{rate_bpm, volume_bbl, stage_name}]
        Each stage pumps at its own rate for its specified volume.
        """
        # Build cumulative volume-time map from stages
        stages = []
        cum_vol = 0.0
        cum_time = 0.0
        for stage in pump_schedule:
            rate = stage.get("rate_bpm", 5.0)
            vol = stage.get("volume_bbl", 0.0)
            name = stage.get("stage_name", "Stage")
            if rate <= 0 or vol <= 0:
                continue
            t_stage = vol / rate
            stages.append({
                "stage_name": name,
                "rate_bpm": rate,
                "volume_bbl": vol,
                "start_vol": cum_vol,
                "end_vol": cum_vol + vol,
                "start_time": cum_time,
                "end_time": cum_time + t_stage,
            })
            cum_vol += vol
            cum_time += t_stage

        if not stages:
            return {"error": "No valid stages in pump_schedule"}

        total_volume = cum_vol
        total_time = cum_time

        # Milestones
        v_spacer_end = spacer_volume_bbl
        v_lead_end = v_spacer_end + lead_cement_bbl
        v_tail_end = v_lead_end + tail_cement_bbl
        v_plug_bump = v_tail_end + displacement_volume_bbl

        def vol_to_time(v):
            """Convert cumulative volume to time using variable rates."""
            remaining = v
            t = 0.0
            for s in stages:
                stage_vol = s["volume_bbl"]
                if remaining <= stage_vol:
                    t += remaining / s["rate_bpm"]
                    return t
                remaining -= stage_vol
                t += stage_vol / s["rate_bpm"]
            # Beyond schedule — use last rate
            if stages:
                t += remaining / stages[-1]["rate_bpm"]
            return t

        # Generate schedule points
        schedule = []
        step = total_volume / max(num_points - 1, 1)
        for i in range(num_points):
            v_cum = min(i * step, total_volume)
            t_min = vol_to_time(v_cum)

            # Current fluid
            if v_cum <= v_spacer_end:
                current_fluid = "Spacer"
                pct = (v_cum / v_spacer_end * 100) if v_spacer_end > 0 else 100
            elif v_cum <= v_lead_end:
                current_fluid = "Lead Cement"
                pct = ((v_cum - v_spacer_end) / lead_cement_bbl * 100) if lead_cement_bbl > 0 else 100
            elif v_cum <= v_tail_end:
                current_fluid = "Tail Cement"
                pct = ((v_cum - v_lead_end) / tail_cement_bbl * 100) if tail_cement_bbl > 0 else 100
            else:
                current_fluid = "Displacement (Mud)"
                pct = ((v_cum - v_tail_end) / displacement_volume_bbl * 100) if displacement_volume_bbl > 0 else 100

            # Current rate
            current_rate = stages[-1]["rate_bpm"] if stages else 5.0
            for s in stages:
                if s["start_vol"] <= v_cum <= s["end_vol"]:
                    current_rate = s["rate_bpm"]
                    break

            schedule.append({
                "cumulative_bbl": round(v_cum, 1),
                "time_min": round(t_min, 1),
                "current_fluid": current_fluid,
                "fluid_pct_complete": round(min(pct, 100), 1),
                "job_pct_complete": round(v_cum / total_volume * 100, 1),
                "pump_rate_bbl_min": current_rate,
            })

        events = [
            {"event": "Spacer Away", "volume_bbl": round(v_spacer_end, 1),
             "time_min": round(vol_to_time(v_spacer_end), 1)},
            {"event": "Lead Cement Away", "volume_bbl": round(v_lead_end, 1),
             "time_min": round(vol_to_time(v_lead_end), 1)},
            {"event": "Tail Cement Away", "volume_bbl": round(v_tail_end, 1),
             "time_min": round(vol_to_time(v_tail_end), 1)},
            {"event": "Plug Bump / End Displacement", "volume_bbl": round(v_plug_bump, 1),
             "time_min": round(vol_to_time(v_plug_bump), 1)},
        ]

        # Identify critical stage (max ECD proxy = max rate)
        max_rate_stage = max(stages, key=lambda s: s["rate_bpm"])

        return {
            "schedule": schedule,
            "events": events,
            "stages": stages,
            "total_volume_bbl": round(total_volume, 1),
            "total_time_min": round(total_time, 1),
            "total_time_hrs": round(total_time / 60, 2),
            "critical_stage": max_rate_stage["stage_name"],
            "variable_rate": True,
        }

    # ===================================================================
    # 3. ECD During Cementing — multi-fluid column
    # ===================================================================
    @staticmethod
    def calculate_ecd_during_job(
        casing_shoe_tvd_ft: float,
        hole_id_in: float,
        casing_od_in: float,
        mud_weight_ppg: float,
        spacer_density_ppg: float,
        lead_cement_density_ppg: float,
        tail_cement_density_ppg: float,
        annular_sections: Optional[List[Dict[str, Any]]] = None,
        pump_rate_bbl_min: float = 5.0,
        pv_mud: float = 15.0,
        yp_mud: float = 10.0,
        fracture_gradient_ppg: float = 16.5,
        pore_pressure_ppg: float = 9.0,
        num_snapshots: int = 8,
    ) -> Dict[str, Any]:
        """
        Calculate ECD at shoe during cementing as different fluids
        pass through the annulus.

        The annular column is a stack of fluid segments, each with
        its own density. Hydrostatic = sum(rho_i * 0.052 * h_i).
        Friction losses are approximated using Bingham model.

        Parameters:
        - annular_sections: optional custom sections; if None uses uniform annulus
        - num_snapshots: number of time steps to capture ECD evolution
        """
        if casing_shoe_tvd_ft <= 0:
            return {"error": "Invalid TVD"}

        ann_cap = (hole_id_in ** 2 - casing_od_in ** 2) / 1029.4  # bbl/ft
        if ann_cap <= 0:
            return {"error": "Invalid annular geometry"}

        total_annular_bbl = casing_shoe_tvd_ft * ann_cap

        # Fluid densities in pumping order (bottom-up as they fill annulus)
        fluids = [
            {"name": "Mud", "density": mud_weight_ppg},
            {"name": "Spacer", "density": spacer_density_ppg},
            {"name": "Lead Cement", "density": lead_cement_density_ppg},
            {"name": "Tail Cement", "density": tail_cement_density_ppg},
        ]

        # Simulate snapshots: fraction of annulus filled by heavy fluids
        snapshots = []
        for i in range(num_snapshots + 1):
            fill_fraction = i / num_snapshots  # 0 = all mud, 1 = all cement

            # Simple model: fluids fill annulus from bottom (shoe) upward
            # fill_fraction represents how much of the annulus is displaced
            cement_height_ft = fill_fraction * casing_shoe_tvd_ft
            mud_height_ft = casing_shoe_tvd_ft - cement_height_ft

            # Weight the cement column with lead/tail split (80% lead, 20% tail)
            tail_frac = 0.2
            tail_h = min(cement_height_ft, casing_shoe_tvd_ft * tail_frac)
            lead_h = cement_height_ft - tail_h

            # Hydrostatic at shoe
            p_hydro = (
                mud_weight_ppg * 0.052 * mud_height_ft
                + lead_cement_density_ppg * 0.052 * lead_h
                + tail_cement_density_ppg * 0.052 * tail_h
            )

            # Friction loss (Bingham approximation for annular flow)
            d_eff = hole_id_in - casing_od_in
            if d_eff > 0 and pump_rate_bbl_min > 0:
                v_ann = 24.5 * (pump_rate_bbl_min * 42.0) / (hole_id_in ** 2 - casing_od_in ** 2)
                # Convert pump_rate from bbl/min to gpm (1 bbl = 42 gal)
                q_gpm = pump_rate_bbl_min * 42.0
                v_ann = 24.5 * q_gpm / (hole_id_in ** 2 - casing_od_in ** 2)
                dp_friction = (pv_mud * v_ann * casing_shoe_tvd_ft) / (1000.0 * d_eff ** 2) + \
                              (yp_mud * casing_shoe_tvd_ft) / (200.0 * d_eff)
            else:
                dp_friction = 0.0
                v_ann = 0.0

            ecd_psi = p_hydro + dp_friction
            ecd_ppg = ecd_psi / (0.052 * casing_shoe_tvd_ft) if casing_shoe_tvd_ft > 0 else 0

            snapshots.append({
                "fill_pct": round(fill_fraction * 100, 1),
                "cement_height_ft": round(cement_height_ft, 0),
                "mud_height_ft": round(mud_height_ft, 0),
                "hydrostatic_psi": round(p_hydro, 0),
                "friction_psi": round(dp_friction, 0),
                "bhp_psi": round(ecd_psi, 0),
                "ecd_ppg": round(ecd_ppg, 2),
                "fracture_margin_ppg": round(fracture_gradient_ppg - ecd_ppg, 2),
            })

        # Find max ECD and check against fracture gradient
        max_ecd = max(s["ecd_ppg"] for s in snapshots)
        min_margin = min(s["fracture_margin_ppg"] for s in snapshots)

        status = "OK — Within fracture window"
        if min_margin < 0:
            status = "CRITICAL — ECD exceeds fracture gradient!"
        elif min_margin < 0.5:
            status = "WARNING — Tight margin to fracture gradient"
        elif min_margin < 1.0:
            status = "CAUTION — Monitor closely"

        alerts = []
        if min_margin < 0:
            alerts.append(f"ECD exceeds fracture gradient by {abs(min_margin):.2f} ppg — risk of losses!")
        if max_ecd > fracture_gradient_ppg:
            alerts.append("Reduce pump rate or use lighter lead cement")

        return {
            "snapshots": snapshots,
            "max_ecd_ppg": round(max_ecd, 2),
            "min_fracture_margin_ppg": round(min_margin, 2),
            "fracture_gradient_ppg": fracture_gradient_ppg,
            "pore_pressure_ppg": pore_pressure_ppg,
            "annular_velocity_ft_min": round(v_ann, 1),
            "status": status,
            "alerts": alerts,
        }

    # ===================================================================
    # 4. Free-Fall Calculation (Corrected physical model)
    # ===================================================================
    @staticmethod
    def calculate_free_fall(
        casing_shoe_tvd_ft: float,
        mud_weight_ppg: float,
        cement_density_ppg: float,
        casing_id_in: float,
        hole_id_in: float,
        casing_od_in: float,
        cement_column_ft: float = 0.0,
        friction_factor: float = 0.02,
    ) -> Dict[str, Any]:
        """
        Calculate free-fall height during cementing (corrected model).

        Physical model: cement falls inside casing while displacing mud
        upward in the annulus, until pressures equilibrate considering
        the volume-conservation coupling between both legs.

        Corrected formula (density does NOT cancel):
        h_ff = (rho_c - rho_m) * csg_cap * shoe_tvd /
               ((rho_c - rho_m) * csg_cap + rho_m * ann_cap + rho_c * csg_cap * friction)

        Friction drag opposes free-fall: F_drag = f * rho * V^2 * L / (2 * D_h)
        Simplified as friction_factor applied to driving pressure.
        """
        grad_mud = mud_weight_ppg * 0.052
        grad_cement = cement_density_ppg * 0.052

        if grad_cement <= grad_mud:
            return {
                "free_fall_height_ft": 0.0,
                "free_fall_occurs": False,
                "explanation": "No free-fall: cement density <= mud density",
                "cement_gradient_psi_ft": round(grad_cement, 4),
                "mud_gradient_psi_ft": round(grad_mud, 4),
            }

        ann_cap = (hole_id_in ** 2 - casing_od_in ** 2) / 1029.4
        csg_cap = casing_id_in ** 2 / 1029.4

        if ann_cap <= 0 or csg_cap <= 0:
            return {"error": "Invalid geometry"}

        vol_ratio = csg_cap / ann_cap

        # Corrected pressure balance including volume coupling:
        # When cement drops h_ff in casing, mud rises h_ff * vol_ratio in annulus
        # Equilibrium: rho_c * h_ff = rho_m * (h_ff + h_ff * vol_ratio)
        # Solving: h_ff = delta_grad * shoe_tvd / (delta_grad * (1 + vol_ratio) + friction_resistance)

        delta_grad = grad_cement - grad_mud
        friction_resistance = friction_factor * grad_cement  # friction opposes fall

        denominator = delta_grad * (1.0 + vol_ratio) + friction_resistance
        if denominator <= 0:
            h_ff = 0.0
        else:
            h_ff = delta_grad * casing_shoe_tvd_ft / denominator

        h_ff = min(h_ff, casing_shoe_tvd_ft)
        h_ff = max(h_ff, 0.0)

        # Terminal velocity estimate (Stokes-modified for annular geometry)
        # V_ff = sqrt(2 * g * h_ff * (rho_c - rho_m) / rho_c) — simplified
        g = 32.174  # ft/s2
        rho_c_pcf = cement_density_ppg * 7.48  # ppg to lb/ft3
        rho_m_pcf = mud_weight_ppg * 7.48
        if rho_c_pcf > 0 and h_ff > 0:
            v_terminal = math.sqrt(2.0 * g * h_ff * (rho_c_pcf - rho_m_pcf) / rho_c_pcf)
            fall_time_sec = 2.0 * h_ff / max(v_terminal, 0.01)  # avg velocity ≈ V/2
        else:
            v_terminal = 0.0
            fall_time_sec = 0.0

        free_fall_vol_bbl = h_ff * csg_cap

        return {
            "free_fall_height_ft": round(h_ff, 1),
            "free_fall_volume_bbl": round(free_fall_vol_bbl, 1),
            "free_fall_occurs": h_ff > 10.0,
            "terminal_velocity_fts": round(v_terminal, 1),
            "estimated_fall_time_sec": round(fall_time_sec, 0),
            "cement_gradient_psi_ft": round(grad_cement, 4),
            "mud_gradient_psi_ft": round(grad_mud, 4),
            "delta_gradient_psi_ft": round(delta_grad, 4),
            "volume_ratio_csg_ann": round(vol_ratio, 3),
            "friction_factor": friction_factor,
            "explanation": (
                f"Cement free-falls ~{h_ff:.0f} ft due to {cement_density_ppg - mud_weight_ppg:.1f} ppg "
                f"density differential (friction-corrected)"
            ) if h_ff > 10 else "Minimal free-fall — manageable with standard procedures",
        }

    # ===================================================================
    # 5. U-Tube Effect
    # ===================================================================
    @staticmethod
    def calculate_utube_effect(
        casing_shoe_tvd_ft: float,
        mud_weight_ppg: float,
        cement_density_ppg: float,
        cement_top_tvd_ft: float,
        casing_id_in: float,
        hole_id_in: float,
        casing_od_in: float,
        gel_strength_10s: float = 0.0,
        gel_strength_10min: float = 0.0,
        static_time_min: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Calculate U-tube equilibrium when pumps stop, including gel strength resistance.

        Gel strength opposes flow: P_gel = 4 * tau_gel * L / D_h (Bingham in annular)
        If P_gel > hydrostatic imbalance → NO U-tube (gel holds the column).

        Parameters:
        - gel_strength_10s/10min: gel strength at 10 sec / 10 min (lbf/100sqft)
        - static_time_min: time since pumps stopped (for gel interpolation)
        """
        grad_mud = mud_weight_ppg * 0.052
        grad_cement = cement_density_ppg * 0.052

        ann_cap = (hole_id_in ** 2 - casing_od_in ** 2) / 1029.4
        csg_cap = casing_id_in ** 2 / 1029.4

        if ann_cap <= 0 or csg_cap <= 0:
            return {"error": "Invalid geometry"}

        # Annulus side pressure at shoe
        cement_height_ann = casing_shoe_tvd_ft - cement_top_tvd_ft
        if cement_height_ann < 0:
            cement_height_ann = 0.0
        mud_height_ann = casing_shoe_tvd_ft - cement_height_ann

        p_annulus = grad_cement * cement_height_ann + grad_mud * mud_height_ann
        p_casing = grad_mud * casing_shoe_tvd_ft
        delta_p = p_annulus - p_casing

        # Gel strength resistance (opposing U-tube flow)
        # Interpolate gel between 10s and 10min based on static time
        if static_time_min <= 0 or (gel_strength_10s <= 0 and gel_strength_10min <= 0):
            tau_gel = 0.0
        elif static_time_min <= 0.167:  # ~10 seconds
            tau_gel = gel_strength_10s
        elif static_time_min >= 10.0:
            tau_gel = gel_strength_10min
        else:
            # Log interpolation between 10s (0.167 min) and 10 min
            t_10s = 0.167
            t_10m = 10.0
            frac = math.log(static_time_min / t_10s) / math.log(t_10m / t_10s)
            tau_gel = gel_strength_10s + frac * (gel_strength_10min - gel_strength_10s)

        # Gel resistance pressure: P_gel = 4 * tau_gel * L / (D_h * 300)
        # D_h = hydraulic diameter of annulus = hole_id - casing_od (inches)
        # tau_gel in lbf/100sqft; factor 300 for unit conversion
        d_h = hole_id_in - casing_od_in
        p_gel = 0.0
        if d_h > 0 and tau_gel > 0:
            # Gel in annulus (cement section)
            p_gel_ann = 4.0 * tau_gel * cement_height_ann / (300.0 * d_h)
            # Gel in casing
            p_gel_csg = 4.0 * tau_gel * casing_shoe_tvd_ft / (300.0 * casing_id_in)
            p_gel = p_gel_ann + p_gel_csg

        # Net driving pressure after gel resistance
        net_delta_p = delta_p - p_gel
        gel_holds = net_delta_p <= 0

        if delta_p <= 0 or gel_holds:
            return {
                "utube_occurs": False,
                "pressure_imbalance_psi": round(max(delta_p, 0), 0),
                "gel_resistance_psi": round(p_gel, 0),
                "net_driving_pressure_psi": round(max(net_delta_p, 0), 0),
                "gel_holds_column": gel_holds and p_gel > 0,
                "fluid_drop_ft": 0.0,
                "fluid_drop_bbl": 0.0,
                "explanation": "Gel strength holds column — no U-tube flow" if gel_holds and p_gel > 0
                    else "No U-tube: casing side is heavier or balanced",
                "p_annulus_psi": round(p_annulus, 0),
                "p_casing_psi": round(p_casing, 0),
            }

        # Calculate drop using net driving pressure (after gel)
        combined_factor = (grad_cement - grad_mud) * (1 + csg_cap / ann_cap)
        if combined_factor > 0:
            h_drop = net_delta_p / combined_factor
        else:
            h_drop = 0.0

        h_drop = min(h_drop, casing_shoe_tvd_ft)
        h_drop = max(h_drop, 0.0)
        drop_vol = h_drop * csg_cap

        return {
            "utube_occurs": net_delta_p > 5.0,
            "pressure_imbalance_psi": round(delta_p, 0),
            "gel_resistance_psi": round(p_gel, 0),
            "net_driving_pressure_psi": round(net_delta_p, 0),
            "gel_holds_column": False,
            "fluid_drop_ft": round(h_drop, 1),
            "fluid_drop_bbl": round(drop_vol, 1),
            "p_annulus_psi": round(p_annulus, 0),
            "p_casing_psi": round(p_casing, 0),
            "explanation": (
                f"U-tube: {net_delta_p:.0f} psi net driving (after {p_gel:.0f} psi gel resistance) "
                f"causes ~{h_drop:.0f} ft fluid movement ({drop_vol:.1f} bbl)"
            ) if net_delta_p > 5 else "Negligible U-tube effect (gel partially resists)",
        }

    # ===================================================================
    # 6. BHP Schedule vs. Volume Pumped
    # ===================================================================
    @staticmethod
    def calculate_bhp_schedule(
        casing_shoe_tvd_ft: float,
        mud_weight_ppg: float,
        spacer_density_ppg: float,
        lead_cement_density_ppg: float,
        tail_cement_density_ppg: float,
        spacer_volume_bbl: float,
        lead_cement_bbl: float,
        tail_cement_bbl: float,
        displacement_volume_bbl: float,
        hole_id_in: float,
        casing_od_in: float,
        casing_id_in: float,
        pump_rate_bbl_min: float = 5.0,
        pv_mud: float = 15.0,
        yp_mud: float = 10.0,
        num_points: int = 30,
    ) -> Dict[str, Any]:
        """
        Calculate bottom-hole pressure (at shoe TVD) vs. cumulative
        volume pumped. Tracks hydrostatic changes as fluid column
        composition changes during displacement.

        BHP = P_hydrostatic_annulus + P_friction_annulus
        """
        ann_cap = (hole_id_in ** 2 - casing_od_in ** 2) / 1029.4
        csg_cap = casing_id_in ** 2 / 1029.4

        if ann_cap <= 0 or csg_cap <= 0 or casing_shoe_tvd_ft <= 0:
            return {"error": "Invalid geometry or TVD"}

        total_ann_ft = casing_shoe_tvd_ft
        total_vol = spacer_volume_bbl + lead_cement_bbl + tail_cement_bbl + displacement_volume_bbl

        if total_vol <= 0:
            return {"error": "Zero total volume"}

        # Friction loss contribution (constant while pumping)
        d_eff = hole_id_in - casing_od_in
        if d_eff > 0 and pump_rate_bbl_min > 0:
            q_gpm = pump_rate_bbl_min * 42.0
            v_ann = 24.5 * q_gpm / (hole_id_in ** 2 - casing_od_in ** 2)
            dp_friction = (pv_mud * v_ann * total_ann_ft) / (1000.0 * d_eff ** 2) + \
                          (yp_mud * total_ann_ft) / (200.0 * d_eff)
        else:
            dp_friction = 0.0

        # Track BHP at each volume increment
        bhp_schedule = []
        step = total_vol / max(num_points - 1, 1)

        for i in range(num_points):
            v_cum = min(i * step, total_vol)
            t_min = v_cum / pump_rate_bbl_min if pump_rate_bbl_min > 0 else 0

            # Determine how much of each fluid is in the annulus
            # Fluids enter annulus from bottom (shoe) and fill upward
            vol_in_annulus = v_cum  # all pumped volume goes to annulus initially
            ann_filled_ft = min(vol_in_annulus / ann_cap, total_ann_ft) if ann_cap > 0 else 0

            # Fluid stack in annulus (bottom to top):
            # First: tail cement, then lead, then spacer, rest is mud
            fluids_bbl = [
                ("Tail Cement", tail_cement_bbl, tail_cement_density_ppg),
                ("Lead Cement", lead_cement_bbl, lead_cement_density_ppg),
                ("Spacer", spacer_volume_bbl, spacer_density_ppg),
            ]

            remaining_ft = ann_filled_ft
            p_hydro = 0.0
            fluid_desc = []

            for fname, fvol, fdens in fluids_bbl:
                if remaining_ft <= 0:
                    break
                fluid_ft = min(fvol / ann_cap if ann_cap > 0 else 0, remaining_ft)
                if fluid_ft > 0:
                    p_hydro += fdens * 0.052 * fluid_ft
                    remaining_ft -= fluid_ft
                    fluid_desc.append(fname)

            # Remaining height is mud
            if remaining_ft > 0:
                p_hydro += mud_weight_ppg * 0.052 * remaining_ft

            # Above the filled section is also mud
            unfilled_ft = total_ann_ft - ann_filled_ft
            if unfilled_ft > 0:
                p_hydro += mud_weight_ppg * 0.052 * unfilled_ft

            bhp = p_hydro + dp_friction

            bhp_schedule.append({
                "cumulative_bbl": round(v_cum, 1),
                "time_min": round(t_min, 1),
                "hydrostatic_psi": round(p_hydro, 0),
                "friction_psi": round(dp_friction, 0),
                "bhp_psi": round(bhp, 0),
                "bhp_ppg": round(bhp / (0.052 * casing_shoe_tvd_ft), 2) if casing_shoe_tvd_ft > 0 else 0,
            })

        max_bhp = max(p["bhp_psi"] for p in bhp_schedule)
        max_bhp_ppg = max(p["bhp_ppg"] for p in bhp_schedule)
        initial_bhp = bhp_schedule[0]["bhp_psi"] if bhp_schedule else 0
        final_bhp = bhp_schedule[-1]["bhp_psi"] if bhp_schedule else 0

        return {
            "bhp_schedule": bhp_schedule,
            "max_bhp_psi": round(max_bhp, 0),
            "max_bhp_ppg": round(max_bhp_ppg, 2),
            "initial_bhp_psi": round(initial_bhp, 0),
            "final_bhp_psi": round(final_bhp, 0),
            "friction_contribution_psi": round(dp_friction, 0),
            "total_volume_bbl": round(total_vol, 1),
        }

    # ===================================================================
    # 7. Lift Pressure
    # ===================================================================
    @staticmethod
    def calculate_lift_pressure(
        casing_shoe_tvd_ft: float,
        toc_tvd_ft: float,
        cement_density_ppg: float,
        mud_weight_ppg: float,
        hole_id_in: float,
        casing_od_in: float,
        casing_id_in: float,
        friction_factor: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Calculate the surface pressure required to lift cement
        to the desired TOC (Top of Cement) in the annulus.

        P_lift = P_hydro_cement_column - P_hydro_mud_column + P_friction

        Parameters:
        - toc_tvd_ft: desired top of cement TVD
        - friction_factor: multiplier for friction (1.0 = standard)
        """
        cement_height_ft = casing_shoe_tvd_ft - toc_tvd_ft
        if cement_height_ft <= 0:
            return {
                "lift_pressure_psi": 0.0,
                "explanation": "TOC is at or below shoe — no lift needed",
            }

        # Hydrostatic of cement column in annulus
        p_cement = cement_density_ppg * 0.052 * cement_height_ft

        # Hydrostatic of mud column being displaced (same height in casing)
        p_mud = mud_weight_ppg * 0.052 * cement_height_ft

        # Differential = pressure needed to support heavier cement
        p_diff = p_cement - p_mud

        # Friction estimate (simplified — proportional to length)
        d_eff = hole_id_in - casing_od_in
        ann_cap = (hole_id_in ** 2 - casing_od_in ** 2) / 1029.4
        p_friction = 0.0
        if d_eff > 0:
            # Simple friction: ~0.015 psi/ft for typical annular flow
            p_friction = 0.015 * cement_height_ft * friction_factor

        lift_pressure = max(p_diff + p_friction, 0.0)

        return {
            "lift_pressure_psi": round(lift_pressure, 0),
            "hydrostatic_cement_psi": round(p_cement, 0),
            "hydrostatic_mud_psi": round(p_mud, 0),
            "differential_psi": round(p_diff, 0),
            "friction_psi": round(p_friction, 0),
            "cement_height_ft": round(cement_height_ft, 0),
            "explanation": (
                f"Need {lift_pressure:.0f} psi surface pressure to lift "
                f"{cement_density_ppg} ppg cement {cement_height_ft:.0f} ft "
                f"against {mud_weight_ppg} ppg mud"
            ),
        }

    # ===================================================================
    # 8. Caliper-Integrated Fluid Volumes
    # ===================================================================
    @staticmethod
    def calculate_fluid_volumes_caliper(
        caliper_data: List[Dict[str, float]],
        casing_od_in: float,
        toc_md_ft: float,
        casing_shoe_md_ft: float,
        lead_cement_density_ppg: float = 13.5,
        tail_cement_density_ppg: float = 16.0,
        tail_length_ft: float = 500.0,
        excess_pct: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Calculate annular volumes using caliper log data instead of gauge diameter.

        caliper_data: [{md, diameter}] — measured depth and actual hole diameter
        Computes real annular volume per section and compares against nominal.

        Reference: API RP 10B-2 (standard OptiCem/CemCADE practice)
        """
        if not caliper_data or len(caliper_data) < 2:
            return {"error": "Caliper data requires at least 2 points"}
        if casing_od_in <= 0:
            return {"error": "Invalid casing OD"}

        # Sort by MD
        sorted_cal = sorted(caliper_data, key=lambda p: p["md"])

        total_real_vol = 0.0
        total_nominal_vol = 0.0
        sections = []
        washout_max = 0.0
        washout_max_md = 0.0

        for i in range(len(sorted_cal) - 1):
            md_top = sorted_cal[i]["md"]
            md_bot = sorted_cal[i + 1]["md"]
            d_top = sorted_cal[i]["diameter"]
            d_bot = sorted_cal[i + 1]["diameter"]
            dL = md_bot - md_top
            if dL <= 0:
                continue

            # Average caliper diameter in this section
            d_avg = (d_top + d_bot) / 2.0
            # Nominal = assume first point's diameter as gauge (or use casing_od + clearance)
            # We use d_avg for real, and the minimum of the two for a nominal baseline
            d_nominal = min(d_top, d_bot)  # conservative gauge estimate

            # Annular volume: pi/4 * (D^2 - OD^2) / 144 * 12 * dL / 5.615 to get bbl
            # Simpler: (D^2 - OD^2) / 1029.4 * dL
            real_ann_cap = (d_avg ** 2 - casing_od_in ** 2) / 1029.4
            nominal_ann_cap = (d_nominal ** 2 - casing_od_in ** 2) / 1029.4

            real_ann_cap = max(real_ann_cap, 0.0)
            nominal_ann_cap = max(nominal_ann_cap, 0.0)

            real_vol = real_ann_cap * dL
            nominal_vol = nominal_ann_cap * dL

            # Washout index
            wo_pct = ((d_avg - d_nominal) / d_nominal * 100) if d_nominal > 0 else 0.0
            if wo_pct > washout_max:
                washout_max = wo_pct
                washout_max_md = (md_top + md_bot) / 2.0

            total_real_vol += real_vol
            total_nominal_vol += nominal_vol

            sections.append({
                "md_top": round(md_top, 0),
                "md_bot": round(md_bot, 0),
                "caliper_avg_in": round(d_avg, 2),
                "annular_volume_bbl": round(real_vol, 2),
                "washout_pct": round(wo_pct, 1),
            })

        excess_real = ((total_real_vol - total_nominal_vol) / total_nominal_vol * 100) if total_nominal_vol > 0 else 0.0

        # Apply additional user excess
        excess_factor = 1.0 + excess_pct / 100.0
        total_with_excess = total_real_vol * excess_factor

        return {
            "total_caliper_volume_bbl": round(total_real_vol, 1),
            "total_nominal_volume_bbl": round(total_nominal_vol, 1),
            "caliper_excess_pct": round(excess_real, 1),
            "total_with_user_excess_bbl": round(total_with_excess, 1),
            "washout_max_pct": round(washout_max, 1),
            "washout_max_md": round(washout_max_md, 0),
            "sections": sections,
            "num_sections": len(sections),
        }

    # ===================================================================
    # 9. Temperature-Dependent Slurry Properties
    # ===================================================================
    @staticmethod
    def correct_slurry_properties_pt(
        slurry_density_ppg: float,
        pv_slurry: float,
        yp_slurry: float,
        temperature_f: float,
        pressure_psi: float,
        ref_temperature_f: float = 80.0,
        ref_pressure_psi: float = 14.7,
        fluid_type: str = "wbm",
    ) -> Dict[str, Any]:
        """
        Correct slurry density and rheology for temperature and pressure.

        Reference: API Spec 10A/10B, API RP 10B-2
        - Density: rho(P,T) = rho_0 * [1 + Cp*(P-P0)] / [1 + Ct*(T-T0)]
        - Viscosity: PV(T) = PV_ref * exp(-alpha*(T-T_ref))
        """
        # Compressibility and thermal expansion coefficients
        if fluid_type.lower() == "obm":
            Cp = 5.0e-6   # /psi — oil-based
            Ct = 3.5e-4   # /°F
            alpha = 0.015  # viscosity temperature coefficient
        else:
            Cp = 3.0e-6   # /psi — water-based / cement slurry
            Ct = 2.0e-4   # /°F
            alpha = 0.012

        dP = pressure_psi - ref_pressure_psi
        dT = temperature_f - ref_temperature_f

        # Density correction
        rho_corrected = slurry_density_ppg * (1.0 + Cp * dP) / (1.0 + Ct * dT)
        rho_corrected = max(rho_corrected, 1.0)

        # Viscosity correction (exponential decay with temperature)
        temp_factor = math.exp(-alpha * dT)
        pv_corrected = pv_slurry * temp_factor
        yp_corrected = yp_slurry * temp_factor

        pv_corrected = max(pv_corrected, 0.5)
        yp_corrected = max(yp_corrected, 0.1)

        return {
            "density_corrected_ppg": round(rho_corrected, 2),
            "pv_corrected": round(pv_corrected, 1),
            "yp_corrected": round(yp_corrected, 1),
            "density_change_ppg": round(rho_corrected - slurry_density_ppg, 3),
            "temperature_f": temperature_f,
            "pressure_psi": pressure_psi,
            "temp_factor": round(temp_factor, 4),
        }

    @staticmethod
    def estimate_bhct(
        well_depth_ft: float,
        surface_temperature_f: float = 70.0,
        geothermal_gradient_f_per_100ft: float = 1.2,
        circulation_time_hrs: float = 4.0,
    ) -> Dict[str, Any]:
        """
        Estimate Bottom Hole Circulating Temperature (BHCT).

        Correlation: API RP 10B-2 — BHCT < BHST due to cooling by circulation.
        BHST = T_surface + gradient * depth
        BHCT = BHST * cooling_factor (typ 0.60-0.85 depending on circ time)
        """
        bhst = surface_temperature_f + geothermal_gradient_f_per_100ft * well_depth_ft / 100.0

        # Cooling factor: longer circulation → more cooling → lower BHCT
        # Empirical: f = 0.85 - 0.03 * ln(t_hrs + 1) for t > 0
        cooling_factor = 0.85 - 0.03 * math.log(max(circulation_time_hrs, 0.1) + 1.0)
        cooling_factor = max(min(cooling_factor, 0.95), 0.55)

        bhct = surface_temperature_f + (bhst - surface_temperature_f) * cooling_factor

        return {
            "bhst_f": round(bhst, 1),
            "bhct_f": round(bhct, 1),
            "cooling_factor": round(cooling_factor, 3),
            "surface_temperature_f": surface_temperature_f,
            "geothermal_gradient_f_per_100ft": geothermal_gradient_f_per_100ft,
        }

    # ===================================================================
    # 10. Gas Migration Risk Assessment
    # ===================================================================
    @staticmethod
    def calculate_gas_migration_risk(
        reservoir_pressure_psi: float,
        cement_column_height_ft: float,
        slurry_density_ppg: float,
        pore_pressure_ppg: float,
        tvd_ft: float,
        transition_time_hr: float = 2.0,
        thickening_time_hr: float = 5.0,
        sgs_10min_lbf_100sqft: float = 20.0,
    ) -> Dict[str, Any]:
        """
        Evaluate post-placement gas migration risk.

        Reference: API RP 65-2 (Gas Migration)
        - Gas Flow Potential (GFP) = (P_res - P_hydro_cement) / P_overbalance
        - Risk: HIGH if GFP > 1.0 AND transition_time < thickening_time
        """
        # Hydrostatic from cement column
        p_hydro_cement = slurry_density_ppg * 0.052 * cement_column_height_ft

        # Hydrostatic at reservoir depth (full column)
        p_hydro_total = slurry_density_ppg * 0.052 * tvd_ft

        # Overbalance
        p_pore = pore_pressure_ppg * 0.052 * tvd_ft
        overbalance = p_hydro_total - reservoir_pressure_psi

        # Gas Flow Potential
        if overbalance > 0:
            gfp = reservoir_pressure_psi / p_hydro_total
        else:
            gfp = 1.5  # underbalanced → high GFP

        # Transition time ratio
        transition_ratio = transition_time_hr / thickening_time_hr if thickening_time_hr > 0 else 999

        # SGS assessment: low SGS → gas can migrate through gel structure
        sgs_adequate = sgs_10min_lbf_100sqft >= 100  # API target: 500 lbf/100sqft ideal

        # Risk classification
        recommendations = []
        if gfp >= 1.5 or (gfp >= 1.0 and transition_ratio < 0.5):
            risk_level = "CRITICAL"
            recommendations.append("Use gas-tight cement system with anti-gas additives")
            recommendations.append("Consider inner string cementing or staged cementing")
            recommendations.append("Apply external casing packer (ECP) across gas zone")
        elif gfp >= 1.0:
            risk_level = "HIGH"
            recommendations.append("Use cement with short transition time and high SGS development")
            recommendations.append("Maximize displacement efficiency (turbulent flow, spacer)")
        elif gfp >= 0.5:
            risk_level = "MODERATE"
            recommendations.append("Standard anti-gas cement additives recommended")
            recommendations.append("Ensure good mud removal and centralization")
        else:
            risk_level = "LOW"
            recommendations.append("Standard cementing practices adequate")

        if not sgs_adequate:
            recommendations.append("SGS too low — consider right-angle-set (RAS) cement system")

        return {
            "gfp": round(gfp, 3),
            "risk_level": risk_level,
            "overbalance_psi": round(overbalance, 0),
            "p_hydro_cement_psi": round(p_hydro_cement, 0),
            "reservoir_pressure_psi": round(reservoir_pressure_psi, 0),
            "transition_time_hr": transition_time_hr,
            "thickening_time_hr": thickening_time_hr,
            "transition_ratio": round(transition_ratio, 3),
            "sgs_adequate": sgs_adequate,
            "recommendations": recommendations,
        }

    # ===================================================================
    # 11. Spacer Optimization
    # ===================================================================
    @staticmethod
    def optimize_spacer(
        mud_density_ppg: float,
        mud_pv: float,
        mud_yp: float,
        slurry_density_ppg: float,
        slurry_pv: float,
        slurry_yp: float,
        hole_id_in: float,
        casing_od_in: float,
        casing_shoe_tvd_ft: float,
        pump_rate_bbl_min: float = 5.0,
        min_contact_time_min: float = 10.0,
        min_contact_length_ft: float = 500.0,
    ) -> Dict[str, Any]:
        """
        Calculate optimal spacer volume and properties.

        Rules:
        - Density: intermediate between mud and cement
        - Rheology hierarchy: PV_wash < PV_spacer < PV_mud for efficient displacement
        - Minimum 500 ft contact length OR 10 min contact time
        - Velocity > 150 ft/min for turbulent regime
        """
        ann_cap = (hole_id_in ** 2 - casing_od_in ** 2) / 1029.4  # bbl/ft
        if ann_cap <= 0 or pump_rate_bbl_min <= 0:
            return {"error": "Invalid annular geometry or pump rate"}

        # Annular velocity
        q_gpm = pump_rate_bbl_min * 42.0
        v_ann = 24.5 * q_gpm / (hole_id_in ** 2 - casing_od_in ** 2)

        # Minimum volume from contact length
        vol_from_length = min_contact_length_ft * ann_cap

        # Minimum volume from contact time
        vol_from_time = pump_rate_bbl_min * min_contact_time_min

        spacer_volume = max(vol_from_length, vol_from_time)

        # Spacer density: geometric mean of mud and slurry (industry practice)
        spacer_density = (mud_density_ppg + slurry_density_ppg) / 2.0

        # Spacer rheology: intermediate hierarchy
        spacer_pv = (mud_pv + slurry_pv) / 2.0 * 0.8  # slightly thinner
        spacer_yp = (mud_yp + slurry_yp) / 2.0 * 0.7

        # Contact time achieved
        contact_time = spacer_volume / pump_rate_bbl_min
        contact_length = spacer_volume / ann_cap

        # Flow regime check
        d_eff = hole_id_in - casing_od_in
        if d_eff > 0 and spacer_pv > 0:
            # Reynolds number for Bingham
            rho_spacer_approx = spacer_density * 7.48  # lb/ft3
            re = 928 * spacer_density * v_ann * d_eff / spacer_pv
            flow_regime = "turbulent" if re > 2100 else "laminar"
        else:
            re = 0
            flow_regime = "unknown"

        return {
            "spacer_volume_bbl": round(spacer_volume, 1),
            "spacer_density_ppg": round(spacer_density, 1),
            "spacer_pv": round(spacer_pv, 1),
            "spacer_yp": round(spacer_yp, 1),
            "contact_time_min": round(contact_time, 1),
            "contact_length_ft": round(contact_length, 0),
            "annular_velocity_ftmin": round(v_ann, 1),
            "reynolds_number": round(re, 0),
            "flow_regime": flow_regime,
            "density_hierarchy_ok": mud_density_ppg < spacer_density < slurry_density_ppg,
            "rheology_hierarchy_ok": spacer_pv < mud_pv,
        }

    # ===================================================================
    # 12. Centralizer Design
    # ===================================================================
    @staticmethod
    def design_centralizers(
        casing_od_in: float,
        hole_id_in: float,
        casing_weight_ppf: float,
        inclination_profile: List[Dict[str, float]],
        centralizer_type: str = "bow_spring",
        target_standoff_pct: float = 67.0,
        restoring_force_lbf: float = 500.0,
    ) -> Dict[str, Any]:
        """
        Calculate centralizer spacing and standoff.

        Reference: API RP 10D-2 (Centralizer Placement)
        - Standoff without centralizer: SO_0 = radial_clearance * (1 - W*sin(inc)/F_restore)
        - Target: standoff > 67% (industry standard for good cement placement)
        """
        if hole_id_in <= casing_od_in:
            return {"error": "Hole ID must be > casing OD"}

        radial_clearance = (hole_id_in - casing_od_in) / 2.0  # inches

        if not inclination_profile:
            inclination_profile = [{"md": 0, "inc": 0}]

        # Centralizer stiffness (bow spring vs rigid)
        if centralizer_type == "rigid":
            k_stiffness = 2000.0  # lbf/in (rigid = high stiffness)
        else:
            k_stiffness = restoring_force_lbf / radial_clearance if radial_clearance > 0 else 500.0

        results_by_section = []
        total_centralizers = 0
        total_drag_extra = 0.0

        for i in range(len(inclination_profile)):
            station = inclination_profile[i]
            md = station.get("md", 0)
            inc = station.get("inc", 0)
            inc_rad = math.radians(inc)

            # Lateral weight component
            w_lateral = casing_weight_ppf * math.sin(inc_rad)  # lbf/ft

            # Standoff without centralizer
            if k_stiffness > 0 and radial_clearance > 0:
                deflection = w_lateral * 40.0 / k_stiffness  # 40 ft nominal section
                so_no_cent = max(1.0 - deflection / radial_clearance, 0.0) * 100.0
            else:
                so_no_cent = 100.0

            # Spacing for target standoff
            # spacing = F_restore / (W_lateral * (1 - target_SO/100))
            target_factor = 1.0 - target_standoff_pct / 100.0
            if w_lateral > 0.01 and target_factor > 0:
                spacing = restoring_force_lbf / (w_lateral * target_factor)
                spacing = max(min(spacing, 120.0), 20.0)  # clamp 20-120 ft
            else:
                spacing = 120.0  # max spacing for vertical sections

            # Number of centralizers in section (assume 500 ft per section)
            section_length = 500.0
            if i < len(inclination_profile) - 1:
                section_length = inclination_profile[i + 1].get("md", md + 500) - md
            num_in_section = max(int(math.ceil(section_length / spacing)), 1)
            total_centralizers += num_in_section

            # Drag force from centralizers (friction × restoring force × num)
            drag_per_cent = 0.3 * restoring_force_lbf if centralizer_type == "bow_spring" else 0.15 * restoring_force_lbf
            section_drag = drag_per_cent * num_in_section
            total_drag_extra += section_drag

            results_by_section.append({
                "md_ft": round(md, 0),
                "inclination_deg": round(inc, 1),
                "standoff_no_cent_pct": round(so_no_cent, 1),
                "spacing_ft": round(spacing, 0),
                "num_centralizers": num_in_section,
                "drag_force_lbf": round(section_drag, 0),
            })

        return {
            "total_centralizers": total_centralizers,
            "total_drag_extra_lbf": round(total_drag_extra, 0),
            "centralizer_type": centralizer_type,
            "target_standoff_pct": target_standoff_pct,
            "restoring_force_lbf": restoring_force_lbf,
            "radial_clearance_in": round(radial_clearance, 3),
            "sections": results_by_section,
        }

    # ===================================================================
    # MASTER: Full Cementing Simulation
    # ===================================================================
    @staticmethod
    def calculate_full_cementing(
        casing_od_in: float = 9.625,
        casing_id_in: float = 8.681,
        hole_id_in: float = 12.25,
        casing_shoe_md_ft: float = 10000.0,
        casing_shoe_tvd_ft: float = 9500.0,
        toc_md_ft: float = 5000.0,
        toc_tvd_ft: float = 4750.0,
        float_collar_md_ft: float = 9900.0,
        mud_weight_ppg: float = 10.5,
        spacer_density_ppg: float = 11.5,
        lead_cement_density_ppg: float = 13.5,
        tail_cement_density_ppg: float = 16.0,
        tail_length_ft: float = 500.0,
        spacer_volume_bbl: float = 25.0,
        excess_pct: float = 50.0,
        rat_hole_ft: float = 50.0,
        pump_rate_bbl_min: float = 5.0,
        pv_mud: float = 15.0,
        yp_mud: float = 10.0,
        fracture_gradient_ppg: float = 16.5,
        pore_pressure_ppg: float = 9.0,
    ) -> Dict[str, Any]:
        """
        Run complete cementing simulation: volumes, displacement,
        ECD, free-fall, U-tube, BHP schedule, and lift pressure.
        """
        # 1. Volumes
        volumes = CementingEngine.calculate_fluid_volumes(
            casing_od_in=casing_od_in, casing_id_in=casing_id_in,
            hole_id_in=hole_id_in, casing_shoe_md_ft=casing_shoe_md_ft,
            toc_md_ft=toc_md_ft, float_collar_md_ft=float_collar_md_ft,
            lead_cement_density_ppg=lead_cement_density_ppg,
            tail_cement_density_ppg=tail_cement_density_ppg,
            tail_length_ft=tail_length_ft, spacer_volume_bbl=spacer_volume_bbl,
            excess_pct=excess_pct, rat_hole_ft=rat_hole_ft,
        )

        if "error" in volumes:
            return volumes

        # 2. Displacement Schedule
        displacement = CementingEngine.calculate_displacement_schedule(
            spacer_volume_bbl=volumes["spacer_volume_bbl"],
            lead_cement_bbl=volumes["lead_cement_bbl"],
            tail_cement_bbl=volumes["tail_cement_bbl"],
            displacement_volume_bbl=volumes["displacement_volume_bbl"],
            pump_rate_bbl_min=pump_rate_bbl_min,
        )

        # 3. ECD During Job
        ecd_during = CementingEngine.calculate_ecd_during_job(
            casing_shoe_tvd_ft=casing_shoe_tvd_ft,
            hole_id_in=hole_id_in, casing_od_in=casing_od_in,
            mud_weight_ppg=mud_weight_ppg, spacer_density_ppg=spacer_density_ppg,
            lead_cement_density_ppg=lead_cement_density_ppg,
            tail_cement_density_ppg=tail_cement_density_ppg,
            pump_rate_bbl_min=pump_rate_bbl_min,
            pv_mud=pv_mud, yp_mud=yp_mud,
            fracture_gradient_ppg=fracture_gradient_ppg,
            pore_pressure_ppg=pore_pressure_ppg,
        )

        # 4. Free-Fall
        free_fall = CementingEngine.calculate_free_fall(
            casing_shoe_tvd_ft=casing_shoe_tvd_ft,
            mud_weight_ppg=mud_weight_ppg,
            cement_density_ppg=tail_cement_density_ppg,
            casing_id_in=casing_id_in, hole_id_in=hole_id_in,
            casing_od_in=casing_od_in,
        )

        # 5. U-Tube
        utube = CementingEngine.calculate_utube_effect(
            casing_shoe_tvd_ft=casing_shoe_tvd_ft,
            mud_weight_ppg=mud_weight_ppg,
            cement_density_ppg=lead_cement_density_ppg,
            cement_top_tvd_ft=toc_tvd_ft,
            casing_id_in=casing_id_in, hole_id_in=hole_id_in,
            casing_od_in=casing_od_in,
        )

        # 6. BHP Schedule
        bhp = CementingEngine.calculate_bhp_schedule(
            casing_shoe_tvd_ft=casing_shoe_tvd_ft,
            mud_weight_ppg=mud_weight_ppg, spacer_density_ppg=spacer_density_ppg,
            lead_cement_density_ppg=lead_cement_density_ppg,
            tail_cement_density_ppg=tail_cement_density_ppg,
            spacer_volume_bbl=volumes["spacer_volume_bbl"],
            lead_cement_bbl=volumes["lead_cement_bbl"],
            tail_cement_bbl=volumes["tail_cement_bbl"],
            displacement_volume_bbl=volumes["displacement_volume_bbl"],
            hole_id_in=hole_id_in, casing_od_in=casing_od_in,
            casing_id_in=casing_id_in, pump_rate_bbl_min=pump_rate_bbl_min,
            pv_mud=pv_mud, yp_mud=yp_mud,
        )

        # 7. Lift Pressure
        lift = CementingEngine.calculate_lift_pressure(
            casing_shoe_tvd_ft=casing_shoe_tvd_ft,
            toc_tvd_ft=toc_tvd_ft,
            cement_density_ppg=lead_cement_density_ppg,
            mud_weight_ppg=mud_weight_ppg,
            hole_id_in=hole_id_in, casing_od_in=casing_od_in,
            casing_id_in=casing_id_in,
        )

        # Assemble summary
        alerts = ecd_during.get("alerts", [])[:]
        if free_fall.get("free_fall_occurs"):
            alerts.append(f"Free-fall detected: ~{free_fall['free_fall_height_ft']:.0f} ft — "
                          f"consider staged cementing or float equipment")
        if utube.get("utube_occurs"):
            alerts.append(f"U-tube effect: {utube['pressure_imbalance_psi']:.0f} psi imbalance — "
                          f"hold pressure after pumps stop")

        summary = {
            "total_cement_bbl": volumes["total_cement_bbl"],
            "total_cement_sacks": volumes["lead_cement_sacks"] + volumes["tail_cement_sacks"],
            "displacement_bbl": volumes["displacement_volume_bbl"],
            "total_pump_bbl": volumes["total_pump_volume_bbl"],
            "job_time_hrs": displacement.get("total_time_hrs", 0),
            "max_ecd_ppg": ecd_during.get("max_ecd_ppg", 0),
            "fracture_margin_ppg": ecd_during.get("min_fracture_margin_ppg", 0),
            "max_bhp_psi": bhp.get("max_bhp_psi", 0),
            "lift_pressure_psi": lift.get("lift_pressure_psi", 0),
            "free_fall_ft": free_fall.get("free_fall_height_ft", 0),
            "utube_psi": utube.get("pressure_imbalance_psi", 0),
            "ecd_status": ecd_during.get("status", ""),
            "alerts": alerts,
        }

        return {
            "volumes": volumes,
            "displacement": displacement,
            "ecd_during_job": ecd_during,
            "free_fall": free_fall,
            "utube": utube,
            "bhp_schedule": bhp,
            "lift_pressure": lift,
            "summary": summary,
        }

    # ===================================================================
    # 9. Operational Recommendations Generator
    # ===================================================================
    @staticmethod
    def generate_recommendations(result: Dict[str, Any]) -> List[str]:
        """
        Generate operational recommendations from cementing simulation results.

        Parameters:
        - result: output from calculate_full_cementing()

        Returns list of plain-text recommendations.
        """
        recs: List[str] = []
        summary = result.get("summary", {})

        # ECD management
        margin = summary.get("fracture_margin_ppg", 999)
        if margin < 0:
            recs.append("CRITICAL: ECD exceeds fracture gradient. Reduce pump rate or cement density.")
        elif margin < 0.3:
            recs.append("Tight ECD margin — consider reducing pump rate during cement displacement.")
        elif margin < 0.5:
            recs.append("Monitor ECD closely during tail cement placement.")

        # Free-fall
        ff = result.get("free_fall", {})
        if ff.get("free_fall_occurs"):
            h = ff.get("free_fall_height_ft", 0)
            if h > 1000:
                recs.append(f"Significant free-fall ({h} ft). Use staged cementing or low-density lead.")
            elif h > 300:
                recs.append(f"Moderate free-fall ({h} ft). Monitor returns and pressures carefully.")

        # U-tube
        ut = result.get("utube", {})
        if ut.get("utube_occurs"):
            recs.append("U-tube effect detected. Hold back-pressure after displacement.")

        # Volume check
        volumes = result.get("volumes", {})
        total = volumes.get("total_cement_bbl", 0)
        if total > 600:
            recs.append("Large cement volume — verify mixing capacity and bulk storage.")

        # Job time
        job_time = summary.get("job_time_hrs", 0)
        if job_time > 4:
            recs.append("Extended job time — verify slurry thickening time exceeds job duration + safety.")

        if not recs:
            recs.append("All parameters within normal operating range. Standard execution recommended.")

        return recs
