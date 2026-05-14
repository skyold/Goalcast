"""Verify that doomed provider/datasource directories have been deleted."""
import importlib
import sys
import os
import pytest

# Ensure backend/ is on the path so we test the actual backend modules
BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


@pytest.mark.parametrize("mod", [
    "provider.footystats",
    "provider.sportmonks",
    "provider.understat",
    "datasource.datafusion",
    "datasource.sportmonks",
])
def test_doomed_modules_absent(mod):
    # Remove any cached version of the module before testing
    for key in list(sys.modules.keys()):
        if key == mod or key.startswith(mod + "."):
            del sys.modules[key]
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(mod)
