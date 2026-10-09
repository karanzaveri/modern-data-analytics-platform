"""Check dynamic figure content and deterministic publication output."""

import hashlib

from PIL import Image
import pytest

from experimentation.analyze_experiment import analyze_experiment
from experimentation.business_impact import calculate_business_impact
from experimentation.executive_summary import create_summary_figure, main
from experimentation.simulate_experiment import simulate_experiment


def test_figure_uses_supplied_results_and_complete_comparison_ranges():
    # A different seed and arm size catches a figure that embeds the case-study observations.
    analysis = analyze_experiment(simulate_experiment(1000, seed=7))
    impact = calculate_business_impact(analysis.control.conversion_rate, analysis.treatment.conversion_rate,
                                       200000, 20, 10000,
                                       difference_confidence_interval=analysis.confidence_interval)
    figure = create_summary_figure(analysis, impact)
    rates, effect, finances, assumptions = figure.axes
    assert [bar.get_height() for bar in rates.patches] == pytest.approx(
        [100 * analysis.control.conversion_rate, 100 * analysis.treatment.conversion_rate])
    assert rates.get_ylim()[0] == 0
    left, right = effect.get_xlim()
    assert left < min(0, 100 * analysis.confidence_interval[0])
    assert right > max(100 * analysis.confidence_interval[1], impact.break_even_uplift_percentage_points)
    expected_net = [impact.lower.estimated_net_financial_benefit,
                    impact.point.estimated_net_financial_benefit, impact.upper.estimated_net_financial_benefit]
    assert [bar.get_height() for bar in finances.patches] == pytest.approx(expected_net)
    assert finances.get_ylim()[0] < min(0, *expected_net)
    assert finances.get_ylim()[1] > max(0, *expected_net)
    assert "200,000" in " ".join(text.get_text() for text in assumptions.texts)


def test_image_cli_is_reproducible_and_writes_only_the_png(tmp_path, capsys):
    destination = tmp_path / "summary.png"
    assert main(["--output", str(destination)]) == 0
    first_hash = hashlib.sha256(destination.read_bytes()).hexdigest()
    assert main(["--output", str(destination)]) == 0
    assert hashlib.sha256(destination.read_bytes()).hexdigest() == first_hash
    assert sorted(path.name for path in tmp_path.iterdir()) == ["summary.png"]
    with Image.open(destination) as image:
        assert image.size == (2240, 1440)
        assert "Synthetic" in image.info["Description"]
    assert "Saved reproducible executive summary" in capsys.readouterr().out
