"""
Hydraulics Engine — ECD, BHA Pressure Breakdown, and Pressure Waterfall.

References:
- API RP 13D: Rheology and Hydraulics of Oil-Well Drilling Fluids
"""
from typing import Dict, Any, List, Optional

from .rheology import (
    pressure_loss_bingham,
    pressure_loss_power_law,
    pressure_loss_herschel_bulkley,
)


def calculate_ecd_dynamic(
    mud_weight: float,
    tvd: float,
    annular_pressure_loss: float,
    cuttings_loading: float = 0.0,
    temperature_effect: float = 0.0
) -> Dict[str, Any]:
    """
    Calculate dynamic ECD including cuttings and temperature effects.
    ECD = MW + cuttings + temp_effect + APL/(0.052*TVD)
    """
    if tvd <= 0:
        return {"ecd": mud_weight, "status": "Error: Zero TVD"}

    ecd_apl = annular_pressure_loss / (0.052 * tvd)
    ecd = mud_weight + cuttings_loading + temperature_effect + ecd_apl

    status = "Normal"
    margin = ecd - mud_weight
    if margin > 1.5:
        status = "HIGH — Risk of losses/fracturing"
    elif margin > 1.0:
        status = "Elevated — Monitor closely"
    elif margin < 0.2:
        status = "LOW — Poor hole cleaning likely"

    return {
        "ecd_ppg": round(ecd, 2),
        "ecd_from_apl": round(ecd_apl, 3),
        "cuttings_effect_ppg": round(cuttings_loading, 3),
        "temperature_effect_ppg": round(temperature_effect, 3),
        "total_margin_ppg": round(margin, 3),
        "status": status
    }


def calculate_bha_pressure_breakdown(
    bha_tools: List[Dict[str, Any]],
    flow_rate: float,
    mud_weight: float,
    pv: float,
    yp: float,
    rheology_model: str = "bingham_plastic",
    n: float = 0.5,
    k: float = 300.0,
    tau_0: float = 0.0,
    k_hb: float = 0.0,
    n_hb: float = 0.5
) -> Dict[str, Any]:
    """
    Calculate pressure loss breakdown for individual BHA tools.

    Each tool can have a loss_coefficient to model internal restrictions
    (e.g., motors, MWD/LWD tools with complex internal geometries).

    Args:
        bha_tools: list of dicts, each with:
            - tool_name: descriptive name (e.g., "PDM Motor 6-3/4")
            - tool_type: 'motor', 'mwd', 'lwd', 'stabilizer', 'collar',
                         'jar', 'reamer', 'crossover'
            - od: outer diameter (in)
            - id_inner: inner diameter (in)
            - length: tool length (ft)
            - loss_coefficient: multiplier for internal restrictions (default 1.0)
        flow_rate: circulation rate (gpm)
        mud_weight: mud weight (ppg)
        pv, yp: Bingham parameters
        rheology_model: 'bingham_plastic', 'power_law', or 'herschel_bulkley'
        n, k: Power Law parameters
        tau_0, k_hb, n_hb: Herschel-Bulkley parameters

    Returns:
        Dict with tools_breakdown[], total_bha_loss_psi, critical_tool
    """
    if not bha_tools or flow_rate <= 0:
        return {
            "tools_breakdown": [],
            "total_bha_loss_psi": 0.0,
            "critical_tool": None
        }

    tools_breakdown = []
    total_loss = 0.0
    max_dp_per_ft = 0.0
    critical_tool = None

    for tool in bha_tools:
        tool_name = tool.get("tool_name", "Unknown")
        tool_type = tool.get("tool_type", "collar")
        od = tool.get("od", 6.75)
        id_inner = tool.get("id_inner", 2.8125)
        length = tool.get("length", 30.0)
        loss_coeff = tool.get("loss_coefficient", 1.0)

        if length <= 0 or od <= 0 or id_inner <= 0:
            tools_breakdown.append({
                "tool_name": tool_name,
                "tool_type": tool_type,
                "length": length,
                "pressure_loss_psi": 0.0,
                "velocity_ftmin": 0.0,
                "regime": "none",
                "loss_coefficient": loss_coeff,
                "dp_per_ft": 0.0
            })
            continue

        # Calculate base pressure loss through the tool bore
        if rheology_model == "herschel_bulkley":
            result = pressure_loss_herschel_bulkley(
                flow_rate=flow_rate, mud_weight=mud_weight,
                tau_0=tau_0, k_hb=k_hb, n_hb=n_hb,
                length=length, od=od, id_inner=id_inner,
                is_annular=False
            )
        elif rheology_model == "power_law":
            result = pressure_loss_power_law(
                flow_rate=flow_rate, mud_weight=mud_weight,
                n=n, k=k,
                length=length, od=od, id_inner=id_inner,
                is_annular=False
            )
        else:
            result = pressure_loss_bingham(
                flow_rate=flow_rate, mud_weight=mud_weight,
                pv=pv, yp=yp,
                length=length, od=od, id_inner=id_inner,
                is_annular=False
            )

        # Apply loss coefficient (for motors, MWD, etc.)
        base_loss = result.get("pressure_loss_psi", 0.0)
        actual_loss = base_loss * loss_coeff

        # Pressure drop per foot (identifies bottleneck)
        dp_per_ft = actual_loss / length if length > 0 else 0.0

        tools_breakdown.append({
            "tool_name": tool_name,
            "tool_type": tool_type,
            "length": length,
            "pressure_loss_psi": round(actual_loss, 1),
            "velocity_ftmin": result.get("velocity_ft_min", 0.0),
            "regime": result.get("flow_regime", "unknown"),
            "loss_coefficient": loss_coeff,
            "dp_per_ft": round(dp_per_ft, 2)
        })

        total_loss += actual_loss

        if dp_per_ft > max_dp_per_ft:
            max_dp_per_ft = dp_per_ft
            critical_tool = tool_name

    return {
        "tools_breakdown": tools_breakdown,
        "total_bha_loss_psi": round(total_loss, 1),
        "critical_tool": critical_tool
    }


def generate_pressure_waterfall(
    circuit_result: Dict[str, Any],
    bha_breakdown: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generate a detailed pressure waterfall from circuit results.

    Breaks down total SPP into sequential steps from pump to annular return.
    If bha_breakdown is provided, expands BHA into individual tools.

    Args:
        circuit_result: output from calculate_full_circuit()
        bha_breakdown: optional output from calculate_bha_pressure_breakdown()

    Returns:
        Dict with waterfall_steps[], total_spp_psi
    """
    summary = circuit_result.get("summary", {})
    section_results = circuit_result.get("section_results", [])
    bit_hydraulics = circuit_result.get("bit_hydraulics", {})

    waterfall_steps = []
    cumulative = 0.0

    # 1. Surface Equipment
    surface_loss = summary.get("surface_equipment_psi", 0.0)
    cumulative += surface_loss
    waterfall_steps.append({
        "label": "Surface Equipment",
        "pressure_psi": round(surface_loss, 0),
        "cumulative_psi": round(cumulative, 0),
        "pct_of_total": 0.0  # calculated at the end
    })

    # 2. Pipe sections (non-annular, non-BHA)
    pipe_sections = [s for s in section_results if "annulus" not in s.get("section_type", "")]
    annular_sections = [s for s in section_results if "annulus" in s.get("section_type", "")]

    # If BHA breakdown is provided, separate collar/BHA from drillpipe/HWDP
    if bha_breakdown and bha_breakdown.get("tools_breakdown"):
        # Add BHA tools as individual steps
        for sec in pipe_sections:
            sec_type = sec.get("section_type", "")
            if sec_type in ("drill_pipe", "hwdp"):
                loss = sec.get("pressure_loss_psi", 0.0)
                cumulative += loss
                label = "Drill Pipe" if sec_type == "drill_pipe" else "HWDP"
                waterfall_steps.append({
                    "label": label,
                    "pressure_psi": round(loss, 0),
                    "cumulative_psi": round(cumulative, 0),
                    "pct_of_total": 0.0
                })

        # BHA tools breakdown
        for tool in bha_breakdown["tools_breakdown"]:
            loss = tool.get("pressure_loss_psi", 0.0)
            cumulative += loss
            waterfall_steps.append({
                "label": f"BHA: {tool['tool_name']}",
                "pressure_psi": round(loss, 0),
                "cumulative_psi": round(cumulative, 0),
                "pct_of_total": 0.0
            })
    else:
        # No BHA breakdown — add pipe sections grouped
        for sec in pipe_sections:
            sec_type = sec.get("section_type", "")
            loss = sec.get("pressure_loss_psi", 0.0)
            cumulative += loss
            label_map = {
                "drill_pipe": "Drill Pipe",
                "hwdp": "HWDP",
                "collar": "Drill Collars/BHA"
            }
            label = label_map.get(sec_type, sec_type.replace("_", " ").title())
            waterfall_steps.append({
                "label": label,
                "pressure_psi": round(loss, 0),
                "cumulative_psi": round(cumulative, 0),
                "pct_of_total": 0.0
            })

    # 3. Bit
    bit_loss = bit_hydraulics.get("pressure_drop_psi", summary.get("bit_loss_psi", 0.0))
    cumulative += bit_loss
    waterfall_steps.append({
        "label": "Bit Nozzles",
        "pressure_psi": round(bit_loss, 0),
        "cumulative_psi": round(cumulative, 0),
        "pct_of_total": 0.0
    })

    # 4. Annular sections
    for sec in annular_sections:
        sec_type = sec.get("section_type", "")
        loss = sec.get("pressure_loss_psi", 0.0)
        cumulative += loss
        label_map = {
            "annulus_dc": "Annular (DC)",
            "annulus_hwdp": "Annular (HWDP)",
            "annulus_dp": "Annular (DP)"
        }
        label = label_map.get(sec_type, sec_type.replace("_", " ").title())
        waterfall_steps.append({
            "label": label,
            "pressure_psi": round(loss, 0),
            "cumulative_psi": round(cumulative, 0),
            "pct_of_total": 0.0
        })

    # Calculate percentages
    total_spp = cumulative if cumulative > 0 else 1.0
    for step in waterfall_steps:
        step["pct_of_total"] = round(step["pressure_psi"] / total_spp * 100, 1)

    return {
        "waterfall_steps": waterfall_steps,
        "total_spp_psi": round(cumulative, 0)
    }
