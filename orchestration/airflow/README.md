# Local Airflow orchestration

This DAG adapts the existing local WSL workflow into a portable repository file.
Airflow runs separately on a local/external installation; this repository does
not containerize Airflow or provide a production deployment.

## Behavior

The `fx_pipeline` DAG runs daily at 07:00 in Airflow's configured default
timezone (normally UTC). It retains the September 29, 2026 start date,
`catchup=False`, and two retries with a one-minute delay for each task.

Tasks execute sequentially:

1. `python -m ingestion.fx_api.run_fx_pipeline --date YYYY-MM-DD`, using the
   Airflow logical date, not the wall-clock execution date. This fetches FX
   data, saves a raw JSON response, and loads BigQuery.
2. `dbt run --exclude fct_orders_incremental` from the dbt project directory.
3. `dbt test --exclude fct_orders_incremental` from the same directory.

Subprocess stdout/stderr is included in task logs, including on failure;
failures propagate to Airflow for retry. Runs without a logical date fail
explicitly rather than silently ingesting the latest rates.

The DAG does not load Olist CSVs. The existing Olist raw tables must already
be available. FX rates are currently independent of the Olist dbt models.

## Prerequisites and configuration

Use a separate Airflow 3 installation supporting `airflow.sdk`, for example
on Linux or WSL. The task worker needs access to this checkout, a Python
environment with the ingestion dependencies, and a dbt executable with the
BigQuery adapter. Airflow is not included in the repository requirements files.

| Environment variable | Default / when required |
| --- | --- |
| `PROJECT_DIR` | Repository root derived from this DAG's location. Set an absolute checkout path if the DAG is copied elsewhere. |
| `PROJECT_PYTHON` | Airflow worker's Python (`sys.executable`). Set an absolute Python executable path when ingestion uses a separate environment. |
| `DBT_EXECUTABLE` | `dbt` on the worker's `PATH`. Set an absolute executable path if needed. |
| `DBT_PROJECT_DIR` | `PROJECT_DIR/analytics`; optional absolute override. |
| `DBT_PROFILES_DIR` | Inherited by dbt. Set to the directory containing your `profiles.yml` if it is outside dbt's normal profile location. |

No custom path variables are mandatory when the DAG stays in this checkout
and its default executables are available. Executable variables take a single
executable path/name, not shell commands or arguments. Set configuration in
the environment that starts Airflow and its task workers, not only an unrelated
terminal session.

Provide an `analytics` dbt profile and BigQuery authentication through your
existing external setup. Do not commit credentials or personal profiles.
The ingestion loaders and dbt sources currently reference
`mda-platform-2026`; configuring DAG paths does not change those warehouse
identifiers. The worker also needs write access to `data/raw/fx` in the checkout.

## Point Airflow at the repository DAG

From the repository root in your Linux/WSL shell, before starting your local
Airflow services:

```bash
export PROJECT_DIR="$(pwd)"
export AIRFLOW__CORE__DAGS_FOLDER="$PROJECT_DIR/orchestration/airflow/dags"
# If using a separate project environment, configure its executables:
# export PROJECT_PYTHON="/path/to/project-venv/bin/python"
# export DBT_EXECUTABLE="/path/to/project-venv/bin/dbt"
# export DBT_PROFILES_DIR="/path/to/dbt-profile-directory"
```

Restart the relevant Airflow services so they inherit the settings, confirm
that `fx_pipeline` is discovered without import errors, and unpause it when
ready to execute warehouse jobs. Pointing `dags_folder` here changes the DAG
directory for that Airflow installation; alternatively, symlink this DAG into
your existing DAG directory and set `PROJECT_DIR` explicitly.

Keep only one discovered DAG with the ID `fx_pipeline`; do not load both this
copy and the original WSL copy. The external WSL DAG has not been changed.
The schedule timezone follows your Airflow configuration, as in the original.

The repository's GitHub Actions workflow runs pytest and dbt parse only. It
does not start Airflow, execute this DAG, or connect to BigQuery.
