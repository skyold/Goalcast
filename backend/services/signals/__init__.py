"""Goalcast Signals package — re-exports + side-effect imports.

Importing a signal module triggers its @register decorator, which appends
the signal to REGISTERED.
"""
from .base import BaseSignal, REGISTERED, register
from . import gs_mispricing  # noqa: F401  -- imported for @register side-effect

__all__ = ["BaseSignal", "REGISTERED", "register"]
