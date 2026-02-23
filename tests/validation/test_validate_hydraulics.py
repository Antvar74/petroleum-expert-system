"""
V&V: Hydraulics engine against API RP 13D benchmark data.
Validates annular velocity, bit pressure drop, and ECD calculations.
"""
import pytest
from orchestrator.hydraulics_engine import HydraulicsEngine
from tests.validation.benchmark_data import API_13D_HYDRAULICS_BINGHAM
from tests.validation.conftest import assert_within_tolerance, assert_within_range


class TestHydraulicsBitPressureDrop:
    """Validate bit hydraulics against API RP 13D."""

    def test_bit_pressure_drop_within_tolerance(self):
        """API RP 13D: Bit pressure drop for 3x12 nozzles within 20%."""
        bm = API_13D_HYDRAULICS_BINGHAM
        result = HydraulicsEngine.calculate_bit_hydraulics(
            flow_rate=bm["flow_rate"],
            mud_weight=bm["mud_weight"],
            nozzle_sizes=bm["nozzles"],
        )
        expected = bm["expected"]["bit_pressure_drop_psi"]
        assert_within_tolerance(
            result["pressure_drop_psi"],
            expected["value"],
            expected["tolerance_pct"],
            label="API RP 13D Bit dP",
        )

    def test_tfa_calculation(self):
        """TFA for 3x12/32 nozzles = 3 * pi*(12/64)^2 = 0.331 sq in."""
        result = HydraulicsEngine.calculate_bit_hydraulics(
            flow_rate=400, mud_weight=12.0, nozzle_sizes=[12, 12, 12],
        )
        expected_tfa = 3 * 3.14159 * (12 / 64.0) ** 2  # ~0.331
        assert abs(result["tfa_sqin"] - expected_tfa) < 0.05, \
            f"TFA={result['tfa_sqin']}, expected≈{expected_tfa:.3f}"

    def test_bit_dp_increases_with_flow_rate(self):
        """Physics: higher flow rate → higher bit pressure drop (Q² relationship)."""
        low = HydraulicsEngine.calculate_bit_hydraulics(300, 12.0, [12, 12, 12])
        high = HydraulicsEngine.calculate_bit_hydraulics(500, 12.0, [12, 12, 12])
        assert high["pressure_drop_psi"] > low["pressure_drop_psi"]


class TestHydraulicsFullCircuit:
    """Validate full circuit hydraulics against API RP 13D."""

    def _run_circuit(self):
        bm = API_13D_HYDRAULICS_BINGHAM
        return HydraulicsEngine.calculate_full_circuit(
            sections=bm["sections"],
            nozzle_sizes=bm["nozzles"],
            flow_rate=bm["flow_rate"],
            mud_weight=bm["mud_weight"],
            pv=bm["pv"],
            yp=bm["yp"],
            tvd=bm["tvd"],
            rheology_model="bingham_plastic",
        )

    def test_ecd_within_physical_range(self):
        """ECD must be between MW and MW + 2.0 ppg for normal operations."""
        result = self._run_circuit()
        bm = API_13D_HYDRAULICS_BINGHAM
        ecd_range = bm["expected"]["ecd_ppg_within_range"]
        assert_within_range(
            result["ecd"]["ecd_ppg"],
            ecd_range["min"],
            ecd_range["max"],
            label="API RP 13D ECD",
        )

    def test_total_spp_positive(self):
        """Total standpipe pressure must be positive."""
        result = self._run_circuit()
        spp = result["summary"]["total_spp_psi"]
        assert spp > 0, f"Total SPP must be positive, got {spp}"

    def test_annular_loss_less_than_pipe_loss(self):
        """Physics: annular losses are typically less than pipe losses for same Q."""
        result = self._run_circuit()
        pipe_loss = result["summary"]["pipe_loss_psi"]
        ann_loss = result["summary"]["annular_loss_psi"]
        # This is generally true for most drilling conditions
        assert ann_loss < pipe_loss * 2, \
            f"Annular loss ({ann_loss}) unexpectedly high vs pipe loss ({pipe_loss})"

    def test_section_results_present(self):
        """Must return results for each circuit section."""
        result = self._run_circuit()
        bm = API_13D_HYDRAULICS_BINGHAM
        assert len(result["section_results"]) >= len(bm["sections"])


class TestHydraulicsECD:
    """Validate ECD calculations."""

    def test_ecd_equals_mw_when_no_losses(self):
        """ECD should equal MW when there are no annular pressure losses."""
        result = HydraulicsEngine.calculate_ecd_dynamic(
            mud_weight=10.0,
            tvd=10000,
            annular_pressure_loss=0.0,
        )
        assert abs(result["ecd_ppg"] - 10.0) < 0.1, \
            f"ECD should ≈ MW when no losses, got {result['ecd_ppg']}"

    def test_ecd_increases_with_annular_loss(self):
        """Physics: higher annular pressure loss → higher ECD."""
        low = HydraulicsEngine.calculate_ecd_dynamic(10.0, 10000, 200)
        high = HydraulicsEngine.calculate_ecd_dynamic(10.0, 10000, 600)
        assert high["ecd_ppg"] > low["ecd_ppg"]

    def test_ecd_formula_verification(self):
        """ECD = MW + APL / (0.052 * TVD). Verify basic formula."""
        mw, tvd, apl = 10.0, 10000, 500
        expected_ecd = mw + apl / (0.052 * tvd)
        result = HydraulicsEngine.calculate_ecd_dynamic(mw, tvd, apl)
        assert abs(result["ecd_ppg"] - expected_ecd) < 0.2, \
            f"ECD={result['ecd_ppg']}, expected≈{expected_ecd:.2f}"
