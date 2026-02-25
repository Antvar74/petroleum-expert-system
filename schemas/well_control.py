"""
Pydantic request schemas for Well Control routes.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class KillSheetPreRecordRequest(BaseModel):
    """Body for ``POST /wells/{well_id}/kill-sheet/pre-record``."""

    depth_md: float = Field(default=0, description="Measured depth (ft)")
    depth_tvd: float = Field(default=0, description="True vertical depth (ft)")
    original_mud_weight: float = Field(default=10.0, description="Original mud weight (ppg)")
    casing_shoe_tvd: float = Field(default=0, description="Casing shoe TVD (ft)")
    casing_id: float = Field(default=8.681, description="Casing inner diameter (in)")
    dp_od: float = Field(default=5.0, description="Drill pipe outer diameter (in)")
    dp_id: float = Field(default=4.276, description="Drill pipe inner diameter (in)")
    dp_length: float = Field(default=0, description="Drill pipe length (ft)")
    dc_od: float = Field(default=6.5, description="Drill collar outer diameter (in)")
    dc_id: float = Field(default=2.813, description="Drill collar inner diameter (in)")
    dc_length: float = Field(default=0, description="Drill collar length (ft)")
    scr_pressure: float = Field(default=0, description="Slow circulating rate pressure (psi)")
    scr_rate: float = Field(default=0, description="Slow circulating rate (spm)")
    lot_emw: float = Field(default=14.0, description="LOT equivalent mud weight (ppg)")
    pump_output: float = Field(default=0.1, description="Pump output (bbl/stroke)")
    hole_size: float = Field(default=8.5, description="Hole size (in)")


class KillSheetCalculateRequest(BaseModel):
    """Body for ``POST /wells/{well_id}/kill-sheet/calculate``."""

    sidpp: float = Field(default=0, description="Shut-in drill pipe pressure (psi)")
    sicp: float = Field(default=0, description="Shut-in casing pressure (psi)")
    pit_gain: float = Field(default=0, description="Pit gain (bbl)")
    kill_method: str = Field(default="wait_weight", description="Kill method: wait_weight | drillers")


class VolumetricRequest(BaseModel):
    """Body for ``POST /kill-sheet/volumetric``."""

    mud_weight: float = Field(default=10.0, description="Mud weight (ppg)")
    sicp: float = Field(default=0, description="Shut-in casing pressure (psi)")
    tvd: float = Field(default=10000, description="True vertical depth (ft)")
    annular_capacity: float = Field(default=0.05, description="Annular capacity (bbl/ft)")
    lot_emw: float = Field(default=14.0, description="LOT EMW (ppg)")
    casing_shoe_tvd: float = Field(default=5000, description="Casing shoe TVD (ft)")
    safety_margin_psi: float = Field(default=50, description="Safety margin (psi)")
    pressure_increment_psi: float = Field(default=100, description="Pressure increment per cycle (psi)")


class BullheadRequest(BaseModel):
    """Body for ``POST /kill-sheet/bullhead``."""

    mud_weight: float = Field(default=10.0, description="Mud weight (ppg)")
    kill_mud_weight: float = Field(default=11.0, description="Kill mud weight (ppg)")
    depth_tvd: float = Field(default=10000, description="TVD (ft)")
    casing_shoe_tvd: float = Field(default=5000, description="Casing shoe TVD (ft)")
    lot_emw: float = Field(default=14.0, description="LOT EMW (ppg)")
    dp_capacity: float = Field(default=0.018, description="Drill pipe capacity (bbl/ft)")
    depth_md: float = Field(default=10000, description="Measured depth (ft)")
    formation_pressure: float = Field(default=5720, description="Formation pressure (psi)")


class KickToleranceRequest(BaseModel):
    """Body for ``POST /well-control/kick-tolerance``."""

    mud_weight: float = Field(default=10.0, description="Mud weight (ppg)")
    shoe_tvd: float = Field(default=5000, description="Shoe TVD (ft)")
    lot_emw: float = Field(default=14.0, description="LOT EMW (ppg)")
    well_depth_tvd: float = Field(default=10000, description="Well depth TVD (ft)")
    gas_gravity: float = Field(default=0.65, description="Gas gravity (air=1)")
    bht: float = Field(default=150.0, description="Bottom hole temperature (F)")
    annular_capacity: float = Field(default=0.05, description="Annular capacity (bbl/ft)")
    influx_type: str = Field(default="gas", description="Influx type: gas | oil | water")


class BariteRequirementsRequest(BaseModel):
    """Body for ``POST /well-control/barite-requirements``."""

    current_mud_weight: float = Field(default=10.0, description="Current mud weight (ppg)")
    target_mud_weight: float = Field(default=12.0, description="Target mud weight (ppg)")
    system_volume_bbl: float = Field(default=500, description="Mud system volume (bbl)")
    barite_sg: float = Field(default=4.20, description="Barite specific gravity")
    sack_weight_lbs: float = Field(default=100.0, description="Sack weight (lbs)")


class ZFactorRequest(BaseModel):
    """Body for ``POST /well-control/z-factor``."""

    pressure: float = Field(default=5000, description="Pressure (psi)")
    temperature: float = Field(default=200, description="Temperature (F)")
    gas_gravity: float = Field(default=0.65, description="Gas gravity (air=1)")


class KickMigrationRequest(BaseModel):
    """Body for ``POST /calculate/well-control/kick-migration``."""

    well_depth_tvd: float = Field(default=10000, description="Well depth TVD (ft)")
    mud_weight: float = Field(default=10.0, description="Mud weight (ppg)")
    kick_volume_bbl: float = Field(default=20, description="Kick volume (bbl)")
    kick_gradient: float = Field(default=0.1, description="Kick gradient (psi/ft)")
    sidpp: float = Field(default=200, description="SIDPP (psi)")
    sicp: float = Field(default=350, description="SICP (psi)")
    annular_capacity_bbl_ft: float = Field(default=0.0459, description="Annular capacity (bbl/ft)")
    time_steps_min: int = Field(default=120, description="Simulation duration (min)")
    gas_gravity: float = Field(default=0.65, description="Gas gravity")
    migration_rate_ft_hr: float = Field(default=1000.0, description="Migration rate (ft/hr)")


class KillSimulationRequest(BaseModel):
    """Body for ``POST /calculate/well-control/kill-simulation``."""

    well_depth_tvd: float = Field(default=10000, description="Well depth TVD (ft)")
    mud_weight: float = Field(default=10.0, description="Mud weight (ppg)")
    kill_mud_weight: float = Field(default=11.0, description="Kill mud weight (ppg)")
    sidpp: float = Field(default=200, description="SIDPP (psi)")
    scr: float = Field(default=400, description="Slow circulating rate pressure (psi)")
    strokes_to_bit: int = Field(default=1000, description="Strokes surface to bit")
    strokes_bit_to_surface: int = Field(default=2000, description="Strokes bit to surface")
    method: str = Field(default="drillers", description="Kill method: drillers | wait_weight")
    step_size: int = Field(default=50, description="Step size (strokes)")


class KickMigrationMultiphaseRequest(BaseModel):
    """Body for ``POST /calculate/well-control/kick-migration-multiphase``."""

    well_depth_tvd: float = Field(default=10000, description="Well depth TVD (ft)")
    mud_weight: float = Field(default=10.0, description="Mud weight (ppg)")
    kick_volume_bbl: float = Field(default=20, description="Kick volume (bbl)")
    sidpp: float = Field(default=200, description="SIDPP (psi)")
    sicp: float = Field(default=350, description="SICP (psi)")
    annular_id_in: float = Field(default=8.681, description="Annular ID (in)")
    pipe_od_in: float = Field(default=5.0, description="Pipe OD (in)")
    gas_gravity: float = Field(default=0.65, description="Gas gravity")
    time_steps_min: int = Field(default=120, description="Simulation duration (min)")
    n_cells: int = Field(default=50, description="Number of cells in finite-volume mesh")
