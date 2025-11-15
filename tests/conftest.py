"""Test configuration helpers."""

import importlib
import sys
from pathlib import Path
from types import ModuleType

# Ensure the pkms package (found under .pkms/) is importable when pytest runs
ROOT_DIR = Path(__file__).resolve().parent.parent
PKMS_SRC = ROOT_DIR / ".pkms"

if str(PKMS_SRC) not in sys.path:
    sys.path.insert(0, str(PKMS_SRC))

# Mirror the legacy pkms package namespace (lib/, models/, tools/) for pytest
if "pkms" not in sys.modules:
    pkms_module = ModuleType("pkms")
    sys.modules["pkms"] = pkms_module
else:
    pkms_module = sys.modules["pkms"]

for subpkg in ("lib", "models", "tools"):
    try:
        module = importlib.import_module(subpkg)
    except ModuleNotFoundError:
        continue

    sys.modules[f"pkms.{subpkg}"] = module
    setattr(pkms_module, subpkg, module)
