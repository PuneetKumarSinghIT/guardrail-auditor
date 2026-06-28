"""Pytest path setup (repo root).

At runtime every service's Docker image has WORKDIR=/app with the code under
/app/src, so the Lambda/ECS handlers import `from src.X import ...` — the
absolute-import rule mandated in CLAUDE.md. Pytest, however, is invoked from the
repo root in CI (`pytest scanner/ api/ ai-engine/`), where the package is
`scanner.src`, so a bare `from src.X` would raise `ModuleNotFoundError: No
module named 'src'` during collection (it did — it broke test_rules_engine.py).

Prepending each service directory to sys.path makes `src` resolve as a
top-level package during tests too, so the exact same `from src.X` imports the
containers use work unchanged under CI — no test or handler edits required.

Add a service here only once it ships its own `src/` package with tests
(ai-engine in Phase 6, api in Phase 7). Each container only ever contains its
own `src`, so the multi-service `src` ambiguity exists only in the shared test
session — keep this list to services that actually have tests.
"""
import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))

for _service in ("scanner",):
    _service_dir = os.path.join(_ROOT, _service)
    if os.path.isdir(os.path.join(_service_dir, "src")) and _service_dir not in sys.path:
        sys.path.insert(0, _service_dir)
