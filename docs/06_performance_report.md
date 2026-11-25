# Performance report

Run this in Desktop after the four report pages exist. The targets are: every visual under 800 ms of DAX query time, and at least 80% of visuals under 400 ms. This file is the place to record what Performance Analyzer and DAX Studio actually returned. The numbers below the tables are not filled in, because they have to come from a trace of the model on your machine.

## How to capture

1. Open the report with Year = 2025 selected, and no RLS view-as active, so the trace sees a full tenant rather than an empty filter. Then repeat once as Ben, to confirm the role does not make a visual scan every organisation.
2. View → Performance Analyzer → Start recording. Change a slicer on the page so each visual runs, or use Refresh visuals.
3. Expand each visual and record **DAX query**. Copy is available on the query if you need it in DAX Studio.
4. Stop recording before you change pages, then start again, so each page stays readable.

| Page | Visual | DAX query (ms) | Under 400 ms | Under 800 ms |
|---|---|---|---|---|
| Executive | Active Headcount card | | | |
| Executive | Turnover Rate card | | | |
| Executive | Avg Tenure card | | | |
| Executive | Avg Base Salary card | | | |
| Executive | Headcount trend | | | |
| Executive | Headcount by department group | | | |
| Executive | New hires vs terminations | | | |
| Composition | Seniority pyramid | | | |
| Composition | Employment type donut | | | |
| Composition | Tenure by department | | | |
| Composition | Top 10 departments table | | | |
| Compensation | Salary by job level | | | |
| Compensation | Salary distribution | | | |
| Compensation | Band width by department | | | |
| Compensation | Tenure vs salary scatter | | | |
| Leave | Utilization by leave type | | | |
| Leave | Monthly leave days | | | |
| Leave | Top 10 departments by leave | | | |
| Leave | Leave type donut | | | |

Slowest visual: _______________ at _______________ ms.

## What to trace in DAX Studio

The measure most likely to be slowest is `Leave Utilization %`. It is the only measure that iterates the period-end roster and calls `LOOKUPVALUE` once per person. Headcount measures are a single `COUNTROWS` with an equality filter on `snapshot_date`.

Paste the DAX query Performance Analyzer copied for that visual into DAX Studio. Server Timings on. Clear the cache, run once to warm nothing, then run the timed pass on a cold cache.

| | Formula engine (ms) | Storage engine (ms) | SE queries |
|---|---|---|---|
| Before | | | |
| After | | | |

## Optimization already in the library

The shipped `Leave Utilization %` evaluates entitlement on the period-end snapshot only. A slower version that looks equivalent walks every active monthly row in the selected year, which is about twelve times the work and would also overstate entitlement if the result were summed naively:

```dax
Leave Utilization % (before) =
VAR LeaveType =
    SELECTEDVALUE ( dim_leave_type[leave_type], "Annual" )
VAR Entitled =
    SUMX (
        FILTER (
            fact_employee_monthly,
            fact_employee_monthly[is_active] = TRUE ()
                && fact_employee_monthly[is_data_error] = FALSE ()
        ),
        DIVIDE (
            LOOKUPVALUE (
                leave_entitlement[annual_entitlement_days],
                leave_entitlement[leave_type], LeaveType,
                leave_entitlement[employment_type], fact_employee_monthly[employment_type]
            ),
            12
        )
    )
VAR Taken =
    SUM ( fact_leave[days_taken] )
RETURN
    DIVIDE ( Taken, Entitled ) * 100
```

To record a real before and after: add that measure, point the utilization bar at it, run Performance Analyzer, then point the bar back at `Leave Utilization %` and run again. Delete the before measure when the table above is filled in. Do not leave it in the published model. It is easy to put on a page by mistake, and its denominator is not the one the design doc defines.

Two other choices are already applied and should show up as less work rather than as a second timing:

- `DateKey`, `snapshot_date`, and `is_data_error` are built in Power Query. They are not DAX calculated columns, so the formula engine does not recompute them when a slicer changes.
- `first_name` and `last_name` are not columns on the fact. The monthly table is 628,428 rows; those strings would have been stored on every row and never used by a measure.

If a visual is still over 800 ms after the utilization measure is on the shipped definition, the next place to look is a visual that puts `employee_id` on the detail of a scatter or a table with no department filter. Aggregate to department on pages 1–4. The department detail page is the one that is allowed to be at employee grain, and it is reached for a single department.
