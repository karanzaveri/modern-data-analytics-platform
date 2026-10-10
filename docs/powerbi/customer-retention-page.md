# Customer Retention & Cohorts ? Page 5

Implemented in the existing `dashboard/Data Analytics.pbip`. Page ID:
`b5c0a170e8204dc8a501`.

## Saved semantic model

The Desktop-generated cohort import has the six expected columns and correct
DATE-backed dateTime / int64 / double types. It imports
`mda-platform-2026.analytics_dev.customer_cohort_retention` once. Its two existing
local date tables and relationships are preserved. The separate `analytics_dev`
table is schema-navigation metadata, not a duplicate cohort import. All six prior
business tables, measures, relationships and the model diagram are preserved.
No BigQuery refresh or query was performed. The imported 278-row count and 11 dbt
mart-test results are user-reported, not revalidated by this implementation.

## Page behaviour

Canvas 1920 ? 1080; existing Segoe UI typography, colours, borders and padding.
Page-local acquisition-cohort filter: January 2017 through May 2018 inclusive.
This selects 17 comparable cohorts with complete M1?M3 calendar observation
through the August 2018 cutoff. The cohort-month slicer selects subsets within
this default window; extending it requires changing the page's cohort filter.
No acquisition filter is applied to activity_month. No slicer sync is configured.

Four cards show cohort customers and weighted M1/M2/M3 retention. The matrix
uses raw cohort_month rows, numeric month-age columns and the Cohort Retention
measure. Both subtotal and grand-total directions are disabled. M0 is neutral
grey; future cells remain blank and observed zero-activity cells are white 0%.
M1+ teal bands are >0?<0.5%, 0.5?<1%, 1?<2%, and ?2%. The matrix can scroll
horizontally; it does not compress all ages into illegible columns.

Supporting charts show M1/M2/M3 by acquisition cohort and original cohort size.
The cohort slicer filters all seven data visuals. Matrix and chart selections
are explicitly prevented from filtering the cards, other data visuals or slicer.
Native navigators retain their existing position, styling and behaviour; only
columnCount changes from four to five on the original pages. The fifth page is
appended to pageOrder; Executive Overview remains the active saved page.

## Measures

These definitions are stored in
`dashboard/Data Analytics.SemanticModel/definition/tables/customer_cohort_retention.tmdl`.
Counts are formatted as whole numbers; matrix rates as 0.00%; weighted KPI rates
as 0.000%. The colour measure is hidden. Dates display MMM yyyy; month age,
cohort_size and retention_rate use summarizeBy none to discourage unsafe
implicit aggregation. Import partitions, lineage tags and date variations remain intact.

```dax
Cohort Customers =
CALCULATE(
    SUMX(
        VALUES(customer_cohort_retention[cohort_month]),
        CALCULATE(MAX(customer_cohort_retention[cohort_size]))
    ),
    REMOVEFILTERS(customer_cohort_retention[months_since_first_purchase]),
    REMOVEFILTERS(customer_cohort_retention[activity_month])
)

Cohort Size =
IF(
    HASONEVALUE(customer_cohort_retention[cohort_month]),
    CALCULATE(
        MAX(customer_cohort_retention[cohort_size]),
        REMOVEFILTERS(customer_cohort_retention[months_since_first_purchase]),
        REMOVEFILTERS(customer_cohort_retention[activity_month])
    )
)

Cohort Retention =
IF(
    HASONEVALUE(customer_cohort_retention[months_since_first_purchase]),
    DIVIDE(
        SUM(customer_cohort_retention[retained_customers]),
        SUM(customer_cohort_retention[cohort_size])
    )
)

Weighted M1 Retention =
CALCULATE(
    [Cohort Retention],
    REMOVEFILTERS(customer_cohort_retention[months_since_first_purchase]),
    REMOVEFILTERS(customer_cohort_retention[activity_month]),
    customer_cohort_retention[months_since_first_purchase] = 1
)

Weighted M2 Retention =
CALCULATE(
    [Cohort Retention],
    REMOVEFILTERS(customer_cohort_retention[months_since_first_purchase]),
    REMOVEFILTERS(customer_cohort_retention[activity_month]),
    customer_cohort_retention[months_since_first_purchase] = 2
)

Weighted M3 Retention =
CALCULATE(
    [Cohort Retention],
    REMOVEFILTERS(customer_cohort_retention[months_since_first_purchase]),
    REMOVEFILTERS(customer_cohort_retention[activity_month]),
    customer_cohort_retention[months_since_first_purchase] = 3
)

Retention Cell Colour =
VAR Rate = [Cohort Retention]
VAR Age = SELECTEDVALUE(customer_cohort_retention[months_since_first_purchase])
RETURN
    SWITCH(
        TRUE(),
        ISBLANK(Rate), BLANK(),
        Age = 0, "#EDF1F5",
        Rate >= 0.02, "#5BA99B",
        Rate >= 0.01, "#A5D6C8",
        Rate >= 0.005, "#CCE8DD",
        Rate > 0, "#E9F5F0",
        "#FFFFFF"
    )
```

Cohort Customers counts each cohort's original population once. Weighted rates
use only rows available at the specified age, so unavailable follow-up does not
enter the denominator as zero. Rates across multiple ages return blank. Retained
counts summed across ages are not lifetime distinct returning customers.

## Visual inventory

Coordinates are x, y, width, height in report canvas units. All visual files are
under `dashboard/Data Analytics.Report/definition/pages/b5c0a170e8204dc8a501/visuals/<ID>/visual.json`.

| ID | Type | Title | Coordinates |
| --- | --- | --- | --- |
| `b5c0a170e8204dc80001` | textbox | Text / navigation | 64, 36, 844, 104 |
| `b5c0a170e8204dc80002` | textbox | Text / navigation | 1456, 48, 400, 92 |
| `b5c0a170e8204dc80003` | slicer | Cohort month | 932, 48, 500, 92 |
| `b5c0a170e8204dc80004` | cardVisual | Cohort Customers | 64, 164, 430, 144 |
| `b5c0a170e8204dc80005` | cardVisual | Weighted M1 Retention | 518, 164, 430, 144 |
| `b5c0a170e8204dc80006` | cardVisual | Weighted M2 Retention | 972, 164, 430, 144 |
| `b5c0a170e8204dc80007` | cardVisual | Weighted M3 Retention | 1426, 164, 430, 144 |
| `b5c0a170e8204dc80008` | pivotTable | Monthly Cohort Retention | 64, 332, 1120, 548 |
| `b5c0a170e8204dc80009` | lineChart | M1?M3 Retention by Cohort | 1208, 332, 648, 348 |
| `b5c0a170e8204dc8000a` | columnChart | Original Cohort Size | 1208, 704, 648, 320 |
| `b5c0a170e8204dc8000b` | textbox | Text / navigation | 64, 904, 1120, 120 |
| `b5c0a170e8204dc8ff01` | pageNavigator | Text / navigation | 756, 4, 1100, 28 |

## Static validation and offline reference check

- New page, twelve visuals and page order validated against Microsoft's published
  PBIR schemas: 14 files, zero errors. New visuals use published 2.12.0; the existing
  four pages retain their original schema references.
- JSON syntax, unique IDs, field and DAX references, numeric/date sorting, matrix
  field roles and total settings, canvas bounds, non-overlap, navigation and
  interaction endpoints checked. The new JSON files are explicitly unignored.
- Original four-page content is preserved byte for byte except navigator files;
  those differ structurally only in columnCount. Existing dbt work is unchanged.
- Offline recomputation from local source CSVs confirms 17 cohorts, 75,123 customers,
  M1 364/75,123 = 0.484538690%, M2 257/75,123 = 0.342105613%, and
  M3 192/75,123 = 0.255580847%. This is a reference calculation, not execution
  of DAX or validation of the cached semantic model contents.

## Desktop validation still required

Power BI Desktop rendering and DAX execution have **not** been verified.
Before declaring the page complete in Desktop, open the existing PBIP without
refreshing BigQuery and check: the four KPI reference values; slicer subsets and
clearing selections; M0 and future blanks; matrix shading, totals and scrolling;
chronological ordering; chart legends and label clipping; five-page navigation;
and the preservation of all four original pages. Save and reopen to confirm
serialization. This implementation creates no screenshot claiming a rendered result.

The cutoff is a reporting convention, not proven source completeness. Cohorts
represent first observed delivered purchases, not necessarily true acquisition.
Rates describe monthly periodic repeat purchases, not lifetime or subscription
retention. No sixth page, warehouse operation, dependency installation, commit,
push or pull request is included.
