"""
Unit tests for CalculationEngine (legacy motor).
Tests: calculate_ecd, calculate_cci, assess_mechanical_risk.
"""
import pytest
from orchestrator.calculation_engine import CalculationEngine


engine = CalculationEngine()


class TestCalculateEcd:

    def test_missing_data(self):
        r = engine.calculate_ecd({})
        assert r["status"] == "Missing Data"

    def test_standard_ecd(self):
        r = engine.calculate_ecd({
            "mud_weight": 10.0,
            "depth_tvd": 10000.0,
            "flow_rate": 400,
            "viscosity_yp": 10
        })
        assert r["value"] is not None
        assert r["value"] > 10.0


class TestCalculateCci:

    def test_missing_data(self):
        r = engine.calculate_cci({})
        assert r["status"] == "Missing Data"

    def test_standard_cci(self):
        r = engine.calculate_cci({
            "flow_rate": 400,
            "mud_weight": 10.0,
            "viscosity_pv": 15
        })
        assert r["value"] is not None
        assert r["value"] > 0


class TestAssessMechanicalRisk:

    def test_high_torque_alert(self):
        r = engine.assess_mechanical_risk({"torque": 30000})
        assert "High Torque" in r["alerts"]

    def test_low_values(self):
        r = engine.assess_mechanical_risk({
            "torque": 5000,
            "overpull": 10,
            "dogleg_severity": 1.0
        })
        assert r["risk_level"] == "Low"
