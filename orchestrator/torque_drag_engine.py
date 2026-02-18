"""
Torque & Drag Calculation Engine
Based on Johancsik (1984) Soft-String Model
References: Applied Drilling Engineering (Bourgoyne et al.), SPE 11380
"""
import math
from typing import List, Dict, Any, Optional


class TorqueDragEngine:
    """
    Implements the soft-string torque & drag model for drillstring
    mechanical analysis in directional/horizontal wells.
    """

    # Steel properties
    STEEL_E = 30e6          # Young's modulus, psi
    STEEL_DENSITY = 490.0   # lb/ft³

    @staticmethod
    def compute_survey_derived(stations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Compute TVD, North, East, DLS using minimum curvature method.
        Input: list of {md, inclination, azimuth} (degrees)
        Output: same list enriched with tvd, north, east, dls
        """
        if not stations:
            return []

        results = []
        # First station
        s0 = stations[0]
        s0_out = {
            "md": s0["md"],
            "inclination": s0["inclination"],
            "azimuth": s0["azimuth"],
            "tvd": s0.get("tvd", 0.0),
            "north": s0.get("north", 0.0),
            "east": s0.get("east", 0.0),
            "dls": 0.0
        }
        results.append(s0_out)

        for i in range(1, len(stations)):
            prev = stations[i - 1]
            curr = stations[i]

            delta_md = curr["md"] - prev["md"]
            if delta_md <= 0:
                results.append({
                    "md": curr["md"],
                    "inclination": curr["inclination"],
                    "azimuth": curr["azimuth"],
                    "tvd": results[-1]["tvd"],
                    "north": results[-1]["north"],
                    "east": results[-1]["east"],
                    "dls": 0.0
                })
                continue

            inc1 = math.radians(prev["inclination"])
            inc2 = math.radians(curr["inclination"])
            azi1 = math.radians(prev["azimuth"])
            azi2 = math.radians(curr["azimuth"])

            # Dogleg angle
            cos_dl = (math.cos(inc2 - inc1)
                      - math.sin(inc1) * math.sin(inc2) * (1 - math.cos(azi2 - azi1)))
            cos_dl = max(-1.0, min(1.0, cos_dl))
            dl = math.acos(cos_dl)

            # Ratio factor (minimum curvature)
            if dl < 1e-7:
                rf = 1.0
            else:
                rf = (2.0 / dl) * math.tan(dl / 2.0)

            # Increments
            delta_tvd = (delta_md / 2.0) * (math.cos(inc1) + math.cos(inc2)) * rf
            delta_north = (delta_md / 2.0) * (
                math.sin(inc1) * math.cos(azi1) + math.sin(inc2) * math.cos(azi2)
            ) * rf
            delta_east = (delta_md / 2.0) * (
                math.sin(inc1) * math.sin(azi1) + math.sin(inc2) * math.sin(azi2)
            ) * rf

            # DLS in deg/100ft
            dls = math.degrees(dl) / delta_md * 100.0

            results.append({
                "md": curr["md"],
                "inclination": curr["inclination"],
                "azimuth": curr["azimuth"],
                "tvd": round(results[-1]["tvd"] + delta_tvd, 2),
                "north": round(results[-1]["north"] + delta_north, 2),
                "east": round(results[-1]["east"] + delta_east, 2),
                "dls": round(dls, 2)
            })

        return results

    @staticmethod
    def compute_torque_drag(
        survey: List[Dict[str, Any]],
        drillstring: List[Dict[str, Any]],
        friction_cased: float,
        friction_open: float,
        operation: str,
        mud_weight: float,
        wob: float = 0.0,
        rpm: float = 0.0,
        casing_shoe_md: float = 0.0
    ) -> Dict[str, Any]:
        """
        Johancsik Soft-String Model for Torque & Drag.

        Parameters:
        - survey: list of stations with md, inclination, azimuth (degrees)
        - drillstring: list of sections with od, id_inner, weight (lb/ft), length, order_from_bit
        - friction_cased/open: friction factors
        - operation: 'rotating', 'sliding', 'trip_in', 'trip_out', 'back_ream'
        - mud_weight: ppg
        - wob: weight on bit (klb) — only for rotating/sliding
        - rpm: rotary speed (only for rotating)
        - casing_shoe_md: casing shoe depth for friction factor selection
        """
        if len(survey) < 2:
            return {"error": "Need at least 2 survey stations"}

        # Determine direction factor
        # trip_out / back_ream => pulling up (friction opposes upward motion) => drag adds
        # trip_in / sliding => going down => friction opposes => drag subtracts from tension
        # rotating => friction is tangential (torque), axial drag from WOB
        direction = 1.0  # +1 for trip out (tension increases going up)
        if operation in ("trip_in", "sliding"):
            direction = -1.0

        # Build weight profile per station from drillstring
        # Map each survey interval to the drillstring section that covers it
        total_string_length = sum(s["length"] for s in drillstring)
        sorted_ds = sorted(drillstring, key=lambda x: x.get("order_from_bit", 0))

        # Build cumulative length map from bit
        ds_map = []  # (start_md_from_bit, end_md_from_bit, weight_per_ft, od, id_inner)
        cum = 0.0
        for sec in sorted_ds:
            ds_map.append({
                "start": cum,
                "end": cum + sec["length"],
                "weight": sec["weight"],
                "od": sec["od"],
                "id_inner": sec.get("id_inner", sec["od"] - 1.0)
            })
            cum += sec["length"]

        bit_md = survey[-1]["md"]  # assume last survey station ~ bit depth

        def get_ds_at_md(md_val):
            """Get drillstring properties at a given MD."""
            dist_from_bit = bit_md - md_val
            if dist_from_bit < 0:
                dist_from_bit = 0
            for sec in ds_map:
                if sec["start"] <= dist_from_bit <= sec["end"]:
                    return sec
            # If beyond drillstring, use last section
            return ds_map[-1] if ds_map else {"weight": 20.0, "od": 5.0, "id_inner": 4.276}

        # Buoyancy factor
        bf = 1.0 - (mud_weight / 65.5)  # 65.5 ppg = steel SG

        # Process from bit to surface (bottom-up for trip_out/rotating)
        # or surface to bit (top-down for trip_in), but Johancsik always goes bottom-up
        station_results = []

        # Start at bit: axial force = -WOB (compression) for drilling operations
        if operation in ("rotating", "sliding"):
            fa = -wob * 1000.0  # convert klb to lb
        else:
            fa = 0.0  # free at bit for tripping

        cumulative_torque = 0.0

        # Process bottom to top
        for i in range(len(survey) - 1, 0, -1):
            s_lower = survey[i]
            s_upper = survey[i - 1]

            md_lower = s_lower["md"]
            md_upper = s_upper["md"]
            delta_md = md_lower - md_upper

            if delta_md <= 0:
                continue

            inc_lower = math.radians(s_lower["inclination"])
            inc_upper = math.radians(s_upper["inclination"])
            azi_lower = math.radians(s_lower["azimuth"])
            azi_upper = math.radians(s_upper["azimuth"])

            d_inc = inc_upper - inc_lower
            d_azi = azi_upper - azi_lower
            avg_inc = (inc_upper + inc_lower) / 2.0

            # Drillstring properties at midpoint
            mid_md = (md_lower + md_upper) / 2.0
            ds = get_ds_at_md(mid_md)

            # Buoyed weight of this interval
            w = ds["weight"] * bf * delta_md  # total buoyed weight of segment

            # Friction factor selection
            mu = friction_open
            if mid_md < casing_shoe_md:
                mu = friction_cased

            # Normal force (Johancsik)
            # Fn = sqrt( (Fa*d_inc + w*sin(avg_inc))^2 + (Fa*sin(avg_inc)*d_azi)^2 )
            term1 = fa * d_inc + w * math.sin(avg_inc)
            term2 = fa * math.sin(avg_inc) * d_azi
            fn = math.sqrt(term1**2 + term2**2)

            # Drag force
            f_drag = mu * fn

            # Update axial force going upward
            if operation == "rotating":
                # In rotating, friction goes to torque, not axial drag
                # But there's still axial component from WOB transmission
                fa = fa + w * math.cos(avg_inc)
            else:
                fa = fa + w * math.cos(avg_inc) + direction * f_drag

            # Torque calculation
            torque_increment = 0.0
            if operation in ("rotating", "back_ream"):
                r_contact = ds["od"] / 2.0 / 12.0  # convert to feet
                torque_increment = mu * fn * r_contact
                cumulative_torque += torque_increment

            # Buckling check
            buckling = TorqueDragEngine._buckling_check(
                fa, avg_inc, ds, mud_weight, delta_md, mid_md, casing_shoe_md
            )

            station_results.append({
                "md": round(md_upper, 1),
                "tvd": s_upper.get("tvd", 0),
                "inclination": s_upper["inclination"],
                "axial_force": round(fa, 0),
                "normal_force": round(fn, 0),
                "drag": round(f_drag, 0),
                "torque": round(cumulative_torque, 0),
                "buckling_status": buckling
            })

        # Reverse so results go top to bottom
        station_results.reverse()

        # Surface values
        surface_hookload = fa / 1000.0  # klb
        surface_torque = cumulative_torque

        # Alerts
        alerts = []
        if surface_hookload < 0:
            alerts.append("Negative hookload at surface — check WOB/friction")
        for sr in station_results:
            if sr["buckling_status"] != "OK":
                alerts.append(f"Buckling at MD {sr['md']} ft: {sr['buckling_status']}")
                break  # Only first occurrence

        max_side_force = max((sr["normal_force"] for sr in station_results), default=0)

        summary = {
            "surface_hookload_klb": round(surface_hookload, 1),
            "surface_torque_ftlb": round(surface_torque, 0),
            "max_side_force_lb": round(max_side_force, 0),
            "operation": operation,
            "friction_cased": friction_cased,
            "friction_open": friction_open,
            "buoyancy_factor": round(bf, 4),
            "alerts": alerts
        }

        return {
            "station_results": station_results,
            "summary": summary
        }

    @staticmethod
    def _buckling_check(
        axial_force: float,
        inclination: float,
        ds: Dict,
        mud_weight: float,
        delta_md: float,
        md: float,
        casing_shoe_md: float
    ) -> str:
        """
        Check for sinusoidal and helical buckling.
        Lubinski (sinusoidal): Fc_sin = 2 * sqrt(E*I*w*sin(inc)/r)
        Mitchell (helical):    Fc_hel = 2 * sqrt(2) * sqrt(E*I*w*sin(inc)/r)
        """
        if axial_force >= 0:
            return "OK"  # Tension, no buckling

        od = ds["od"]
        id_inner = ds.get("id_inner", od - 1.0)

        # Moment of inertia
        i_moment = math.pi / 64.0 * (od**4 - id_inner**4)

        # Buoyed weight per inch
        bf = 1.0 - (mud_weight / 65.5)
        w_per_inch = ds["weight"] * bf / 12.0  # lb/in

        # Radial clearance — estimate wellbore ID
        if md < casing_shoe_md:
            hole_id = TorqueDragEngine._casing_id_estimate(od)
        else:
            hole_id = od + 3.0  # rough open hole clearance

        r = (hole_id - od) / 2.0  # radial clearance, inches
        if r <= 0:
            r = 0.5

        sin_inc = math.sin(inclination)
        if sin_inc < 0.01:
            sin_inc = 0.01  # Avoid division by zero in vertical

        e = TorqueDragEngine.STEEL_E
        ei = e * i_moment

        # Critical forces
        fc_sin = 2.0 * math.sqrt(ei * w_per_inch * sin_inc / r)
        fc_hel = 2.0 * math.sqrt(2.0) * math.sqrt(ei * w_per_inch * sin_inc / r)

        compression = abs(axial_force)
        if compression > fc_hel:
            return "HELICAL"
        elif compression > fc_sin:
            return "SINUSOIDAL"
        return "OK"

    @staticmethod
    def _casing_id_estimate(pipe_od: float) -> float:
        """Estimate casing ID based on common pipe OD."""
        casing_map = {
            5.0: 8.681,    # 9-5/8" casing
            5.5: 8.681,
            3.5: 6.366,    # 7" casing
            4.5: 8.681,
            6.625: 10.772, # 11-3/4" casing
        }
        return casing_map.get(pipe_od, pipe_od + 3.5)

    @staticmethod
    def back_calculate_friction(
        survey: List[Dict[str, Any]],
        drillstring: List[Dict[str, Any]],
        measured_hookload: float,
        operation: str,
        mud_weight: float,
        wob: float = 0.0,
        casing_shoe_md: float = 0.0,
        tolerance: float = 0.5
    ) -> Dict[str, Any]:
        """
        Back-calculate friction factor using bisection method.
        Finds the friction factor that matches the measured hookload.

        Parameters:
        - measured_hookload: measured surface hookload in klb
        - tolerance: acceptable error in klb
        Returns: dict with calculated friction factor and iterations
        """
        mu_low = 0.05
        mu_high = 0.60
        max_iter = 50

        for iteration in range(max_iter):
            mu_mid = (mu_low + mu_high) / 2.0

            result = TorqueDragEngine.compute_torque_drag(
                survey=survey,
                drillstring=drillstring,
                friction_cased=mu_mid,
                friction_open=mu_mid,
                operation=operation,
                mud_weight=mud_weight,
                wob=wob,
                casing_shoe_md=casing_shoe_md
            )

            if "error" in result:
                return {"error": result["error"]}

            calc_hookload = result["summary"]["surface_hookload_klb"]
            error = calc_hookload - measured_hookload

            if abs(error) < tolerance:
                return {
                    "friction_factor": round(mu_mid, 4),
                    "calculated_hookload_klb": round(calc_hookload, 1),
                    "measured_hookload_klb": measured_hookload,
                    "error_klb": round(error, 2),
                    "iterations": iteration + 1,
                    "converged": True
                }

            if operation in ("trip_out", "back_ream", "rotating"):
                # Higher friction -> higher hookload
                if calc_hookload > measured_hookload:
                    mu_high = mu_mid
                else:
                    mu_low = mu_mid
            else:
                # trip_in, sliding: higher friction -> lower hookload
                if calc_hookload < measured_hookload:
                    mu_high = mu_mid
                else:
                    mu_low = mu_mid

        return {
            "friction_factor": round(mu_mid, 4),
            "calculated_hookload_klb": round(calc_hookload, 1),
            "measured_hookload_klb": measured_hookload,
            "error_klb": round(error, 2),
            "iterations": max_iter,
            "converged": False
        }
