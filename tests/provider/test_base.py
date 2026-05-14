"""Tests for the simplified provider base + singleton factory."""
import sys
import os

# Ensure backend/ is on the path so we test the actual backend modules
BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from provider.base import BaseProvider, get_provider, reset_provider
from provider.oddalerts.client import OddAlertsProvider


def test_get_provider_returns_oddalerts_instance():
    reset_provider()
    p = get_provider()
    assert isinstance(p, OddAlertsProvider)
    assert p.name == "oddalerts"


def test_get_provider_returns_singleton():
    reset_provider()
    p1 = get_provider()
    p2 = get_provider()
    assert p1 is p2


def test_reset_provider_drops_singleton():
    reset_provider()
    p1 = get_provider()
    reset_provider()
    p2 = get_provider()
    assert p1 is not p2


def test_base_provider_keeps_minimal_abstract_surface():
    # discover_fixtures must remain abstract (used by OddAlertsProvider)
    # name and is_available must remain abstract
    abstract = BaseProvider.__abstractmethods__
    assert "name" in abstract
    assert "is_available" in abstract
    assert "discover_fixtures" in abstract
