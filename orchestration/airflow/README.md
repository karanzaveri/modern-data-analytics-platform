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
4. `python -m ai.generate_insights` from the repository root,
   selecting the latest available `order_month` in `monthly_revenue_reporting`. This
   runs only after all upstream tasks succeed. It reuses the AI CLI's numeric
   validation and one built-in generation retry; failures propagate to Airflow.
   Successful runs overwrite the month's JSON and Markdown files in `ai/outputs/`.

Subprocess stdout/stderr is included in task logs, including on failure;
failures propagate to Airflow for retry. FX ingestion runs without a logical date fail
explicitly rather than silently ingesting the latest rates.

The DAG does not load Olist CSVs. The existing Olist raw tables must already
be available. FX rates are currently independent of the Olist dbt models.

## Prerequisites and configuration

Use a separate Airflow 3 installation supporting `airflow.sdk`, for example
on Linux or WSL. The task worker needs access to this checkout, a Python
environment with the ingestion dependencies, and a dbt executable with the
BigQuery adapter. The project Python environment also needs the AI dependencies.
Airflow is not included in the repository requirements files.

| Environment variable | Default / when required |
| --- | --- |
| `PROJECT_DIR` | Repository root derived from this DAG's location. Set an absolute checkout path if the DAG is copied elsewhere. |
| `PROJECT_PYTHON` | Ingestion defaults to Airflow worker's Python (`sys.executable`); AI defaults to `/home/karan/venvs/mda_platform/bin/python`. Set an absolute executable path to override both. |
| `DBT_EXECUTABLE` | `dbt` on the worker's `PATH`. Set an absolute executable path if needed. |
| `DBT_PROJECT_DIR` | `PROJECT_DIR/analytics`; optional absolute override. |
| `DBT_PROFILES_DIR` | Inherited by dbt. Set to the directory containing your `profiles.yml` if it is outside dbt's normal profile location. |
| `GEMINI_API_KEY` | Required in the Airflow worker process environment for AI generation; inherited by the CLI, never included in command arguments. Missing or blank values fail before subprocess execution. |

No custom path variables are mandatory when the DAG stays in this checkout
and its default executables are available. Executable variables take a single
executable path/name, not shell commands or arguments. Set configuration in
the environment that starts Airflow and its task workers, not only an unrelated
terminal session.

Provide an `analytics` dbt profile and BigQuery authentication through your
existing external setup. Do not commit credentials or personal profiles.
The ingestion loaders and dbt sources currently reference
`mda-platform-2026`; configuring DAG paths does not change those warehouse
identifiers. The worker also needs write access to `data/raw/fx` and `ai/outputs`
in the checkout. Supply the Gemini key through your existing external environment
setup; do not put it in the DAG or commit it. AI reporting uses the latest KPI
month independently of the Airflow logical date. An empty KPI mart causes a
clear error. For a manual historical report, use `--month YYYY-MM`; an explicitly
requested month must exist. The daily schedule generates the latest month's report
repeatedly and retains the existing Airflow task retries in addition to the
CLI's built-in retry.

## Point Airflow at the repository DAG

From the repository root in your Linux/WSL shell, before starting your local
Airflow services:

```bash
export PROJECT_DIR="$(pwd)"
export AIRFLOW__CORE__DAGS_FOLDER="$PROJECT_DIR/orchestration/airflow/dags"
# If using a separate project environment, configure its executables:
# export PROJECT_PYTHON="/home/karan/venvs/mda_platform/bin/python"
# export DBT_EXECUTABLE="/home/karan/venvs/mda_platform/bin/dbt"
# export DBT_PROFILES_DIR="/path/to/dbt-profile-directory"
```

Restart the relevant Airflow services so they inherit the settings, confirm
that `fx_pipeline` is discovered without import errors, and unpause it when
ready to execute warehouse jobs. Pointing `dags_folder` here changes the DAG
directory for that Airflow installation; alternatively, symlink this DAG into
your existing DAG directory and set `PROJECT_DIR` explicitly.

Keep only one discovered DAG with the ID `fx_pipeline`; do not load both this
copy and the original WSL copy. The external WSL DAG also uses latest-month AI reporting.
The schedule timezone follows your Airflow configuration, as in the original.

The repository's GitHub Actions workflow runs pytest and dbt parse only. It
does not start Airflow, execute this DAG, or connect to BigQuery.
