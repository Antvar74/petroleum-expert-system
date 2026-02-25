"""
Pydantic request schemas for well and problem routes.
"""

from __future__ import annotations

from typing import Any, Dict

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CreateProblemRequest(BaseModel):
    """Body for ``POST /wells/{well_id}/problems``."""

    model_config = ConfigDict(extra="ignore")

    depth_md: float = Field(..., description="Measured depth (ft)")
    depth_tvd: float = Field(..., description="True vertical depth (ft)")
    description: str = Field(..., min_length=1, description="Problem description")
    operation: str = Field(..., min_length=1, description="Current operation type")
    formation: str | None = Field(default=None, description="Formation name")
    mud_weight: float | None = Field(default=None, description="Mud weight (ppg)")
    inclination: float | None = Field(default=None, description="Wellbore inclination (deg)")
    azimuth: float | None = Field(default=None, description="Wellbore azimuth (deg)")
    torque: float | None = Field(default=None, description="Torque (klb-ft)")
    drag: float | None = Field(default=None, description="Drag (lbs)")
    overpull: float | None = Field(default=None, description="Overpull (lbs)")
    string_weight: float | None = Field(default=None, description="String weight (lbs)")
    additional_data: Dict[str, Any] = Field(default_factory=dict, description="Extra contextual data")

    @model_validator(mode="before")
    @classmethod
    def normalise_aliases(cls, values: Any) -> Any:  # noqa: N805
        """Accept both canonical and suffixed field names (e.g. mud_weight_ppg → mud_weight)."""
        if not isinstance(values, dict):
            return values

        # operation alias
        if "operation" not in values and "operation_type" in values:
            values["operation"] = values.pop("operation_type")

        # Numeric field aliases — suffixed versions take priority
        alias_map = {
            "mud_weight": "mud_weight_ppg",
            "inclination": "inclination_deg",
            "azimuth": "azimuth_deg",
            "torque": "torque_klbft",
            "drag": "drag_lbs",
            "overpull": "overpull_lbs",
            "string_weight": "string_weight_lbs",
        }
        for canonical, alt in alias_map.items():
            if alt in values:
                values[canonical] = values.pop(alt)

        return values
