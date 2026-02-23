"""Unit tests for WITSML 1.4.1 client — XML parsing, query building, and data conversion."""
import pytest
from orchestrator.witsml_client import WITSMLClient


SAMPLE_LOG_XML = """<?xml version="1.0" encoding="UTF-8"?>
<logs xmlns="http://www.witsml.org/schemas/1series" version="1.4.1.1">
  <log uidWell="W-001" uidWellbore="WB-001">
    <name>Real-Time MWD</name>
    <logCurveInfo>
      <mnemonic>DEPT</mnemonic><unit>ft</unit>
    </logCurveInfo>
    <logCurveInfo>
      <mnemonic>GR</mnemonic><unit>gAPI</unit>
    </logCurveInfo>
    <logCurveInfo>
      <mnemonic>HKLD</mnemonic><unit>klb</unit>
    </logCurveInfo>
    <logData>
      <data>5000.0,45.0,250.5</data>
      <data>5010.0,50.0,248.3</data>
      <data>5020.0,42.0,252.1</data>
    </logData>
  </log>
</logs>"""

SAMPLE_TRAJECTORY_XML = """<?xml version="1.0" encoding="UTF-8"?>
<trajectorys xmlns="http://www.witsml.org/schemas/1series" version="1.4.1.1">
  <trajectory uidWell="W-001" uidWellbore="WB-001">
    <trajectoryStation>
      <md uom="ft">0</md><incl uom="deg">0</incl><azi uom="deg">0</azi>
    </trajectoryStation>
    <trajectoryStation>
      <md uom="ft">5000</md><incl uom="deg">30</incl><azi uom="deg">135</azi>
    </trajectoryStation>
    <trajectoryStation>
      <md uom="ft">10000</md><incl uom="deg">45</incl><azi uom="deg">135</azi>
    </trajectoryStation>
  </trajectory>
</trajectorys>"""

SAMPLE_MUDLOG_XML = """<?xml version="1.0" encoding="UTF-8"?>
<mudLogs xmlns="http://www.witsml.org/schemas/1series" version="1.4.1.1">
  <mudLog uidWell="W-001" uidWellbore="WB-001">
    <geologyInterval>
      <mdTop uom="ft">5000</mdTop>
      <mdBottom uom="ft">5050</mdBottom>
      <description>Fine-grained sandstone</description>
      <lithology type="sandstone"/>
    </geologyInterval>
    <geologyInterval>
      <mdTop uom="ft">5050</mdTop>
      <mdBottom uom="ft">5100</mdBottom>
      <description>Shale with minor silt</description>
      <lithology type="shale"/>
    </geologyInterval>
  </mudLog>
</mudLogs>"""


class TestWITSMLLogParser:
    """Test WITSML log XML parsing."""

    def test_parse_log_curves(self):
        result = WITSMLClient.parse_log_response(SAMPLE_LOG_XML)
        assert result["curves"] == ["DEPT", "GR", "HKLD"]

    def test_parse_log_units(self):
        result = WITSMLClient.parse_log_response(SAMPLE_LOG_XML)
        assert result["units"] == ["ft", "gAPI", "klb"]

    def test_parse_log_data_count(self):
        result = WITSMLClient.parse_log_response(SAMPLE_LOG_XML)
        assert result["point_count"] == 3

    def test_parse_log_data_values(self):
        result = WITSMLClient.parse_log_response(SAMPLE_LOG_XML)
        assert result["data"][0]["DEPT"] == 5000.0
        assert result["data"][0]["GR"] == 45.0
        assert result["data"][1]["HKLD"] == 248.3

    def test_parse_log_well_uid(self):
        result = WITSMLClient.parse_log_response(SAMPLE_LOG_XML)
        assert result["well_uid"] == "W-001"
        assert result["wellbore_uid"] == "WB-001"

    def test_parse_log_name(self):
        result = WITSMLClient.parse_log_response(SAMPLE_LOG_XML)
        assert result["log_name"] == "Real-Time MWD"

    def test_parse_empty_log(self):
        xml = '<logs xmlns="http://www.witsml.org/schemas/1series"><log></log></logs>'
        result = WITSMLClient.parse_log_response(xml)
        assert result["point_count"] == 0
        assert result["curves"] == []


class TestWITSMLTrajectoryParser:
    """Test WITSML trajectory XML parsing."""

    def test_parse_trajectory_stations(self):
        result = WITSMLClient.parse_trajectory_response(SAMPLE_TRAJECTORY_XML)
        assert result["station_count"] == 3

    def test_parse_trajectory_values(self):
        result = WITSMLClient.parse_trajectory_response(SAMPLE_TRAJECTORY_XML)
        assert result["stations"][0]["md"] == 0
        assert result["stations"][0]["inclination"] == 0
        assert result["stations"][1]["md"] == 5000
        assert result["stations"][1]["inclination"] == 30
        assert result["stations"][2]["azimuth"] == 135

    def test_parse_trajectory_well_uid(self):
        result = WITSMLClient.parse_trajectory_response(SAMPLE_TRAJECTORY_XML)
        assert result["well_uid"] == "W-001"


class TestWITSMLMudlogParser:
    """Test WITSML mudLog XML parsing."""

    def test_parse_mudlog_intervals(self):
        result = WITSMLClient.parse_mudlog_response(SAMPLE_MUDLOG_XML)
        assert len(result["intervals"]) == 2

    def test_parse_mudlog_lithology(self):
        result = WITSMLClient.parse_mudlog_response(SAMPLE_MUDLOG_XML)
        assert result["intervals"][0]["lithology"] == "sandstone"
        assert result["intervals"][1]["lithology"] == "shale"

    def test_parse_mudlog_depths(self):
        result = WITSMLClient.parse_mudlog_response(SAMPLE_MUDLOG_XML)
        assert result["intervals"][0]["top_md"] == 5000
        assert result["intervals"][0]["base_md"] == 5050


class TestWITSMLQueryBuilder:
    """Test WITSML query XML generation."""

    def test_build_log_query_contains_uids(self):
        xml = WITSMLClient.build_log_query("W-001", "WB-001")
        assert "W-001" in xml
        assert "WB-001" in xml
        assert "witsml" in xml.lower()

    def test_build_log_query_with_mnemonics(self):
        xml = WITSMLClient.build_log_query("W-001", "WB-001", mnemonics=["GR", "DEPT"])
        assert "<mnemonic>GR</mnemonic>" in xml
        assert "<mnemonic>DEPT</mnemonic>" in xml

    def test_build_log_query_with_index_range(self):
        xml = WITSMLClient.build_log_query("W-001", "WB-001", start_index="5000", end_index="6000")
        assert "5000" in xml
        assert "6000" in xml

    def test_build_trajectory_query(self):
        xml = WITSMLClient.build_trajectory_query("W-001", "WB-001")
        assert "W-001" in xml
        assert "trajectory" in xml.lower()


class TestWITSMLDataConversion:
    """Test conversion from WITSML format to PetroExpert format."""

    def test_log_to_petro_format(self):
        parsed = WITSMLClient.parse_log_response(SAMPLE_LOG_XML)
        converted = WITSMLClient.witsml_log_to_petro_format(parsed)
        assert len(converted) == 3
        assert converted[0]["md"] == 5000.0
        assert converted[0]["gr"] == 45.0
        assert converted[0]["hookload"] == 250.5

    def test_trajectory_to_survey(self):
        parsed = WITSMLClient.parse_trajectory_response(SAMPLE_TRAJECTORY_XML)
        survey = WITSMLClient.witsml_trajectory_to_survey(parsed)
        assert len(survey) == 3
        assert survey[1]["inclination"] == 30
        assert survey[2]["md"] == 10000


class TestWITSMLConnection:
    """Test connection stub."""

    def test_connect_returns_status(self):
        result = WITSMLClient.connect("https://witsml.example.com", "user", "pass")
        assert "connected" in result
        assert "capabilities" in result

    def test_connect_invalid_url(self):
        result = WITSMLClient.connect("not-a-url", "user", "pass")
        assert result["connected"] is False
        assert "error" in result
