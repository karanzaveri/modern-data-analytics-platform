import json
import re
from unittest.mock import Mock

import pytest

import ai.generate_insights as workflow


KPIS = {
    "order_month": "2018-07-01",
    "previous_month_revenue": 1012090.68,
    "order_count": 6292,
    "previous_month_order_count": 6159,
}


def response(headline="July 2018 performance summary."):
    return workflow.InsightResponse(
        headline=headline,
        summary="Orders were 6,292 compared with 6,159 in the previous month.",
        key_observations=[
            "The prior month's revenue was 1,012,090.68.",
            "Order volume increased.",
            "The supplied KPIs do not establish the cause.",
        ],
        watchout="Monitor performance; causes cannot be determined from these KPIs.",
    )


def test_valid_first_response_needs_one_generation(monkeypatch, capsys):
    valid = response()
    generate = Mock(return_value=valid)
    monkeypatch.setattr(workflow, "generate_insights", generate)

    assert workflow.generate_validated_insights(KPIS) is valid
    generate.assert_called_once_with(KPIS)
    assert capsys.readouterr().out == ""


def test_invalid_first_response_retries_and_returns_second(monkeypatch, capsys):
    invalid = response("Previous revenue was 1,012,903.68.")
    valid = response()
    generate = Mock(side_effect=[invalid, valid])
    monkeypatch.setattr(workflow, "generate_insights", generate)

    assert workflow.generate_validated_insights(KPIS) is valid
    assert generate.call_count == 2
    assert all(call.args == (KPIS,) for call in generate.call_args_list)
    output = capsys.readouterr().out
    assert "Numeric validation failed (1/2)" in output
    assert "1012903.68" in output


def test_two_invalid_responses_raise_chained_error(monkeypatch, capsys):
    generate = Mock(
        side_effect=[
            response("Previous revenue was 1,012,903.68."),
            response("Order volume increased by 133 orders."),
        ]
    )
    monkeypatch.setattr(workflow, "generate_insights", generate)

    with pytest.raises(ValueError, match="after 2 attempts") as error:
        workflow.generate_validated_insights(KPIS)

    assert generate.call_count == 2
    assert isinstance(error.value.__cause__, ValueError)
    assert "133.0" in str(error.value.__cause__)
    output = capsys.readouterr().out
    assert output.count("Numeric validation failed") == 2
    assert "(2/2)" in output


def test_explicit_single_attempt_does_not_retry(monkeypatch):
    generate = Mock(return_value=response("There were 9999 orders."))
    monkeypatch.setattr(workflow, "generate_insights", generate)

    with pytest.raises(ValueError, match="after 1 attempts"):
        workflow.generate_validated_insights(KPIS, max_attempts=1)
    generate.assert_called_once_with(KPIS)


@pytest.mark.parametrize("max_attempts", [0, -1, 1.5, True])
def test_invalid_attempt_limit_fails_before_generation(monkeypatch, max_attempts):
    generate = Mock()
    monkeypatch.setattr(workflow, "generate_insights", generate)

    with pytest.raises(ValueError, match="positive integer"):
        workflow.generate_validated_insights(KPIS, max_attempts=max_attempts)
    generate.assert_not_called()


def test_generation_errors_do_not_trigger_validation_retries(monkeypatch):
    generate = Mock(side_effect=RuntimeError("Generation service unavailable."))
    monkeypatch.setattr(workflow, "generate_insights", generate)

    with pytest.raises(RuntimeError, match="Generation service unavailable"):
        workflow.generate_validated_insights(KPIS)
    generate.assert_called_once_with(KPIS)


def test_cli_saves_only_validated_response_after_retry(monkeypatch, capsys):
    valid = response()
    generate = Mock(side_effect=[response("There were 9999 orders."), valid])
    fetch = Mock(return_value=KPIS)
    saved = []

    def save_json(insights, kpis):
        assert insights is valid
        assert generate.call_count == 2
        saved.append("json")
        return "validated.json"

    def save_markdown(insights, kpis):
        assert insights is valid
        assert saved == ["json"]
        saved.append("markdown")
        return "validated.md"

    monkeypatch.setattr("sys.argv", ["generate_insights", "--month", "2018-07"])
    monkeypatch.setattr(workflow, "fetch_kpis", fetch)
    monkeypatch.setattr(workflow, "generate_insights", generate)
    monkeypatch.setattr(workflow, "save_insights", save_json)
    monkeypatch.setattr(workflow, "save_markdown_report", save_markdown)

    workflow.main()

    fetch.assert_called_once_with("2018-07")
    assert saved == ["json", "markdown"]
    output = capsys.readouterr().out
    assert "AI response validation passed." in output
    assert "GENERATED RESPONSE BEFORE VALIDATION" not in output
    assert "KPI PAYLOAD" not in output
    assert "previous_month_revenue" not in output


def test_cli_does_not_save_when_both_responses_fail(monkeypatch):
    generate = Mock(return_value=response("There were 9999 orders."))
    save_json = Mock()
    save_markdown = Mock()
    monkeypatch.setattr("sys.argv", ["generate_insights", "--month", "2018-07"])
    monkeypatch.setattr(workflow, "fetch_kpis", Mock(return_value=KPIS))
    monkeypatch.setattr(workflow, "generate_insights", generate)
    monkeypatch.setattr(workflow, "save_insights", save_json)
    monkeypatch.setattr(workflow, "save_markdown_report", save_markdown)

    with pytest.raises(ValueError, match="after 2 attempts"):
        workflow.main()
    assert generate.call_count == 2
    save_json.assert_not_called()
    save_markdown.assert_not_called()


def test_cli_invalid_month_fails_before_external_calls(monkeypatch, capsys):
    fetch = Mock()
    generate = Mock()
    save_json = Mock()
    save_markdown = Mock()
    monkeypatch.setattr("sys.argv", ["generate_insights", "--month", "2018-99"])
    monkeypatch.setattr(workflow, "fetch_kpis", fetch)
    monkeypatch.setattr(workflow, "generate_insights", generate)
    monkeypatch.setattr(workflow, "save_insights", save_json)
    monkeypatch.setattr(workflow, "save_markdown_report", save_markdown)

    with pytest.raises(SystemExit) as error:
        workflow.main()
    assert error.value.code == 2
    assert "Month must use YYYY-MM format" in capsys.readouterr().err
    fetch.assert_not_called()
    generate.assert_not_called()
    save_json.assert_not_called()
    save_markdown.assert_not_called()


def test_cli_default_month_uses_latest_kpis(monkeypatch, capsys):
    latest_kpis = {**KPIS, "order_month": "2018-08-01"}
    valid = response()
    fetch = Mock(return_value=latest_kpis)
    generate = Mock(return_value=valid)
    monkeypatch.setattr("sys.argv", ["generate_insights"])
    monkeypatch.setattr(workflow, "fetch_kpis", fetch)
    monkeypatch.setattr(workflow, "generate_insights", generate)
    monkeypatch.setattr(workflow, "save_insights", Mock(return_value="validated.json"))
    monkeypatch.setattr(workflow, "save_markdown_report", Mock(return_value="validated.md"))

    workflow.main()

    fetch.assert_called_once_with(None)
    generate.assert_called_once_with(latest_kpis)
    assert "Reporting month: 2018-08" in capsys.readouterr().out


def test_cli_no_kpi_rows_fails_before_generation_or_output(monkeypatch):
    fetch = Mock(side_effect=ValueError("No KPI rows returned from BigQuery."))
    generate = Mock()
    save_json = Mock()
    save_markdown = Mock()
    monkeypatch.setattr("sys.argv", ["generate_insights"])
    monkeypatch.setattr(workflow, "fetch_kpis", fetch)
    monkeypatch.setattr(workflow, "generate_insights", generate)
    monkeypatch.setattr(workflow, "save_insights", save_json)
    monkeypatch.setattr(workflow, "save_markdown_report", save_markdown)

    with pytest.raises(ValueError, match="No KPI rows returned from BigQuery"):
        workflow.main()
    fetch.assert_called_once_with(None)
    generate.assert_not_called()
    save_json.assert_not_called()
    save_markdown.assert_not_called()


@pytest.mark.parametrize("observation_count", [3, 4])
def test_cli_overwrites_both_files_with_same_validated_response(
    monkeypatch, tmp_path, observation_count
):
    kpis = {
        **KPIS,
        "delivered_order_count": 6159,
        "unique_customers": 6230,
        "delivered_revenue": 1027903.86,
        "delivered_average_order_value": 166.89,
        "revenue_growth_pct": 1.56,
        "order_growth_pct": 2.03,
        "delivered_merchandise_value": 867953.46,
        "delivered_freight_value": 159853.82,
    }
    valid = workflow.InsightResponse(
        headline="July 2018 validated performance.",
        summary="Revenue grew by 1.56%; order growth was 2.03%.",
        key_observations=[
            "Delivered revenue was 1,027,903.86.",
            "Delivered orders totaled 6,159.",
            "Delivered average order value was 166.89.",
            "Unique customers totaled 6,230.",
        ][:observation_count],
        watchout="The supplied KPIs cannot establish the cause of the changes.",
    )
    output_dir = tmp_path / "outputs"
    output_dir.mkdir()
    json_path = output_dir / "monthly_insights_2018-07.json"
    markdown_path = output_dir / "monthly_insights_2018-07.md"
    stale = "STALE NARRATIVE " * 500
    json_path.write_text(json.dumps({"insights": {"summary": stale}}), encoding="utf-8")
    markdown_path.write_text(stale, encoding="utf-8")

    generate = Mock(return_value=valid)
    save_json = Mock(wraps=workflow.save_insights)
    save_markdown = Mock(wraps=workflow.save_markdown_report)
    monkeypatch.setattr(workflow, "__file__", str(tmp_path / "generate_insights.py"))
    monkeypatch.setattr("sys.argv", ["generate_insights", "--month", "2018-07"])
    monkeypatch.setattr(workflow, "fetch_kpis", Mock(return_value=kpis))
    monkeypatch.setattr(workflow, "generate_insights", generate)
    monkeypatch.setattr(workflow, "save_insights", save_json)
    monkeypatch.setattr(workflow, "save_markdown_report", save_markdown)

    workflow.main()

    generate.assert_called_once_with(kpis)
    save_json.assert_called_once_with(valid, kpis)
    save_markdown.assert_called_once_with(valid, kpis)
    assert save_json.call_args.args[0] is valid
    assert save_markdown.call_args.args[0] is valid
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = markdown_path.read_text(encoding="utf-8")
    assert payload == {"kpis": kpis, "insights": valid.model_dump()}
    assert "STALE NARRATIVE" not in markdown

    def section(name, following):
        return markdown.split(f"## {name}\n\n", 1)[1].split(
            f"\n\n## {following}", 1
        )[0]

    saved = payload["insights"]
    assert section("Headline", "Executive Summary") == saved["headline"]
    assert section("Executive Summary", "Key Observations") == saved["summary"]
    assert section("Key Observations", "Watchout") == "\n".join(
        f"- {item}" for item in saved["key_observations"]
    )
    assert section("Watchout", "KPI Snapshot") == saved["watchout"]


def test_generation_contract_requires_stakeholder_language(monkeypatch):
    kpis = {
        **KPIS,
        "previous_month_order_count": 6167,
        "delivered_order_count": 6159,
        "unique_customers": 6230,
        "delivered_revenue": 1027903.86,
        "delivered_average_order_value": 166.89,
        "revenue_growth_pct": 1.56,
        "order_growth_pct": 2.03,
        "delivered_merchandise_value": 867953.46,
        "delivered_freight_value": 159853.82,
    }
    natural = workflow.InsightResponse(
        headline="July 2018 delivered revenue increased by 1.56%.",
        summary="Order volume increased by 2.03% month over month.",
        key_observations=[
            "Delivered revenue was 1,027,903.86.",
            "Total orders reached 6,292.",
            "Delivered orders totaled 6,159.",
        ],
        watchout="The supplied KPIs cannot establish the cause of these changes.",
    )
    client = Mock()
    client.models.generate_content.return_value = Mock(text=natural.model_dump_json())
    client_factory = Mock(return_value=client)
    monkeypatch.setenv("GEMINI_API_KEY", "mock-key-for-test")
    monkeypatch.setattr(workflow.genai, "Client", client_factory)

    generated = workflow.generate_insights(kpis)

    client.models.generate_content.assert_called_once()
    prompt = client.models.generate_content.call_args.kwargs["contents"]
    rules = prompt.split("KPI data:", 1)[0]
    assert "Never expose raw field names, database column names, Python variable names," in rules
    assert "snake_case identifiers, or internal metric names in stakeholder-facing narrative" in rules
    assert "every headline, summary, key observation, and watchout" in rules
    assert "rewrite any raw column name, Python variable name," in rules
    assert "keep the required JSON response schema unchanged" in rules
    assert "Never repeat the raw numeric values of previous_month_revenue or" in rules
    assert "previous_month_order_count in any headline, summary, key observation, or watchout" in rules
    assert "prior-period fields are trusted context only; do not quote their values" in rules
    assert "use the already supplied revenue_growth_pct and" in rules
    assert "order_growth_pct instead of quoting previous-period amounts or counts" in rules
    assert "Current-period numeric values remain allowed: delivered_revenue, order_count," in rules
    assert "delivered_order_count, unique_customers, delivered_average_order_value," in rules
    assert "delivered_merchandise_value, and delivered_freight_value" in rules
    assert "You may compare current values with previous-period values" not in rules
    supplied = json.loads(prompt.split("KPI data:", 1)[1])
    assert supplied == kpis
    replacements = {
        "previous_month_revenue": "previous month's revenue",
        "previous_month_order_count": "previous month's order count",
        "revenue_growth_pct": "revenue growth",
        "order_growth_pct": "order growth",
        "delivered_order_count": "delivered orders",
        "order_count": "total orders",
    }
    for internal, business_label in replacements.items():
        assert f"{internal} -> {business_label}" in rules

    assert generated == natural
    narrative = " ".join(
        [generated.headline, generated.summary, *generated.key_observations, generated.watchout]
    )
    assert re.search(r"\b[A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]+\b", narrative) is None
    assert all(internal not in narrative for internal in replacements)
    for field in ["previous_month_revenue", "previous_month_order_count"]:
        value = kpis[field]
        assert str(value) not in narrative
        assert f"{value:,}" not in narrative
