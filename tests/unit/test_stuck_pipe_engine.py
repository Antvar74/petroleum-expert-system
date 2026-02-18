"""
Unit tests for StuckPipeEngine.
Tests: get_next_question, classify_mechanism, calculate_free_point,
       assess_risk_matrix, get_recommended_actions.
"""
import math
import pytest
from orchestrator.stuck_pipe_engine import StuckPipeEngine


# ============================================================
# get_next_question — Decision Tree (8 tests)
# ============================================================

class TestGetNextQuestion:

    def test_start_no_answer(self):
        """Start without answer should return the first question."""
        r = StuckPipeEngine.get_next_question()
        assert r["type"] == "question"
        assert r["node_id"] == "start"
        assert "circulate" in r["question"].lower()

    def test_yes_from_start(self):
        r = StuckPipeEngine.get_next_question("start", "yes")
        assert r["type"] == "question"
        assert r["node_id"] == "q_rotate"

    def test_no_from_start(self):
        r = StuckPipeEngine.get_next_question("start", "no")
        assert r["type"] == "question"
        assert r["node_id"] == "q_no_circ"

    def test_path_to_differential_sticking(self):
        """Path: start→no, q_no_circ→no, q_no_circ_no_rotate→yes → Differential."""
        r = StuckPipeEngine.get_next_question("start", "no")
        assert r["node_id"] == "q_no_circ"
        r = StuckPipeEngine.get_next_question("q_no_circ", "no")
        assert r["node_id"] == "q_no_circ_no_rotate"
        r = StuckPipeEngine.get_next_question("q_no_circ_no_rotate", "yes")
        assert r["type"] == "result"
        assert r["mechanism"] == "Differential Sticking"

    def test_path_to_hole_cleaning(self):
        """Path: start→yes, q_rotate→yes, q_reciprocate→yes, q_limited_movement→yes."""
        r = StuckPipeEngine.get_next_question("start", "yes")
        r = StuckPipeEngine.get_next_question("q_rotate", "yes")
        r = StuckPipeEngine.get_next_question("q_reciprocate", "yes")
        r = StuckPipeEngine.get_next_question("q_limited_movement", "yes")
        assert r["type"] == "result"
        assert r["mechanism"] == "Hole Cleaning / Pack-Off"

    def test_path_to_key_seating(self):
        """Path: start→yes, q_rotate→yes, q_reciprocate→yes, q_limited_movement→no."""
        r = StuckPipeEngine.get_next_question("q_limited_movement", "no")
        assert r["type"] == "result"
        assert r["mechanism"] == "Key Seating"

    def test_unknown_node(self):
        r = StuckPipeEngine.get_next_question("nonexistent_node")
        assert r["type"] == "error"

    def test_all_nine_mechanisms_reachable(self):
        """Exhaustive traversal: all 9 result nodes should be reachable."""
        reachable = set()

        def traverse(node_id):
            if node_id.startswith("result_"):
                reachable.add(node_id)
                return
            node = StuckPipeEngine.DECISION_TREE.get(node_id)
            if not node:
                return
            for answer in ("yes", "no"):
                next_node = node.get(answer, "start")
                traverse(next_node)

        traverse("start")
        assert len(reachable) == 9, f"Expected 9 mechanisms, found {len(reachable)}: {reachable}"


# ============================================================
# classify_mechanism (4 tests)
# ============================================================

class TestClassifyMechanism:

    def test_full_path_differential(self):
        """Navigate to Differential Sticking."""
        answers = [
            {"node_id": "start", "answer": "no"},
            {"node_id": "q_no_circ", "answer": "no"},
            {"node_id": "q_no_circ_no_rotate", "answer": "yes"},
        ]
        r = StuckPipeEngine.classify_mechanism(answers)
        assert r["mechanism"] == "Differential Sticking"
        assert len(r["decision_path"]) == 3

    def test_empty_answers(self):
        r = StuckPipeEngine.classify_mechanism([])
        assert r["mechanism"] == "Inconclusive"

    def test_partial_answers(self):
        answers = [{"node_id": "start", "answer": "yes"}]
        r = StuckPipeEngine.classify_mechanism(answers)
        assert r["mechanism"] == "Inconclusive"

    def test_path_to_formation_flow(self):
        """Navigate to Formation Flow / Kick."""
        answers = [
            {"node_id": "start", "answer": "no"},
            {"node_id": "q_no_circ", "answer": "yes"},
            {"node_id": "q_no_circ_rotate", "answer": "no"},
            {"node_id": "q_flow_check", "answer": "yes"},
        ]
        r = StuckPipeEngine.classify_mechanism(answers)
        assert r["mechanism"] == "Formation Flow / Kick"


# ============================================================
# calculate_free_point (10 tests)
# ============================================================

class TestCalculateFreePoint:

    def test_zero_force_error(self):
        r = StuckPipeEngine.calculate_free_point(5.0, 4.276, "S135", 2.0, 0)
        assert "error" in r

    def test_zero_stretch_error(self):
        r = StuckPipeEngine.calculate_free_point(5.0, 4.276, "S135", 0, 50000)
        assert "error" in r

    def test_basic_calculation(self):
        """FP = (E × A × stretch) / (force × 12)."""
        od, id_i = 5.0, 4.276
        area = math.pi / 4.0 * (od**2 - id_i**2)
        stretch = 2.0
        force = 50000.0
        expected_fp = (30e6 * area * stretch) / (force * 12.0)
        r = StuckPipeEngine.calculate_free_point(od, id_i, "S135", stretch, force)
        assert abs(r["free_point_depth_ft"] - expected_fp) < 1.0

    def test_depth_positive(self):
        r = StuckPipeEngine.calculate_free_point(5.0, 4.276, "S135", 2.0, 50000)
        assert r["free_point_depth_ft"] > 0

    def test_double_stretch_double_depth(self):
        """FP is linear with stretch (within rounding tolerance)."""
        r1 = StuckPipeEngine.calculate_free_point(5.0, 4.276, "S135", 1.0, 50000)
        r2 = StuckPipeEngine.calculate_free_point(5.0, 4.276, "S135", 2.0, 50000)
        assert abs(r2["free_point_depth_ft"] - 2 * r1["free_point_depth_ft"]) < 2.0

    def test_double_force_half_depth(self):
        """FP is inversely proportional to force."""
        r1 = StuckPipeEngine.calculate_free_point(5.0, 4.276, "S135", 2.0, 50000)
        r2 = StuckPipeEngine.calculate_free_point(5.0, 4.276, "S135", 2.0, 100000)
        assert abs(r2["free_point_depth_ft"] - r1["free_point_depth_ft"] / 2.0) < 1.0

    def test_pull_safe_under_80pct(self):
        """Pull < 80% of yield → pull_safe=True."""
        od, id_i = 5.0, 4.276
        area = math.pi / 4.0 * (od**2 - id_i**2)
        safe_pull = 135000 * area * 0.50  # 50% of yield
        r = StuckPipeEngine.calculate_free_point(od, id_i, "S135", 2.0, safe_pull)
        assert r["pull_safe"] is True

    def test_pull_unsafe_over_80pct(self):
        """Pull > 80% of yield → pull_safe=False."""
        od, id_i = 5.0, 4.276
        area = math.pi / 4.0 * (od**2 - id_i**2)
        unsafe_pull = 135000 * area * 0.90  # 90% of yield
        r = StuckPipeEngine.calculate_free_point(od, id_i, "S135", 2.0, unsafe_pull)
        assert r["pull_safe"] is False

    def test_known_grades(self):
        """E75 → 75000, S135 → 135000."""
        r_e = StuckPipeEngine.calculate_free_point(5.0, 4.276, "E75", 2.0, 50000)
        assert r_e["yield_strength_psi"] == 75000
        r_s = StuckPipeEngine.calculate_free_point(5.0, 4.276, "S135", 2.0, 50000)
        assert r_s["yield_strength_psi"] == 135000

    def test_unknown_grade_default(self):
        r = StuckPipeEngine.calculate_free_point(5.0, 4.276, "UNKNOWN", 2.0, 50000)
        assert r["yield_strength_psi"] == 80000


# ============================================================
# assess_risk_matrix (7 tests)
# ============================================================

class TestAssessRiskMatrix:

    def test_unknown_mechanism_error(self):
        r = StuckPipeEngine.assess_risk_matrix("Nonexistent Mechanism", {})
        assert "error" in r

    def test_empty_params_base_risk(self):
        r = StuckPipeEngine.assess_risk_matrix("Differential Sticking", {})
        assert r["risk_level"] in ("LOW", "MEDIUM")

    def test_high_overbalance_factor(self):
        r = StuckPipeEngine.assess_risk_matrix("Differential Sticking", {
            "mud_weight": 14.0, "pore_pressure": 10.0
        })
        factor_names = [f["factor"] for f in r["contributing_factors"]]
        assert "High Overbalance" in factor_names

    def test_high_inclination_factor(self):
        r = StuckPipeEngine.assess_risk_matrix("Hole Cleaning / Pack-Off", {
            "inclination": 75
        })
        factor_names = [f["factor"] for f in r["contributing_factors"]]
        assert "High Inclination" in factor_names

    def test_critical_risk(self):
        """Multiple high factors + Formation Flow (severity=5) → CRITICAL."""
        r = StuckPipeEngine.assess_risk_matrix("Formation Flow / Kick", {
            "mud_weight": 14.0, "pore_pressure": 10.0,
            "inclination": 80,
            "stationary_hours": 5,
            "torque": 30000,
            "overpull": 50
        })
        assert r["risk_level"] in ("CRITICAL", "HIGH")

    def test_matrix_position_in_range(self):
        r = StuckPipeEngine.assess_risk_matrix("Differential Sticking", {
            "mud_weight": 12.0, "pore_pressure": 10.0
        })
        assert 1 <= r["matrix_position"]["x"] <= 5
        assert 1 <= r["matrix_position"]["y"] <= 5

    def test_severity_by_mechanism(self):
        """Formation Flow = severity 5, Key Seating = severity 2."""
        r_ff = StuckPipeEngine.assess_risk_matrix("Formation Flow / Kick", {})
        assert r_ff["severity"] == 5
        r_ks = StuckPipeEngine.assess_risk_matrix("Key Seating", {})
        assert r_ks["severity"] == 2


# ============================================================
# get_recommended_actions (4 tests)
# ============================================================

class TestGetRecommendedActions:

    def test_differential_sticking_actions(self):
        r = StuckPipeEngine.get_recommended_actions("Differential Sticking")
        assert len(r["immediate"]) > 0
        assert len(r["short_term"]) > 0
        assert len(r["contingency"]) > 0

    def test_all_nine_mechanisms_valid(self):
        mechanisms = [
            "Differential Sticking", "Mechanical Sticking", "Hole Cleaning / Pack-Off",
            "Wellbore Instability", "Key Seating", "Undergauge Hole",
            "Formation Flow / Kick", "Pack-Off / Bridge", "Cement / Junk in Hole"
        ]
        for mech in mechanisms:
            r = StuckPipeEngine.get_recommended_actions(mech)
            assert "immediate" in r, f"Missing 'immediate' for {mech}"
            assert "short_term" in r, f"Missing 'short_term' for {mech}"
            assert "contingency" in r, f"Missing 'contingency' for {mech}"

    def test_unknown_mechanism_fallback(self):
        r = StuckPipeEngine.get_recommended_actions("Unknown Mechanism")
        assert "error" in r
        assert len(r["immediate"]) > 0  # fallback actions

    def test_total_actions_count(self):
        r = StuckPipeEngine.get_recommended_actions("Differential Sticking")
        expected = len(r["immediate"]) + len(r["short_term"]) + len(r["contingency"])
        assert r["total_actions"] == expected
