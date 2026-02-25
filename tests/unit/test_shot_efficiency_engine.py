"""
Unit tests for ShotEfficiencyEngine.

Covers: parse_log_data, calculate_porosity, calculate_water_saturation,
        calculate_vshale, identify_net_pay_intervals, calculate_skin_factor,
        rank_intervals, calculate_full_shot_efficiency.
"""
import math
import pytest
from orchestrator.shot_efficiency_engine import ShotEfficiencyEngine


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def engine():
    return ShotEfficiencyEngine()


@pytest.fixture
def valid_log_entry():
    """Single valid log entry with mid-range values."""
    return {"md": 5000.0, "gr": 45.0, "rhob": 2.35, "nphi": 0.18, "rt": 20.0}


@pytest.fixture
def valid_log_entries():
    """Several valid entries spanning a depth interval suitable for net-pay."""
    base = []
    for i in range(10):
        base.append({
            "md": 5000.0 + i * 0.5,
            "gr": 30.0 + i,
            "rhob": 2.30,
            "nphi": 0.20,
            "rt": 50.0,
        })
    return base


@pytest.fixture
def mixed_log_entries():
    """Mix of valid and out-of-range entries."""
    return [
        {"md": 5000, "gr": 40, "rhob": 2.30, "nphi": 0.15, "rt": 30},   # valid
        {"md": 5001, "gr": 400, "rhob": 2.30, "nphi": 0.15, "rt": 30},  # gr > 300
        {"md": 5002, "gr": 40, "rhob": 0.50, "nphi": 0.15, "rt": 30},   # rhob < 1.5
        {"md": 5003, "gr": 40, "rhob": 2.30, "nphi": 0.70, "rt": 30},   # nphi > 0.65
        {"md": 5004, "gr": 40, "rhob": 2.30, "nphi": 0.15, "rt": 200000},  # rt > 100000
        {"md": 5005, "gr": 40, "rhob": 2.30, "nphi": 0.15, "rt": 30},   # valid
    ]


@pytest.fixture
def net_pay_log_data():
    """Pre-processed log data for net-pay identification (phi, sw, vsh already computed)."""
    data = []
    # Interval 1: md 5000-5002 (5 points, 2.0 ft), good reservoir
    for i in range(5):
        data.append({"md": 5000.0 + i * 0.5, "phi": 0.18, "sw": 0.30, "vsh": 0.10})
    # Shale barrier at 5002.5
    data.append({"md": 5002.5, "phi": 0.03, "sw": 0.90, "vsh": 0.80})
    # Interval 2: md 5003-5006 (7 points, 3.0 ft), good reservoir
    for i in range(7):
        data.append({"md": 5003.0 + i * 0.5, "phi": 0.22, "sw": 0.25, "vsh": 0.08})
    return data


@pytest.fixture
def sample_intervals():
    """Intervals ready for ranking."""
    return [
        {"avg_phi": 0.20, "avg_sw": 0.30, "thickness_ft": 4.0, "skin_total": 1.5},
        {"avg_phi": 0.15, "avg_sw": 0.50, "thickness_ft": 6.0, "skin_total": 3.0},
        {"avg_phi": 0.25, "avg_sw": 0.25, "thickness_ft": 3.0, "skin_total": 0.5},
    ]


# ===========================================================================
# parse_log_data
# ===========================================================================

class TestParseLogData:
    def test_accepts_valid_entries(self, engine, valid_log_entries):
        result = engine.parse_log_data(valid_log_entries)
        assert result["accepted_count"] == len(valid_log_entries)
        assert result["rejected_count"] == 0

    def test_rejects_out_of_range_gr(self, engine):
        entries = [{"md": 100, "gr": 350, "rhob": 2.3, "nphi": 0.2, "rt": 10}]
        result = engine.parse_log_data(entries)
        assert result["accepted_count"] == 0
        assert result["rejected_count"] == 1

    def test_rejects_out_of_range_rhob(self, engine):
        entries = [{"md": 100, "gr": 50, "rhob": 3.5, "nphi": 0.2, "rt": 10}]
        result = engine.parse_log_data(entries)
        assert result["rejected_count"] == 1

    def test_rejects_out_of_range_nphi(self, engine):
        entries = [{"md": 100, "gr": 50, "rhob": 2.3, "nphi": 0.70, "rt": 10}]
        result = engine.parse_log_data(entries)
        assert result["rejected_count"] == 1

    def test_rejects_out_of_range_rt(self, engine):
        entries = [{"md": 100, "gr": 50, "rhob": 2.3, "nphi": 0.2, "rt": 200000}]
        result = engine.parse_log_data(entries)
        assert result["rejected_count"] == 1

    def test_sorts_by_depth(self, engine):
        entries = [
            {"md": 5010, "gr": 30, "rhob": 2.3, "nphi": 0.15, "rt": 20},
            {"md": 5000, "gr": 30, "rhob": 2.3, "nphi": 0.15, "rt": 20},
            {"md": 5005, "gr": 30, "rhob": 2.3, "nphi": 0.15, "rt": 20},
        ]
        result = engine.parse_log_data(entries)
        depths = [p["md"] for p in result["accepted"]]
        assert depths == sorted(depths)

    def test_handles_empty_list(self, engine):
        result = engine.parse_log_data([])
        assert "error" in result
        assert result["accepted"] == []
        assert result["rejected_count"] == 0

    def test_mixed_valid_and_invalid(self, engine, mixed_log_entries):
        result = engine.parse_log_data(mixed_log_entries)
        assert result["accepted_count"] == 2
        assert result["rejected_count"] == 4

    def test_depth_range_computed(self, engine, valid_log_entries):
        result = engine.parse_log_data(valid_log_entries)
        assert result["depth_range"]["min_md"] == 5000.0
        assert result["depth_range"]["max_md"] == pytest.approx(5004.5, abs=0.1)


# ===========================================================================
# calculate_porosity
# ===========================================================================

class TestCalculatePorosity:
    def test_rms_crossplot_formula(self, engine):
        """Verify the density-neutron RMS crossplot: phi = sqrt((phiD^2 + phiN^2)/2)."""
        rhob = 2.35
        nphi = 0.18
        rho_ma = 2.65
        rho_fl = 1.0
        phi_d = (rho_ma - rhob) / (rho_ma - rho_fl)
        expected = math.sqrt((phi_d ** 2 + nphi ** 2) / 2.0)

        result = engine.calculate_porosity(rhob, nphi, rho_ma, rho_fl)
        assert result["phi"] == pytest.approx(expected, abs=1e-4)
        assert result["phi_density"] == pytest.approx(phi_d, abs=1e-4)
        assert result["phi_neutron"] == pytest.approx(nphi, abs=1e-4)
        assert result["method"] == "density_neutron_rms_crossplot"

    def test_porosity_clamped_upper(self, engine):
        """Very low density should not exceed 0.5."""
        result = engine.calculate_porosity(rhob=1.50, nphi=0.60, rho_matrix=2.65, rho_fluid=1.0)
        assert result["phi"] <= 0.50

    def test_porosity_clamped_lower(self, engine):
        """Dense rock, negative phi_D, should not go below 0."""
        result = engine.calculate_porosity(rhob=3.10, nphi=0.0, rho_matrix=2.65, rho_fluid=1.0)
        assert result["phi"] >= 0.0

    def test_limestone_matrix(self, engine):
        """Limestone rho_matrix=2.71 gives different porosity than sandstone."""
        result_sand = engine.calculate_porosity(2.35, 0.18, 2.65, 1.0)
        result_lime = engine.calculate_porosity(2.35, 0.18, 2.71, 1.0)
        assert result_lime["phi"] != result_sand["phi"]
        # Limestone has higher matrix density => higher phi_D => higher phi
        assert result_lime["phi"] > result_sand["phi"]

    def test_equal_matrix_fluid_returns_error(self, engine):
        result = engine.calculate_porosity(2.0, 0.2, rho_matrix=1.0, rho_fluid=1.0)
        assert "error" in result


# ===========================================================================
# calculate_water_saturation
# ===========================================================================

class TestCalculateWaterSaturation:
    def test_archie_equation(self, engine):
        """Manually verify Archie: Sw = ((a*Rw)/(Rt*phi^m))^(1/n)."""
        rt, phi, rw, a, m, n = 50.0, 0.20, 0.05, 1.0, 2.0, 2.0
        expected_sw = ((a * rw) / (rt * phi ** m)) ** (1.0 / n)

        result = engine.calculate_water_saturation(rt, phi, rw, a, m, n)
        assert result["sw"] == pytest.approx(expected_sw, abs=1e-4)
        assert result["hydrocarbon_saturation"] == pytest.approx(1.0 - expected_sw, abs=1e-4)

    def test_sw_clamped_to_one(self, engine):
        """Very low Rt should yield Sw capped at 1.0."""
        result = engine.calculate_water_saturation(rt=0.5, porosity=0.05, rw=0.10)
        assert result["sw"] <= 1.0

    def test_sw_clamped_to_zero(self, engine):
        """Extremely high Rt should give very small Sw, but never negative."""
        result = engine.calculate_water_saturation(rt=100000, porosity=0.30, rw=0.01)
        assert result["sw"] >= 0.0

    def test_water_classification(self, engine):
        """Sw > 0.80 should classify as Water."""
        result = engine.calculate_water_saturation(rt=2.0, porosity=0.10, rw=0.10)
        assert result["sw"] > 0.80
        assert result["classification"] == "Water"

    def test_hydrocarbon_classification(self, engine):
        """Low Sw should classify as Hydrocarbon."""
        result = engine.calculate_water_saturation(rt=200.0, porosity=0.25, rw=0.02)
        assert result["sw"] < 0.40
        assert "Hydrocarbon" in result["classification"]

    def test_zero_porosity_returns_non_reservoir(self, engine):
        result = engine.calculate_water_saturation(rt=50.0, porosity=0.0)
        assert result["sw"] == 1.0
        assert result["classification"] == "Non-reservoir"

    def test_zero_rt_returns_non_reservoir(self, engine):
        result = engine.calculate_water_saturation(rt=0.0, porosity=0.20)
        assert result["sw"] == 1.0
        assert result["classification"] == "Non-reservoir"


# ===========================================================================
# calculate_vshale
# ===========================================================================

class TestCalculateVshale:
    def test_linear_method(self, engine):
        """Linear IGR = (GR - GR_clean) / (GR_shale - GR_clean)."""
        gr, gr_clean, gr_shale = 70.0, 20.0, 120.0
        expected_igr = (70 - 20) / (120 - 20)
        result = engine.calculate_vshale(gr, gr_clean, gr_shale, method="linear")
        assert result["vsh"] == pytest.approx(expected_igr, abs=1e-4)
        assert result["igr"] == pytest.approx(expected_igr, abs=1e-4)
        assert result["method"] == "linear"

    def test_larionov_tertiary(self, engine):
        """Larionov: Vsh = 0.083 * (2^(3.7*IGR) - 1), should be less than linear IGR."""
        gr, gr_clean, gr_shale = 70.0, 20.0, 120.0
        igr = (70 - 20) / (120 - 20)
        expected_vsh = 0.083 * (2.0 ** (3.7 * igr) - 1.0)
        result = engine.calculate_vshale(gr, gr_clean, gr_shale, method="larionov_tertiary")
        assert result["vsh"] == pytest.approx(expected_vsh, abs=1e-4)
        # Larionov correction is always <= linear IGR for IGR in [0, 1]
        assert result["vsh"] <= igr + 1e-6

    def test_vsh_clamped_to_zero(self, engine):
        """GR below clean line should give Vsh = 0."""
        result = engine.calculate_vshale(10.0, gr_clean=20.0, gr_shale=120.0, method="linear")
        assert result["vsh"] == 0.0
        assert result["igr"] == 0.0

    def test_vsh_clamped_to_one(self, engine):
        """GR above shale line should give Vsh clamped to 1.0."""
        result = engine.calculate_vshale(200.0, gr_clean=20.0, gr_shale=120.0, method="linear")
        assert result["vsh"] == 1.0
        assert result["igr"] == 1.0

    def test_error_when_gr_shale_le_gr_clean(self, engine):
        result = engine.calculate_vshale(50, gr_clean=100, gr_shale=50)
        assert "error" in result


# ===========================================================================
# identify_net_pay_intervals
# ===========================================================================

class TestIdentifyNetPayIntervals:
    def test_contiguous_grouping(self, engine, net_pay_log_data):
        result = engine.identify_net_pay_intervals(net_pay_log_data)
        assert result["interval_count"] == 2
        assert len(result["intervals"]) == 2

    def test_min_thickness_filter(self, engine):
        """Single thin point (< min_thickness) should be discarded."""
        data = [
            {"md": 5000, "phi": 0.20, "sw": 0.30, "vsh": 0.10},
            {"md": 5000.5, "phi": 0.20, "sw": 0.30, "vsh": 0.10},
            # only 0.5 ft span => below default 2.0 ft cutoff
        ]
        result = engine.identify_net_pay_intervals(data, min_thickness_ft=2.0)
        assert result["interval_count"] == 0

    def test_cutoff_rejects_shaly_points(self, engine):
        """High Vsh points should not be net pay."""
        data = [
            {"md": 5000 + i, "phi": 0.20, "sw": 0.30, "vsh": 0.80}
            for i in range(5)
        ]
        result = engine.identify_net_pay_intervals(data)
        assert result["interval_count"] == 0

    def test_empty_data(self, engine):
        result = engine.identify_net_pay_intervals([])
        assert result["intervals"] == []
        assert result["total_net_pay_ft"] == 0.0

    def test_total_net_pay_accumulation(self, engine, net_pay_log_data):
        result = engine.identify_net_pay_intervals(net_pay_log_data)
        total = sum(iv["thickness_ft"] for iv in result["intervals"])
        assert result["total_net_pay_ft"] == pytest.approx(total, abs=0.1)


# ===========================================================================
# calculate_skin_factor
# ===========================================================================

class TestCalculateSkinFactor:
    def test_karakas_tariq_components_present(self, engine):
        result = engine.calculate_skin_factor(
            perf_length_in=12.0, perf_radius_in=0.20,
            wellbore_radius_ft=0.354, spf=4, phasing_deg=90,
            h_perf_ft=5.0, kv_kh=0.5,
        )
        assert "s_p" in result
        assert "s_v" in result
        assert "s_wb" in result
        assert "s_total" in result
        assert result["s_total"] == pytest.approx(
            result["s_p"] + result["s_v"] + result["s_wb"], abs=1e-4
        )

    def test_different_phasings_differ(self, engine):
        """Different phasing angles should produce different skin values."""
        results = {}
        for deg in [0, 60, 90, 120, 180]:
            r = engine.calculate_skin_factor(
                perf_length_in=12.0, perf_radius_in=0.20,
                wellbore_radius_ft=0.354, spf=4, phasing_deg=deg,
                h_perf_ft=5.0, kv_kh=0.5,
            )
            results[deg] = r["s_total"]
        # Not all phasing skins should be identical
        unique_skins = set(results.values())
        assert len(unique_skins) > 1

    def test_longer_perforation_reduces_sp(self, engine):
        """Longer perf tunnel should reduce plane-flow pseudo-skin (more negative or smaller)."""
        short = engine.calculate_skin_factor(
            perf_length_in=6.0, perf_radius_in=0.20,
            wellbore_radius_ft=0.354, spf=4, phasing_deg=90,
            h_perf_ft=5.0,
        )
        long_ = engine.calculate_skin_factor(
            perf_length_in=18.0, perf_radius_in=0.20,
            wellbore_radius_ft=0.354, spf=4, phasing_deg=90,
            h_perf_ft=5.0,
        )
        # With a longer tunnel, s_p should be more negative (or at least not greater)
        assert long_["s_p"] <= short["s_p"]

    def test_s_v_nonzero(self, engine):
        """S_v should be non-zero with corrected K-T h_D^B exponent (SPE 18247)."""
        result = engine.calculate_skin_factor(
            perf_length_in=12.0, perf_radius_in=0.20,
            wellbore_radius_ft=0.354, spf=4, phasing_deg=90,
            h_perf_ft=30.0, kv_kh=0.5,
        )
        assert result["s_v"] > 0.0, "S_v must be non-zero with corrected K-T formula"

    def test_s_v_varies_with_spf(self, engine):
        """S_v should change when SPF changes (different vertical convergence)."""
        base_kw = dict(perf_length_in=12.0, perf_radius_in=0.20,
                       wellbore_radius_ft=0.354, phasing_deg=90,
                       h_perf_ft=30.0, kv_kh=0.5)
        r1 = engine.calculate_skin_factor(spf=1, **base_kw)
        r4 = engine.calculate_skin_factor(spf=4, **base_kw)
        r12 = engine.calculate_skin_factor(spf=12, **base_kw)
        assert r1["s_v"] != r4["s_v"]
        assert r4["s_v"] != r12["s_v"]

    def test_s_wb_nonzero(self, engine):
        """S_wb should be non-zero for standard perforation geometry."""
        result = engine.calculate_skin_factor(
            perf_length_in=12.0, perf_radius_in=0.20,
            wellbore_radius_ft=0.354, spf=4, phasing_deg=90,
            h_perf_ft=30.0, kv_kh=0.5,
        )
        assert result["s_wb"] > 0.0, "S_wb must be non-zero"

    def test_s_wb_uses_dimensionless_wellbore_radius(self, engine):
        """S_wb must use r_wD = r_w / (r_w + l_p) per SPE 18247, not r_p / r_w."""
        result = engine.calculate_skin_factor(
            perf_length_in=12.0, perf_radius_in=0.20,
            wellbore_radius_ft=0.354, spf=4, phasing_deg=90,
            h_perf_ft=5.0, kv_kh=0.5,
        )
        # r_wD = 0.354 / (0.354 + 1.0) = 0.2615
        # S_wb = 0.0066 * exp(5.320 * 0.2615) ≈ 0.0265
        assert result["s_wb"] > 0.02, (
            f"S_wb={result['s_wb']} is too small; "
            f"should use r_wD=r_w/(r_w+l_p) per SPE 18247"
        )
        assert result["s_wb"] < 0.10, "S_wb should be small for standard geometry"


# ===========================================================================
# rank_intervals
# ===========================================================================

class TestRankIntervals:
    def test_weighted_composite_score(self, engine, sample_intervals):
        result = engine.rank_intervals(sample_intervals)
        ranked = result["ranked"]
        assert len(ranked) == 3
        # All entries should have a 'score' and 'rank' key
        for item in ranked:
            assert "score" in item
            assert "rank" in item

    def test_best_has_highest_score(self, engine, sample_intervals):
        result = engine.rank_intervals(sample_intervals)
        best = result["best"]
        for item in result["ranked"]:
            assert best["score"] >= item["score"]

    def test_single_interval(self, engine):
        """A single interval should still rank as #1 with a valid score."""
        intervals = [{"avg_phi": 0.20, "avg_sw": 0.30, "thickness_ft": 5.0, "skin_total": 1.0}]
        result = engine.rank_intervals(intervals)
        assert result["best"]["rank"] == 1
        # With a single interval, all normalized values become 1.0
        assert result["best"]["score"] > 0

    def test_empty_intervals(self, engine):
        result = engine.rank_intervals([])
        assert result["ranked"] == []
        assert result["best"] is None

    def test_custom_weights(self, engine, sample_intervals):
        """Custom weights should produce different ordering when exaggerated."""
        # Weight heavily toward thickness only
        heavy_thick = {"phi": 0.0, "sw": 0.0, "thickness": 1.0, "skin": 0.0}
        result = engine.rank_intervals(sample_intervals, weights=heavy_thick)
        # Interval with thickness 6.0 should be best
        assert result["best"]["thickness_ft"] == 6.0


# ===========================================================================
# calculate_full_shot_efficiency (end-to-end pipeline)
# ===========================================================================

class TestFullShotEfficiency:
    @pytest.fixture
    def full_pipeline_entries(self):
        """Log entries that form one clear reservoir interval and one shale break."""
        entries = []
        # Good reservoir: depths 5000-5005 (11 points at 0.5 ft)
        for i in range(11):
            entries.append({
                "md": 5000.0 + i * 0.5,
                "gr": 25.0,
                "rhob": 2.25,
                "nphi": 0.22,
                "rt": 80.0,
            })
        # Shale break at 5005.5
        entries.append({"md": 5005.5, "gr": 110.0, "rhob": 2.55, "nphi": 0.35, "rt": 3.0})
        # Marginal zone: 5006-5007 (3 points)
        for i in range(3):
            entries.append({
                "md": 5006.0 + i * 0.5,
                "gr": 50.0,
                "rhob": 2.40,
                "nphi": 0.15,
                "rt": 25.0,
            })
        return entries

    def test_end_to_end_returns_summary(self, engine, full_pipeline_entries):
        result = engine.calculate_full_shot_efficiency(full_pipeline_entries)
        assert "summary" in result
        assert "processed_logs" in result
        assert "net_pay" in result
        assert "rankings" in result
        assert "alerts" in result

    def test_summary_fields_present(self, engine, full_pipeline_entries):
        result = engine.calculate_full_shot_efficiency(full_pipeline_entries)
        summary = result["summary"]
        for key in [
            "total_log_points", "rejected_points", "avg_porosity",
            "avg_sw", "avg_vsh", "net_pay_intervals_count",
            "total_net_pay_ft", "perf_config",
        ]:
            assert key in summary, f"Missing summary key: {key}"

    def test_alerts_on_rejected_points(self, engine, mixed_log_entries):
        """Pipeline should generate alert when points are rejected."""
        result = engine.calculate_full_shot_efficiency(mixed_log_entries)
        alert_text = " ".join(result["alerts"])
        assert "rejected" in alert_text.lower()

    def test_empty_input_returns_error_alert(self, engine):
        result = engine.calculate_full_shot_efficiency([])
        assert len(result["alerts"]) > 0

    def test_parameters_echo_back(self, engine, full_pipeline_entries):
        """Returned parameters should reflect input or defaults."""
        result = engine.calculate_full_shot_efficiency(
            full_pipeline_entries,
            archie_params={"rw": 0.03, "m": 1.8},
        )
        assert result["parameters"]["archie"]["rw"] == 0.03
        assert result["parameters"]["archie"]["m"] == 1.8
        # Default a should still be 1.0
        assert result["parameters"]["archie"]["a"] == 1.0
