# Page 6 visual redesign

Page 6 uses Page 5's Segoe UI, navy/slate typography, white backgrounds, subtle rounded borders and 24-unit panel padding. Its 1920 x 1080 canvas, original KPI positions, disconnected source tables and six-page navigation are preserved.

The visible presentation uses 18 native visual objects. Diagnostics show four metrics rather than ten; quarterly economics shows four metrics with net benefit emphasised. The guardrail table wraps the existing validated Guardrail Availability Text measure: each metric is displayed on a separate line as Not measured. Raw availability remains missing and numeric observations remain null.

No semantic model, existing DAX, relationships, Python exports or CSV contents were changed.

## Units

Observed uplift uses the existing Absolute Uplift pp measure. CI endpoints, planned MDE and break-even bind directly to fractional numeric source columns. Native percentage formatting multiplies their displayed magnitude by 100. They are conversion-rate differences, so their displayed percentage magnitudes are percentage-point differences. Relative uplift is a relative percentage and must not be interpreted as percentage points.

No interval distribution, decorative interval chart or new statistical calculation is introduced. The native numeric-card presentation displays both supplied interval endpoints.

## Secondary fields and assumptions

The complete local reporting sources remain available here:

- [Experiment summary](../../dashboard/data/ab_testing/ab_summary.csv): one experiment row.
- [Variant observations](../../dashboard/data/ab_testing/ab_variants.csv): control and treatment rows.
- [Guardrail availability](../../dashboard/data/ab_testing/ab_guardrails.csv): three metric rows.

Use the summary CSV to inspect the fields omitted from the visible four-row panels:

| Context | Source fields |
| --- | --- |
| Sample planning | planned_sample_size_per_arm, actual_sample_size_per_arm, planned_mde, planned_relative_mde, target_power, theoretical_power |
| Monte Carlo diagnostics | monte_carlo_random_seed, power_simulation_trials, power_significant_trials, power_non_significant_trials, power_undefined_trials, empirical_power, null_simulation_trials, null_false_positive_trials, null_non_significant_trials, null_undefined_trials, empirical_false_positive_rate, nominal_false_positive_rate |
| Allocation diagnostics | srm_statistic, srm_degrees_of_freedom, srm_p_value, srm_threshold, srm_detected, allocation_note |
| Financial assumptions | financial_assumptions_are_hypothetical, financial_period, currency, projected_eligible_users, contribution_profit_per_conversion, implementation_cost, ongoing_costs |
| Financial outputs and scenarios | expected_incremental_conversions, expected_incremental_contribution, estimated_net_financial_benefit, lower_net_financial_scenario, upper_net_financial_scenario, break_even_uplift, economically_attractive_under_assumptions |
| Interpretation | rollout_readiness, limitations, statistical_test_method, confidence_interval_method, confidence_level, difference_orientation |

Financial scenarios propagate the supplied effect interval under fixed hypothetical traffic and economics. They are not profit prediction intervals. The CSV preserves the explicit ongoing-cost zero; it is not a substitute for missing guardrail observations.

## Validation and Desktop review

Static checks cover page preservation, unique IDs, field references, query projections, explicit NoFilter interactions, bounds, non-overlap, formatting properties, source text dimensions and compact four-row layout budgets. Native TMDL parsing and git diff --check are also required.

Desktop must verify the four-field header layout, three-value inference card, wrapped method/guardrail text, four-row matrices, negative net benefit emphasis, footer readability, absence of scrollbars and save/reopen behaviour. Static checks do not execute DAX or prove rendered layout. Saved visual definitions declaring 2.13 use the published 2.12 compatibility schema during offline validation.
