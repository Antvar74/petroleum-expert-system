"""
Volumetric Cycles Normalization Tests.

The VolumetricCyclesChart component normalizes engine field names:
  - Engine: max_pressure, volume_bled
  - Chart: max_pressure_psi, volume_bled_bbl, cumulative_volume_bbl

This test module replicates the TypeScript normalization logic in Python
and verifies it works correctly with real engine output.
"""
import pytest
from orchestrator.well_control_engine import WellControlEngine


# ============================================================
# Python replica of the TypeScript normalization logic
# from VolumetricCyclesChart.tsx (lines 44-53)
# ============================================================

def normalize_cycles(raw_cycles):
    """
    Replicate frontend normalization:

    const cycles = rawCycles.map(c => {
      const vol = c.volume_bled_bbl ?? c.volume_bled ?? 0;
      cumulative += vol;
      return {
        cycle: c.cycle,
        max_pressure_psi: c.max_pressure_psi ?? c.max_pressure ?? 0,
        volume_bled_bbl: vol,
        cumulative_volume_bbl: c.cumulative_volume_bbl ?? round(cumulative * 100) / 100,
      };
    });
    """
    if not raw_cycles:
        return []

    cumulative = 0.0
    result = []
    for c in raw_cycles:
        vol = c.get("volume_bled_bbl") if c.get("volume_bled_bbl") is not None else (c.get("volume_bled") or 0)
        cumulative += vol
        result.append({
            "cycle": c.get("cycle", 0),
            "max_pressure_psi": c.get("max_pressure_psi") if c.get("max_pressure_psi") is not None else (c.get("max_pressure") or 0),
            "volume_bled_bbl": vol,
            "cumulative_volume_bbl": c.get("cumulative_volume_bbl") if c.get("cumulative_volume_bbl") is not None else round(cumulative * 100) / 100,
        })
    return result


# ============================================================
# Tests
# ============================================================

class TestVolumetricNormalization:

    def test_engine_fields_map_correctly(self):
        """Engine's max_pressure and volume_bled map to _psi and _bbl respectively."""
        raw = [
            {"cycle": 1, "max_pressure": 300, "volume_bled": 5.0},
            {"cycle": 2, "max_pressure": 400, "volume_bled": 5.0},
        ]
        normalized = normalize_cycles(raw)
        assert normalized[0]["max_pressure_psi"] == 300
        assert normalized[0]["volume_bled_bbl"] == 5.0
        assert normalized[1]["max_pressure_psi"] == 400
        assert normalized[1]["volume_bled_bbl"] == 5.0

    def test_alternative_field_names_map(self):
        """If input already has _psi/_bbl suffixed names, use those directly."""
        raw = [
            {"cycle": 1, "max_pressure_psi": 350, "volume_bled_bbl": 4.5},
        ]
        normalized = normalize_cycles(raw)
        assert normalized[0]["max_pressure_psi"] == 350
        assert normalized[0]["volume_bled_bbl"] == 4.5

    def test_fallback_uses_engine_names(self):
        """When max_pressure_psi is None but max_pressure exists, use max_pressure."""
        raw = [
            {"cycle": 1, "max_pressure_psi": None, "max_pressure": 250, "volume_bled": 3.0},
        ]
        normalized = normalize_cycles(raw)
        assert normalized[0]["max_pressure_psi"] == 250

    def test_cumulative_volume_computed(self):
        """When cumulative_volume_bbl not in input, compute as running sum."""
        raw = [
            {"cycle": 1, "max_pressure": 300, "volume_bled": 5.0},
            {"cycle": 2, "max_pressure": 350, "volume_bled": 5.0},
            {"cycle": 3, "max_pressure": 400, "volume_bled": 5.0},
        ]
        normalized = normalize_cycles(raw)
        assert normalized[0]["cumulative_volume_bbl"] == 5.0
        assert normalized[1]["cumulative_volume_bbl"] == 10.0
        assert normalized[2]["cumulative_volume_bbl"] == 15.0

    def test_cumulative_volume_passed_through(self):
        """When cumulative_volume_bbl already exists in input, use it directly."""
        raw = [
            {"cycle": 1, "max_pressure": 300, "volume_bled": 5.0, "cumulative_volume_bbl": 99.9},
        ]
        normalized = normalize_cycles(raw)
        assert normalized[0]["cumulative_volume_bbl"] == 99.9

    def test_empty_cycles_returns_empty(self):
        """Empty input should return empty output without errors."""
        assert normalize_cycles([]) == []
        assert normalize_cycles(None) == []

    def test_missing_fields_default_zero(self):
        """If max_pressure and volume_bled are both missing, default to 0."""
        raw = [{"cycle": 1}]
        normalized = normalize_cycles(raw)
        assert normalized[0]["max_pressure_psi"] == 0
        assert normalized[0]["volume_bled_bbl"] == 0
        assert normalized[0]["cumulative_volume_bbl"] == 0

    def test_real_engine_output_normalizes(self):
        """Run actual WellControlEngine.calculate_volumetric() and normalize its cycles."""
        result = WellControlEngine.calculate_volumetric(
            mud_weight=10, sicp=200, tvd=10000,
            annular_capacity=0.05, lot_emw=14.0, casing_shoe_tvd=5000
        )
        raw_cycles = result["cycles"]
        assert len(raw_cycles) > 0, "Engine should produce at least 1 cycle"

        # Normalize
        normalized = normalize_cycles(raw_cycles)
        assert len(normalized) == len(raw_cycles)

        # Every normalized cycle must have all 4 fields with correct types
        for nc in normalized:
            assert isinstance(nc["cycle"], int)
            assert isinstance(nc["max_pressure_psi"], (int, float))
            assert isinstance(nc["volume_bled_bbl"], (int, float))
            assert isinstance(nc["cumulative_volume_bbl"], (int, float))

        # Cumulative should be monotonically non-decreasing
        for i in range(1, len(normalized)):
            assert normalized[i]["cumulative_volume_bbl"] >= normalized[i - 1]["cumulative_volume_bbl"]

    def test_mixed_field_names_priority(self):
        """When both max_pressure and max_pressure_psi exist, _psi takes priority (JS ?? operator)."""
        raw = [
            {"cycle": 1, "max_pressure_psi": 500, "max_pressure": 300, "volume_bled_bbl": 4.0, "volume_bled": 3.0},
        ]
        normalized = normalize_cycles(raw)
        # In JS: c.max_pressure_psi ?? c.max_pressure → 500 (since 500 is not null/undefined)
        assert normalized[0]["max_pressure_psi"] == 500
        assert normalized[0]["volume_bled_bbl"] == 4.0
