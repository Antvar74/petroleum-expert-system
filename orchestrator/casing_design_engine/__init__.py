"""Casing Design Engine -- backward-compatible facade.

Package split from monolithic casing_design_engine.py.
All existing imports continue to work unchanged:
    from orchestrator.casing_design_engine import CasingDesignEngine
"""

# Temporary shim: re-export from monolith while sub-modules are built
from orchestrator._casing_design_engine_monolith import CasingDesignEngine

__all__ = ["CasingDesignEngine"]
