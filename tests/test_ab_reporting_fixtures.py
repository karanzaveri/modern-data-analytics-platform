"""Reconcile the small dashboard fixtures and their disconnected import contract."""

from pathlib import Path

import pandas as pd

from experimentation.export_powerbi import export_powerbi_csvs


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "dashboard/data/ab_testing"
DEFINITION = ROOT / "dashboard/Data Analytics.SemanticModel/definition"


def test_dashboard_fixtures_match_deterministic_exporter(tmp_path):
    generated = export_powerbi_csvs(tmp_path)
    assert sorted(p.name for p in FIXTURES.iterdir()) == sorted(p.name for p in generated)
    for path in generated:
        assert (FIXTURES / path.name).read_bytes() == path.read_bytes()


def test_guardrail_import_preserves_missing_numeric_values():
    guardrails = pd.read_csv(FIXTURES / "ab_guardrails.csv")
    assert len(guardrails) == 3
    assert guardrails[["control_value", "treatment_value"]].isna().all().all()
    tmdl = (DEFINITION / "tables/ab_guardrails.tmdl").read_text()
    assert 'Table.ReplaceValue(Headers, "", null' in tmdl
    for column in ("control_value", "treatment_value"):
        assert f'{{"{column}", type number}}' in tmdl


def test_fixture_tables_are_referenced_once_and_disconnected():
    model = (DEFINITION / "model.tmdl").read_text()
    relationships = (DEFINITION / "relationships.tmdl").read_text()
    for name in ("ab_variants", "ab_summary", "ab_guardrails"):
        assert model.count(f"ref table {name}\n") == 1
        assert name not in relationships
        table = (DEFINITION / f"tables/{name}.tmdl").read_text()
        assert table.count(f"partition {name} = m") == 1
        assert 'mode: import' in table
        assert '"en-US"' in table
