"""
Stuck Pipe Analysis Engine
Interactive decision tree, free point calculation, risk assessment.
References: IADC Stuck Pipe Prevention Guidelines, SPE publications
"""
import math
from typing import Dict, Any, List, Optional


class StuckPipeEngine:
    """
    Stuck pipe diagnostic engine with interactive decision tree,
    free point calculator, risk matrix, and recommended actions.
    """

    # ============================================================
    # Decision Tree for Stuck Pipe Mechanism Classification
    # ============================================================
    DECISION_TREE = {
        "start": {
            "question": "Can you circulate freely?",
            "yes": "q_rotate",
            "no": "q_no_circ"
        },
        "q_rotate": {
            "question": "Can you rotate the string?",
            "yes": "q_reciprocate",
            "no": "q_circ_no_rotate"
        },
        "q_reciprocate": {
            "question": "Can you reciprocate (move up and down)?",
            "yes": "q_limited_movement",
            "no": "q_circ_rotate_no_recip"
        },
        "q_limited_movement": {
            "question": "Is the movement progressively getting more restricted?",
            "yes": "result_hole_cleaning",
            "no": "result_key_seating"
        },
        "q_circ_no_rotate": {
            "question": "Were you stationary for an extended period before getting stuck?",
            "yes": "q_overbalance",
            "no": "q_formation_instability"
        },
        "q_overbalance": {
            "question": "Is the wellbore significantly overbalanced (MW >> pore pressure)?",
            "yes": "result_differential",
            "no": "q_reactive_formation"
        },
        "q_reactive_formation": {
            "question": "Are you drilling through shale or reactive clay formations?",
            "yes": "result_wellbore_instability",
            "no": "result_mechanical"
        },
        "q_formation_instability": {
            "question": "Have you observed cavings or increased torque trends?",
            "yes": "result_wellbore_instability",
            "no": "q_undergauge"
        },
        "q_undergauge": {
            "question": "Are you tripping through a section drilled with a worn bit?",
            "yes": "result_undergauge",
            "no": "result_mechanical"
        },
        "q_no_circ": {
            "question": "Can you rotate the string?",
            "yes": "q_no_circ_rotate",
            "no": "q_no_circ_no_rotate"
        },
        "q_no_circ_rotate": {
            "question": "Was there a sudden increase in pump pressure before losing circulation?",
            "yes": "result_packoff",
            "no": "q_flow_check"
        },
        "q_flow_check": {
            "question": "Do you observe flow on connections or flow check?",
            "yes": "result_formation_flow",
            "no": "result_hole_cleaning"
        },
        "q_no_circ_no_rotate": {
            "question": "Did the pipe get stuck while making a connection (stationary)?",
            "yes": "result_differential",
            "no": "q_cement_junk"
        },
        "q_circ_rotate_no_recip": {
            "question": "Is there a ledge or known dogleg in the wellbore?",
            "yes": "result_key_seating",
            "no": "result_mechanical"
        },
        "q_cement_junk": {
            "question": "Is there cement or junk in the hole (recent cementing or milling)?",
            "yes": "result_cement_junk",
            "no": "result_packoff"
        }
    }

    # Result nodes and their mechanisms
    MECHANISMS = {
        "result_differential": {
            "mechanism": "Differential Sticking",
            "description": "The drillstring is held against the wellbore wall by the differential pressure between the hydrostatic column and the formation pore pressure. Common in permeable formations with high overbalance.",
            "indicators": [
                "Pipe stuck while stationary (connections, surveys)",
                "Can circulate but cannot move pipe",
                "High overbalance pressure",
                "Permeable formation (sandstone, limestone)",
                "Thick filter cake buildup"
            ],
            "risk_factors": {
                "overbalance": 0.9,
                "permeability": 0.8,
                "stationary_time": 0.7,
                "contact_area": 0.6
            }
        },
        "result_mechanical": {
            "mechanism": "Mechanical Sticking",
            "description": "Physical obstruction or geometry preventing pipe movement. Includes ledges, dog legs, micro-doglegs, and BHA configuration issues.",
            "indicators": [
                "Stuck while tripping",
                "Can circulate",
                "High torque and drag trends",
                "Known doglegs or ledges",
                "Stiff BHA assembly"
            ],
            "risk_factors": {
                "dogleg_severity": 0.8,
                "bha_stiffness": 0.7,
                "hole_angle": 0.6,
                "trip_speed": 0.5
            }
        },
        "result_hole_cleaning": {
            "mechanism": "Hole Cleaning / Pack-Off",
            "description": "Accumulated cuttings or cavings pack around the drillstring, restricting or preventing movement. Progressive restriction is the hallmark.",
            "indicators": [
                "Progressive increase in drag/torque",
                "Increasing SPP while drilling",
                "Cuttings accumulation at shakers",
                "Tight spots while tripping",
                "Inadequate flow rate or mud properties"
            ],
            "risk_factors": {
                "flow_rate_inadequate": 0.9,
                "inclination_high": 0.8,
                "rop_too_high": 0.7,
                "mud_properties": 0.6
            }
        },
        "result_wellbore_instability": {
            "mechanism": "Wellbore Instability",
            "description": "The wellbore is collapsing due to in-situ stresses, reactive formations, or inadequate mud weight. Shale swelling and stress-related breakouts are common causes.",
            "indicators": [
                "Cavings at shakers (splintery = stress, tabular = pressure)",
                "Increasing torque trends",
                "Tight hole conditions",
                "Reactive shale formations",
                "MW potentially too low for stress state"
            ],
            "risk_factors": {
                "formation_reactivity": 0.9,
                "mud_weight_margin": 0.8,
                "time_exposed": 0.7,
                "inhibition": 0.6
            }
        },
        "result_key_seating": {
            "mechanism": "Key Seating",
            "description": "The drillpipe has worn a groove (key seat) in the formation at a dogleg. The BHA/tool joints are too large to pass through this groove while tripping.",
            "indicators": [
                "Stuck while tripping out (pulling up)",
                "Can circulate and rotate",
                "Known dogleg in the well",
                "Typically occurs at build section",
                "BHA will not pass through dogleg"
            ],
            "risk_factors": {
                "dogleg_severity": 0.9,
                "rotating_hours": 0.7,
                "formation_softness": 0.6,
                "bha_od_change": 0.8
            }
        },
        "result_undergauge": {
            "mechanism": "Undergauge Hole",
            "description": "The hole has become undergauge (smaller than bit size) due to formation creep, swelling clays, or drilling with a worn bit. Tripping through these sections causes sticking.",
            "indicators": [
                "Stuck while tripping",
                "Tight spots at specific depths",
                "Worn bit on previous run",
                "Salt or reactive formation",
                "Increasing drag at same depth"
            ],
            "risk_factors": {
                "formation_type": 0.8,
                "bit_wear": 0.7,
                "time_since_drilled": 0.6,
                "reaming_history": 0.5
            }
        },
        "result_formation_flow": {
            "mechanism": "Formation Flow / Kick",
            "description": "Formation fluids are entering the wellbore, potentially packing around the string or causing wellbore instability. This is a well control situation.",
            "indicators": [
                "Flow observed on connections",
                "Pit gain",
                "Decreasing mud weight returns",
                "Gas cut mud",
                "Pressure increase in annulus"
            ],
            "risk_factors": {
                "underbalance": 0.9,
                "pore_pressure_uncertainty": 0.8,
                "permeability": 0.7,
                "gas_proximity": 0.8
            }
        },
        "result_packoff": {
            "mechanism": "Pack-Off / Bridge",
            "description": "A sudden bridging of the annulus by cuttings, cavings, or formation material. Distinguished from gradual hole cleaning by its sudden onset and loss of circulation.",
            "indicators": [
                "Sudden pump pressure increase",
                "Lost circulation simultaneously",
                "Cannot circulate or reciprocate",
                "Previous signs of poor hole cleaning",
                "Occurred while tripping or reaming"
            ],
            "risk_factors": {
                "hole_cleaning_index": 0.9,
                "trip_speed": 0.7,
                "formation_stability": 0.6,
                "annular_velocity": 0.8
            }
        },
        "result_cement_junk": {
            "mechanism": "Cement / Junk in Hole",
            "description": "Cement from a recent cementing job or metallic junk (from milling, broken equipment) has settled around the drillstring.",
            "indicators": [
                "Recent cementing operation",
                "Milling or fishing operation",
                "Known junk in hole",
                "Cannot circulate or rotate",
                "Sudden onset"
            ],
            "risk_factors": {
                "recent_cement_job": 0.9,
                "junk_in_hole": 0.9,
                "wait_time": 0.7,
                "displacement_quality": 0.6
            }
        }
    }

    @staticmethod
    def get_next_question(
        current_node: str = "start",
        answer: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Navigate the decision tree. Returns next question or final result.

        Parameters:
        - current_node: current position in tree (default: "start")
        - answer: "yes" or "no" for the current question
        """
        if answer and current_node in StuckPipeEngine.DECISION_TREE:
            node = StuckPipeEngine.DECISION_TREE[current_node]
            next_node = node.get(answer.lower(), "start")

            # Check if we've reached a result
            if next_node.startswith("result_"):
                mechanism_data = StuckPipeEngine.MECHANISMS.get(next_node, {})
                return {
                    "type": "result",
                    "node_id": next_node,
                    "mechanism": mechanism_data.get("mechanism", "Unknown"),
                    "description": mechanism_data.get("description", ""),
                    "indicators": mechanism_data.get("indicators", [])
                }
            else:
                # Return next question
                next_q = StuckPipeEngine.DECISION_TREE.get(next_node, {})
                return {
                    "type": "question",
                    "node_id": next_node,
                    "question": next_q.get("question", "Unknown question"),
                    "options": ["yes", "no"]
                }

        # Return first question
        if current_node in StuckPipeEngine.DECISION_TREE:
            node = StuckPipeEngine.DECISION_TREE[current_node]
            return {
                "type": "question",
                "node_id": current_node,
                "question": node["question"],
                "options": ["yes", "no"]
            }

        # Unknown node
        return {"type": "error", "message": f"Unknown node: {current_node}"}

    @staticmethod
    def classify_mechanism(answers: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Walk the entire decision tree with a list of pre-recorded answers.

        Parameters:
        - answers: list of {"node_id": "...", "answer": "yes"/"no"}
        Returns: final mechanism classification
        """
        current = "start"
        path = []

        for ans in answers:
            node = StuckPipeEngine.DECISION_TREE.get(current)
            if not node:
                break

            path.append({
                "node_id": current,
                "question": node["question"],
                "answer": ans["answer"]
            })

            next_node = node.get(ans["answer"].lower(), "start")
            current = next_node

            if current.startswith("result_"):
                mechanism_data = StuckPipeEngine.MECHANISMS.get(current, {})
                return {
                    "mechanism": mechanism_data.get("mechanism", "Unknown"),
                    "result_node": current,
                    "description": mechanism_data.get("description", ""),
                    "indicators": mechanism_data.get("indicators", []),
                    "decision_path": path
                }

        return {
            "mechanism": "Inconclusive",
            "result_node": current,
            "description": "Could not determine mechanism from provided answers.",
            "decision_path": path
        }

    @staticmethod
    def calculate_free_point(
        pipe_od: float,
        pipe_id: float,
        pipe_grade: str,
        stretch_inches: float,
        pull_force_lbs: float
    ) -> Dict[str, Any]:
        """
        Calculate free point depth using the pipe stretch method.

        FP = (E * A * stretch) / (F * 12)

        Where:
        - E = Young's modulus (30 x 10^6 psi for steel)
        - A = cross-sectional area of pipe wall (in²)
        - stretch = measured stretch (inches)
        - F = applied pull force (lbs)
        - 12 = conversion factor (inches to feet)

        Parameters:
        - pipe_od: outer diameter (inches)
        - pipe_id: inner diameter (inches)
        - pipe_grade: steel grade (e.g., "E75", "S135", "G105")
        - stretch_inches: measured pipe stretch at surface (inches)
        - pull_force_lbs: applied overpull force (lbs)
        """
        if pull_force_lbs <= 0 or stretch_inches <= 0:
            return {"error": "Pull force and stretch must be positive"}

        # Cross-sectional area
        area = math.pi / 4.0 * (pipe_od**2 - pipe_id**2)

        # Young's modulus for steel
        e = 30e6  # psi

        # Free point depth calculation
        fp_depth = (e * area * stretch_inches) / (pull_force_lbs * 12.0)

        # Yield strength check
        grade_yield = {
            "E75": 75000, "X95": 95000, "G105": 105000,
            "S135": 135000, "V150": 150000, "UD165": 165000
        }
        yield_strength = grade_yield.get(pipe_grade.upper(), 80000)
        max_pull = yield_strength * area * 0.80  # 80% of yield
        pull_pct_yield = (pull_force_lbs / (yield_strength * area)) * 100

        return {
            "free_point_depth_ft": round(fp_depth, 0),
            "pipe_area_sqin": round(area, 3),
            "pull_force_lbs": pull_force_lbs,
            "stretch_inches": stretch_inches,
            "pipe_grade": pipe_grade.upper(),
            "yield_strength_psi": yield_strength,
            "max_safe_pull_lbs": round(max_pull, 0),
            "pull_pct_of_yield": round(pull_pct_yield, 1),
            "pull_safe": pull_force_lbs < max_pull
        }

    @staticmethod
    def assess_risk_matrix(
        mechanism: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Assess stuck pipe risk using a probability x severity matrix.

        Parameters:
        - mechanism: identified mechanism name
        - params: operational parameters for risk factor evaluation
        """
        # Find mechanism data
        mech_data = None
        for key, data in StuckPipeEngine.MECHANISMS.items():
            if data["mechanism"].lower() == mechanism.lower():
                mech_data = data
                break

        if not mech_data:
            return {"error": f"Unknown mechanism: {mechanism}"}

        # Evaluate contributing factors
        factors = []
        probability_score = 0.0
        factor_count = 0

        # Generic factors based on parameters
        if params.get("mud_weight") and params.get("pore_pressure"):
            overbalance = params["mud_weight"] - params["pore_pressure"]
            if overbalance > 2.0:
                factors.append({"factor": "High Overbalance", "score": 0.8, "detail": f"{overbalance:.1f} ppg"})
                probability_score += 0.8
                factor_count += 1
            elif overbalance > 1.0:
                factors.append({"factor": "Moderate Overbalance", "score": 0.5, "detail": f"{overbalance:.1f} ppg"})
                probability_score += 0.5
                factor_count += 1

        if params.get("inclination", 0) > 60:
            factors.append({"factor": "High Inclination", "score": 0.7, "detail": f"{params['inclination']}°"})
            probability_score += 0.7
            factor_count += 1

        if params.get("stationary_hours", 0) > 2:
            factors.append({"factor": "Extended Stationary Time", "score": 0.8, "detail": f"{params['stationary_hours']}h"})
            probability_score += 0.8
            factor_count += 1

        if params.get("torque") and params.get("torque") > 25000:
            factors.append({"factor": "High Torque", "score": 0.6, "detail": f"{params['torque']} ft-lb"})
            probability_score += 0.6
            factor_count += 1

        if params.get("overpull", 0) > 30:
            factors.append({"factor": "Significant Overpull", "score": 0.7, "detail": f"{params['overpull']} klb"})
            probability_score += 0.7
            factor_count += 1

        # Calculate probability (0-5 scale)
        if factor_count > 0:
            avg_score = probability_score / factor_count
        else:
            avg_score = 0.3  # base risk

        prob = min(5, max(1, round(avg_score * 5)))

        # Severity based on mechanism
        severity_map = {
            "Differential Sticking": 4,
            "Mechanical Sticking": 3,
            "Hole Cleaning / Pack-Off": 3,
            "Wellbore Instability": 4,
            "Key Seating": 2,
            "Undergauge Hole": 2,
            "Formation Flow / Kick": 5,
            "Pack-Off / Bridge": 3,
            "Cement / Junk in Hole": 4
        }
        severity = severity_map.get(mechanism, 3)

        # Risk level
        risk_score = prob * severity
        if risk_score >= 15:
            risk_level = "CRITICAL"
        elif risk_score >= 10:
            risk_level = "HIGH"
        elif risk_score >= 5:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        return {
            "mechanism": mechanism,
            "probability": prob,
            "severity": severity,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "contributing_factors": factors,
            "matrix_position": {"x": prob, "y": severity}
        }

    @staticmethod
    def get_recommended_actions(mechanism: str) -> Dict[str, Any]:
        """
        Get recommended actions for a given stuck pipe mechanism.
        Actions are categorized: immediate, short_term, contingency.
        """
        actions = {
            "Differential Sticking": {
                "immediate": [
                    "Apply maximum allowable torque and work pipe",
                    "Attempt to circulate — spot LCM/oil-based pill at stuck point",
                    "Reduce hydrostatic pressure if safe (lighter fluid pill)",
                    "Apply steady overpull up to 80% of yield"
                ],
                "short_term": [
                    "Spot oil/diesel soak at stuck zone (minimum 4 hours)",
                    "Consider reducing mud weight if formation pressure allows",
                    "Run free point indicator to determine stuck depth",
                    "Consider back-off and sidetrack plan"
                ],
                "contingency": [
                    "Back-off above stuck point",
                    "Wash over stuck fish with washover pipe",
                    "Sidetrack around the fish",
                    "Consider abandoning fish and setting cement plug"
                ]
            },
            "Mechanical Sticking": {
                "immediate": [
                    "Work pipe with combined rotation and reciprocation",
                    "Apply gradual overpull — do not exceed 80% yield",
                    "Circulate to clean hole while working pipe",
                    "Attempt to jar (upward for trip-out stuck, down for trip-in)"
                ],
                "short_term": [
                    "Ream through tight spots with reduced WOB",
                    "Consider wiper trip to clean ledges",
                    "Review BHA configuration for next run",
                    "Consider hole reaming or hole opening"
                ],
                "contingency": [
                    "Run free point indicator",
                    "Back-off above stuck point",
                    "Fishing operation with overshot/bumper sub",
                    "Sidetrack if fishing is unsuccessful"
                ]
            },
            "Hole Cleaning / Pack-Off": {
                "immediate": [
                    "Increase circulation rate to maximum available",
                    "Rotate pipe and slowly work upward",
                    "Do NOT force pipe downward",
                    "Monitor SPP for pack-off signs"
                ],
                "short_term": [
                    "Increase mud viscosity (sweeps or base mud)",
                    "Increase flow rate for better hole cleaning",
                    "Reduce ROP to match hole cleaning capacity",
                    "Perform wiper trips more frequently"
                ],
                "contingency": [
                    "Circulate clean with high-vis sweeps before any trip",
                    "Consider CCI/hole cleaning index optimization",
                    "Back-off and sidetrack if stuck beyond recovery",
                    "Review mud program and hydraulics"
                ]
            },
            "Wellbore Instability": {
                "immediate": [
                    "Increase mud weight if collapse is suspected",
                    "Maintain circulation and clean cavings",
                    "Minimize time in open hole",
                    "Work pipe carefully — avoid surge/swab"
                ],
                "short_term": [
                    "Optimize mud chemistry (inhibition, salinity)",
                    "Consider casing point revision (set casing earlier)",
                    "Run caliper log if possible",
                    "Monitor cavings type and volume at shakers"
                ],
                "contingency": [
                    "Run casing through unstable zone",
                    "Sidetrack with adjusted mud program",
                    "Consider underreaming or hole opening",
                    "Set mechanical liner or expandable liner"
                ]
            },
            "Key Seating": {
                "immediate": [
                    "DO NOT pull hard — you will worsen the key seat",
                    "Work pipe back to bottom if possible",
                    "Circulate and ream through the key seat slowly",
                    "Consider pumping a lubricant pill"
                ],
                "short_term": [
                    "Use key seat wiper on next trip",
                    "Ream doglegs on every trip",
                    "Review directional plan to minimize doglegs",
                    "Consider string stabilizer placement"
                ],
                "contingency": [
                    "Back-off above key seat",
                    "Fish with overshot and key seat wiper",
                    "Sidetrack if key seat is too severe",
                    "Consider enlarging the hole through dogleg"
                ]
            },
            "Undergauge Hole": {
                "immediate": [
                    "Ream slowly through undergauge zone",
                    "Apply light WOB with rotation",
                    "Circulate to clean reamed cuttings",
                    "Do not force pipe through — risk of pack-off"
                ],
                "short_term": [
                    "Plan reaming trips with near-gauge bit",
                    "Consider hole opener or underreamer",
                    "Monitor bit gauge on each trip out",
                    "Adjust mud chemistry if swelling clays"
                ],
                "contingency": [
                    "Back-off and run bit/reamer to open hole",
                    "Consider casing through undergauge zone",
                    "Sidetrack if section cannot be reamed",
                    "Review bit selection and operating parameters"
                ]
            },
            "Formation Flow / Kick": {
                "immediate": [
                    "SHUT IN THE WELL IMMEDIATELY",
                    "Record SIDPP and SICP",
                    "Record pit gain volume",
                    "Notify well control supervisor"
                ],
                "short_term": [
                    "Calculate kill mud weight",
                    "Prepare kill sheet",
                    "Execute appropriate kill method (Driller's or W&W)",
                    "Monitor pressures throughout kill operation"
                ],
                "contingency": [
                    "If conventional kill fails, consider bullheading",
                    "Consider volumetric method if cannot circulate",
                    "Prepare for possible well control incident escalation",
                    "Emergency disconnect / diverter procedures"
                ]
            },
            "Pack-Off / Bridge": {
                "immediate": [
                    "Do not increase pump pressure — risk of fracturing",
                    "Attempt to gently work pipe with rotation",
                    "Bleed off pressure slowly",
                    "If possible, back-ream slowly upward"
                ],
                "short_term": [
                    "Circulate cautiously at low rate if regained",
                    "Increase hole cleaning parameters",
                    "Perform thorough clean-up circulation",
                    "Check shakers for excessive cuttings/cavings"
                ],
                "contingency": [
                    "Back-off above bridge",
                    "Run drill-through tool",
                    "Consider coiled tubing to clear bridge",
                    "Sidetrack if bridge is impenetrable"
                ]
            },
            "Cement / Junk in Hole": {
                "immediate": [
                    "Attempt to circulate — do not apply excessive torque",
                    "If cement is setting, act quickly (limited time)",
                    "Apply gentle rotation if possible",
                    "Check returns for cement/junk indications"
                ],
                "short_term": [
                    "Acid or solvent spotting if cement",
                    "Milling operation if metal junk",
                    "Free point determination",
                    "Plan fishing/milling BHA"
                ],
                "contingency": [
                    "Back-off above stuck point",
                    "Mill out cement or junk",
                    "Sidetrack around fish",
                    "Abandon in place and plug back"
                ]
            }
        }

        mech_actions = actions.get(mechanism)
        if not mech_actions:
            return {
                "mechanism": mechanism,
                "error": f"No action plan for mechanism: {mechanism}",
                "immediate": ["Assess situation and gather more data"],
                "short_term": ["Consult with engineering team"],
                "contingency": ["Prepare back-off and sidetrack plan"]
            }

        return {
            "mechanism": mechanism,
            "immediate": mech_actions["immediate"],
            "short_term": mech_actions["short_term"],
            "contingency": mech_actions["contingency"],
            "total_actions": (
                len(mech_actions["immediate"])
                + len(mech_actions["short_term"])
                + len(mech_actions["contingency"])
            )
        }
