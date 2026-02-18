from typing import Dict, Any
import math

class CalculationEngine:
    """
    Module 3: Physics Calculation Engine
    Performs deterministic engineering calculations based on captured parameters.
    """
    
    def calculate_all(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Run all available calculations"""
        results = {
            "ecd": self.calculate_ecd(params),
            "cci": self.calculate_cci(params),
            "mechanical_risk": self.assess_mechanical_risk(params)
        }
        return results

    def calculate_ecd(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate Equivalent Circulating Density (ECD).
        ECD = ESD + (Annular Pressure Loss / 0.052 / TVD)
        
        Simplified Model (Power Law) for Annular Pressure Loss if not provided.
        """
        mw = params.get("mud_weight")
        tvd = params.get("depth_tvd")
        
        if not mw or not tvd:
            return {"value": None, "status": "Missing Data"}
            
        # 1. basic estimate of Annular Pressure Loss (APL)
        # If we don't have detailed geometry, we assume a standard loss factor
        # Rule of thumb: APL is often 200-500 psi depending on depth/flow
        # Better: Use flow rate and viscosity if available
        
        flow_rate = params.get("flow_rate", 0) # gpm
        yp = params.get("viscosity_yp", 0)
        
        apl_psi = 0
        if flow_rate > 0:
            # Very rough approximation for demo: P = L * (Visc_term) ... 
            # Let's use a "rule of thumb" friction factor per 1000 ft
            friction_per_1000 = 25 # psi/1000ft (generic)
            if yp > 20: friction_per_1000 += 10
            if flow_rate > 800: friction_per_1000 += 20
            
            apl_psi = (tvd / 1000) * friction_per_1000
        
        if params.get("spp"): # If Standpipe Pressure is known, Annular is usually 10-20% of SPP
            apl_psi = params.get("spp") * 0.15
            
        # ECD Calculation
        # ECD = MW + P_loss / (0.052 * TVD)
        try:
            ecd_val = mw + (apl_psi / (0.052 * tvd))
            
            status = "Normal"
            if ecd_val > mw + 1.5: status = "High (Risk of Fracturing)"
            if ecd_val < mw + 0.2: status = "Low (Poor Hole Cleaning?)"
            
            return {
                "value": round(ecd_val, 2),
                "unit": "ppg",
                "apl_estimated": round(apl_psi, 1),
                "status": status
            }
        except ZeroDivisionError:
            return {"value": None, "status": "Error (Zero Depth)"}

    def calculate_cci(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate Cuttings Carrying Index (CCI).
        CCI = (PV * AV * MW) / 400,000 (Field Rule of Thumb)
        Target > 1.0 for vertical, > 1.5 for deviated
        """
        # We need Annular Velocity (AV)
        # AV = 24.5 * Q / (Dh^2 - Dp^2)
        # Let's assume standard geometry if not provided (8.5" hole, 5" pipe)
        
        flow = params.get("flow_rate")
        mw = params.get("mud_weight")
        pv = params.get("viscosity_pv", 15) # default if missing
        
        if not flow or not mw:
             return {"value": None, "status": "Missing Data"}
             
        # Estimate AV
        dh = 8.5 # inches (hole)
        dp = 5.0 # inches (pipe)
        av_ft_min = (24.5 * flow) / (dh**2 - dp**2)
        
        # CCI Formula (Common Field Approximation)
        # CCI = (AV * MW * K) ... logic varies.
        # Let's use CCI = (Transport Ratio)
        # Simple Robinson Rule: CCI = (MW * AV * PV) / 400000 
        # *Only valid if consistent units
        
        cci_val = (mw * av_ft_min * pv) / 400000
        
        # Adjust for Angle?
        inclination = params.get("inclination", 0)
        target = 0.5 if inclination < 30 else 1.0
        
        status = "Good"
        if cci_val < target: status = "Poor Hole Cleaning"
        
        return {
            "value": round(cci_val, 2),
            "av_estimated": round(av_ft_min, 1),
            "target": target,
            "status": status
        }

    def assess_mechanical_risk(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess Torque & Drag / Mechanical risk flags
        """
        torque = params.get("torque")
        overpull = params.get("overpull")
        depth = params.get("depth_md", 0)
        
        alerts = []
        if torque and torque > 25000: # Generic threshold
            alerts.append("High Torque")
            
        if overpull and overpull > 50: # klb
            alerts.append("Significant Overpull")
            
        if params.get("dogleg_severity", 0) > 3.0:
            alerts.append("High Dogleg Severity")
            
        risk_level = "Low"
        if len(alerts) == 1: risk_level = "Medium"
        if len(alerts) > 1: risk_level = "High"
        
        return {
            "risk_level": risk_level,
            "alerts": alerts
        }
