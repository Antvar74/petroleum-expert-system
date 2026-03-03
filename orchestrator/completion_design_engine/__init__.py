"""
Completion Design Engine — backward-compatible facade.

All code has been split into sub-modules:
  constants.py    — gun databases, CF ranges
  penetration.py  — API RP 19B penetration corrections
  productivity.py — K&T 1991 skin model + sweep optimization
  underbalance.py — underbalance analysis
  gun_selection.py — simple + expanded gun selection
  fracture.py     — fracture initiation & gradient (Eaton, Daines, M&K)
  ipr.py          — IPR models (Vogel, Fetkovich, Darcy)
  vlp.py          — VLP Beggs & Brill + nodal analysis
  advanced.py     — crushed zone skin, Joshi horizontal productivity
  pipeline.py     — full integrated calculation

All existing callers of CompletionDesignEngine.<method>() continue to work
unchanged through the staticmethod wrappers below.
"""

from .constants    import GUN_DATABASE, GUN_CATALOG, STRESS_CF_RANGE, TEMP_CF_RANGE, FLUID_CF_RANGE
from .penetration  import calculate_penetration_depth
from .productivity import calculate_productivity_ratio, optimize_perforation_design
from .underbalance import calculate_underbalance
from .gun_selection import select_gun_configuration, select_gun_from_catalog
from .fracture     import (
    calculate_fracture_initiation,
    calculate_fracture_gradient,
    calculate_fracture_gradient_daines,
    calculate_fracture_gradient_matthews_kelly,
)
from .ipr     import calculate_ipr_vogel, calculate_ipr_fetkovich, calculate_ipr_darcy
from .vlp     import calculate_vlp_beggs_brill, calculate_nodal_analysis
from .advanced import calculate_crushed_zone_skin, calculate_horizontal_productivity
from .pipeline import calculate_full_completion_design


class CompletionDesignEngine:
    """
    Backward-compatible facade.

    All methods are staticmethod wrappers around the modular functions.
    New code should import directly from the sub-modules.
    """

    # Class-level data
    GUN_DATABASE = GUN_DATABASE
    GUN_CATALOG  = GUN_CATALOG
    STRESS_CF_RANGE = STRESS_CF_RANGE
    TEMP_CF_RANGE   = TEMP_CF_RANGE
    FLUID_CF_RANGE  = FLUID_CF_RANGE

    calculate_penetration_depth          = staticmethod(calculate_penetration_depth)
    calculate_productivity_ratio         = staticmethod(calculate_productivity_ratio)
    optimize_perforation_design          = staticmethod(optimize_perforation_design)
    calculate_underbalance               = staticmethod(calculate_underbalance)
    select_gun_configuration             = staticmethod(select_gun_configuration)
    select_gun_from_catalog              = staticmethod(select_gun_from_catalog)
    calculate_fracture_initiation        = staticmethod(calculate_fracture_initiation)
    calculate_fracture_gradient          = staticmethod(calculate_fracture_gradient)
    calculate_fracture_gradient_daines   = staticmethod(calculate_fracture_gradient_daines)
    calculate_fracture_gradient_matthews_kelly = staticmethod(calculate_fracture_gradient_matthews_kelly)
    calculate_ipr_vogel                  = staticmethod(calculate_ipr_vogel)
    calculate_ipr_fetkovich              = staticmethod(calculate_ipr_fetkovich)
    calculate_ipr_darcy                  = staticmethod(calculate_ipr_darcy)
    calculate_vlp_beggs_brill            = staticmethod(calculate_vlp_beggs_brill)
    calculate_nodal_analysis             = staticmethod(calculate_nodal_analysis)
    calculate_crushed_zone_skin          = staticmethod(calculate_crushed_zone_skin)
    calculate_horizontal_productivity    = staticmethod(calculate_horizontal_productivity)
    calculate_full_completion_design     = staticmethod(calculate_full_completion_design)
