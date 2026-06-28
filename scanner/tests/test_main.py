"""Tests for the ECS dispatcher entry point (src/main.py).

main.py is the container entry point for ECS Fargate tasks: it reads the MODE
env var and dispatches to the matching handler's main(). These tests use the
`src.` import identity that the container itself uses at runtime (WORKDIR=/app),
made importable under pytest by the repo-root conftest.py.
"""
import os
from unittest.mock import patch

import pytest

os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("MODE", "")

from src import main as main_module


def test_unknown_mode_exits_nonzero():
    """An unset/unknown MODE must exit non-zero so ECS marks the task failed."""
    with patch.object(main_module, "MODE", "bogus"):
        with pytest.raises(SystemExit) as exc:
            main_module.main()
    assert exc.value.code == 1


def test_missing_mode_exits_nonzero():
    """Empty MODE (the default) is treated the same as unknown."""
    with patch.object(main_module, "MODE", ""):
        with pytest.raises(SystemExit) as exc:
            main_module.main()
    assert exc.value.code == 1


def test_rules_engine_mode_dispatches():
    """MODE=rules_engine dispatches to the rules-engine handler's main()."""
    with patch.object(main_module, "MODE", "rules_engine"), patch(
        "src.handlers.rules_engine.main"
    ) as mock_run:
        main_module.main()
    mock_run.assert_called_once()
