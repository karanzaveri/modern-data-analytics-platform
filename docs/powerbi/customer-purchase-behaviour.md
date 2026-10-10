# Page 5: Customer Purchase Behaviour enhancement

The project entry point is `dashboard/Data Analytics.pbip`. This enhancement updates
the existing Customer Retention & Cohorts page (`b5c0a170e8204dc8a501`); it does not
create a report page or replace the existing semantic model.

## Import definition and measures

`dashboard/Data Analytics.SemanticModel/definition/tables/customer_repeat_behavior.tmdl`
defines exactly one Import partition, using the existing cohort mart's BigQuery
connection/navigation convention to select
`mda-platform-2026.analytics_dev.customer_repeat_behavior`.
No warehouse query or data refresh was executed during authoring. The table has
ten source columns, native Boolean flags, DATE-backed cohort_month and nullable
has_returned_within_3_months / first_return_month_age columns. No relationships,
automatic relationship detection settings or local date tables were added.

The seven requested measures are:

- Repeat Customers: distinct customer IDs, with the current cohort selection
  transferred using CALCULATETABLE, REMOVEFILTERS, TREATAS and KEEPFILTERS.
- Single-purchase Customers: the base count restricted to Single-purchase.
- Same-month Repeat Customers: the base count restricted to Same-month repeat only.
- Cross-month Repeat Customers: the base count restricted to Cross-month repeat.
- Complete Three-month Follow-up Customers: the base count with complete follow-up.
- Three-month Returning Customers: complete-follow-up customers with a TRUE outcome.
- Three-month Return Rate: returning customers divided by complete-follow-up customers.

The additional hidden Customer Segment Share measure supports the chart tooltip:
the segment count divided by the base count with only customer_segment filtering
removed. Counts use `#,0`; rates use `0.000%`. The complete DAX definitions are in
the new TMDL file, with expression indentation distinct from measure metadata.
Existing filters on the repeat mart are intersected, not overwritten. Incomplete
three-month outcomes never become FALSE or enter the complete-follow-up denominator.
The KPI is cumulative M1-M3 return, not periodic M3 retention or a sum of monthly rates.

## Current layout and interactions

This inventory supersedes the affected coordinates in customer-retention-page.md.
The five cards occupy y164, height144, at x64/428/792/1156/1520, with widths
340/340/340/340/336. The new card displays Three-month Return Rate. The matrix stays
at (64,332,1120,548), and the trend stays at (1208,332,648,348).

The former Original Cohort Size visual is a horizontal Customer Purchase Behaviour
chart at (1208,704,648,320), with customer_segment as Category and Repeat Customers
as Y. It uses descending count sorting, a zero-based count axis, unscaled integer
labels and the teal palette. Segment share is a tooltip; original cohort size is
available in the trend tooltip. No dynamic subtitle measure is used.

The existing raw cohort_month slicer and January 2017-May 2018 page window are
preserved. TREATAS passes their combined selection to the disconnected repeat mart.
The slicer filters both new visuals, and explicit NoFilter rules prevent the bar
chart from filtering other analytical visuals or the slicer. Existing rules remain.
The original four pages, native navigation, matrix, measures, relationships, source
queries and local date tables are preserved.

## Safe reload and Desktop checks

1. Desktop was saved and closed before the external batch. Reopen
   `dashboard/Data Analytics.pbip`. Do not save an older in-memory session over it.
2. Check the table appears once, with the intended types and no relationships.
   Keep automatic relationship detection disabled before any subsequent data load.
3. Refresh the new table explicitly only when warehouse access is authorized.
   Reopening the project alone does not load its new Import partition. Avoid a
   full-model refresh unless intended. Both marts must reflect the same cutoff/build.
4. Confirm the five cards fit, three-decimal percentages are shown, category labels
   are readable, outside-end counts fit, bars are sorted and start at zero, and
   both tooltips render. Static PBIR validation cannot establish these facts.
5. Check the supplied Jan 2017-May 2018 reference results: 75,123 customers;
   72,527 Single-purchase; 1,612 Cross-month repeat; 984 Same-month repeat only;
   and 790 / 75,123 = 1.052% three-month return. These references were not
   revalidated with warehouse queries or DAX execution during authoring.
6. Select individual/multiple cohorts and verify both new visuals respond. Clicking
   segment bars must not change the existing KPIs, matrix, trend or slicer.
7. Before extending the reporting window, test incomplete-follow-up cohorts:
   they must be excluded from the three-month denominator. A zero denominator
   returns a blank rate. Segment counts still include eligible incomplete cohorts.
8. Confirm all five navigation tabs and original report pages still work, then save.

No dbt execution, BigQuery queries, dependency installation, commits or pushes
are part of this implementation. Loading data and confirming Desktop visuals
remain explicit user actions.

## Authoring validation results

- Full native TMDL deserialization passed: 24 tables, 19 unchanged relationships,
  one new Import partition, ten new source columns and eight new measures. Measure
  formatString metadata parsed separately from DAX; the new table is disconnected.
- Fifteen Page 5/page-order PBIR files passed JSON schema checks. Four used their
  exact published schemas; eleven saved Desktop 2.13 visuals were checked against
  published 2.12 compatibility schemas because the 2.13 schema is unavailable.
  Existing schema declarations on disk were not changed.
- All five pages remain; 55 report visual IDs are globally unique. Query roles,
  field references, duplicate projections, axis/label settings, interaction endpoints,
  exact card placements, canvas bounds and non-overlap passed static checks.
- File hashes confirm the original four pages, existing table TMDL definitions,
  relationships, local date tables, matrix, navigation and dbt/experimentation code
  are unchanged from the saved pre-batch snapshot. The trend changed only for its tooltip.
- `git diff --check` passed, with additional whitespace checks for untracked files.
  `git status` includes existing uncommitted work as well as this batch.
- These checks do not execute DAX or validate imported results/rendering in Desktop.
