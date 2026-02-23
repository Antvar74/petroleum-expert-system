"""
V&V: Petrophysics engine against Volve field dataset (Equinor).
Tests auto-skip if Volve LAS files are not present in data/volve/.

Reference: Equinor Volve Dataset (2018), Well 15/9-F-1
Hugin Formation (Upper Jurassic) — sandstone reservoir
"""
import os
import math
import pytest
from tests.validation.conftest import assert_within_range

# Path to Volve data directory
VOLVE_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "volve",
)

# Check for LAS file presence
VOLVE_LAS_FILES = [
    f for f in os.listdir(VOLVE_DATA_DIR) if f.lower().endswith(".las")
] if os.path.isdir(VOLVE_DATA_DIR) else []

HAS_VOLVE_DATA = len(VOLVE_LAS_FILES) > 0

# Published reference ranges from Equinor
VOLVE_REFERENCE = {
    "well": "15/9-F-1",
    "formation": "Hugin (Upper Jurassic)",
    "reservoir_interval_m": (3650, 3700),
    "porosity_range": (0.15, 0.30),  # 15-30%
    "sw_range": (0.10, 0.50),  # 10-50% in pay zones
    "rw": 0.04,  # Ohm·m at formation temperature
}


@pytest.mark.skipif(not HAS_VOLVE_DATA, reason="Volve LAS files not present in data/volve/")
class TestVolveValidation:
    """Validate petrophysics engine against Volve field data."""

    @pytest.fixture(autouse=True)
    def load_volve_data(self):
        """Load the first available Volve LAS file."""
        from orchestrator.petrophysics_engine import PetrophysicsEngine
        las_path = os.path.join(VOLVE_DATA_DIR, VOLVE_LAS_FILES[0])
        self.parsed = PetrophysicsEngine.parse_las_file(las_path)
        assert "data" in self.parsed, f"Failed to parse Volve LAS: {self.parsed.get('error')}"

    def test_las_parsed_successfully(self):
        """LAS file must parse without errors."""
        assert len(self.parsed["data"]) > 0
        assert "curves" in self.parsed

    def test_required_curves_present(self):
        """Must contain at least depth + one log curve."""
        curves = [c.lower() for c in self.parsed["curves"]]
        assert any(c in curves for c in ["dept", "depth", "md"]), \
            f"No depth curve found in {curves}"

    def test_porosity_within_published_range(self):
        """Computed porosity should fall within Equinor's published range."""
        from orchestrator.petrophysics_engine import PetrophysicsEngine
        # Run full evaluation on parsed data
        data = self.parsed["data"]
        if not any("rhob" in d for d in data):
            pytest.skip("No RHOB curve for porosity calculation")

        result = PetrophysicsEngine.run_full_evaluation(
            log_data=data,
            archie_params={"a": 1.0, "m": 2.0, "n": 2.0, "rw": VOLVE_REFERENCE["rw"]},
            matrix_params={"rho_matrix": 2.65, "rho_fluid": 1.0, "gr_clean": 20, "gr_shale": 120},
            cutoffs={"phi_min": 0.08, "sw_max": 0.60, "vsh_max": 0.40},
        )

        if result["summary"]["total_points"] > 0 and result["summary"]["avg_phi_pay"] > 0:
            phi_avg = result["summary"]["avg_phi_pay"]
            ref = VOLVE_REFERENCE["porosity_range"]
            assert_within_range(
                phi_avg, ref[0], ref[1],
                label=f"Volve avg porosity ({phi_avg:.3f})",
            )

    def test_sw_within_published_range(self):
        """Computed Sw should fall within Equinor's published range."""
        from orchestrator.petrophysics_engine import PetrophysicsEngine
        data = self.parsed["data"]
        if not all(any(k in d for d in data) for k in ["rhob", "rt"]):
            pytest.skip("Missing curves for Sw calculation")

        result = PetrophysicsEngine.run_full_evaluation(
            log_data=data,
            archie_params={"a": 1.0, "m": 2.0, "n": 2.0, "rw": VOLVE_REFERENCE["rw"]},
            matrix_params={"rho_matrix": 2.65, "rho_fluid": 1.0, "gr_clean": 20, "gr_shale": 120},
            cutoffs={"phi_min": 0.08, "sw_max": 0.60, "vsh_max": 0.40},
        )

        if result["summary"]["total_points"] > 0 and result["summary"]["avg_sw_pay"] > 0:
            sw_avg = result["summary"]["avg_sw_pay"]
            ref = VOLVE_REFERENCE["sw_range"]
            assert_within_range(
                sw_avg, ref[0], ref[1],
                label=f"Volve avg Sw ({sw_avg:.3f})",
            )


@pytest.mark.skipif(HAS_VOLVE_DATA, reason="Only runs when Volve data is NOT present")
class TestVolveDataNotPresent:
    """Verify graceful handling when Volve data is not available."""

    def test_skip_message(self):
        """Confirm that absence of data is properly detected."""
        assert not HAS_VOLVE_DATA
        # This test documents that the V&V framework handles missing data gracefully
