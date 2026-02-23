"""
Validation-specific conftest.
Inherits from root conftest.py but provides V&V-specific helpers.
"""
import sys
import os

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def assert_within_tolerance(actual, expected_value, tolerance_pct, label=""):
    """Assert that actual is within tolerance_pct of expected_value."""
    tolerance = abs(expected_value) * tolerance_pct / 100.0
    diff_pct = abs(actual - expected_value) / abs(expected_value) * 100 if expected_value != 0 else abs(actual) * 100
    assert abs(actual - expected_value) <= tolerance, (
        f"{label}: actual={actual:.4f}, expected={expected_value:.4f}, "
        f"diff={diff_pct:.1f}%, allowed={tolerance_pct}%"
    )


def assert_within_range(actual, min_val, max_val, label=""):
    """Assert that actual is within [min_val, max_val]."""
    assert min_val <= actual <= max_val, (
        f"{label}: actual={actual:.4f}, expected range [{min_val}, {max_val}]"
    )
