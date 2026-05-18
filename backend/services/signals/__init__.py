"""Goalcast Signals package — re-exports + side-effect imports.

Importing a signal module triggers its @register decorator, which appends
the signal to REGISTERED.
"""
from .base import BaseSignal, REGISTERED, register
from . import gs_mispricing    # noqa: F401  -- imported for @register side-effect
from . import gs_line_move     # noqa: F401
from . import gs_sharp_square  # noqa: F401
from . import gs_ht_ev         # noqa: F401

__all__ = ["BaseSignal", "REGISTERED", "register"]
