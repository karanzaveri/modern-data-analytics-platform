# Checkout Redesign A/B Test — Synthetic Experiment Case Study

**Educational portfolio case study. All experiment observations are synthetic;
all financial inputs are hypothetical. This is not a real company's experiment
or a production deployment.**

The simulated redesign improves conversion with a statistically significant
effect, but does not cover the assumed implementation cost within one quarter.
Payment, refund, and latency guardrails were never measured. The stakeholder
recommendation is to **withhold a full-rollout recommendation**, validate a real
measurement plan, and revisit the economics before investing in a real test.

![Executive summary: synthetic conversion improvement, hypothetical negative quarterly net benefit, and missing guardrails](../docs/images/checkout-ab-test-executive-summary.png)

## Business problem and experiment design

A fictional e-commerce team is considering a checkout redesign intended to
reduce friction and increase purchases. The analytical question is whether the
redesign improves conversion enough to justify its cost without degrading
payment reliability, refunds, or checkout performance.

The primary metric is the **user purchase conversion rate**: users with a binary
purchase outcome of 1 divided by users in the variant. Every synthetic user has
one unique identifier, one variant, and one 0/1 outcome. The experimental unit is
the user, not the session or payment attempt. All differences below are
**treatment B minus control A**.

The two-sided hypotheses are `H0: p_B = p_A` and `H1: p_B != p_A`. The test can
detect a treatment decrease as well as an increase; significance alone does not
mean the treatment should launch.

| Planning parameter | Value |
| --- | --- |
| True generation / planning baseline, A | 12% |
| True generation / planning target, B | 14% |
| Two-sided significance level, alpha | 0.05 |
| Target statistical power | 0.80 |
| Planning minimum detectable effect (MDE) | 2 percentage points; 16.666667% relative to baseline |
| Allocation | Equal groups, 1:1 |
| Planned sample size | 4,433 users per arm; 8,866 total |
| Local random generator / outcome seed | NumPy PCG64 / 42 |

MDE here is the effect used for planning at the specified alpha and power,
not the smallest difference that could ever produce a significant p-value.
Phase 1 uses Cohen's h, the difference between arcsine-square-root transformed
rates, with Statsmodels `NormalIndPower.solve_power`. Each arm is rounded up.
This is a normal approximation, with no continuity correction.

A real experiment would require independent user assignment, persistent variant
membership, comparable eligibility and outcome collection, and no interference
between users. This dataset **does not implement independent random assignment**:
it fixes exactly 4,433 A users and 4,433 B users, then draws independent Bernoulli
purchase outcomes within each arm. Independence and stable rates are model
assumptions, not empirical proof of randomisation quality. The synthetic dataset
has no real recruitment dates or actual experiment duration.

## Observed synthetic results

These are the seed-42 results computed by `analyze_experiment`, not the true
probabilities used to generate the data:

| Variant | Users | Purchases | Observed conversion |
| --- | ---: | ---: | ---: |
| Control A | 4,433 | 527 | 11.888112% |
| Treatment B | 4,433 | 603 | 13.602527% |

The absolute uplift is **1.714414618 percentage points**. The relative uplift is
**14.421252%**, calculated against the observed A rate, not the 12% generation
probability. The observed effect differs from the 2-point planning effect
because outcomes are random.

The primary inference is a **two-sided pooled two-proportion z-test** with
`proportions_ztest`, passing B first. Its signed z-statistic is **2.42036020** and
its p-value is **0.0155051398**. Equal rates are rejected at alpha 0.05. This
conclusion concerns the synthetic model and fixed-horizon test; it does not
establish product-launch readiness.

The **95% Newcombe/Wilson confidence interval for p_B - p_A** is
**[0.003259318216, 0.031034163540]** in probability units, or
**[0.325931822, 3.103416354] percentage points**. Both bounds are positive.
The method combines separate Wilson score intervals and is explicitly selected
instead of relying on a library default.

Correct interpretation: under the method's assumptions, repeated intervals
constructed this way have approximately 95% coverage of the fixed true
conversion-rate difference. It is **not** a 95% probability that the true effect
lies in this particular realized interval, and it does not forecast future
traffic or profit. Newcombe's interval is not the inversion of the pooled z-test,
so its exclusion of zero and the test decision can disagree near the threshold.

## Sample Ratio Mismatch review

Phase 3 uses SciPy's Pearson chi-square goodness-of-fit test against a
prespecified allocation, with `k - 1` degrees of freedom and SRM threshold 0.001.
This threshold is a convention, not a universal rule.

| Allocation scenario | Observed A / B | Expected A / B | Chi-square | df | SRM p-value | SRM detected |
| --- | --- | --- | ---: | ---: | ---: | --- |
| Original fixed-size synthetic experiment | 4,433 / 4,433 | 4,433 / 4,433 | 0 | 1 | 1 | No |
| Independent 50/50 assignment, 10,000 synthetic users, seed 42 | 5,015 / 4,985 | 5,000 / 5,000 | 0.09 | 1 | 0.76417715562209465 | No |
| Deliberate mismatch, 10,000 participants | 6,500 / 3,500 | 5,000 / 5,000 | 900 | 1 | 9.8134278542964546e-198 | Yes |

The original dataset's perfect allocation is **guaranteed by construction**.
Its SRM result demonstrates checker functionality, not real-world randomisation
quality. The other scenarios are separate allocation-only demonstrations, with
no conversion records added to the original dataset. The healthy scenario permits
ordinary random imbalance; a healthy process can occasionally flag SRM by chance.
The deliberate mismatch is a reason to investigate assignment, eligibility,
logging, and exclusions before trusting a treatment-effect estimate.

SRM tests **participant allocation**, not purchase-conversion differences. A
passing SRM check cannot rule out logging defects, biased exclusions, correlated
assignments, or offsetting segment imbalances.

## Monte Carlo power and Type I errors

Phase 4 draws new independent binomial A/B conversion counts in every trial,
equivalent to summing independent Bernoulli user outcomes. It uses the same
pooled z-test as the primary analysis without storing millions of user records.
Each scenario has 1,000 trials, 4,433 users per arm, alpha 0.05, and seed 42.

| Measure | Effect scenario: A=12%, B=14% | Null scenario: A=B=12% |
| --- | ---: | ---: |
| Significant trials | 796 | 44 false positives |
| Non-significant trials | 204 | 956 |
| Undefined tests | 0 | 0 |
| Empirical rejection rate | **79.6% power** | **4.4% false-positive rate** |
| Theoretical reference | 80.0047535491% power | Nominal alpha, 5% |
| Mean observed uplift (percentage points) | 2.014527408076 | -0.036047823145 |
| Sample SD of uplift, ddof=1 (percentage points) | 0.716982385645 | 0.678273504357 |

Power is the probability of detecting the specified true effect; a Type II error
misses that effect. A Type I error rejects equal rates when the null is true.
Neither empirical power nor false-positive frequency is forced to match a target.
Their plug-in Monte Carlo standard errors are about **1.2743 percentage points**
and **0.6486 percentage points**, respectively.

Finite simulation noise, discrete counts, and differences between the pooled
z-test and Phase 1's arcsine power approximation explain differences from the
theoretical references. The two scenarios restart their own seed-42 generators;
no cross-scenario independence is claimed or needed. Tests occur once at their
fixed sample horizon, with no peeking or early stopping. These findings do not
validate repeated significance checks during a live experiment.

The four exploratory figures remain generated artifacts under the Git-ignored
`outputs/monte_carlo/` directory. They can be regenerated with the commands below;
the executive image above is stored in the version-controlled documentation tree.

## Hypothetical quarterly business impact

The projection compares giving B to **all 100,000 eligible users in one
hypothetical quarter (three months)** with giving A to those same users. It
assumes **EUR 12 contribution profit per incremental conversion**, **EUR 40,000
one-time implementation cost**, and **EUR 0 ongoing costs**. The entire one-time
cost is charged to this quarter. These are illustrative inputs, not company
financials, revenue observations, or a validated forecast.

Incremental conversions are `users * (p_B - p_A)`; contribution is incremental
conversions times profit contribution; net benefit subtracts implementation and
period ongoing costs. Fractional conversions are expected values.

| Effect scenario | Uplift (percentage points) | Incremental conversions | Contribution | Quarterly net benefit |
| --- | ---: | ---: | ---: | ---: |
| Lower 95% effect bound | 0.325931822 | 325.931821553 | EUR 3,911.18 | **EUR -36,088.82** |
| Observed point estimate | 1.714414618 | 1,714.414617640 | EUR 20,572.98 | **EUR -19,427.02** |
| Upper 95% effect bound | 3.103416354 | 3,103.416353952 | EUR 37,241.00 | **EUR -2,759.00** |

The required **break-even uplift is 3.333333333 percentage points**:
`100 * 40000 / (100000 * 12)`. The upper effect bound is still below this hurdle.
Under the supplied assumptions, even that scenario has negative quarterly net
benefit. Statistical significance is therefore not economic attractiveness.

These financial bounds are linear transformations of the conversion-effect
interval **conditional on fixed traffic, margins, and costs**. They are not a
prediction interval for future profit and do not quantify a probability of
profitability. Generalisability, stable eligible traffic, stable effects, and
stable per-conversion economics are unresolved assumptions. Refunds, payment
failures, latency, seasonality, capacity, taxes, discounting, and cost uncertainty
are not priced into this model.

## Missing guardrails and stakeholder recommendation

**Payment failures, refunds, and checkout latency were NOT observed in the
original synthetic conversion data.** All three original-data guardrails are
classified as **Insufficient data**, not safe or passed. Phase 5's separate
hypothetical examples demonstrate a within-threshold payment-failure comparison,
a breached refund threshold, and missing latency data. They are not evidence
about the primary experiment; their thresholds were not an actual prespecified
plan for that experiment.

The guardrail framework is a descriptive directional threshold check. A small
point difference, a nonsignificant ordinary test, or being within threshold
cannot establish non-inferiority or statistical safety.

**Recommendation: do not proceed to full rollout on this evidence.** The
conversion signal is statistically significant under the synthetic model, the
quarterly net benefit is negative under the hypothetical assumptions, and real
validity checks and all three guardrails remain unresolved. This is a portfolio
demonstration of decision discipline, not a real deployment decision.

Before a real experiment or rollout decision:

1. Validate user assignment, persistent exposure, eligibility, event logging,
   and exclusions; prespecify the fixed horizon and allocation checks.
2. Instrument payment failures and latency, and collect mature refund follow-up
   with comparable definitions and denominators in both arms.
3. Confirm relevant traffic, per-conversion contribution, implementation cost,
   ongoing costs, and the intended economic payback horizon.
4. Prespecify a real guardrail evaluation plan with sufficient data, then review
   experiment validity, effect uncertainty, and business impact together.

## Reproduction and final technical review

From the repository root, use Python 3.11 and an activated virtual environment:

```bash
python -m pip install -r requirements-docker.txt
python -m experimentation.sample_size
python -m experimentation.simulate_experiment
python -m experimentation.analyze_experiment
python -m experimentation.srm_check
python -m experimentation.srm_check --demo all
python -m experimentation.monte_carlo
python -m experimentation.monte_carlo --treatment-probability 0.12
python -m experimentation.business_impact
python -m experimentation.guardrails
python -m experimentation.executive_summary
python -m pytest -v
python -m pip check
```

The executive generator invokes the original seed-42 simulator **in memory**
and reuses the existing analysis and financial functions. It needs no ignored
CSV to render, writes no experiment data, and hardcodes no experimental
observations. Regenerate it with `python -m experimentation.executive_summary`; use `--output`
for a different PNG destination. Its source is [executive_summary.py](executive_summary.py).

The numerical snapshot was reproduced with NumPy 2.4.6, pandas 3.0.6, Statsmodels
0.14.6, SciPy 1.17.1, and Matplotlib 3.11.2. Preserve package versions and draw
order for exact reproduction. `requirements.txt` pins the broader development
environment; the shared Docker/CI file pins direct dependencies but resolves
NumPy and pandas transitively, so it is not a complete environment lock.

| Review area | Finding |
| --- | --- |
| Calculation consistency | Recomputed counts, signed effect, p-value, B-minus-A interval, and financial scenarios agree with existing reports. Statistical calculations unchanged. |
| Sample-size assumptions | Cohen's h normal approximation, equal allocation, two-sided test, upward rounding; not an exact power guarantee. |
| SRM interpretation | Original perfect balance is fixed by construction; the separate randomisation and mismatch demos have appropriate interpretations. |
| Monte Carlo | Local RNG, fresh trial draws, pooled test consistent with Phase 2; probabilistic tests use sampling tolerances rather than exact rejection counts. |
| Business and guardrails | Period costs and signed effects are consistent; conditional financial bounds and missing guardrails are explicit. No automatic rollout endorsement. |
| Tests and maintainability | Existing independent formula checks and cross-module consistency tests serve distinct purposes. No statistical refactor or broad test rewrite was justified; two figure integration tests add dynamic-data and image reproducibility coverage. |
| Packaging issue corrected | Docker omitted `ai/` and DAG files referenced by existing tests; shared CI dependencies omitted Google GenAI imported by existing tests. Added those files to image copying and the already-used GenAI pin to the shared dependency file. |
| Documentation corrected | Root README's original 70-test total updated to include the experimentation suite. Existing platform architecture and illustrations preserved. |

Final local validation: **377 tests passed** with `python -m pytest -v`.
All reproduction CLIs completed successfully, the executive image was generated
and visually reviewed, `python -m pip check` found no broken requirements, and
`git diff --check` passed. A separately regenerated seed-42 CSV matched the
original byte for byte; the original dataset was unchanged.

Validation is local Python validation, not a production, warehouse, hosted CI,
or Docker deployment claim. The chi-square and z-test approximations can be
unreliable for sparse data; aggregate counts do not prove independence or
randomisation quality. No sequential adjustment, multiple-comparison correction,
clustering analysis, non-inferiority inference, or real-company evidence is
included in this case study.
