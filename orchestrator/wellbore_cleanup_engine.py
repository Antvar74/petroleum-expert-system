"""
Wellbore Cleanup (Hole Cleaning) Calculation Engine

Evaluates cuttings transport efficiency in directional/horizontal wells.
References:
- API RP 13D: Rheology & Hydraulics of Oil-Well Drilling Fluids
- Moore correlation for slip velocity
- Luo et al. (1992): Hole Cleaning Index (HCI)
- Bourgoyne et al.: Applied Drilling Engineering, Ch. 4
"""
import math
from typing import List, Dict, Any, Optional


class WellboreCleanupEngine:
    """
    Implements hole-cleaning calculations for vertical-to-horizontal wells.
    All methods are @staticmethod — no external dependencies beyond math.
    """

    # Physical constants
    GRAVITY = 32.174        # ft/s²
    WATER_DENSITY = 8.34    # ppg (fresh water)

    # Recommended minimums (API RP 13D)
    MIN_AV_VERTICAL = 120.0      # ft/min for <30° inclination
    MIN_AV_HIGH_ANGLE = 150.0    # ft/min for >60° inclination
    MIN_AV_TRANSITION = 130.0    # ft/min for 30-60°

    @staticmethod
    def calculate_annular_velocity(
        flow_rate: float,
        hole_id: float,
        pipe_od: float
    ) -> float:
        """
        Calculate annular velocity.

        Args:
            flow_rate: pump rate (gpm)
            hole_id: hole inner diameter (inches)
            pipe_od: pipe outer diameter (inches)

        Returns:
            Annular velocity (ft/min)
        """
        if hole_id <= pipe_od:
            return 0.0
        annular_area = (hole_id ** 2 - pipe_od ** 2)
        if annular_area <= 0:
            return 0.0
        # Va = 24.51 * Q / (Dh² - Dp²)
        return 24.51 * flow_rate / annular_area

    @staticmethod
    def calculate_slip_velocity(
        mud_weight: float,
        pv: float,
        yp: float,
        cutting_size: float,
        cutting_density: float
    ) -> float:
        """
        Calculate cuttings slip velocity using Moore correlation.

        Args:
            mud_weight: mud density (ppg)
            pv: plastic viscosity (cP)
            yp: yield point (lb/100ft²)
            cutting_size: mean cutting diameter (inches)
            cutting_density: cutting density (ppg, typically 21-22 for sandstone)

        Returns:
            Slip velocity (ft/min)
        """
        if cutting_size <= 0 or mud_weight <= 0:
            return 0.0

        # Apparent viscosity for Moore correlation
        mu_a = pv + 5.0 * yp  # simplified apparent viscosity (cP)
        if mu_a <= 0:
            mu_a = 1.0

        # Density difference
        delta_rho = cutting_density - mud_weight
        if delta_rho <= 0:
            return 0.0

        # Moore correlation: Vs = 113.4 * d * sqrt(delta_rho / (mud_weight * Cd))
        # Cd depends on particle Reynolds number — use iterative approach
        # Simplified: assume intermediate regime
        d_ft = cutting_size / 12.0  # convert inches to feet

        # Reynolds number estimate
        re_p = 15.47 * mud_weight * cutting_size * math.sqrt(
            delta_rho * cutting_size / mud_weight
        ) / mu_a

        if re_p < 1:
            # Stokes regime: Vs = 113.4 * d_in^2 * delta_rho / mu_a
            vs = 113.4 * (cutting_size ** 2) * delta_rho / mu_a
        elif re_p < 2000:
            # Intermediate regime (Moore)
            vs = 175.0 * cutting_size * math.sqrt(delta_rho / mud_weight)
        else:
            # Turbulent (Newton)
            vs = 175.0 * cutting_size * math.sqrt(delta_rho / mud_weight)

        return max(vs, 0.0)

    @staticmethod
    def calculate_slip_velocity_larsen(
        mud_weight: float, pv: float, yp: float,
        cutting_size: float, cutting_density: float,
        inclination: float, rpm: float = 0.0,
        hole_id: float = 8.5, pipe_od: float = 5.0,
        annular_velocity: float = 0.0
    ) -> Dict[str, Any]:
        """
        Calculate cuttings slip velocity using Larsen correlation (SPE 36383, 1997)
        for high-angle and horizontal wells (inclination > 30°).

        Extends Moore vertical slip with inclination, RPM, and bed erosion factors.

        Parameters:
        - inclination: wellbore inclination (degrees from vertical)
        - rpm: drillstring rotation speed (RPM)
        - hole_id: hole inner diameter (inches)
        - pipe_od: pipe outer diameter (inches)
        - annular_velocity: actual annular velocity (ft/min, for transport calc)

        Returns:
        - slip_velocity_ftmin, bed_erosion_velocity, effective_transport_velocity,
          rpm_factor, inclination_factor, correlation_used
        """
        # Base vertical slip velocity using existing Moore correlation
        vs_vertical = WellboreCleanupEngine.calculate_slip_velocity(
            mud_weight, pv, yp, cutting_size, cutting_density
        )

        inc_rad = math.radians(inclination)

        # Inclination factor (Larsen 1997)
        if inclination < 10.0:
            # Near-vertical: no correction needed
            f_inc = 1.0
        elif inclination <= 60.0:
            # Transition zone (30-60°): maximum settling tendency at ~45-60°
            f_inc = 1.0 + 0.3 * math.sin(2.0 * inc_rad)
        else:
            # High angle (60-90°): cuttings bed forms, reduced vertical component
            f_inc = 1.0 + 0.2 * (1.0 - math.cos(inc_rad))

        # Inclined slip velocity: vertical component corrected by inclination
        vs_inclined = vs_vertical * abs(math.cos(inc_rad)) * f_inc
        # For horizontal (cos~0), slip is dominated by bed behavior
        if inclination > 80.0:
            vs_inclined = max(vs_inclined, vs_vertical * 0.1)

        # RPM factor: drillstring rotation disturbs cuttings bed and improves transport
        if inclination > 30.0:
            if inclination >= 75.0:
                # Near-horizontal: RPM very effective
                f_rpm = 1.0 - min(rpm / 150.0, 0.5)
            else:
                # Inclined: RPM moderately effective
                f_rpm = 1.0 - min(rpm / 200.0, 0.4)
        else:
            f_rpm = 1.0  # RPM has minimal effect in vertical wells

        f_rpm = max(f_rpm, 0.3)  # Cap minimum reduction

        # Effective slip velocity
        vs_effective = vs_inclined * f_rpm

        # Bed erosion velocity (empirical): minimum annular velocity to erode
        # a stationary cuttings bed (applicable for inc > 60°)
        if inclination > 60.0:
            # Higher inclination needs higher velocity to erode bed
            v_bed_erosion = 50.0 + 2.5 * (inclination - 60.0)  # ft/min
        elif inclination > 30.0:
            v_bed_erosion = 30.0 + (inclination - 30.0) * 0.67  # ramp from 30 to 50
        else:
            v_bed_erosion = 0.0  # not applicable for vertical wells

        # Effective transport velocity (if annular velocity provided)
        effective_transport = annular_velocity - vs_effective if annular_velocity > 0 else 0.0

        return {
            "slip_velocity_ftmin": round(vs_effective, 2),
            "vs_vertical_ftmin": round(vs_vertical, 2),
            "bed_erosion_velocity_ftmin": round(v_bed_erosion, 2),
            "effective_transport_velocity_ftmin": round(effective_transport, 2),
            "rpm_factor": round(f_rpm, 4),
            "inclination_factor": round(f_inc, 4),
            "inclination_deg": inclination,
            "correlation_used": "larsen"
        }

    @staticmethod
    def calculate_ctr(annular_velocity: float, slip_velocity: float) -> float:
        """
        Calculate Cuttings Transport Ratio.
        CTR = (Va - Vs) / Va

        Args:
            annular_velocity: annular velocity (ft/min)
            slip_velocity: cuttings slip velocity (ft/min)

        Returns:
            CTR (dimensionless, 0-1). Values > 0.55 indicate adequate cleaning.
        """
        if annular_velocity <= 0:
            return 0.0
        ctr = (annular_velocity - slip_velocity) / annular_velocity
        return max(ctr, 0.0)

    @staticmethod
    def calculate_transport_velocity(
        annular_velocity: float,
        slip_velocity: float
    ) -> float:
        """
        Net cuttings transport velocity.
        Vt = Va - Vs

        Returns:
            Transport velocity (ft/min). Positive = cuttings moving up.
        """
        return annular_velocity - slip_velocity

    @staticmethod
    def calculate_minimum_flow_rate(
        hole_id: float,
        pipe_od: float,
        inclination: float
    ) -> float:
        """
        Calculate minimum flow rate for adequate hole cleaning (API RP 13D).

        Args:
            hole_id: hole diameter (inches)
            pipe_od: pipe OD (inches)
            inclination: wellbore inclination (degrees)

        Returns:
            Minimum flow rate (gpm)
        """
        if hole_id <= pipe_od:
            return 0.0

        annular_area = hole_id ** 2 - pipe_od ** 2

        if inclination < 30:
            min_av = WellboreCleanupEngine.MIN_AV_VERTICAL
        elif inclination > 60:
            min_av = WellboreCleanupEngine.MIN_AV_HIGH_ANGLE
        else:
            min_av = WellboreCleanupEngine.MIN_AV_TRANSITION

        # Va = 24.51 * Q / (Dh² - Dp²) → Q = Va * (Dh² - Dp²) / 24.51
        return min_av * annular_area / 24.51

    @staticmethod
    def calculate_hole_cleaning_index(
        annular_velocity: float,
        rpm: float,
        inclination: float,
        mud_weight: float,
        cutting_density: float,
        pv: float,
        yp: float
    ) -> float:
        """
        Hole Cleaning Index (HCI) based on Luo et al. (1992).
        Accounts for inclination, pipe rotation, and fluid properties.

        HCI = (Va / Va_min) * f(rpm) * f(rheology)

        Values: >1.0 = good cleaning, 0.7-1.0 = marginal, <0.7 = poor

        Returns:
            HCI (dimensionless)
        """
        # Minimum annular velocity for inclination
        if inclination < 30:
            va_min = WellboreCleanupEngine.MIN_AV_VERTICAL
        elif inclination > 60:
            va_min = WellboreCleanupEngine.MIN_AV_HIGH_ANGLE
        else:
            va_min = WellboreCleanupEngine.MIN_AV_TRANSITION

        if va_min <= 0:
            return 0.0

        # Velocity ratio
        ratio_v = annular_velocity / va_min

        # RPM benefit: rotation improves cleaning 10-25% in high-angle wells
        rpm_factor = 1.0
        if inclination > 30 and rpm > 0:
            rpm_factor = 1.0 + min(rpm / 600.0, 0.25)  # cap at 25% benefit

        # Rheology factor: higher YP/PV ratio helps carry cuttings
        rheo_factor = 1.0
        if pv > 0:
            yp_pv_ratio = yp / pv
            if yp_pv_ratio >= 1.0:
                rheo_factor = 1.0 + min((yp_pv_ratio - 1.0) * 0.1, 0.15)
            elif yp_pv_ratio < 0.5:
                rheo_factor = 0.85

        # Density factor: heavier mud carries better
        density_factor = 1.0
        if cutting_density > 0 and mud_weight > 0:
            density_ratio = mud_weight / cutting_density
            if density_ratio > 0.5:
                density_factor = 1.0 + min((density_ratio - 0.4) * 0.2, 0.1)

        hci = ratio_v * rpm_factor * rheo_factor * density_factor
        return round(hci, 3)

    @staticmethod
    def design_sweep_pill(
        annular_volume_per_ft: float,
        annular_length: float,
        mud_weight: float,
        pill_weight_increment: float = 2.0,
        coverage_factor: float = 1.5
    ) -> Dict[str, Any]:
        """
        Design a viscous/heavy sweep pill for hole cleaning.

        Args:
            annular_volume_per_ft: annular volume (bbl/ft)
            annular_length: length of annulus to sweep (ft)
            mud_weight: current mud weight (ppg)
            pill_weight_increment: extra weight over current mud (ppg)
            coverage_factor: annular volume coverage (typically 1.0-2.0)

        Returns:
            Dict with pill_volume_bbl, pill_weight_ppg, pill_length_ft
        """
        annular_vol = annular_volume_per_ft * annular_length
        pill_volume = annular_vol * coverage_factor
        pill_weight = mud_weight + pill_weight_increment

        # Pill length in the annulus
        pill_length = 0.0
        if annular_volume_per_ft > 0:
            pill_length = pill_volume / annular_volume_per_ft

        return {
            "pill_volume_bbl": round(pill_volume, 1),
            "pill_weight_ppg": round(pill_weight, 1),
            "pill_length_ft": round(pill_length, 0),
            "annular_volume_bbl": round(annular_vol, 1)
        }

    @staticmethod
    def calculate_cuttings_concentration(
        rop: float,
        hole_id: float,
        pipe_od: float,
        flow_rate: float,
        transport_velocity: float
    ) -> float:
        """
        Estimate cuttings concentration in annulus (% by volume).

        Args:
            rop: rate of penetration (ft/hr)
            hole_id: hole diameter (inches)
            pipe_od: pipe OD (inches)
            flow_rate: pump rate (gpm)
            transport_velocity: net transport velocity (ft/min)

        Returns:
            Cuttings concentration (vol %)
        """
        if flow_rate <= 0 or transport_velocity <= 0:
            return 100.0

        # Bit area (generating cuttings)
        bit_area = math.pi * (hole_id / 2.0) ** 2  # in²

        # Volume rate of cuttings generated
        cutting_gen_rate = bit_area * (rop / 60.0) / 144.0  # ft³/min

        # Annular flow volume rate
        annular_area = math.pi * (hole_id ** 2 - pipe_od ** 2) / (4.0 * 144.0)  # ft²
        annular_flow = annular_area * transport_velocity  # ft³/min

        if annular_flow <= 0:
            return 100.0

        concentration = (cutting_gen_rate / (annular_flow + cutting_gen_rate)) * 100.0
        return round(min(concentration, 100.0), 2)

    @staticmethod
    def calculate_cuttings_ecd_contribution(
        concentration_pct: float, cutting_density: float, mud_weight: float
    ) -> Dict[str, Any]:
        """
        Calculate the ECD contribution from cuttings in the annulus.

        The effective mud weight increase due to suspended cuttings is:
        cuttings_ecd = (concentration_fraction) * (cutting_density - mud_weight)

        Parameters:
        - concentration_pct: cuttings concentration (vol %)
        - cutting_density: cuttings density (ppg, typically 21-22)
        - mud_weight: base mud weight (ppg)

        Returns:
        - cuttings_ecd_ppg: additional ECD from cuttings
        - effective_mud_weight_ppg: mud_weight + cuttings_ecd
        """
        # Guards
        if concentration_pct <= 0:
            return {
                "cuttings_ecd_ppg": 0.0,
                "effective_mud_weight_ppg": round(mud_weight, 3),
                "concentration_fraction": 0.0,
                "density_difference_ppg": round(max(cutting_density - mud_weight, 0.0), 3)
            }

        conc = min(concentration_pct, 100.0)
        conc_frac = conc / 100.0

        # If cutting density <= mud weight, cuttings don't add to ECD
        delta_rho = cutting_density - mud_weight
        if delta_rho <= 0:
            return {
                "cuttings_ecd_ppg": 0.0,
                "effective_mud_weight_ppg": round(mud_weight, 3),
                "concentration_fraction": round(conc_frac, 4),
                "density_difference_ppg": 0.0
            }

        cuttings_ecd = conc_frac * delta_rho
        effective_mw = mud_weight + cuttings_ecd

        return {
            "cuttings_ecd_ppg": round(cuttings_ecd, 3),
            "effective_mud_weight_ppg": round(effective_mw, 3),
            "concentration_fraction": round(conc_frac, 4),
            "density_difference_ppg": round(delta_rho, 3)
        }

    @staticmethod
    def calculate_full_cleanup(
        flow_rate: float,
        mud_weight: float,
        pv: float,
        yp: float,
        hole_id: float,
        pipe_od: float,
        inclination: float,
        rop: float = 60.0,
        cutting_size: float = 0.25,
        cutting_density: float = 21.0,
        rpm: float = 0.0,
        annular_length: float = 1000.0
    ) -> Dict[str, Any]:
        """
        Complete wellbore cleanup analysis combining all calculations.

        Returns:
            Dict with summary, alerts, and per-calculation details.
        """
        eng = WellboreCleanupEngine

        # Core calculations
        va = eng.calculate_annular_velocity(flow_rate, hole_id, pipe_od)

        # Auto-select slip velocity correlation: Larsen for inc >= 30°, Moore otherwise
        if inclination >= 30.0:
            vs_result = eng.calculate_slip_velocity_larsen(
                mud_weight, pv, yp, cutting_size, cutting_density,
                inclination, rpm, hole_id, pipe_od, va
            )
            vs = vs_result["slip_velocity_ftmin"]
            slip_correlation = "larsen"
        else:
            vs = eng.calculate_slip_velocity(mud_weight, pv, yp, cutting_size, cutting_density)
            vs_result = None
            slip_correlation = "moore"

        ctr = eng.calculate_ctr(va, vs)
        vt = eng.calculate_transport_velocity(va, vs)
        min_q = eng.calculate_minimum_flow_rate(hole_id, pipe_od, inclination)
        hci = eng.calculate_hole_cleaning_index(
            va, rpm, inclination, mud_weight, cutting_density, pv, yp
        )
        cc = eng.calculate_cuttings_concentration(rop, hole_id, pipe_od, flow_rate, max(vt, 0.1))

        # Cuttings-ECD bridge: calculate ECD contribution from cuttings
        ecd_contrib = eng.calculate_cuttings_ecd_contribution(cc, cutting_density, mud_weight)

        # Annular volume per foot
        ann_area_in2 = (hole_id ** 2 - pipe_od ** 2)
        annular_vol_per_ft = ann_area_in2 / 1029.4 if ann_area_in2 > 0 else 0.0

        # Sweep pill design
        sweep = eng.design_sweep_pill(annular_vol_per_ft, annular_length, mud_weight)

        # Evaluate cleaning quality
        if hci >= 1.0:
            cleaning_quality = "Good"
        elif hci >= 0.7:
            cleaning_quality = "Marginal"
        else:
            cleaning_quality = "Poor"

        # Alerts
        alerts = []
        if va < eng.MIN_AV_VERTICAL and inclination < 30:
            alerts.append(f"Annular velocity {va:.0f} ft/min below minimum {eng.MIN_AV_VERTICAL:.0f} ft/min for vertical section")
        if va < eng.MIN_AV_HIGH_ANGLE and inclination > 60:
            alerts.append(f"Annular velocity {va:.0f} ft/min below minimum {eng.MIN_AV_HIGH_ANGLE:.0f} ft/min for high-angle section")
        if ctr < 0.55:
            alerts.append(f"CTR {ctr:.2f} below recommended 0.55 — risk of cuttings accumulation")
        if vt <= 0:
            alerts.append("Negative transport velocity — cuttings falling back!")
        if flow_rate < min_q:
            alerts.append(f"Flow rate {flow_rate:.0f} gpm below minimum {min_q:.0f} gpm")
        if hci < 0.7:
            alerts.append(f"HCI {hci:.2f} indicates poor hole cleaning")
        if cc > 5.0:
            alerts.append(f"High cuttings concentration {cc:.1f}% — consider increasing flow rate or sweeps")
        if inclination > 30 and rpm == 0:
            alerts.append("No pipe rotation in deviated section — rotation significantly improves cleaning")
        # Bed erosion alert (Larsen)
        if vs_result is not None and vs_result["bed_erosion_velocity_ftmin"] > 0:
            if va < vs_result["bed_erosion_velocity_ftmin"]:
                alerts.append(
                    f"Annular velocity {va:.0f} ft/min below bed erosion velocity "
                    f"{vs_result['bed_erosion_velocity_ftmin']:.0f} ft/min — cuttings bed will not be eroded"
                )

        summary = {
            "annular_velocity_ftmin": round(va, 1),
            "slip_velocity_ftmin": round(vs, 1),
            "transport_velocity_ftmin": round(vt, 1),
            "cuttings_transport_ratio": round(ctr, 3),
            "minimum_flow_rate_gpm": round(min_q, 0),
            "hole_cleaning_index": hci,
            "cuttings_concentration_pct": cc,
            "cleaning_quality": cleaning_quality,
            "flow_rate_adequate": flow_rate >= min_q,
            "slip_velocity_correlation": slip_correlation,
            "cuttings_ecd_ppg": ecd_contrib["cuttings_ecd_ppg"],
            "effective_mud_weight_ppg": ecd_contrib["effective_mud_weight_ppg"],
            "alerts": alerts
        }

        return {
            "summary": summary,
            "ecd_contribution": ecd_contrib,
            "sweep_pill": sweep,
            "parameters": {
                "flow_rate_gpm": flow_rate,
                "mud_weight_ppg": mud_weight,
                "pv_cp": pv,
                "yp_lb100ft2": yp,
                "hole_id_in": hole_id,
                "pipe_od_in": pipe_od,
                "inclination_deg": inclination,
                "rop_fthr": rop,
                "cutting_size_in": cutting_size,
                "cutting_density_ppg": cutting_density,
                "rpm": rpm,
                "annular_length_ft": annular_length
            },
            "alerts": alerts
        }
