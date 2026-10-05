"""Local/external Airflow orchestration for FX ingestion and dbt validation."""

from datetime import datetime, timedelta
import logging
import os
from pathlib import Path
import subprocess
import sys

from airflow.sdk import DAG, task


logger = logging.getLogger(__name__)


def project_directory():
    """Resolve configuration at task execution time, on the worker."""
    configured = os.environ.get("PROJECT_DIR")
    root = (
        Path(configured).expanduser().resolve()
        if configured
        else Path(__file__).resolve().parents[3]
    )
    if not (root / "ingestion/fx_api/run_fx_pipeline.py").is_file():
        raise ValueError("Set PROJECT_DIR to the repository checkout on the Airflow worker.")
    return root


def dbt_directory():
    configured = os.environ.get("DBT_PROJECT_DIR")
    return (
        Path(configured).expanduser().resolve()
        if configured
        else project_directory() / "analytics"
    )


def run_command(command, cwd):
    """Keep subprocess output in task logs and propagate failures for retries."""
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as error:
        logger.error("Command failed with exit code %s: %s", error.returncode, command)
        logger.error("stdout:\n%s", error.stdout or "")
        logger.error("stderr:\n%s", error.stderr or "")
        raise
    except OSError:
        logger.exception("Could not execute %s in %s", command, cwd)
        raise

    if result.stdout:
        logger.info("%s", result.stdout)
    if result.stderr:
        logger.warning("%s", result.stderr)


with DAG(
    dag_id="fx_pipeline",
    start_date=datetime(2026, 9, 29),
    schedule="0 7 * * *",
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=1),
    },
    tags=["fx", "portfolio"],
):

    @task
    def run_fx_ingestion(logical_date=None):
        if logical_date is None:
            raise ValueError("FX ingestion requires an Airflow logical_date.")
        run_command(
            [
                os.environ.get("PROJECT_PYTHON", sys.executable),
                "-m",
                "ingestion.fx_api.run_fx_pipeline",
                "--date",
                logical_date.strftime("%Y-%m-%d"),
            ],
            cwd=project_directory(),
        )

    @task
    def run_dbt_project():
        run_command(
            [os.environ.get("DBT_EXECUTABLE", "dbt"), "run", "--exclude", "fct_orders_incremental"],
            cwd=dbt_directory(),
        )

    @task
    def test_dbt_project():
        run_command(
            [os.environ.get("DBT_EXECUTABLE", "dbt"), "test", "--exclude", "fct_orders_incremental"],
            cwd=dbt_directory(),
        )

    run_fx_ingestion() >> run_dbt_project() >> test_dbt_project()
