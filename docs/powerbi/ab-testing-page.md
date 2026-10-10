# A/B Testing & Experimentation - Page 6

This is a **synthetic**, fictional checkout redesign, not an Olist production
experiment. All observations and diagnostics come from the existing deterministic
Python framework. Financial inputs are hypothetical. Missing payment-failure,
refund and checkout-latency measurements remain null, never zero.

## Reporting fixtures and regeneration

From the repository root, update the three version-controlled reporting fixtures:

```powershell
& .\.venv\Scripts\python.exe -m experimentation.export_powerbi --output-dir dashboard/data/ab_testing
```

The destination contains only `ab_variants.csv` (two rows), `ab_summary.csv` (one
row), and `ab_guardrails.csv` (three rows). These files are generated, never edited
by hand. The ordinary exports under `experimentation/outputs/powerbi/` are still
ignored. Regeneration does not change original experiment data or calculations.
The three small dashboard fixtures have narrow `.gitignore` exceptions.

Rates, relative uplift, MDE and confidence bounds in the fixtures are fractions.
The summary table is at experiment grain; variant and guardrail tables are at
experiment/variant and experiment/metric grain. The current fixtures contain one
experiment. All three tables are disconnected from each other and from Olist;
there are no new relationships, date tables or calculated tables.

## Import paths and safe loading

Power Query uses CSV import, UTF-8, quoted fields, explicit types and `en-US`
numeric parsing. Empty fields are converted to null before type conversion.
Counts use `Int64.Type`, numeric rates/CI bounds use `type number`, flags use
`type logical`, and labels use `type text`. Columns have `summarizeBy: none`.

**CSV imports are not automatically portable.** Each of the three new table TMDL
files contains an absolute `SourcePath` for this checkout. On another machine,
close Desktop and update only `SourcePath` in:

- `dashboard/Data Analytics.SemanticModel/definition/tables/ab_variants.tmdl`
- `dashboard/Data Analytics.SemanticModel/definition/tables/ab_summary.tmdl`
- `dashboard/Data Analytics.SemanticModel/definition/tables/ab_guardrails.tmdl`

Point each to the corresponding CSV in that machine's checkout of
`dashboard/data/ab_testing/`. Alternatively update the same step in Desktop's
Power Query editor after opening the project. Regeneration commands and these
documentation paths are repository-relative; Power BI's local file sources are
absolute. Service refresh would require an appropriate gateway/source strategy.

1. Save and close Desktop before any external changes. Reopen
   `dashboard/Data Analytics.pbip`; an old open session does not reload reliably
   and can overwrite external changes.
2. Keep automatic relationship detection disabled. Check that the three tables
   appear exactly once and remain disconnected; existing relationships are unchanged.
3. Load **only** the three local CSV tables. In Power Query, disable
   "Include in report refresh" for the existing warehouse queries if required
   before applying changes; preserve their original setting afterwards. Do not
   use a full-model Refresh or assume opening a PBIP materialises new partitions.
   Cancel if Desktop attempts a BigQuery refresh. No warehouse access was used
   during authoring.
4. Check the visuals and local values below, then save the updated Desktop cache.

## Measures and visual inventory

`ab_variants`: Variant Participants, Variant Conversions, Variant Conversion Rate,
True Generation Probability. The rate divides conversions by participants in the
current variant context, rather than averaging percentages.

`ab_summary`: Total Participants, Control Conversion, Treatment Conversion,
Absolute Uplift pp, Experiment P-value, Experiment Design Text, Inference Text,
Diagnostics Text, Quarterly Impact Text, Recommendation Text. Experiment-level
values use `SELECTEDVALUE`; p-values and stored rates are never summed.

`ab_guardrails`: Guardrail Availability Text, ordered by metric name. Missing
availability is displayed as "Not measured".

The inference panel is a bound native text card showing the observed difference
and explicitly labelled lower and upper absolute 95% interval endpoints. It does
not imply a confidence distribution or a probability of treatment success. Text
panels are native card visuals bound to multiline measures; rendering and wrapping
must be verified in Desktop.

| Visual | x | y | Width | Height |
| --- | ---: | ---: | ---: | ---: |
| Synthetic header | 64 | 36 | 844 | 104 |
| Bound design/seed/alpha note | 932 | 48 | 924 | 92 |
| Total Participants | 64 | 164 | 340 | 144 |
| Control Conversion | 428 | 164 | 340 | 144 |
| Treatment Conversion | 792 | 164 | 340 | 144 |
| Absolute Uplift | 1156 | 164 | 340 | 144 |
| P-value | 1520 | 164 | 336 | 144 |
| Control vs Treatment | 64 | 332 | 648 | 348 |
| Uplift, 95% CI and Statistical Inference | 736 | 332 | 1120 | 348 |
| Experiment Diagnostics | 64 | 704 | 584 | 248 |
| Guardrail Availability | 672 | 704 | 584 | 248 |
| Hypothetical Quarterly Impact | 1280 | 704 | 576 | 248 |
| Recommendation and Limitations | 64 | 976 | 1792 | 48 |
| Native six-page navigator | 64 | 4 | 1792 | 28 |

The canvas remains 1920 x 1080. Colours, borders and Segoe UI inherit the existing
page conventions. Comparison columns start at zero, with conversion percentage
labels and participant/conversion/true-probability tooltips. Explicit NoFilter
interactions prevent chart selection from changing experiment-level panels.
All native navigators now have six columns and use the original page order with
Page 6 appended. Pages 1-4 change only navigator x/width/column count. Page 5
additionally changes only the trend title, three corrupted note strings and the
numeric matrix column width (48 to 64); its calculations and interactions remain.

## Expected Desktop checks and limitations

The reproducible references are 8,866 participants; A 527/4,433 (11.888%); B
603/4,433 (13.603%); difference +1.714 pp; relative uplift +14.421%; p=0.015505;
95% CI +0.326 to +3.103 pp; MDE 2 pp; empirical power 79.6%; SRM p=1.000;
hypothetical quarterly net benefit EUR -19,427.02. These are verification
references, not hardcoded visual observations.

Confirm all bound text panels display every line without clipping, percentage/pp
formats are respected, the recommendation fits, all six navigation labels are
readable, Page 5 M0 shows 100.00% without truncation and its heatmap is unchanged.
Confirm clicking comparison bars changes no other panels and no duplicate semantic
projections or broken fields appear. Static JSON/TMDL checks cannot establish
Desktop rendering, actual DAX evaluation or successful CSV materialisation.

No full rollout is recommended: the projected benefit is negative under fixed
hypothetical economics, guardrails are missing and the experiment is synthetic.
Fixed balanced allocation guarantees the SRM result; it does not prove assignment
quality. Monte Carlo rejection rates are diagnostics, not extra experiment users.
Financial scenarios propagate only the effect interval; they exclude uncertainty
in traffic, costs, margins, persistence and generalisability. Real eligibility,
assignment and instrumentation remain unresolved.

## Authoring validation

- All 317 relevant Python tests passed, including three fixture/import-contract
  tests. Dashboard CSVs match the ordinary generated exports byte for byte.
- The complete model passed native TMDL deserialization: 27 tables, 19 unchanged
  relationships, three new Import partitions and 15 new measures. Format metadata
  is separate from expressions. DAX field and measure references passed static
  checks; this does not execute DAX or validate runtime semantics.
- Twenty-four new/modified report JSON files passed published Microsoft schema
  checks. Seven existing saved 2.13 visual definitions required a 2.12 compatibility
  check because Microsoft's 2.13 schema returns 404; their on-disk declarations
  were preserved. All new Page 6 visuals use the published 2.12 schema.
- Six pages and 69 globally unique visual IDs passed structural checks. Query
  projections, category/value/tooltips, interaction endpoints, new-page bounds,
  non-overlap and native six-column navigation passed static validation.
- Snapshot comparison confirms Pages 1-4 changed only navigator geometry/count;
  Page 5 changed only the three approved cosmetic visuals and its navigator.
  All 24 existing table definitions and existing relationships remain unchanged.
- `git diff --check` passed. No dependency changes, commits, pushes, BigQuery
  refreshes, dbt executions or modifications to experiment calculations occurred.

## Exact file inventory for this batch

New files:

- `dashboard/data/ab_testing/ab_variants.csv`
- `dashboard/data/ab_testing/ab_summary.csv`
- `dashboard/data/ab_testing/ab_guardrails.csv`
- `dashboard/Data Analytics.SemanticModel/definition/tables/ab_variants.tmdl`
- `dashboard/Data Analytics.SemanticModel/definition/tables/ab_summary.tmdl`
- `dashboard/Data Analytics.SemanticModel/definition/tables/ab_guardrails.tmdl`
- `dashboard/Data Analytics.Report/definition/pages/ab600170e8204dc8a601/page.json`
- Under that page's `visuals/`: `visual.json` in each of
  `ab600170e8204dc80001`, `ab600170e8204dc80002`, `ab600170e8204dc80003`,
  `ab600170e8204dc80004`, `ab600170e8204dc80005`, `ab600170e8204dc80006`,
  `ab600170e8204dc80007`, `ab600170e8204dc80008`, `ab600170e8204dc80009`,
  `ab600170e8204dc8000a`, `ab600170e8204dc8000b`, `ab600170e8204dc8000c`,
  `ab600170e8204dc8000d`, `ab600170e8204dc8000e`.
- `tests/test_ab_reporting_fixtures.py`
- `docs/powerbi/ab-testing-page.md` (this file)

Modified files:

- `.gitignore`
- `dashboard/Data Analytics.SemanticModel/definition/model.tmdl`
- `dashboard/Data Analytics.Report/definition/pages/pages.json`
- Under `dashboard/Data Analytics.Report/definition/pages/`, navigator
  `visual.json` files at:
  `8c0b4db3875209122ca8/visuals/a11e0000000000000101/visual.json`,
  `46270c605c5d9d24f127/visuals/a11e0000000000000102/visual.json`,
  `9f6b2e71a4304c8db520/visuals/a11e0000000000000103/visual.json`,
  `4c8a56e9d10347b29a60/visuals/a11e0000000000000104/visual.json`,
  `b5c0a170e8204dc8a501/visuals/b5c0a170e8204dc8ff01/visual.json`.
- Page 5's additional cosmetic files under the same pages directory:
  `b5c0a170e8204dc8a501/visuals/b5c0a170e8204dc80008/visual.json`,
  `b5c0a170e8204dc8a501/visuals/b5c0a170e8204dc80009/visual.json`,
  `b5c0a170e8204dc8a501/visuals/b5c0a170e8204dc8000b/visual.json`.

The batch contains 23 new files and 11 modified files, including files from prior
work that were already untracked. Fixtures are eligible for version control;
nothing has been staged or committed. Existing unrelated uncommitted work remains.
