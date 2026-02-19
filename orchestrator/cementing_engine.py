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
    ) -> Dict[str, Any]:
        """
        Track fluid interfaces vs. cumulative barrels pumped.

        Returns schedule with key events:
          - Spacer away (spacer done pumping)
          - Lead away
          - Tail away
          - Plug bump (displacement complete)

        Parameters:
        - pump_rate_bbl_min: average pump rate
        - num_points: resolution of schedule curve
        """
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
    # 4. Free-Fall Calculation
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
    ) -> Dict[str, Any]:
        """
        Calculate free-fall height during cementing.

        Free-fall occurs when the hydrostatic pressure of the heavier
        cement column inside the casing exceeds the annular hydrostatic
        (mud column). The cement falls until pressures equilibrate.

        h_ff = (P_annulus - P_casing) / (grad_cement - grad_mud)

        where gradients are in psi/ft: grad = density * 0.052
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

        # Hydrostatic imbalance over the full casing depth
        # P_casing (cement inside) vs P_annulus (mud outside)
        delta_grad = grad_cement - grad_mud  # psi/ft

        # Free-fall height: how far cement drops before equilibrium
        # Based on column balance; simplified for uniform annulus
        ann_cap = (hole_id_in ** 2 - casing_od_in ** 2) / 1029.4
        csg_cap = casing_id_in ** 2 / 1029.4

        if ann_cap <= 0 or csg_cap <= 0:
            return {"error": "Invalid geometry"}

        # Volume ratio — cement dropping inside pushes mud up in annulus
        vol_ratio = csg_cap / ann_cap

        # Pressure balance: cement_density * h_ff = mud_density * h_ff * vol_ratio + friction_losses
        # Simplified (ignoring friction): h_ff = delta_P / delta_grad
        # Full depth imbalance
        delta_p = (cement_density_ppg - mud_weight_ppg) * 0.052 * casing_shoe_tvd_ft
        h_ff = delta_p / (delta_grad * (1 + vol_ratio))

        h_ff = min(h_ff, casing_shoe_tvd_ft)  # Cannot exceed total depth
        h_ff = max(h_ff, 0.0)

        # Volume of free-fall
        free_fall_vol_bbl = h_ff * csg_cap

        return {
            "free_fall_height_ft": round(h_ff, 1),
            "free_fall_volume_bbl": round(free_fall_vol_bbl, 1),
            "free_fall_occurs": h_ff > 10.0,  # threshold: >10 ft is significant
            "cement_gradient_psi_ft": round(grad_cement, 4),
            "mud_gradient_psi_ft": round(grad_mud, 4),
            "delta_gradient_psi_ft": round(delta_grad, 4),
            "volume_ratio_csg_ann": round(vol_ratio, 3),
            "explanation": (
                f"Cement free-falls ~{h_ff:.0f} ft due to {cement_density_ppg - mud_weight_ppg:.1f} ppg "
                f"density differential"
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
    ) -> Dict[str, Any]:
        """
        Calculate U-tube equilibrium when pumps stop.

        When the pump stops, the heavier cement column in the annulus
        (or casing) drives fluid until the hydrostatic pressures on
        both legs of the U-tube balance.

        P_casing_side = P_annulus_side  at shoe
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

        # Casing side pressure at shoe (initially all mud)
        p_casing = grad_mud * casing_shoe_tvd_ft

        # Imbalance
        delta_p = p_annulus - p_casing

        if delta_p <= 0:
            return {
                "utube_occurs": False,
                "pressure_imbalance_psi": 0.0,
                "fluid_drop_ft": 0.0,
                "fluid_drop_bbl": 0.0,
                "explanation": "No U-tube: casing side is heavier or balanced",
                "p_annulus_psi": round(p_annulus, 0),
                "p_casing_psi": round(p_casing, 0),
            }

        # Fluid drops inside casing (cement flows down annulus, mud flows up casing)
        # Drop distance to equilibrate
        # delta_p = (grad_cement - grad_mud) * h_drop * (1 + csg_cap/ann_cap)
        combined_factor = (grad_cement - grad_mud) * (1 + csg_cap / ann_cap)
        if combined_factor > 0:
            h_drop = delta_p / combined_factor
        else:
            h_drop = 0.0

        h_drop = min(h_drop, casing_shoe_tvd_ft)
        drop_vol = h_drop * csg_cap

        return {
            "utube_occurs": delta_p > 5.0,
            "pressure_imbalance_psi": round(delta_p, 0),
            "fluid_drop_ft": round(h_drop, 1),
            "fluid_drop_bbl": round(drop_vol, 1),
            "p_annulus_psi": round(p_annulus, 0),
            "p_casing_psi": round(p_casing, 0),
            "explanation": (
                f"U-tube: {delta_p:.0f} psi imbalance causes ~{h_drop:.0f} ft fluid movement "
                f"({drop_vol:.1f} bbl)"
            ) if delta_p > 5 else "Negligible U-tube effect",
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
