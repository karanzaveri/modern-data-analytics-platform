"""Exercise the DAG with an SDK stub; no Airflow services or APIs are called."""

from pathlib import Path
import runpy
import subprocess
import sys
from types import ModuleType
from unittest.mock import Mock

import pytest


DAG_PATH = Path(__file__).resolve().parents[1] / "orchestration/airflow/dags/fx_pipeline.py"


@pytest.fixture
def dag_module(monkeypatch):
    edges = []
    options = {}

    class FakeDAG:
        def __init__(self, **kwargs):
            options.update(kwargs)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class FakeTask:
        def __init__(self, function, **kwargs):
            self.function = function
            self.options = kwargs
            self.name = function.__name__

        def __call__(self):
            return self

        def __rshift__(self, other):
            edges.append((self.name, other.name))
            return other

    def task(function=None, **kwargs):
        if function is None:
            return lambda function: FakeTask(function, **kwargs)
        return FakeTask(function, **kwargs)

    airflow = ModuleType("airflow")
    sdk = ModuleType("airflow.sdk")
    sdk.DAG = FakeDAG
    sdk.task = task
    airflow.sdk = sdk
    monkeypatch.setitem(sys.modules, "airflow", airflow)
    monkeypatch.setitem(sys.modules, "airflow.sdk", sdk)
    monkeypatch.delenv("PROJECT_DIR", raising=False)
    module = runpy.run_path(str(DAG_PATH))
    return module, edges, options


def test_dependency_chain_requires_successful_dbt_tests(dag_module):
    module, edges, options = dag_module
    assert edges == [
        ("run_fx_ingestion", "run_dbt_project"),
        ("run_dbt_project", "test_dbt_project"),
        ("test_dbt_project", "generate_ai_insights"),
    ]
    assert module["generate_ai_insights"].options["trigger_rule"] == "all_success"
    assert options["schedule"] == "0 7 * * *"
    assert options["catchup"] is False
    assert options["default_args"]["retries"] == 2


@pytest.mark.parametrize("configured_python", [None, "/custom/project/bin/python"])
def test_ai_cli_uses_latest_month_and_project_python(
    dag_module, monkeypatch, configured_python
):
    module, _, _ = dag_module
    monkeypatch.setenv("GEMINI_API_KEY", "mock-key-not-a-secret")
    if configured_python is None:
        monkeypatch.delenv("PROJECT_PYTHON", raising=False)
    else:
        monkeypatch.setenv("PROJECT_PYTHON", configured_python)
    run = Mock(return_value=subprocess.CompletedProcess([], 0, "", ""))
    monkeypatch.setattr(subprocess, "run", run)

    module["generate_ai_insights"].function()

    run.assert_called_once_with(
        [configured_python or "/home/karan/venvs/mda_platform/bin/python",
         "-m", "ai.generate_insights"],
        cwd=DAG_PATH.parents[3], capture_output=True, text=True, check=True,
    )
    # No explicit environment is passed: the child inherits the worker's key.
    assert "mock-key-not-a-secret" not in str(run.call_args)


@pytest.mark.parametrize("key", [None, "", "   "])
def test_missing_key_fails_before_subprocess(dag_module, monkeypatch, key):
    module, _, _ = dag_module
    if key is None:
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    else:
        monkeypatch.setenv("GEMINI_API_KEY", key)
    run = Mock()
    monkeypatch.setattr(subprocess, "run", run)

    with pytest.raises(ValueError, match="GEMINI_API_KEY.*Airflow worker"):
        module["generate_ai_insights"].function()
    run.assert_not_called()


def test_cli_failure_propagates_to_airflow(dag_module, monkeypatch):
    module, _, _ = dag_module
    monkeypatch.setenv("GEMINI_API_KEY", "mock-key-not-a-secret")
    failure = subprocess.CalledProcessError(
        1, ["python", "-m", "ai.generate_insights"],
        stderr="Numeric grounding failed after 2 attempts",
    )
    run = Mock(side_effect=failure)
    monkeypatch.setattr(subprocess, "run", run)

    with pytest.raises(subprocess.CalledProcessError) as error:
        module["generate_ai_insights"].function()
    assert error.value is failure
    run.assert_called_once()
