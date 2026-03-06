"""
Torque & Drag Calculation Engine — Package.

Based on Johancsik (1984) Soft-String Model with Mitchell stiff-string extension.
References: Applied Drilling Engineering (Bourgoyne et al.), SPE 11380, SPE 56901.

Sub-modules:
- survey: Minimum curvature TVD/North/East/DLS
- soft_string: Johancsik soft-string T&D with post-buckling drag
- stiff_string: Hybrid Mitchell stiff-string T&D
- buckling: Lubinski/Mitchell sinusoidal & helical buckling checks
- friction: Back-calculation of friction factor via bisection
"""
from .survey import compute_survey_derived
from .soft_string import compute_torque_drag
from .stiff_string import compute_torque_drag_stiff
from .buckling import buckling_check, casing_id_estimate, STEEL_E, STEEL_DENSITY
from .friction import back_calculate_friction


class TorqueDragEngine:
    """
    Backward-compatible facade exposing all sub-module functions
    as static methods on the original class interface.
    """

    STEEL_E = STEEL_E
    STEEL_DENSITY = STEEL_DENSITY

    compute_survey_derived = staticmethod(compute_survey_derived)
    compute_torque_drag = staticmethod(compute_torque_drag)
    compute_torque_drag_stiff = staticmethod(compute_torque_drag_stiff)
    back_calculate_friction = staticmethod(back_calculate_friction)

    # Keep private helpers accessible for any legacy callers
    _buckling_check = staticmethod(buckling_check)
    _casing_id_estimate = staticmethod(casing_id_estimate)
