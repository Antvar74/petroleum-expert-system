# Data Readiness Panel — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Each module shows a Data Readiness panel recommending what data the user needs for optimal analysis, varying by operational phase and event type.

**Architecture:** A `DATA_REQUIREMENTS` registry in the backend maps every module to its phase/event-specific data requirements. A `get_requirements()` function merges base + event requirements. A single API endpoint exposes this. A reusable `DataReadinessPanel` React component consumes the endpoint and renders ✅/❌/⚠️ indicators with readiness percentage.

**Tech Stack:** Python/FastAPI (backend registry + endpoint), React 19/TypeScript/Tailwind CSS/Framer Motion (frontend component), i18next (EN/ES)

**Design Doc:** `Docs/plans/2026-02-23-data-readiness-panel-design.md`

---

## Task 1: Data Requirements Registry — Tests

**Files:**
- Create: `tests/unit/test_data_requirements.py`

**Step 1: Write all registry tests**

```python
# tests/unit/test_data_requirements.py
"""Unit tests for DATA_REQUIREMENTS registry and get_requirements() merge logic."""
import pytest
from orchestrator.data_requirements import DATA_REQUIREMENTS, get_requirements


class TestRegistryCompleteness:
    """Every module in the app should have a requirements entry."""

    EXPECTED_MODULES = [
        "torque-drag", "hydraulics", "stuck-pipe", "well-control",
        "wellbore-cleanup", "packer-forces", "workover-hydraulics",
        "sand-control", "completion-design", "shot-efficiency",
        "vibrations", "cementing", "casing-design", "petrophysics",
    ]

    def test_all_modules_present(self):
        """All 14 modules should exist in DATA_REQUIREMENTS."""
        for mod_id in self.EXPECTED_MODULES:
            assert mod_id in DATA_REQUIREMENTS, f"Missing module: {mod_id}"

    def test_each_module_has_phases(self):
        """Every module must have at least one phase."""
        for mod_id, mod in DATA_REQUIREMENTS.items():
            assert "phases" in mod, f"{mod_id} missing 'phases'"
            assert len(mod["phases"]) >= 1, f"{mod_id} has no phases"

    def test_each_phase_has_base_required(self):
        """Every phase base must have at least one required field."""
        for mod_id, mod in DATA_REQUIREMENTS.items():
            for phase_name, phase in mod["phases"].items():
                assert "base" in phase, f"{mod_id}/{phase_name} missing 'base'"
                assert len(phase["base"]["required"]) >= 1, (
                    f"{mod_id}/{phase_name} has no required fields"
                )

    def test_required_fields_have_key_and_label(self):
        """Every required field must have 'key' and 'label'."""
        for mod_id, mod in DATA_REQUIREMENTS.items():
            for phase_name, phase in mod["phases"].items():
                for field in phase["base"]["required"]:
                    assert "key" in field, f"{mod_id}/{phase_name}: field missing 'key'"
                    assert "label" in field, f"{mod_id}/{phase_name}: field missing 'label'"

    def test_min_readiness_pct_present(self):
        """Every module should have a min_readiness_pct between 0 and 100."""
        for mod_id, mod in DATA_REQUIREMENTS.items():
            pct = mod.get("min_readiness_pct", -1)
            assert 0 < pct <= 100, f"{mod_id} invalid min_readiness_pct: {pct}"


class TestGetRequirements:
    """Test the merge logic that combines base + event requirements."""

    def test_base_only_no_event(self):
        """When no event is given, returns only base requirements."""
        result = get_requirements("well-control", "drilling")
        assert result["module"] == "Well Control"
        assert result["phase"] == "drilling"
        assert result["event"] is None
        assert len(result["required"]) >= 1

    def test_base_plus_event_merges(self):
        """Event adds additional_required to the base required list."""
        base = get_requirements("well-control", "drilling")
        with_event = get_requirements("well-control", "drilling", "kick")
        assert len(with_event["required"]) > len(base["required"])
        assert with_event["event"] == "kick"

    def test_unknown_event_returns_base_only(self):
        """Unknown event should return base requirements (no crash)."""
        result = get_requirements("well-control", "drilling", "nonexistent_event")
        assert result["event"] == "nonexistent_event"
        assert len(result["required"]) >= 1

    def test_unknown_module_raises(self):
        """Unknown module should raise KeyError."""
        with pytest.raises(KeyError):
            get_requirements("nonexistent-module", "drilling")

    def test_unknown_phase_raises(self):
        """Unknown phase should raise KeyError."""
        with pytest.raises(KeyError):
            get_requirements("well-control", "nonexistent_phase")

    def test_optional_fields_returned(self):
        """Result should include optional fields from base."""
        result = get_requirements("torque-drag", "drilling")
        assert "optional" in result
        assert isinstance(result["optional"], list)

    def test_recommended_files_returned(self):
        """Result should include recommended_files list."""
        result = get_requirements("torque-drag", "drilling")
        assert "recommended_files" in result
        assert isinstance(result["recommended_files"], list)
        assert len(result["recommended_files"]) >= 1

    def test_min_readiness_pct_in_result(self):
        """Result should include the module's min_readiness_pct."""
        result = get_requirements("well-control", "drilling")
        assert "min_readiness_pct" in result
        assert 0 < result["min_readiness_pct"] <= 100
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system && python3 -m pytest tests/unit/test_data_requirements.py -v --tb=short`
Expected: ALL FAIL with `ModuleNotFoundError: No module named 'orchestrator.data_requirements'`

**Step 3: Commit failing tests**

```bash
git add tests/unit/test_data_requirements.py
git commit -m "test: add failing tests for DATA_REQUIREMENTS registry (13 tests)"
```

---

## Task 2: Data Requirements Registry — Implementation

**Files:**
- Create: `orchestrator/data_requirements.py`

**Step 1: Implement the registry and merge function**

```python
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
```

**Step 2: Run tests to verify they pass**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system && python3 -m pytest tests/unit/test_data_requirements.py -v --tb=short`
Expected: ALL 13 PASS

**Step 3: Commit**

```bash
git add orchestrator/data_requirements.py tests/unit/test_data_requirements.py
git commit -m "feat: add DATA_REQUIREMENTS registry — 14 modules × phases × events (13 tests)"
```

---

## Task 3: API Endpoint

**Files:**
- Modify: `api_main.py` (add 1 GET route before `if __name__`)

**Step 1: Add the data-requirements endpoint**

Insert before the `if __name__ == "__main__":` line in api_main.py:

```python
# ── Data Requirements Route ────────────────────────────────────────────────────

from orchestrator.data_requirements import get_requirements as get_data_requirements


@app.get("/modules/{module_id}/data-requirements")
async def get_module_data_requirements(
    module_id: str,
    phase: str = Query("drilling"),
    event: Optional[str] = Query(None),
):
    """Return merged data requirements for a module/phase/event combination."""
    try:
        result = get_data_requirements(module_id, phase, event)
        return result
    except KeyError as e:
        raise HTTPException(status_code=404, detail=f"Not found: {str(e)}")
```

**NOTE:** Check that `Query` and `Optional` are already imported at the top of api_main.py. If not, add them:
```python
from fastapi import FastAPI, Body, HTTPException, Query
from typing import Dict, Any, List, Optional
```

**Step 2: Run full test suite**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system && python3 -m pytest tests/ -q --tb=short 2>&1 | tail -5`
Expected: All tests pass

**Step 3: Commit**

```bash
git add api_main.py
git commit -m "feat: add GET /modules/{module_id}/data-requirements endpoint"
```

---

## Task 4: Locale Keys (EN + ES)

**Files:**
- Modify: `frontend/src/locales/en.json`
- Modify: `frontend/src/locales/es.json`

**Step 1: Add dataReadiness section to en.json**

Add a new `"dataReadiness"` top-level key:

```json
"dataReadiness": {
  "title": "Data Readiness",
  "required": "Required",
  "optional": "Optional (improves accuracy)",
  "missingAction": "Upload or enter manually",
  "usingDefault": "Using {{value}}",
  "recommendedUploads": "Recommended uploads",
  "phase": "Phase",
  "event": "Event",
  "noEvent": "General",
  "readinessLabel": "Data Readiness",
  "sufficient": "Sufficient for analysis",
  "insufficient": "More data needed",
  "source": "Source: {{source}}",
  "phases": {
    "drilling": "Drilling",
    "completion": "Completion",
    "workover": "Workover"
  },
  "present": "Loaded",
  "missing": "Missing"
}
```

**Step 2: Add same section to es.json**

```json
"dataReadiness": {
  "title": "Preparación de Datos",
  "required": "Requerido",
  "optional": "Opcional (mejora la precisión)",
  "missingAction": "Sube archivo o ingresa manualmente",
  "usingDefault": "Usando {{value}}",
  "recommendedUploads": "Archivos recomendados",
  "phase": "Fase",
  "event": "Evento",
  "noEvent": "General",
  "readinessLabel": "Preparación de Datos",
  "sufficient": "Suficiente para análisis",
  "insufficient": "Se necesitan más datos",
  "source": "Fuente: {{source}}",
  "phases": {
    "drilling": "Perforación",
    "completion": "Completación",
    "workover": "Workover"
  },
  "present": "Cargado",
  "missing": "Faltante"
}
```

**Step 3: Build to verify**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system/frontend && npm run build 2>&1 | tail -3`
Expected: Build succeeds

**Step 4: Commit**

```bash
git add frontend/src/locales/en.json frontend/src/locales/es.json
git commit -m "feat: add dataReadiness locale keys (EN + ES)"
```

---

## Task 5: DataReadinessPanel Component

**Files:**
- Create: `frontend/src/components/DataReadinessPanel.tsx`

**Step 1: Create the component**

```tsx
/**
 * DataReadinessPanel.tsx — Shows data readiness checklist per module/phase/event.
 *
 * Fetches requirements from /modules/{id}/data-requirements and cross-checks
 * against currentData to show ✅/❌/⚠️ status with readiness percentage.
 */
import React, { useState, useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ClipboardCheck, CheckCircle2, XCircle, AlertTriangle,
  ChevronDown, FileUp, Info,
} from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface DataRequirement {
  key: string;
  label: string;
  source?: string;
  unit?: string;
  min_points?: number;
  default?: string;
  impact?: string;
}

interface RequirementsResponse {
  module: string;
  phase: string;
  event: string | null;
  required: DataRequirement[];
  optional: DataRequirement[];
  recommended_files: string[];
  min_readiness_pct: number;
}

interface DataReadinessPanelProps {
  moduleId: string;
  phase: string;
  event?: string;
  currentData: Record<string, any>;
  onPhaseChange?: (phase: string) => void;
  onEventChange?: (event: string | undefined) => void;
  phases?: string[];
  events?: string[];
}

const DataReadinessPanel: React.FC<DataReadinessPanelProps> = ({
  moduleId,
  phase,
  event,
  currentData,
  onPhaseChange,
  onEventChange,
  phases = ['drilling', 'completion', 'workover'],
  events = [],
}) => {
  const { t } = useTranslation();
  const [requirements, setRequirements] = useState<RequirementsResponse | null>(null);
  const [isExpanded, setIsExpanded] = useState(true);
  const [isLoading, setIsLoading] = useState(false);

  // ── Fetch requirements ──────────────────────────────────────────
  useEffect(() => {
    const fetchRequirements = async () => {
      setIsLoading(true);
      try {
        const params = new URLSearchParams({ phase });
        if (event) params.append('event', event);
        const res = await fetch(`${API_BASE_URL}/modules/${moduleId}/data-requirements?${params}`);
        if (res.ok) {
          const data = await res.json();
          setRequirements(data);
        }
      } catch {
        // Silently fail — panel is supplementary
      } finally {
        setIsLoading(false);
      }
    };
    fetchRequirements();
  }, [moduleId, phase, event]);

  // ── Compute readiness ──────────────────────────────────────────
  const readiness = useMemo(() => {
    if (!requirements) return { pct: 0, present: 0, total: 0, items: [] };

    const items = requirements.required.map((req) => {
      const value = currentData[req.key];
      const isPresent = value !== undefined && value !== null && value !== '' &&
        !(Array.isArray(value) && value.length === 0);
      return { ...req, isPresent, value, type: 'required' as const };
    });

    const optionalItems = requirements.optional.map((opt) => {
      const value = currentData[opt.key];
      const isPresent = value !== undefined && value !== null && value !== '';
      return { ...opt, isPresent, value, type: 'optional' as const };
    });

    const present = items.filter((i) => i.isPresent).length;
    const total = items.length;
    const pct = total > 0 ? Math.round((present / total) * 100) : 0;

    return { pct, present, total, items, optionalItems };
  }, [requirements, currentData]);

  if (!requirements && !isLoading) return null;

  const minPct = requirements?.min_readiness_pct ?? 60;
  const isSufficient = readiness.pct >= minPct;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-panel rounded-2xl border border-white/5 mb-6 overflow-hidden"
    >
      {/* ── Header ── */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-white/5 transition-colors"
      >
        <div className="flex items-center gap-3">
          <ClipboardCheck size={20} className="text-industrial-400" />
          <span className="font-bold text-sm">{t('dataReadiness.title')}</span>
          {onPhaseChange && (
            <span className="text-xs text-white/40 bg-white/5 px-2 py-0.5 rounded-full">
              {t(`dataReadiness.phases.${phase}`)}
              {event && ` • ${event.replace(/_/g, ' ')}`}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          {/* Readiness badge */}
          <div className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold ${
            isSufficient
              ? 'bg-green-500/10 text-green-400 border border-green-500/20'
              : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
          }`}>
            <span>{readiness.pct}%</span>
          </div>
          <ChevronDown
            size={16}
            className={`text-white/30 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          />
        </div>
      </button>

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            <div className="px-4 pb-4 space-y-4">
              {/* ── Phase/Event selectors ── */}
              {(onPhaseChange || onEventChange) && (
                <div className="flex gap-3">
                  {onPhaseChange && (
                    <select
                      value={phase}
                      onChange={(e) => onPhaseChange(e.target.value)}
                      className="bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-white/70 focus:outline-none focus:border-industrial-400"
                    >
                      {phases.map((p) => (
                        <option key={p} value={p}>{t(`dataReadiness.phases.${p}`)}</option>
                      ))}
                    </select>
                  )}
                  {onEventChange && events.length > 0 && (
                    <select
                      value={event || ''}
                      onChange={(e) => onEventChange(e.target.value || undefined)}
                      className="bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-white/70 focus:outline-none focus:border-industrial-400"
                    >
                      <option value="">{t('dataReadiness.noEvent')}</option>
                      {events.map((ev) => (
                        <option key={ev} value={ev}>{ev.replace(/_/g, ' ')}</option>
                      ))}
                    </select>
                  )}
                </div>
              )}

              {/* ── Required fields ── */}
              <div>
                <p className="text-xs font-semibold text-white/50 mb-2">{t('dataReadiness.required')}</p>
                <div className="space-y-1.5">
                  {readiness.items.map((item) => (
                    <div key={item.key} className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2">
                        {item.isPresent ? (
                          <CheckCircle2 size={14} className="text-green-400 shrink-0" />
                        ) : (
                          <XCircle size={14} className="text-red-400 shrink-0" />
                        )}
                        <span className={item.isPresent ? 'text-white/70' : 'text-red-300'}>
                          {item.label}
                        </span>
                      </div>
                      <span className="text-white/30 text-[10px]">
                        {item.isPresent
                          ? `${typeof item.value === 'number' ? item.value : t('dataReadiness.present')}${item.unit ? ` ${item.unit}` : ''}`
                          : t('dataReadiness.missingAction')}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* ── Optional fields ── */}
              {readiness.optionalItems && readiness.optionalItems.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-white/50 mb-2">{t('dataReadiness.optional')}</p>
                  <div className="space-y-1.5">
                    {readiness.optionalItems.map((item) => (
                      <div key={item.key} className="flex items-center justify-between text-xs">
                        <div className="flex items-center gap-2">
                          {item.isPresent ? (
                            <CheckCircle2 size={14} className="text-green-400 shrink-0" />
                          ) : (
                            <AlertTriangle size={14} className="text-amber-400 shrink-0" />
                          )}
                          <span className="text-white/50">{item.label}</span>
                        </div>
                        <span className="text-white/30 text-[10px]">
                          {item.isPresent
                            ? `${typeof item.value === 'number' ? item.value : t('dataReadiness.present')}`
                            : t('dataReadiness.usingDefault', { value: item.default || '—' })}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* ── Recommended files ── */}
              {requirements?.recommended_files && requirements.recommended_files.length > 0 && (
                <div className="flex items-start gap-2 bg-white/5 rounded-xl p-3">
                  <FileUp size={14} className="text-industrial-400 mt-0.5 shrink-0" />
                  <div>
                    <p className="text-[10px] text-white/40 font-semibold mb-1">{t('dataReadiness.recommendedUploads')}</p>
                    <p className="text-xs text-white/60">{requirements.recommended_files.join(', ')}</p>
                  </div>
                </div>
              )}

              {/* ── Status message ── */}
              <div className={`flex items-center gap-2 text-[10px] px-3 py-2 rounded-lg ${
                isSufficient ? 'bg-green-500/5 text-green-400' : 'bg-amber-500/5 text-amber-400'
              }`}>
                <Info size={12} />
                <span>
                  {isSufficient ? t('dataReadiness.sufficient') : t('dataReadiness.insufficient')}
                  {' — '}{readiness.present}/{readiness.total} {t('dataReadiness.required').toLowerCase()}
                </span>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

export default DataReadinessPanel;
```

**Step 2: Build to verify**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system/frontend && npm run build 2>&1 | tail -5`
Expected: Build succeeds (component exists but is not yet imported anywhere)

**Step 3: Commit**

```bash
git add frontend/src/components/DataReadinessPanel.tsx
git commit -m "feat: add DataReadinessPanel component — readiness checklist with phase/event selectors"
```

---

## Task 6: Integrate into WellControlModule (first module)

**Files:**
- Modify: `frontend/src/components/WellControlModule.tsx`

**Step 1: Add import and state**

At the imports section, add:
```tsx
import DataReadinessPanel from './DataReadinessPanel';
```

Add phase/event state after existing state declarations:
```tsx
const [selectedPhase] = useState('drilling');
const [selectedEvent, setSelectedEvent] = useState<string | undefined>('kick');
```

**Step 2: Insert DataReadinessPanel**

Insert the panel in the "Active Kill" tab section, before the kill calculation button. Find the section where `kickData` inputs are rendered and add:

```tsx
<DataReadinessPanel
  moduleId="well-control"
  phase={selectedPhase}
  event={selectedEvent}
  currentData={{
    ...preRecordData,
    ...kickData,
  }}
  onEventChange={setSelectedEvent}
  events={['kick', 'underground_blowout', 'lost_circulation']}
  phases={['drilling']}
/>
```

**Step 3: Build and verify**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system/frontend && npm run build 2>&1 | tail -5`
Expected: Build succeeds

**Step 4: Commit**

```bash
git add frontend/src/components/WellControlModule.tsx
git commit -m "feat: integrate DataReadinessPanel into WellControlModule"
```

---

## Task 7: Integrate into remaining modules

**Files:**
- Modify: 13 remaining module `.tsx` files

For each module, follow the same pattern:
1. Import `DataReadinessPanel`
2. Add phase/event state if needed
3. Insert panel in the parameters/analysis section
4. Pass `currentData` from the module's existing state

**Module integration table:**

| Module File | moduleId | Default Phase | Events |
|---|---|---|---|
| TorqueDragModule.tsx | torque-drag | drilling | stuck_pipe, high_torque |
| HydraulicsModule.tsx | hydraulics | drilling | lost_circulation, barite_sag |
| StuckPipeModule.tsx | stuck-pipe | drilling | differential, mechanical, packoff, keyseating |
| WellboreCleanupModule.tsx | wellbore-cleanup | drilling | poor_hole_cleaning, tight_hole |
| PackerForcesModule.tsx | packer-forces | completion | — |
| WorkoverHydraulicsModule.tsx | workover-hydraulics | workover | bullheading, circulation |
| SandControlModule.tsx | sand-control | completion | — |
| CompletionDesignModule.tsx | completion-design | completion | skin_damage, flow_efficiency |
| ShotEfficiencyModule.tsx | shot-efficiency | completion | — |
| VibrationsModule.tsx | vibrations | drilling | lateral, torsional, axial |
| CementingModule.tsx | cementing | drilling | channeling, contamination |
| CasingDesignModule.tsx | casing-design | drilling | burst, collapse, tension |
| PetrophysicsModule.tsx | petrophysics | drilling | — |

For each: import, add state, insert panel before calculation/analysis button, pass currentData from module state.

**After all integrations:**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system/frontend && npm run build 2>&1 | tail -5`
Expected: Build succeeds

**Commit:**

```bash
git add frontend/src/components/*.tsx
git commit -m "feat: integrate DataReadinessPanel into all 13 remaining modules"
```

---

## Task 8: Final Verification + V&V Report

**Step 1: Run full test suite**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system && python3 -m pytest tests/ -q --tb=short 2>&1 | tail -10`
Expected: ~1262+ passed (1249 existing + 13 new)

**Step 2: Build frontend**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system/frontend && npm run build 2>&1 | tail -5`
Expected: Build succeeds

**Step 3: Regenerate V&V report**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system && python3 scripts/generate_vv_report.py`
Expected: Report generated with updated test count

**Step 4: Commit**

```bash
git add Docs/VV_REPORT_PETROEXPERT.md
git commit -m "docs: regenerate V&V report — updated with DataReadiness registry tests"
```

---

## Dependency Graph

```
Task 1 (Registry tests) ──→ Task 2 (Registry impl) ──→ Task 3 (API endpoint)
                                                              │
                              Task 4 (Locale keys) ──────────┤
                                                              │
                              Task 5 (React component) ──────┤
                                                              │
                                              Task 6 (WellControl integration)
                                                              │
                                              Task 7 (13 remaining modules)
                                                              │
                                              Task 8 (Final verification)
```

Tasks 2, 4, and 5 are independent after Task 1. Tasks 3+4+5 can be done in parallel.
Task 6 depends on Tasks 3, 4, 5. Task 7 depends on Task 6 (pattern established).
Task 8 depends on Task 7.
