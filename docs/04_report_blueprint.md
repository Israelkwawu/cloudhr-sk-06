# Report blueprint

Build this in Power BI Desktop after the queries, relationships, measures, and tenant security are validated. Import `powerbi/CloudHR.theme.json` (View → Themes → Browse for themes) before placing visuals. Work in a separate PBIP copy; retain the source report unchanged.

## Global design system

Use the 16:9 canvas at **1280 × 720**. The report theme supplies the primary palette, light canvas, title styling, and card callout color. Apply these design tokens consistently:

| Token | Value |
|---|---|
| Primary navy | `#17324D` |
| Primary teal | `#167D8D` |
| Secondary indigo | `#5B6FCB` |
| Secondary green | `#35A68A` |
| Canvas | `#F4F7FA` |
| Surface | `#FFFFFF` |
| Border | `#DCE4EC` |
| Primary text | `#263746` |
| Secondary text | `#657789` |
| Muted | `#8292A2` |
| Success / warning / danger / info | `#25865A` / `#D99A32` / `#C45151` / `#3979B8` |

Use Segoe UI or Aptos. Set dashboard title 26 px semibold, page title 22 px semibold, section title 15 px semibold, KPI value 30–34 px bold, KPI label 12 px medium, chart title 14 px semibold, axis 10–11 px, and supporting text 11–12 px. Use an 8 px spacing grid, 16 px card padding, 20–24 px section spacing, 1 px borders, and 8 px card corners. Keep chart gridlines and borders minimal.

Every page uses the same header: CloudHR identity, page title, reporting-period context, and page navigation. Put slicers in a consistent top filter row (except for the mobile layout). Add a footer with the report refresh timestamp. Use four primary navigation destinations—Executive Workforce Summary, Workforce Composition, Compensation Analytics, and Leave & Attendance. The Department Detail page is reached only by drill-through and has a Back button.

Use navy/teal for core workforce series, indigo/green for comparison series, and semantic colors only for meaningful status. Keep category colors stable: job levels use an ordered progression of navy, teal, indigo, green, information blue, and muted; leave types use Annual `#167D8D`, Sick `#D99A32`, Parental `#5B6FCB`, and Other `#8292A2`. Do not add a legend or data labels when they do not improve interpretation.

Add a Reset Filters bookmark on pages with slicers. Configure it to restore the page's default filter state without changing the report's navigation or drill-through state.

Mark `dim_date` as a date table, set the sort-by columns from the design doc, and hide `base_salary_usd` on the fact. Set every id column to Don't summarize.

Before report visuals are exposed, validate the semantic measures against Acme Labs and Year = 2025 in the local authoring model. This control check may be run before RLS is applied, but do not publish or share the report until tenant RLS is configured and validated:

| Check | Value |
|---|---|
| Active Headcount | 84 |
| Headcount BOP | 77 |
| Headcount YoY Growth % | 9.09 |
| New Hires | 13 |
| Terminations | 6 |
| Turnover Rate | 7.45 |
| Voluntary Turnover Rate | 1.24 |
| Avg Base Salary | 91,107.63 |
| Leave Days | 708 |

BrightPath Logistics, same year: headcount 86, average salary 82,695.26, leave days 900. Cedar Health: headcount 66, average salary 85,166.33, leave days 629. An unsliced page covers 2023–2026 and will dilute rates. Select 2025 while you build.

Create a hierarchy on `dim_department` named Department: `department_group`, then `department_name`.

Drill-through field on the detail page: `dim_department[department_name]`. Keep it. Right-click a department name on any page and choose Drill through → Department Detail. Charts that only show `department_group` need one drill down the hierarchy before a single department is available.

## Page 1 — Executive Workforce Summary

Give Active Headcount the strongest emphasis of the four KPI cards.

Slicers across the top, dropdown style: Year, Quarter, Department Group (`dim_department[department_group]`), Employment Type.

| Visual | Fields |
|---|---|
| Card | Active Headcount |
| Card | Turnover Rate |
| Card | Avg Tenure (Years) |
| Card | Avg Base Salary |
| Line chart | Axis: Month Name. Values: Active Headcount, Headcount PY. |
| Bar chart, horizontal | Axis: the Department hierarchy (starts at Department Group). Value: Active Headcount. |
| Clustered column | Axis: Month Name. Values: New Hires, Terminations. |

The line chart is two balances. If March is about three times January, the measure is summing months and the date table is not marked, or the visual is using a column instead of `Active Headcount`.

Mobile layout for this page only (View → Mobile layout). Stack, top to bottom: Year slicer, the four cards, the headcount line, the department bar, the hires-versus-terminations bar, then the remaining slicers. Resize cards to the phone width. Do not leave the auto-generated stack, which puts slicers in the middle of the trend.

## Page 2 — Workforce Composition

| Visual | Fields |
|---|---|
| Stacked bar | Axis: `job_level_name`. Value: Active Headcount. This is the seniority pyramid. Sort is already by level, not by size. |
| Donut | Legend: `employment_type`. Value: Active Headcount. |
| Bar | Axis: `department_name`. Value: Avg Tenure (Years). Sort descending by the measure. |
| Table | Top 10 `department_name` by Active Headcount. Also show Headcount YoY Growth % and Turnover Rate. |

Put `% Workforce at Each Job Level` in the tooltip of the stacked bar so the pyramid can be read as a share.

## Page 3 — Compensation Analytics

Slicers: Department Name, Job Level (`job_level_name`), Employment Type.

| Visual | Fields |
|---|---|
| Bar | Axis: `job_level_name`. Value: Avg Base Salary. |
| Histogram-style clustered column | Axis: a salary bin. Value: Active Headcount. Build the bin as a calculated group on a measure, or as bands in a disconnected table (Under 50k, 50–75k, 75–100k, 100–140k, 140–180k, 180k+). Do not plot the raw salary column. |
| Bar | Axis: `department_name`. Value: Compensation Band Width. |
| Scatter | X: Avg Tenure (Years). Y: Avg Base Salary. Details: `department_name`. |

If the scatter is one dot per department, the tenure and salary measures are already at the right grain. Do not put `employee_id` on Details unless the page is filtered to one small department;  the largest tenant has over a thousand people.

## Page 4 — Leave & Attendance

| Visual | Fields |
|---|---|
| Bar, horizontal | Axis: `leave_type`. Value: Leave Utilization %. |
| Line chart | Axis: Month Name. Values: Leave Days, Leave Days 3M Avg. |
| Bar | Axis: `department_name`. Value: Leave Days. Top 10 by the measure. |
| Donut | Legend: `leave_type`. Value: Leave Days. |

The monthly line attributes every day of a leave to its start month, including leave that runs into the next month. Parental utilization uses the whole active population as the denominator, so that bar will sit far below Annual and Sick. That is the definition in the measure, not a missing filter.

## Page 5 — Department Detail

This page is the drill-through target. Add a Back button (Insert → Buttons → Back).

Show the selected `department_name` and `department_group` in the page header, bound to the drill-through fields. Preserve the department filter context and add a Back button.

| Visual | Fields |
|---|---|
| Card | Active Headcount |
| Card | Turnover Rate |
| Card | Avg Tenure (Years) |
| Card | Avg Base Salary |
| Line chart | Month-end Active Headcount by month |
| Donut | Active Headcount by `employment_type` |
| Bar chart | Active Headcount by `job_level_name`, ordered by job level |
| Clustered column | Monthly New Hires and Terminations |

Keep the page aggregated. Do not add employee names, email addresses, employee-level tables, or raw salary columns.

## What not to add

Do not put `security_mapping`, `salary_data_errors`, or `leave_entitlement` on a page. They are loaded so the role and the utilization measure can see them, and they are hidden in Model view.

Do not activate the relationship from `dim_employee` to any fact. Historical pages would drop leavers.
