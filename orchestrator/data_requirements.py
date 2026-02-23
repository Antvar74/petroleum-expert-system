# orchestrator/data_requirements.py
"""
Data Requirements Registry — defines what data each module needs per phase/event.

Usage:
    from orchestrator.data_requirements import get_requirements
    reqs = get_requirements("well-control", "drilling", "kick")
    # Returns merged required + optional fields with recommended files
"""
from typing import Dict, Any, List, Optional


# ── Registry ──────────────────────────────────────────────────────────────────

DATA_REQUIREMENTS: Dict[str, Any] = {

    # ── Torque & Drag ─────────────────────────────────────────────────────────
    "torque-drag": {
        "name": "Torque & Drag",
        "min_readiness_pct": 60,
        "phases": {
            "drilling": {
                "base": {
                    "required": [
                        {"key": "survey_stations", "label": "Survey Stations (MD, Inc, Azi)", "source": "LAS/CSV/manual", "unit": "ft/deg", "min_points": 3},
                        {"key": "drillstring", "label": "Drillstring (OD, ID, weight, length)", "source": "manual", "unit": "in/lb/ft"},
                        {"key": "mud_weight", "label": "Mud Weight", "source": "LAS/manual", "unit": "ppg"},
                    ],
                    "optional": [
                        {"key": "friction_cased", "label": "Friction Factor (Cased)", "default": "0.25", "impact": "Uses default if not provided"},
                        {"key": "friction_open", "label": "Friction Factor (Open Hole)", "default": "0.35", "impact": "Uses default if not provided"},
                        {"key": "wob", "label": "Weight on Bit", "default": "0 klb", "impact": "Assumes zero WOB"},
                        {"key": "rpm", "label": "Rotary Speed", "default": "0 rpm", "impact": "No torque if zero"},
                    ],
                    "recommended_files": ["Survey LAS/CSV", "Drilling parameters LAS"],
                },
                "events": {
                    "stuck_pipe": {
                        "additional_required": [
                            {"key": "overpull", "label": "Max Allowable Overpull", "source": "manual", "unit": "klb"},
                        ],
                        "additional_optional": [],
                    },
                    "high_torque": {
                        "additional_required": [
                            {"key": "max_torque", "label": "Max Surface Torque", "source": "manual", "unit": "ft-lb"},
                        ],
                        "additional_optional": [],
                    },
                },
            },
            "completion": {
                "base": {
                    "required": [
                        {"key": "survey_stations", "label": "Survey Stations (MD, Inc, Azi)", "source": "LAS/CSV/manual", "unit": "ft/deg", "min_points": 3},
                        {"key": "completion_string", "label": "Completion String (OD, ID, weight)", "source": "manual", "unit": "in/lb/ft"},
                        {"key": "fluid_weight", "label": "Completion Fluid Weight", "source": "manual", "unit": "ppg"},
                    ],
                    "optional": [
                        {"key": "friction_cased", "label": "Friction Factor", "default": "0.20", "impact": "Uses default for cased hole"},
                    ],
                    "recommended_files": ["Survey LAS/CSV"],
                },
                "events": {},
            },
            "workover": {
                "base": {
                    "required": [
                        {"key": "survey_stations", "label": "Survey Stations (MD, Inc, Azi)", "source": "LAS/CSV/manual", "unit": "ft/deg", "min_points": 3},
                        {"key": "workstring", "label": "Work String (OD, ID, weight)", "source": "manual", "unit": "in/lb/ft"},
                        {"key": "fluid_weight", "label": "Fluid Weight", "source": "manual", "unit": "ppg"},
                    ],
                    "optional": [
                        {"key": "overpull_limit", "label": "Max Overpull Limit", "default": "50 klb", "impact": "Uses conservative default"},
                    ],
                    "recommended_files": ["Survey LAS/CSV"],
                },
                "events": {},
            },
        },
    },

    # ── Hydraulics / ECD ──────────────────────────────────────────────────────
    "hydraulics": {
        "name": "Hydraulics / ECD",
        "min_readiness_pct": 60,
        "phases": {
            "drilling": {
                "base": {
                    "required": [
                        {"key": "flow_rate", "label": "Flow Rate", "source": "manual", "unit": "gpm"},
                        {"key": "mud_weight", "label": "Mud Weight", "source": "LAS/manual", "unit": "ppg"},
                        {"key": "pv", "label": "Plastic Viscosity (PV)", "source": "manual", "unit": "cP"},
                        {"key": "yp", "label": "Yield Point (YP)", "source": "manual", "unit": "lb/100ft2"},
                        {"key": "tvd", "label": "True Vertical Depth", "source": "survey/manual", "unit": "ft"},
                        {"key": "circuit_sections", "label": "Hydraulic Circuit (OD, ID, length per section)", "source": "manual", "unit": "in/ft"},
                        {"key": "nozzle_sizes", "label": "Bit Nozzle Sizes", "source": "manual", "unit": "32nds"},
                    ],
                    "optional": [
                        {"key": "rheology_model", "label": "Rheology Model", "default": "bingham_plastic", "impact": "Bingham Plastic if not specified"},
                        {"key": "surface_equipment_loss", "label": "Surface Equipment Loss", "default": "Auto-calculated", "impact": "Estimated from flow rate"},
                    ],
                    "recommended_files": ["Mud report", "Bit record"],
                },
                "events": {
                    "lost_circulation": {
                        "additional_required": [
                            {"key": "frac_gradient", "label": "Fracture Gradient at Loss Zone", "source": "LOT/manual", "unit": "ppg EMW"},
                            {"key": "loss_zone_tvd", "label": "Loss Zone TVD", "source": "manual", "unit": "ft"},
                        ],
                        "additional_optional": [],
                    },
                    "barite_sag": {
                        "additional_required": [
                            {"key": "inclination", "label": "Wellbore Inclination at Sag Zone", "source": "survey", "unit": "deg"},
                        ],
                        "additional_optional": [],
                    },
                },
            },
            "completion": {
                "base": {
                    "required": [
                        {"key": "flow_rate", "label": "Flow Rate", "source": "manual", "unit": "gpm"},
                        {"key": "fluid_weight", "label": "Completion Fluid Weight", "source": "manual", "unit": "ppg"},
                        {"key": "pv", "label": "Plastic Viscosity", "source": "manual", "unit": "cP"},
                        {"key": "yp", "label": "Yield Point", "source": "manual", "unit": "lb/100ft2"},
                        {"key": "tvd", "label": "True Vertical Depth", "source": "manual", "unit": "ft"},
                    ],
                    "optional": [],
                    "recommended_files": ["Completion fluid report"],
                },
                "events": {},
            },
            "workover": {
                "base": {
                    "required": [
                        {"key": "flow_rate", "label": "Flow Rate", "source": "manual", "unit": "gpm"},
                        {"key": "fluid_weight", "label": "Fluid Weight", "source": "manual", "unit": "ppg"},
                        {"key": "pv", "label": "Plastic Viscosity", "source": "manual", "unit": "cP"},
                        {"key": "yp", "label": "Yield Point", "source": "manual", "unit": "lb/100ft2"},
                        {"key": "tvd", "label": "True Vertical Depth", "source": "manual", "unit": "ft"},
                    ],
                    "optional": [],
                    "recommended_files": ["Workover fluid properties"],
                },
                "events": {},
            },
        },
    },

    # ── Stuck Pipe ────────────────────────────────────────────────────────────
    "stuck-pipe": {
        "name": "Stuck Pipe",
        "min_readiness_pct": 50,
        "phases": {
            "drilling": {
                "base": {
                    "required": [
                        {"key": "pipe_od", "label": "Pipe OD", "source": "manual", "unit": "in"},
                        {"key": "pipe_id", "label": "Pipe ID", "source": "manual", "unit": "in"},
                        {"key": "mud_weight", "label": "Mud Weight", "source": "manual", "unit": "ppg"},
                        {"key": "depth_tvd", "label": "Stuck Depth TVD", "source": "manual", "unit": "ft"},
                    ],
                    "optional": [
                        {"key": "pore_pressure", "label": "Pore Pressure", "default": "Hydrostatic", "impact": "Conservative differential pressure estimate"},
                        {"key": "inclination", "label": "Inclination at Stuck Point", "default": "0 deg", "impact": "Underestimates gravity effects"},
                        {"key": "filter_cake_thickness", "label": "Filter Cake Thickness", "default": "3/16 in", "impact": "Standard assumption"},
                    ],
                    "recommended_files": ["Survey LAS/CSV", "Mud report"],
                },
                "events": {
                    "differential": {
                        "additional_required": [
                            {"key": "pore_pressure", "label": "Pore Pressure Gradient", "source": "logs/manual", "unit": "ppg EMW"},
                            {"key": "overbalance", "label": "Overbalance Pressure", "source": "calculated", "unit": "psi"},
                        ],
                        "additional_optional": [],
                    },
                    "mechanical": {
                        "additional_required": [
                            {"key": "torque_at_stuck", "label": "Torque at Stuck Point", "source": "manual", "unit": "ft-lb"},
                        ],
                        "additional_optional": [],
                    },
                    "packoff": {
                        "additional_required": [
                            {"key": "annular_velocity", "label": "Annular Velocity", "source": "calculated", "unit": "ft/min"},
                        ],
                        "additional_optional": [],
                    },
                    "keyseating": {
                        "additional_required": [
                            {"key": "dls", "label": "Dogleg Severity at Key Seat", "source": "survey", "unit": "deg/100ft"},
                        ],
                        "additional_optional": [],
                    },
                },
            },
        },
    },

    # ── Well Control ──────────────────────────────────────────────────────────
    "well-control": {
        "name": "Well Control",
        "min_readiness_pct": 70,
        "phases": {
            "drilling": {
                "base": {
                    "required": [
                        {"key": "depth_md", "label": "Measured Depth", "source": "manual", "unit": "ft"},
                        {"key": "depth_tvd", "label": "True Vertical Depth", "source": "survey/manual", "unit": "ft"},
                        {"key": "mud_weight", "label": "Original Mud Weight", "source": "manual", "unit": "ppg"},
                        {"key": "casing_shoe_tvd", "label": "Casing Shoe TVD", "source": "manual", "unit": "ft"},
                        {"key": "casing_id", "label": "Casing Inner Diameter", "source": "manual", "unit": "in"},
                        {"key": "dp_od", "label": "Drill Pipe OD", "source": "manual", "unit": "in"},
                        {"key": "dp_id", "label": "Drill Pipe ID", "source": "manual", "unit": "in"},
                        {"key": "lot_emw", "label": "LOT / FIT (EMW)", "source": "test/manual", "unit": "ppg"},
                    ],
                    "optional": [
                        {"key": "scr_pressure", "label": "Slow Circulating Rate Pressure", "default": "Auto-calculated", "impact": "Estimated from circuit"},
                        {"key": "pump_output", "label": "Pump Output", "default": "0.1 bbl/stk", "impact": "Standard triplex default"},
                        {"key": "hole_size", "label": "Hole Size", "default": "8.5 in", "impact": "Standard hole size assumed"},
                    ],
                    "recommended_files": ["Well schematic", "Casing tally", "LOT/FIT data"],
                },
                "events": {
                    "kick": {
                        "additional_required": [
                            {"key": "sidpp", "label": "Shut-In Drill Pipe Pressure", "source": "manual", "unit": "psi"},
                            {"key": "sicp", "label": "Shut-In Casing Pressure", "source": "manual", "unit": "psi"},
                            {"key": "pit_gain", "label": "Pit Gain", "source": "manual", "unit": "bbl"},
                        ],
                        "additional_optional": [
                            {"key": "gas_gravity", "label": "Gas Gravity", "default": "0.65", "impact": "Standard hydrocarbon gas assumed"},
                            {"key": "kill_method", "label": "Kill Method", "default": "drillers_method", "impact": "Driller's Method used"},
                        ],
                    },
                    "underground_blowout": {
                        "additional_required": [
                            {"key": "loss_zone_tvd", "label": "Loss Zone TVD", "source": "manual", "unit": "ft"},
                            {"key": "frac_gradient", "label": "Fracture Gradient at Loss Zone", "source": "LOT/manual", "unit": "ppg"},
                        ],
                        "additional_optional": [],
                    },
                    "lost_circulation": {
                        "additional_required": [
                            {"key": "loss_rate", "label": "Loss Rate", "source": "manual", "unit": "bbl/hr"},
                            {"key": "frac_gradient", "label": "Fracture Gradient", "source": "LOT/manual", "unit": "ppg"},
                        ],
                        "additional_optional": [],
                    },
                },
            },
        },
    },

    # ── Wellbore Cleanup ──────────────────────────────────────────────────────
    "wellbore-cleanup": {
        "name": "Wellbore Cleanup",
        "min_readiness_pct": 60,
        "phases": {
            "drilling": {
                "base": {
                    "required": [
                        {"key": "flow_rate", "label": "Flow Rate", "source": "manual", "unit": "gpm"},
                        {"key": "mud_weight", "label": "Mud Weight", "source": "manual", "unit": "ppg"},
                        {"key": "pv", "label": "Plastic Viscosity", "source": "manual", "unit": "cP"},
                        {"key": "yp", "label": "Yield Point", "source": "manual", "unit": "lb/100ft2"},
                        {"key": "hole_diameter", "label": "Hole Diameter", "source": "manual", "unit": "in"},
                        {"key": "pipe_od", "label": "Pipe OD", "source": "manual", "unit": "in"},
                        {"key": "inclination", "label": "Maximum Inclination", "source": "survey", "unit": "deg"},
                    ],
                    "optional": [
                        {"key": "rop", "label": "Rate of Penetration", "default": "0 ft/hr", "impact": "No cuttings generation assumed"},
                        {"key": "rpm", "label": "Pipe Rotation", "default": "0 rpm", "impact": "No rotation effect on cleaning"},
                    ],
                    "recommended_files": ["Survey LAS", "Mud report"],
                },
                "events": {
                    "poor_hole_cleaning": {
                        "additional_required": [
                            {"key": "rop", "label": "Rate of Penetration", "source": "manual", "unit": "ft/hr"},
                            {"key": "cuttings_density", "label": "Cuttings Density", "source": "manual", "unit": "ppg"},
                        ],
                        "additional_optional": [],
                    },
                    "tight_hole": {
                        "additional_required": [
                            {"key": "bed_height", "label": "Estimated Bed Height", "source": "manual", "unit": "in"},
                        ],
                        "additional_optional": [],
                    },
                },
            },
        },
    },

    # ── Packer Forces ─────────────────────────────────────────────────────────
    "packer-forces": {
        "name": "Packer Forces",
        "min_readiness_pct": 70,
        "phases": {
            "completion": {
                "base": {
                    "required": [
                        {"key": "tubing_od", "label": "Tubing OD", "source": "manual", "unit": "in"},
                        {"key": "tubing_id", "label": "Tubing ID", "source": "manual", "unit": "in"},
                        {"key": "packer_depth_tvd", "label": "Packer Depth TVD", "source": "manual", "unit": "ft"},
                        {"key": "initial_pressure_tubing", "label": "Initial Tubing Pressure", "source": "manual", "unit": "psi"},
                        {"key": "initial_pressure_annulus", "label": "Initial Annulus Pressure", "source": "manual", "unit": "psi"},
                        {"key": "initial_temperature", "label": "Initial Temperature", "source": "manual", "unit": "F"},
                    ],
                    "optional": [
                        {"key": "final_temperature", "label": "Final Temperature", "default": "Initial + gradient", "impact": "Temperature change estimated"},
                    ],
                    "recommended_files": ["Completion diagram", "Temperature survey"],
                },
                "events": {},
            },
        },
    },

    # ── Workover Hydraulics ───────────────────────────────────────────────────
    "workover-hydraulics": {
        "name": "Workover Hydraulics",
        "min_readiness_pct": 60,
        "phases": {
            "workover": {
                "base": {
                    "required": [
                        {"key": "flow_rate", "label": "Flow Rate", "source": "manual", "unit": "gpm"},
                        {"key": "fluid_weight", "label": "Fluid Weight", "source": "manual", "unit": "ppg"},
                        {"key": "pv", "label": "Plastic Viscosity", "source": "manual", "unit": "cP"},
                        {"key": "yp", "label": "Yield Point", "source": "manual", "unit": "lb/100ft2"},
                        {"key": "tvd", "label": "True Vertical Depth", "source": "manual", "unit": "ft"},
                        {"key": "string_sections", "label": "Work String Sections (OD, ID, length)", "source": "manual", "unit": "in/ft"},
                    ],
                    "optional": [
                        {"key": "max_pressure", "label": "Max Allowable Surface Pressure", "default": "5000 psi", "impact": "Conservative limit applied"},
                    ],
                    "recommended_files": ["Well schematic", "Work string tally"],
                },
                "events": {
                    "bullheading": {
                        "additional_required": [
                            {"key": "formation_pressure", "label": "Formation Pressure", "source": "manual", "unit": "psi"},
                            {"key": "injectivity_index", "label": "Injectivity Index", "source": "test/manual", "unit": "bbl/min/psi"},
                        ],
                        "additional_optional": [],
                    },
                    "circulation": {
                        "additional_required": [
                            {"key": "return_path", "label": "Return Flow Path (annulus/tubing)", "source": "manual", "unit": ""},
                        ],
                        "additional_optional": [],
                    },
                },
            },
        },
    },

    # ── Sand Control ──────────────────────────────────────────────────────────
    "sand-control": {
        "name": "Sand Control",
        "min_readiness_pct": 60,
        "phases": {
            "completion": {
                "base": {
                    "required": [
                        {"key": "reservoir_pressure", "label": "Reservoir Pressure", "source": "test/manual", "unit": "psi"},
                        {"key": "formation_permeability", "label": "Formation Permeability", "source": "logs/test", "unit": "mD"},
                        {"key": "grain_size_d50", "label": "Grain Size D50", "source": "sieve analysis", "unit": "mm"},
                        {"key": "completion_interval", "label": "Completion Interval (top/bottom TVD)", "source": "manual", "unit": "ft"},
                    ],
                    "optional": [
                        {"key": "fines_content", "label": "Fines Content", "default": "5%", "impact": "Standard estimate for screen sizing"},
                        {"key": "screen_gauge", "label": "Screen Gauge", "default": "Auto-selected", "impact": "Based on grain size"},
                    ],
                    "recommended_files": ["Core analysis", "Sieve analysis", "Well logs LAS"],
                },
                "events": {},
            },
        },
    },

    # ── Completion Design ─────────────────────────────────────────────────────
    "completion-design": {
        "name": "Completion Design",
        "min_readiness_pct": 60,
        "phases": {
            "completion": {
                "base": {
                    "required": [
                        {"key": "reservoir_pressure", "label": "Reservoir Pressure", "source": "test/manual", "unit": "psi"},
                        {"key": "reservoir_temperature", "label": "Reservoir Temperature", "source": "manual", "unit": "F"},
                        {"key": "permeability", "label": "Formation Permeability", "source": "logs/test", "unit": "mD"},
                        {"key": "net_pay", "label": "Net Pay Thickness", "source": "logs/manual", "unit": "ft"},
                        {"key": "wellbore_radius", "label": "Wellbore Radius", "source": "manual", "unit": "ft"},
                    ],
                    "optional": [
                        {"key": "skin_factor", "label": "Skin Factor", "default": "0", "impact": "Assumes no damage"},
                        {"key": "drainage_radius", "label": "Drainage Radius", "default": "1000 ft", "impact": "Standard spacing assumption"},
                    ],
                    "recommended_files": ["Well logs LAS", "DST/well test data"],
                },
                "events": {
                    "skin_damage": {
                        "additional_required": [
                            {"key": "skin_factor", "label": "Measured Skin Factor", "source": "well test", "unit": "dimensionless"},
                        ],
                        "additional_optional": [],
                    },
                    "flow_efficiency": {
                        "additional_required": [
                            {"key": "actual_rate", "label": "Actual Production Rate", "source": "production data", "unit": "STB/d"},
                        ],
                        "additional_optional": [],
                    },
                },
            },
        },
    },

    # ── Shot Efficiency ───────────────────────────────────────────────────────
    "shot-efficiency": {
        "name": "Shot Efficiency",
        "min_readiness_pct": 60,
        "phases": {
            "completion": {
                "base": {
                    "required": [
                        {"key": "perforation_diameter", "label": "Perforation Tunnel Diameter", "source": "gun data", "unit": "in"},
                        {"key": "perforation_length", "label": "Perforation Tunnel Length", "source": "gun data", "unit": "in"},
                        {"key": "shot_density", "label": "Shot Density", "source": "gun data", "unit": "SPF"},
                        {"key": "phasing", "label": "Phasing Angle", "source": "gun data", "unit": "deg"},
                        {"key": "reservoir_permeability", "label": "Reservoir Permeability", "source": "logs/test", "unit": "mD"},
                    ],
                    "optional": [
                        {"key": "crushed_zone_permeability", "label": "Crushed Zone Permeability", "default": "10% of formation", "impact": "Standard damage ratio"},
                        {"key": "wellbore_radius", "label": "Wellbore Radius", "default": "0.354 ft", "impact": "8.5 in hole assumed"},
                    ],
                    "recommended_files": ["Perforation gun spec sheet"],
                },
                "events": {},
            },
        },
    },

    # ── Vibrations ────────────────────────────────────────────────────────────
    "vibrations": {
        "name": "BHA Vibrations",
        "min_readiness_pct": 50,
        "phases": {
            "drilling": {
                "base": {
                    "required": [
                        {"key": "bha_components", "label": "BHA Components (OD, ID, length, weight)", "source": "manual", "unit": "in/ft/lb"},
                        {"key": "hole_diameter", "label": "Hole Diameter", "source": "manual", "unit": "in"},
                        {"key": "rpm", "label": "Rotary Speed", "source": "manual", "unit": "rpm"},
                        {"key": "wob", "label": "Weight on Bit", "source": "manual", "unit": "klb"},
                    ],
                    "optional": [
                        {"key": "inclination", "label": "Wellbore Inclination", "default": "0 deg", "impact": "Vertical well assumed for critical RPM"},
                        {"key": "stabilizer_placement", "label": "Stabilizer Positions", "default": "None", "impact": "Less accurate mode prediction"},
                    ],
                    "recommended_files": ["BHA diagram", "Drilling parameters LAS"],
                },
                "events": {
                    "lateral": {
                        "additional_required": [
                            {"key": "bit_type", "label": "Bit Type (PDC/Roller Cone)", "source": "manual", "unit": ""},
                        ],
                        "additional_optional": [],
                    },
                    "torsional": {
                        "additional_required": [
                            {"key": "torque_variation", "label": "Surface Torque Variation", "source": "sensor/manual", "unit": "ft-lb"},
                        ],
                        "additional_optional": [],
                    },
                    "axial": {
                        "additional_required": [
                            {"key": "wob_variation", "label": "WOB Variation Pattern", "source": "sensor/manual", "unit": "klb"},
                        ],
                        "additional_optional": [],
                    },
                },
            },
        },
    },

    # ── Cementing ─────────────────────────────────────────────────────────────
    "cementing": {
        "name": "Cementing",
        "min_readiness_pct": 60,
        "phases": {
            "drilling": {
                "base": {
                    "required": [
                        {"key": "casing_od", "label": "Casing OD", "source": "manual", "unit": "in"},
                        {"key": "casing_id", "label": "Casing ID", "source": "manual", "unit": "in"},
                        {"key": "hole_diameter", "label": "Hole Diameter", "source": "caliper/manual", "unit": "in"},
                        {"key": "shoe_tvd", "label": "Casing Shoe TVD", "source": "manual", "unit": "ft"},
                        {"key": "slurry_density", "label": "Cement Slurry Density", "source": "lab/manual", "unit": "ppg"},
                        {"key": "mud_weight", "label": "Mud Weight", "source": "manual", "unit": "ppg"},
                    ],
                    "optional": [
                        {"key": "toc", "label": "Top of Cement (TOC)", "default": "Surface", "impact": "Full casing cemented assumed"},
                        {"key": "displacement_rate", "label": "Displacement Rate", "default": "8 bbl/min", "impact": "Standard rate assumed"},
                        {"key": "spacer_volume", "label": "Spacer Volume", "default": "500 ft annular column", "impact": "Standard spacer volume"},
                    ],
                    "recommended_files": ["Well schematic", "Caliper log LAS", "Cement lab report"],
                },
                "events": {
                    "channeling": {
                        "additional_required": [
                            {"key": "centralization", "label": "Centralizer Spacing", "source": "manual", "unit": "ft"},
                            {"key": "standoff", "label": "Standoff Percentage", "source": "calculated", "unit": "%"},
                        ],
                        "additional_optional": [],
                    },
                    "contamination": {
                        "additional_required": [
                            {"key": "contact_time", "label": "Contact Time (spacer)", "source": "calculated", "unit": "min"},
                        ],
                        "additional_optional": [],
                    },
                },
            },
            "completion": {
                "base": {
                    "required": [
                        {"key": "liner_od", "label": "Liner OD", "source": "manual", "unit": "in"},
                        {"key": "liner_id", "label": "Liner ID", "source": "manual", "unit": "in"},
                        {"key": "host_casing_id", "label": "Host Casing ID", "source": "manual", "unit": "in"},
                        {"key": "slurry_density", "label": "Cement Slurry Density", "source": "lab/manual", "unit": "ppg"},
                    ],
                    "optional": [],
                    "recommended_files": ["Well schematic", "Cement lab report"],
                },
                "events": {},
            },
        },
    },

    # ── Casing Design ─────────────────────────────────────────────────────────
    "casing-design": {
        "name": "Casing Design",
        "min_readiness_pct": 70,
        "phases": {
            "drilling": {
                "base": {
                    "required": [
                        {"key": "casing_od", "label": "Casing OD", "source": "manual", "unit": "in"},
                        {"key": "casing_weight", "label": "Casing Weight", "source": "manual", "unit": "lb/ft"},
                        {"key": "casing_grade", "label": "Casing Grade", "source": "manual", "unit": ""},
                        {"key": "setting_depth_tvd", "label": "Setting Depth TVD", "source": "manual", "unit": "ft"},
                        {"key": "mud_weight", "label": "Mud Weight", "source": "manual", "unit": "ppg"},
                        {"key": "pore_pressure_gradient", "label": "Pore Pressure Gradient", "source": "logs/manual", "unit": "ppg"},
                        {"key": "frac_gradient", "label": "Fracture Gradient", "source": "LOT/manual", "unit": "ppg"},
                    ],
                    "optional": [
                        {"key": "sf_burst", "label": "Burst Safety Factor", "default": "1.10", "impact": "Industry standard minimum"},
                        {"key": "sf_collapse", "label": "Collapse Safety Factor", "default": "1.00", "impact": "Industry standard minimum"},
                        {"key": "sf_tension", "label": "Tension Safety Factor", "default": "1.60", "impact": "Industry standard minimum"},
                    ],
                    "recommended_files": ["Pore/frac gradient plot", "Casing catalog"],
                },
                "events": {
                    "burst": {
                        "additional_required": [
                            {"key": "internal_pressure", "label": "Expected Internal Pressure", "source": "calculated", "unit": "psi"},
                        ],
                        "additional_optional": [],
                    },
                    "collapse": {
                        "additional_required": [
                            {"key": "external_pressure", "label": "Expected External Pressure", "source": "calculated", "unit": "psi"},
                        ],
                        "additional_optional": [],
                    },
                    "tension": {
                        "additional_required": [
                            {"key": "buoyed_weight", "label": "Buoyed String Weight", "source": "calculated", "unit": "lb"},
                        ],
                        "additional_optional": [],
                    },
                },
            },
        },
    },

    # ── Petrophysics ──────────────────────────────────────────────────────────
    "petrophysics": {
        "name": "Petrophysics",
        "min_readiness_pct": 50,
        "phases": {
            "drilling": {
                "base": {
                    "required": [
                        {"key": "well_logs", "label": "Well Logs (GR, RHOB, NPHI, RT minimum)", "source": "LAS/DLIS", "unit": "various"},
                    ],
                    "optional": [
                        {"key": "rw", "label": "Formation Water Resistivity (Rw)", "default": "Auto-picked from logs", "impact": "Estimated from SP or Pickett plot"},
                        {"key": "a", "label": "Archie 'a' (tortuosity)", "default": "1.0", "impact": "Standard sandstone"},
                        {"key": "m", "label": "Archie 'm' (cementation)", "default": "2.0", "impact": "Standard sandstone"},
                        {"key": "n", "label": "Archie 'n' (saturation)", "default": "2.0", "impact": "Standard assumption"},
                        {"key": "rhob_matrix", "label": "Matrix Density", "default": "2.65 g/cc", "impact": "Sandstone assumed"},
                        {"key": "rhob_fluid", "label": "Fluid Density", "default": "1.0 g/cc", "impact": "Fresh water assumed"},
                    ],
                    "recommended_files": ["Well logs LAS/DLIS (GR, RHOB, NPHI, RT)"],
                },
                "events": {},
            },
            "completion": {
                "base": {
                    "required": [
                        {"key": "well_logs", "label": "Well Logs (GR, RHOB, NPHI, RT minimum)", "source": "LAS/DLIS", "unit": "various"},
                    ],
                    "optional": [
                        {"key": "core_porosity", "label": "Core Porosity", "default": "None", "impact": "Log porosity only"},
                        {"key": "core_permeability", "label": "Core Permeability", "default": "None", "impact": "Estimated from porosity"},
                    ],
                    "recommended_files": ["Well logs LAS/DLIS", "Core analysis report"],
                },
                "events": {},
            },
        },
    },
}


# ── Merge function ────────────────────────────────────────────────────────────

def get_requirements(
    module_id: str,
    phase: str,
    event: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Return merged data requirements for a module/phase/event combination.

    Merges base requirements with event-specific additional requirements.
    Raises KeyError for unknown module or phase.
    """
    module = DATA_REQUIREMENTS[module_id]
    phase_data = module["phases"][phase]
    base = phase_data["base"]

    result: Dict[str, Any] = {
        "module": module["name"],
        "phase": phase,
        "event": event,
        "required": list(base["required"]),
        "optional": list(base.get("optional", [])),
        "recommended_files": list(base.get("recommended_files", [])),
        "min_readiness_pct": module.get("min_readiness_pct", 60),
    }

    if event and "events" in phase_data and event in phase_data["events"]:
        evt = phase_data["events"][event]
        result["required"].extend(evt.get("additional_required", []))
        result["optional"].extend(evt.get("additional_optional", []))

    return result
