"""
Unit tests for ModuleAnalysisEngine — language support, metric labels,
key metric extraction, problem builders, and response packaging.
"""
import pytest
from orchestrator.module_analysis_engine import ModuleAnalysisEngine, METRIC_LABELS


@pytest.fixture
def engine():
    return ModuleAnalysisEngine()


# ================================================================
# TestLanguagePrefix
# ================================================================

class TestLanguagePrefix:
    def test_english_returns_empty(self, engine):
        assert engine._get_language_prefix("en") == ""

    def test_spanish_returns_instruction(self, engine):
        assert "IMPORTANTE" in engine._get_language_prefix("es")

    def test_spanish_contains_latinoamericano(self, engine):
        assert "latinoamericano" in engine._get_language_prefix("es")

    def test_unknown_language_returns_empty(self, engine):
        assert engine._get_language_prefix("fr") == ""


# ================================================================
# TestInstructionBlock
# ================================================================

class TestInstructionBlock:
    def test_english_has_executive_summary(self, engine):
        block = engine._get_instruction_block("en")
        assert "EXECUTIVE SUMMARY" in block

    def test_english_has_five_sections(self, engine):
        block = engine._get_instruction_block("en")
        for section in ["EXECUTIVE SUMMARY", "KEY FINDINGS", "ALERTS AND RISKS",
                        "OPERATIONAL RECOMMENDATIONS", "MANAGERIAL CONCLUSION"]:
            assert section in block

    def test_spanish_has_resumen_ejecutivo(self, engine):
        block = engine._get_instruction_block("es")
        assert "RESUMEN EJECUTIVO" in block

    def test_spanish_has_five_sections(self, engine):
        block = engine._get_instruction_block("es")
        for section in ["RESUMEN EJECUTIVO", "HALLAZGOS CLAVE", "ALERTAS Y RIESGOS",
                        "RECOMENDACIONES OPERATIVAS", "CONCLUSIÓN GERENCIAL"]:
            assert section in block


# ================================================================
# TestMetricLabel
# ================================================================

class TestMetricLabel:
    def test_hookload_english(self, engine):
        assert engine._ml("Hookload", "en") == "Hookload"

    def test_hookload_spanish(self, engine):
        assert engine._ml("Hookload", "es") == "Carga en Gancho"

    def test_unknown_key_returns_key(self, engine):
        assert engine._ml("UnknownKey", "en") == "UnknownKey"

    def test_unknown_language_falls_back_to_english(self, engine):
        assert engine._ml("Hookload", "fr") == "Hookload"

    def test_kmw_spanish_is_pmm(self, engine):
        assert engine._ml("KMW", "es") == "PMM"


# ================================================================
# TestMetricLabelsStructure
# ================================================================

class TestMetricLabelsStructure:
    def test_both_languages_have_same_keys(self):
        assert set(METRIC_LABELS["en"].keys()) == set(METRIC_LABELS["es"].keys())

    def test_no_empty_values(self):
        for lang in ("en", "es"):
            for key, value in METRIC_LABELS[lang].items():
                assert value, f"Empty value for {lang}:{key}"

    def test_all_expected_keys_present(self):
        expected = {
            "Hookload", "Torque", "Max Side Force", "Buoyancy Factor",
            "ECD at TD", "Total SPP", "HSI", "% at Bit", "Surge Margin",
            "Mechanism", "Risk Level", "Risk Score", "Free Point",
            "Pf", "KMW", "ICP", "FCP", "MAASP", "Influx Type",
        }
        assert expected == set(METRIC_LABELS["en"].keys())


# ================================================================
# TestExtractKeyMetrics — Torque & Drag
# ================================================================

class TestExtractKeyMetricsTD:
    def test_returns_correct_count(self, engine, sample_td_result):
        metrics = engine._extract_key_metrics("torque_drag", sample_td_result, "en")
        assert len(metrics) == 4

    def test_english_labels(self, engine, sample_td_result):
        metrics = engine._extract_key_metrics("torque_drag", sample_td_result, "en")
        labels = [m["label"] for m in metrics]
        assert "Hookload" in labels
        assert "Torque" in labels
        assert "Max Side Force" in labels

    def test_spanish_labels(self, engine, sample_td_result):
        metrics = engine._extract_key_metrics("torque_drag", sample_td_result, "es")
        labels = [m["label"] for m in metrics]
        assert "Carga en Gancho" in labels
        assert "Fuerza Lateral Máx" in labels


# ================================================================
# TestExtractKeyMetrics — Hydraulics
# ================================================================

class TestExtractKeyMetricsHyd:
    def test_returns_correct_count(self, engine, sample_hyd_result):
        metrics = engine._extract_key_metrics("hydraulics", sample_hyd_result, "en")
        assert len(metrics) == 5

    def test_english_labels(self, engine, sample_hyd_result):
        metrics = engine._extract_key_metrics("hydraulics", sample_hyd_result, "en")
        labels = [m["label"] for m in metrics]
        assert "ECD at TD" in labels
        assert "Total SPP" in labels
        assert "HSI" in labels

    def test_spanish_labels(self, engine, sample_hyd_result):
        metrics = engine._extract_key_metrics("hydraulics", sample_hyd_result, "es")
        labels = [m["label"] for m in metrics]
        assert "ECD en TD" in labels
        assert "SPP Total" in labels
        assert "% en Barrena" in labels


# ================================================================
# TestExtractKeyMetrics — Stuck Pipe
# ================================================================

class TestExtractKeyMetricsSP:
    def test_returns_correct_count(self, engine, sample_sp_result):
        metrics = engine._extract_key_metrics("stuck_pipe", sample_sp_result, "en")
        assert len(metrics) == 4

    def test_english_labels(self, engine, sample_sp_result):
        metrics = engine._extract_key_metrics("stuck_pipe", sample_sp_result, "en")
        labels = [m["label"] for m in metrics]
        assert "Mechanism" in labels
        assert "Risk Level" in labels
        assert "Free Point" in labels

    def test_spanish_labels(self, engine, sample_sp_result):
        metrics = engine._extract_key_metrics("stuck_pipe", sample_sp_result, "es")
        labels = [m["label"] for m in metrics]
        assert "Mecanismo" in labels
        assert "Nivel de Riesgo" in labels
        assert "Punto Libre" in labels


# ================================================================
# TestExtractKeyMetrics — Well Control
# ================================================================

class TestExtractKeyMetricsWC:
    def test_returns_correct_count(self, engine, sample_wc_result):
        metrics = engine._extract_key_metrics("well_control", sample_wc_result, "en")
        assert len(metrics) == 6

    def test_english_labels(self, engine, sample_wc_result):
        metrics = engine._extract_key_metrics("well_control", sample_wc_result, "en")
        labels = [m["label"] for m in metrics]
        assert "KMW" in labels
        assert "ICP" in labels
        assert "FCP" in labels
        assert "MAASP" in labels

    def test_spanish_labels(self, engine, sample_wc_result):
        metrics = engine._extract_key_metrics("well_control", sample_wc_result, "es")
        labels = [m["label"] for m in metrics]
        assert "PMM" in labels
        assert "PCI" in labels
        assert "PCF" in labels


# ================================================================
# TestExtractKeyMetrics — Unknown module
# ================================================================

class TestExtractKeyMetricsUnknown:
    def test_unknown_module_returns_empty(self, engine):
        assert engine._extract_key_metrics("unknown_module", {}, "en") == []


# ================================================================
# TestPackage
# ================================================================

class TestPackage:
    def _make_analysis(self):
        return {
            "agent": "well_engineer",
            "role": "Well Engineer",
            "analysis": "Mock analysis text",
            "confidence": "HIGH",
        }

    def test_has_all_required_fields(self, engine, sample_td_result):
        result = engine._package(self._make_analysis(), "torque_drag", sample_td_result, "WELL-1", "en")
        required = {"module", "timestamp", "analysis", "confidence", "agent_used", "agent_role",
                     "key_metrics", "well_name", "language", "provider_used"}
        assert required == set(result.keys())

    def test_language_field_matches_input(self, engine, sample_td_result):
        result = engine._package(self._make_analysis(), "torque_drag", sample_td_result, "WELL-1", "es")
        assert result["language"] == "es"

    def test_analysis_from_agent_response(self, engine, sample_td_result):
        result = engine._package(self._make_analysis(), "torque_drag", sample_td_result, "WELL-1", "en")
        assert result["analysis"] == "Mock analysis text"

    def test_confidence_from_agent_response(self, engine, sample_td_result):
        result = engine._package(self._make_analysis(), "torque_drag", sample_td_result, "WELL-1", "en")
        assert result["confidence"] == "HIGH"

    def test_key_metrics_is_list(self, engine, sample_td_result):
        result = engine._package(self._make_analysis(), "torque_drag", sample_td_result, "WELL-1", "en")
        assert isinstance(result["key_metrics"], list)
        assert len(result["key_metrics"]) > 0


# ================================================================
# TestBuildProblems — Torque & Drag
# ================================================================

class TestBuildTDProblem:
    def test_contains_well_name(self, engine, sample_td_result):
        text = engine._build_td_problem(sample_td_result, "WELL-X", {}, "en")
        assert "WELL-X" in text

    def test_spanish_has_prefix(self, engine, sample_td_result):
        text = engine._build_td_problem(sample_td_result, "WELL-X", {}, "es")
        assert "IMPORTANTE" in text

    def test_english_no_prefix(self, engine, sample_td_result):
        text = engine._build_td_problem(sample_td_result, "WELL-X", {}, "en")
        assert "IMPORTANTE" not in text


# ================================================================
# TestBuildProblems — Hydraulics
# ================================================================

class TestBuildHydProblem:
    def test_contains_well_name(self, engine, sample_hyd_result):
        text = engine._build_hyd_problem(sample_hyd_result, "WELL-Y", {}, "en")
        assert "WELL-Y" in text

    def test_spanish_has_prefix(self, engine, sample_hyd_result):
        text = engine._build_hyd_problem(sample_hyd_result, "WELL-Y", {}, "es")
        assert "IMPORTANTE" in text

    def test_english_no_prefix(self, engine, sample_hyd_result):
        text = engine._build_hyd_problem(sample_hyd_result, "WELL-Y", {}, "en")
        assert "IMPORTANTE" not in text


# ================================================================
# TestBuildProblems — Stuck Pipe
# ================================================================

class TestBuildSPProblem:
    def test_contains_well_name(self, engine, sample_sp_result):
        text = engine._build_sp_problem(sample_sp_result, "WELL-Z", {}, "en")
        assert "WELL-Z" in text

    def test_spanish_has_prefix(self, engine, sample_sp_result):
        text = engine._build_sp_problem(sample_sp_result, "WELL-Z", {}, "es")
        assert "IMPORTANTE" in text

    def test_english_no_prefix(self, engine, sample_sp_result):
        text = engine._build_sp_problem(sample_sp_result, "WELL-Z", {}, "en")
        assert "IMPORTANTE" not in text


# ================================================================
# TestBuildProblems — Well Control
# ================================================================

class TestBuildWCProblem:
    def test_contains_well_name(self, engine, sample_wc_result):
        text = engine._build_wc_problem(sample_wc_result, "WELL-W", {}, "en")
        assert "WELL-W" in text

    def test_spanish_has_prefix(self, engine, sample_wc_result):
        text = engine._build_wc_problem(sample_wc_result, "WELL-W", {}, "es")
        assert "IMPORTANTE" in text

    def test_english_no_prefix(self, engine, sample_wc_result):
        text = engine._build_wc_problem(sample_wc_result, "WELL-W", {}, "en")
        assert "IMPORTANTE" not in text
