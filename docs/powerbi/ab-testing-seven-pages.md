# A/B Testing: seven-page report layout

Page 6 is **A/B Results**; Page 7 is **A/B Quality & Decision**. Their full canvas titles are A/B Testing | Experiment Results and A/B Testing | Quality & Business Decision. Pages 1-5 keep their existing names and content. All seven pages use the existing project and imports.

## Design and data binding

The design follows Page 5: Segoe UI, light grey canvas, white rounded panels, navy/slate text and teal/blue accents. Canvas titles use 28 pt, KPI values 30-32 pt, panel titles 16-17 pt and core table content 12-16 pt. Most panel padding is 24 canvas units.

Page 6 preserves the five original KPI bindings and positions. The comparison chart is enlarged and retains its zero-based percentage axis. The inference table binds the existing multiline Inference Text measure and wraps its individual lines; it displays the effect and CI in percentage points without introducing new measures or statistical calculations. Relative uplift has a separate supporting card.

Page 7 quality and financial cards use Maximum of the existing single-row ab_summary columns, with visual-level formats. Planned MDE and break-even remain fractional numeric bindings formatted as percentages: their conversion-rate-difference magnitudes are percentage-point differences. Relative uplift is a relative percentage, not percentage points. No DAX, CSV, relationship or statistical logic changes were made.

The guardrail table groups by ab_guardrails[guardrail_metric] and evaluates the existing Guardrail Availability Text measure in each metric context. This yields three actual rows with the validated Not measured wording; its explanatory text remains within each wrapped observation cell. Raw availability remains missing and control/treatment observations remain null.

All financial values are hypothetical. Scenario cards propagate only the effect interval under fixed traffic and economics; they are not profit prediction intervals. The decision table binds Recommendation Text rather than hardcoding experimental outcomes.

## Visual inventory

Coordinates are x, y, width, height in the 1920 x 1080 canvas. IDs map directly to visuals/<ID>/visual.json under their page directory.

### Page 6 - Experiment Results

| Visual ID | Native type | Position | Binding / content |
| --- | --- | --- | --- |
| `ab600170e8204dc8000e` | pageNavigator | 64, 4, 1792, 28 |  |
| `ab600170e8204dc80001` | textbox | 64, 44, 1136, 104 | SYNTHETIC EXPERIMENT |
| `ab600170e8204dc80002` | tableEx | 1224, 48, 632, 92 | Seed; Users / arm; Alpha; Confidence |
| `ab600170e8204dc80003` | cardVisual | 64, 164, 340, 144 | Total Participants |
| `ab600170e8204dc80004` | cardVisual | 428, 164, 340, 144 | Control Conversion |
| `ab600170e8204dc80005` | cardVisual | 792, 164, 340, 144 | Treatment Conversion |
| `ab600170e8204dc80006` | cardVisual | 1156, 164, 340, 144 | Absolute Uplift pp |
| `ab600170e8204dc80007` | cardVisual | 1520, 164, 336, 144 | Experiment P-value |
| `ab600170e8204dc80008` | clusteredColumnChart | 64, 332, 912, 540 | variant_label; Variant Participants; Variant Conversions; True Generation Probability; Variant Conversion Rate |
| `ab600170e8204dc80009` | tableEx | 1000, 332, 856, 348 | Observed effect, interval and test |
| `ab600170e8204dc80015` | cardVisual | 1000, 704, 300, 168 | Relative uplift |
| `ab600170e8204dc80019` | textbox | 1324, 704, 532, 168 | Synthetic, fixed-horizon evidence only. |
| `ab600170e8204dc8001a` | textbox | 64, 904, 1792, 104 | INTERPRETING THE RESULT |

### Page 7 - Quality & Business Decision

| Visual ID | Native type | Position | Binding / content |
| --- | --- | --- | --- |
| `ab700170e8204dc800ff` | pageNavigator | 64, 4, 1792, 28 |  |
| `ab700170e8204dc80001` | textbox | 64, 44, 1136, 104 | SYNTHETIC EXPERIMENT |
| `ab700170e8204dc80002` | tableEx | 1224, 48, 632, 92 | Seed; Users / arm; Alpha; Confidence |
| `ab700170e8204dc80003` | cardVisual | 64, 164, 592, 144 | Incremental contribution (EUR) |
| `ab700170e8204dc80004` | cardVisual | 664, 164, 592, 144 | Implementation cost (EUR) |
| `ab700170e8204dc80005` | cardVisual | 1264, 164, 592, 144 | Net benefit (EUR) / Hypothetical |
| `ab700170e8204dc80006` | textbox | 64, 332, 888, 28 | Experiment quality |
| `ab700170e8204dc8000e` | tableEx | 976, 332, 880, 352 | Metric; Availability and interpretation |
| `ab700170e8204dc80007` | cardVisual | 64, 376, 280, 116 | Planned MDE (rate difference) |
| `ab700170e8204dc80008` | cardVisual | 368, 376, 280, 116 | Target power |
| `ab700170e8204dc80009` | cardVisual | 672, 376, 280, 116 | Theoretical power |
| `ab700170e8204dc8000a` | cardVisual | 64, 508, 280, 116 | Empirical power |
| `ab700170e8204dc8000b` | cardVisual | 368, 508, 280, 116 | SRM p-value |
| `ab700170e8204dc8000c` | cardVisual | 672, 508, 280, 116 | Empirical false positives |
| `ab700170e8204dc8000d` | tableEx | 64, 640, 888, 40 | Power simulation trials; Null simulation trials |
| `ab700170e8204dc8000f` | textbox | 64, 684, 888, 20 | Simulation trials are not participants; allocation balance is fixed by construction. |
| `ab700170e8204dc80015` | textbox | 64, 708, 1792, 20 | HYPOTHETICAL ECONOMICS / Effect scenarios are not prediction intervals. Rate differences shown as percentages represent percentage-point differences. |
| `ab700170e8204dc80010` | cardVisual | 64, 728, 592, 112 | Break-even (rate difference) |
| `ab700170e8204dc80011` | cardVisual | 664, 728, 592, 112 | Lower effect scenario (EUR) |
| `ab700170e8204dc80012` | cardVisual | 1264, 728, 592, 112 | Upper effect scenario (EUR) |
| `ab700170e8204dc80013` | tableEx | 64, 856, 1792, 72 | Eligible users / quarter; Profit / conversion (EUR); Ongoing costs (EUR); Hypothetical period |
| `ab700170e8204dc80014` | tableEx | 64, 952, 1792, 104 | No full rollout recommended under the stated assumptions |

## Navigation and interactions

All seven native navigators use seven columns with their existing styling and geometry. Page 7 is appended after Page 6. The prior active-page choice is preserved. Short report-tab names are used for the two A/B pages because the native navigator exposes no documented display-name alias. All chart/table selections on the A/B pages have explicit NoFilter interactions against other data panels.

## Source details

Secondary technical fields remain available in [ab_summary.csv](../../dashboard/data/ab_testing/ab_summary.csv), [ab_variants.csv](../../dashboard/data/ab_testing/ab_variants.csv) and [ab_guardrails.csv](../../dashboard/data/ab_testing/ab_guardrails.csv). All original financial assumptions, scenario endpoints, simulation diagnostics and source definitions remain intact.

## Validation

- Seven pages; 90 globally unique visual IDs; 13 visuals on Page 6 and 22 on Page 7.
- Native TMDL parsing: 27 tables and 19 relationships.
- 43 page, metadata and visual-schema checks. Saved 2.13 definitions receive 2.12 compatibility checks; new definitions use the published 2.12 schema where possible.
- 107 JSON/metadata files parse; 140 project text files are valid UTF-8 without BOM.
- Protected-page preservation, model and CSV hashes, field references, projection identities, interaction endpoints, bounds, non-overlap, text glyph widths, navigation labels and wrapped-panel layout budgets pass.
- No warehouse refresh, dbt, BigQuery, commit, push or PR.

Desktop still must confirm card formats and values, grouped guardrail-measure evaluation, table wrapping, no scrolling/clipping, the zero-based chart, navigation labels, isolated selections and save/reopen behaviour. Static checks do not execute DAX or prove rendered layout.

## Exact file changes

### Modified

- `dashboard/Data Analytics.Report/definition/pages/46270c605c5d9d24f127/visuals/a11e0000000000000102/visual.json`
- `dashboard/Data Analytics.Report/definition/pages/4c8a56e9d10347b29a60/visuals/a11e0000000000000104/visual.json`
- `dashboard/Data Analytics.Report/definition/pages/8c0b4db3875209122ca8/visuals/a11e0000000000000101/visual.json`
- `dashboard/Data Analytics.Report/definition/pages/9f6b2e71a4304c8db520/visuals/a11e0000000000000103/visual.json`
- `dashboard/Data Analytics.Report/definition/pages/ab600170e8204dc8a601/page.json`
- `dashboard/Data Analytics.Report/definition/pages/ab600170e8204dc8a601/visuals/ab600170e8204dc80001/visual.json`
- `dashboard/Data Analytics.Report/definition/pages/ab600170e8204dc8a601/visuals/ab600170e8204dc80002/visual.json`
- `dashboard/Data Analytics.Report/definition/pages/ab600170e8204dc8a601/visuals/ab600170e8204dc80003/visual.json`
- `dashboard/Data Analytics.Report/definition/pages/ab600170e8204dc8a601/visuals/ab600170e8204dc80004/visual.json`
- `dashboard/Data Analytics.Report/definition/pages/ab600170e8204dc8a601/visuals/ab600170e8204dc80005/visual.json`
- `dashboard/Data Analytics.Report/definition/pages/ab600170e8204dc8a601/visuals/ab600170e8204dc80006/visual.json`
- `dashboard/Data Analytics.Report/definition/pages/ab600170e8204dc8a601/visuals/ab600170e8204dc80007/visual.json`
- `dashboard/Data Analytics.Report/definition/pages/ab600170e8204dc8a601/visuals/ab600170e8204dc80008/visual.json`
- `dashboard/Data Analytics.Report/definition/pages/ab600170e8204dc8a601/visuals/ab600170e8204dc80009/visual.json`
- `dashboard/Data Analytics.Report/definition/pages/ab600170e8204dc8a601/visuals/ab600170e8204dc8000e/visual.json`
- `dashboard/Data Analytics.Report/definition/pages/ab600170e8204dc8a601/visuals/ab600170e8204dc80019/visual.json`
- `dashboard/Data Analytics.Report/definition/pages/ab600170e8204dc8a601/visuals/ab600170e8204dc8001a/visual.json`
- `dashboard/Data Analytics.Report/definition/pages/b5c0a170e8204dc8a501/visuals/b5c0a170e8204dc8ff01/visual.json`
- `dashboard/Data Analytics.Report/definition/pages/pages.json`

### Added

- `dashboard/Data Analytics.Report/definition/pages/ab600170e8204dc8a601/visuals/ab600170e8204dc80015/visual.json`
- `dashboard/Data Analytics.Report/definition/pages/ab700170e8204dc8a701/page.json`
- `dashboard/Data Analytics.Report/definition/pages/ab700170e8204dc8a701/visuals/ab700170e8204dc80001/visual.json`
- `dashboard/Data Analytics.Report/definition/pages/ab700170e8204dc8a701/visuals/ab700170e8204dc80002/visual.json`
- `dashboard/Data Analytics.Report/definition/pages/ab700170e8204dc8a701/visuals/ab700170e8204dc80003/visual.json`
- `dashboard/Data Analytics.Report/definition/pages/ab700170e8204dc8a701/visuals/ab700170e8204dc80004/visual.json`
- `dashboard/Data Analytics.Report/definition/pages/ab700170e8204dc8a701/visuals/ab700170e8204dc80005/visual.json`
- `dashboard/Data Analytics.Report/definition/pages/ab700170e8204dc8a701/visuals/ab700170e8204dc80006/visual.json`
- `dashboard/Data Analytics.Report/definition/pages/ab700170e8204dc8a701/visuals/ab700170e8204dc80007/visual.json`
- `dashboard/Data Analytics.Report/definition/pages/ab700170e8204dc8a701/visuals/ab700170e8204dc80008/visual.json`
- `dashboard/Data Analytics.Report/definition/pages/ab700170e8204dc8a701/visuals/ab700170e8204dc80009/visual.json`
- `dashboard/Data Analytics.Report/definition/pages/ab700170e8204dc8a701/visuals/ab700170e8204dc8000a/visual.json`
- `dashboard/Data Analytics.Report/definition/pages/ab700170e8204dc8a701/visuals/ab700170e8204dc8000b/visual.json`
- `dashboard/Data Analytics.Report/definition/pages/ab700170e8204dc8a701/visuals/ab700170e8204dc8000c/visual.json`
- `dashboard/Data Analytics.Report/definition/pages/ab700170e8204dc8a701/visuals/ab700170e8204dc8000d/visual.json`
- `dashboard/Data Analytics.Report/definition/pages/ab700170e8204dc8a701/visuals/ab700170e8204dc8000e/visual.json`
- `dashboard/Data Analytics.Report/definition/pages/ab700170e8204dc8a701/visuals/ab700170e8204dc8000f/visual.json`
- `dashboard/Data Analytics.Report/definition/pages/ab700170e8204dc8a701/visuals/ab700170e8204dc80010/visual.json`
- `dashboard/Data Analytics.Report/definition/pages/ab700170e8204dc8a701/visuals/ab700170e8204dc80011/visual.json`
- `dashboard/Data Analytics.Report/definition/pages/ab700170e8204dc8a701/visuals/ab700170e8204dc80012/visual.json`
- `dashboard/Data Analytics.Report/definition/pages/ab700170e8204dc8a701/visuals/ab700170e8204dc80013/visual.json`
- `dashboard/Data Analytics.Report/definition/pages/ab700170e8204dc8a701/visuals/ab700170e8204dc80014/visual.json`
- `dashboard/Data Analytics.Report/definition/pages/ab700170e8204dc8a701/visuals/ab700170e8204dc80015/visual.json`
- `dashboard/Data Analytics.Report/definition/pages/ab700170e8204dc8a701/visuals/ab700170e8204dc800ff/visual.json`

### Removed superseded visuals

- `dashboard/Data Analytics.Report/definition/pages/ab600170e8204dc8a601/visuals/ab600170e8204dc8000a/visual.json`
- `dashboard/Data Analytics.Report/definition/pages/ab600170e8204dc8a601/visuals/ab600170e8204dc8000b/visual.json`
- `dashboard/Data Analytics.Report/definition/pages/ab600170e8204dc8a601/visuals/ab600170e8204dc8000c/visual.json`
- `dashboard/Data Analytics.Report/definition/pages/ab600170e8204dc8a601/visuals/ab600170e8204dc8000d/visual.json`
- `dashboard/Data Analytics.Report/definition/pages/ab600170e8204dc8a601/visuals/ab600170e8204dc80017/visual.json`
- `dashboard/Data Analytics.Report/definition/pages/ab600170e8204dc8a601/visuals/ab600170e8204dc8001c/visual.json`

This documentation file, `docs/powerbi/ab-testing-seven-pages.md`, is also new.
