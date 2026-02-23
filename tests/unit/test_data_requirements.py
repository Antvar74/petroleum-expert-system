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
