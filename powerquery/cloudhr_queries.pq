// CloudHR Power Query (M) library
// Paste each block into its own query. The first comment line is the query name.
// Mode: Import. Do not use DirectQuery.
//
// Parameters (Manage parameters, or paste as queries):
//   Server    text    localhost:5435
//   Database  text    cloudhr
//
// Credentials: postgres / postgres on the local container only.
// If the navigator fails, install the official PostgreSQL provider (Npgsql)
// when Power BI prompts for it.
//
// Load flags
//   Database, stg_employee_monthly     Disable load
//   salary_data_errors, security_mapping, leave_entitlement
//                                      Enable load, then hide the table in Model view
//   every dim_* and fact_*             Enable load
//
// After load, set the sort-by columns listed under dim_date, dim_job_level,
// dim_employment_type, and dim_leave_type. M cannot set Sort by column.

// =============================================================================
// Query: Database
// Disable load
// =============================================================================
let
    Source = PostgreSQL.Database(Server, DatabaseName, [HierarchicalNavigation = false])
in
    Source

// =============================================================================
// Query: dim_organisation
// =============================================================================
let
    Source = Database,
    Table = Source{[Schema = "hr", Item = "organisations"]}[Data],
    Typed = Table.TransformColumnTypes(
        Table,
        {
            {"org_id", Int64.Type},
            {"org_name", type text},
            {"industry", type text},
            {"employee_count_band", type text},
            {"country", type text},
            {"subscription_tier", type text}
        }
    )
in
    Typed

// =============================================================================
// Query: dim_department
// =============================================================================
let
    Source = Database,
    Table = Source{[Schema = "hr", Item = "departments"]}[Data],
    Typed = Table.TransformColumnTypes(
        Table,
        {
            {"department_id", Int64.Type},
            {"org_id", Int64.Type},
            {"department_name", type text},
            {"department_group", type text},
            {"cost_centre", type text}
        }
    )
in
    Typed

// =============================================================================
// Query: dim_employee
// Current roster only. Fact history stays on fact_employee_monthly.
// Keep names here: a tenant HR user needs them, and RLS confines them to one org.
// =============================================================================
let
    Source = Database,
    Table = Source{[Schema = "hr", Item = "employees"]}[Data],
    Typed = Table.TransformColumnTypes(
        Table,
        {
            {"employee_sk", Int64.Type},
            {"employee_id", Int64.Type},
            {"org_id", Int64.Type},
            {"first_name", type text},
            {"last_name", type text},
            {"department_id", Int64.Type},
            {"job_level", type text},
            {"employment_type", type text},
            {"hire_date", type date},
            {"termination_date", type date},
            {"termination_reason", type text},
            {"effective_start", type date},
            {"effective_end", type date},
            {"is_current", type logical},
            {"is_active", type logical}
        }
    ),
    Current = Table.SelectRows(
        Typed,
        each [is_current] = true and [is_active] = true and [termination_date] = null
    ),
    Kept = Table.SelectColumns(
        Current,
        {
            "employee_id",
            "org_id",
            "first_name",
            "last_name",
            "department_id",
            "job_level",
            "employment_type",
            "hire_date"
        }
    ),
    WithName = Table.AddColumn(Kept, "Full Name", each [first_name] & " " & [last_name], type text)
in
    WithName

// =============================================================================
// Query: dim_job_level
// Sort job_level_name by job_level_sort, then hide job_level_sort.
// =============================================================================
let
    Source = #table(
        type table [job_level = text, job_level_name = text, job_level_sort = Int64.Type],
        {
            {"L1", "L1 Associate", 1},
            {"L2", "L2 Specialist", 2},
            {"L3", "L3 Senior", 3},
            {"L4", "L4 Manager", 4},
            {"L5", "L5 Director", 5},
            {"L6", "L6 Executive", 6}
        }
    )
in
    Source

// =============================================================================
// Query: dim_employment_type
// Sort employment_type by employment_type_sort, then hide the sort column.
// =============================================================================
let
    Source = #table(
        type table [employment_type = text, employment_type_sort = Int64.Type],
        {
            {"Full-time", 1},
            {"Part-time", 2},
            {"Contract", 3},
            {"Intern", 4}
        }
    )
in
    Source

// =============================================================================
// Query: dim_leave_type
// Sort leave_type by leave_type_sort, then hide the sort column.
// =============================================================================
let
    Source = #table(
        type table [leave_type = text, leave_type_sort = Int64.Type],
        {
            {"Annual", 1},
            {"Sick", 2},
            {"Parental", 3},
            {"Other", 4}
        }
    )
in
    Source

// =============================================================================
// Query: dim_date
// Calendar year, 1 January through 31 December.
// The table starts in 2023 so SAMEPERIODLASTYEAR has a prior year to land on.
// Facts start in January 2024, so 2024 year-on-year growth is blank on purpose.
//
// Sort by column (Model view, after this query is loaded):
//   Month Name  -> Month Number
//   Day of Week -> Day of Week Number
//   Quarter     -> Quarter Number
// Mark as date table on the Date column.
// Is Holiday is US federal, observed (Saturday -> Friday, Sunday -> Monday).
// =============================================================================
let
    StartDate = #date(2023, 1, 1),
    EndDate = #date(2026, 12, 31),
    Observe = (d as date) as date =>
        let
            dow = Date.DayOfWeek(d, Day.Monday)
        in
            if dow = 5 then Date.AddDays(d, -1)
            else if dow = 6 then Date.AddDays(d, 1)
            else d,
    NthWeekday = (year as number, month as number, weekday as number, n as number) as date =>
        let
            first = #date(year, month, 1),
            offset = Number.Mod(weekday - Date.DayOfWeek(first, Day.Monday) + 7, 7)
        in
            Date.AddDays(first, offset + (n - 1) * 7),
    LastWeekday = (year as number, month as number, weekday as number) as date =>
        let
            last = Date.EndOfMonth(#date(year, month, 1)),
            delta = Number.Mod(Date.DayOfWeek(last, Day.Monday) - weekday + 7, 7)
        in
            Date.AddDays(last, -delta),
    HolidaysForYear = (year as number) as list =>
        {
            Observe(#date(year, 1, 1)),
            NthWeekday(year, 1, 0, 3),
            NthWeekday(year, 2, 0, 3),
            LastWeekday(year, 5, 0),
            Observe(#date(year, 6, 19)),
            Observe(#date(year, 7, 4)),
            NthWeekday(year, 9, 0, 1),
            NthWeekday(year, 10, 0, 2),
            Observe(#date(year, 11, 11)),
            NthWeekday(year, 11, 3, 4),
            Observe(#date(year, 12, 25))
        },
    HolidayDates = List.Buffer(
        List.Distinct(List.Combine(List.Transform({2023, 2024, 2025, 2026}, each HolidaysForYear(_))))
    ),
    MonthNames = {"January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"},
    DayNames = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"},
    DayCount = Duration.Days(EndDate - StartDate) + 1,
    DateList = List.Dates(StartDate, DayCount, #duration(1, 0, 0, 0)),
    ToKey = (d as date) as number => Date.Year(d) * 10000 + Date.Month(d) * 100 + Date.Day(d),
    Rows = List.Transform(
        DateList,
        each
            let
                d = _,
                dow = Date.DayOfWeek(d, Day.Monday),
                quarterNumber = Date.QuarterOfYear(d)
            in
                {
                    ToKey(d),
                    d,
                    Date.Year(d),
                    Date.Month(d),
                    MonthNames{Date.Month(d) - 1},
                    "Q" & Text.From(quarterNumber),
                    quarterNumber,
                    DayNames{dow},
                    dow + 1,
                    dow >= 5,
                    List.Contains(HolidayDates, d),
                    Date.WeekOfYear(d, Day.Monday)
                }
    ),
    AsTable = Table.FromRows(
        Rows,
        {
            "DateKey",
            "Date",
            "Year",
            "Month Number",
            "Month Name",
            "Quarter",
            "Quarter Number",
            "Day of Week",
            "Day of Week Number",
            "Is Weekend",
            "Is Holiday",
            "Week Number"
        }
    ),
    Typed = Table.TransformColumnTypes(
        AsTable,
        {
            {"DateKey", Int64.Type},
            {"Date", type date},
            {"Year", Int64.Type},
            {"Month Number", Int64.Type},
            {"Month Name", type text},
            {"Quarter", type text},
            {"Quarter Number", Int64.Type},
            {"Day of Week", type text},
            {"Day of Week Number", Int64.Type},
            {"Is Weekend", type logical},
            {"Is Holiday", type logical},
            {"Week Number", Int64.Type}
        }
    )
in
    Typed

// =============================================================================
// Query: stg_employee_monthly
// Disable load. Downstream queries split the clean fact from the error log.
// Join the current employee version: hire and termination dates do not change
// across SCD versions, and the month-end job level and department are already
// on the snapshot. Joining every version would duplicate the fact.
// =============================================================================
let
    DatabaseNav = Database,
    Snapshots = DatabaseNav{[Schema = "hr", Item = "employee_monthly_snapshots"]}[Data],
    Employees = DatabaseNav{[Schema = "hr", Item = "employees"]}[Data],
    EmployeesTyped = Table.TransformColumnTypes(
        Employees,
        {
            {"employee_id", Int64.Type},
            {"hire_date", type date},
            {"termination_date", type date},
            {"termination_reason", type text},
            {"first_name", type text},
            {"last_name", type text},
            {"is_current", type logical}
        }
    ),
    Current = Table.Buffer(
        Table.SelectColumns(
            Table.SelectRows(EmployeesTyped, each [is_current] = true),
            {"employee_id", "hire_date", "termination_date", "termination_reason", "first_name", "last_name"}
        )
    ),
    SnapshotsTyped = Table.TransformColumnTypes(
        Snapshots,
        {
            {"snapshot_month", type date},
            {"employee_id", Int64.Type},
            {"org_id", Int64.Type},
            {"is_active", type logical},
            {"base_salary_usd", type number},
            {"job_level", type text},
            {"department_id", Int64.Type},
            {"employment_type", type text}
        }
    ),
    Joined = Table.NestedJoin(SnapshotsTyped, {"employee_id"}, Current, {"employee_id"}, "emp", JoinKind.LeftOuter),
    Expanded = Table.ExpandTableColumn(
        Joined,
        "emp",
        {"hire_date", "termination_date", "termination_reason", "first_name", "last_name"}
    ),
    // Names are not needed at monthly grain. The current roster keeps them.
    WithoutPII = Table.RemoveColumns(Expanded, {"first_name", "last_name"}),
    WithMonthEnd = Table.AddColumn(WithoutPII, "snapshot_date", each Date.EndOfMonth([snapshot_month]), type date),
    WithDateKey = Table.AddColumn(
        WithMonthEnd,
        "DateKey",
        each Date.Year([snapshot_date]) * 10000 + Date.Month([snapshot_date]) * 100 + Date.Day([snapshot_date]),
        Int64.Type
    ),
    // Use "= null", not "<> null". A comparison with null yields null, and a
    // null flag would drop every active employee out of the headcount measures.
    WithErrorFlag = Table.AddColumn(
        WithDateKey,
        "is_data_error",
        each
            if [hire_date] = null or [termination_date] = null then false
            else [hire_date] > [termination_date],
        type logical
    )
in
    WithErrorFlag

// =============================================================================
// Query: salary_data_errors
// Enable load, then hide the table. Relate org_id to dim_organisation so RLS
// covers the log. Do not use this table on a report page.
// =============================================================================
let
    Source = stg_employee_monthly,
    Bad = Table.SelectRows(Source, each [base_salary_usd] <> null and [base_salary_usd] <= 0),
    Kept = Table.SelectColumns(Bad, {"snapshot_month", "employee_id", "org_id", "base_salary_usd"}),
    WithReason = Table.AddColumn(
        Kept,
        "error_reason",
        each if [base_salary_usd] = 0 then "Zero salary" else "Negative salary",
        type text
    ),
    Typed = Table.TransformColumnTypes(
        WithReason,
        {
            {"snapshot_month", type date},
            {"employee_id", Int64.Type},
            {"org_id", Int64.Type},
            {"base_salary_usd", type number},
            {"error_reason", type text}
        }
    )
in
    Typed

// =============================================================================
// Query: fact_employee_monthly
// Zero and negative salaries become null here. The error query above still
// sees the original values because it reads stg_employee_monthly directly.
// =============================================================================
let
    Source = stg_employee_monthly,
    CleanSalary = Table.AddColumn(
        Source,
        "base_salary_clean",
        each if [base_salary_usd] <> null and [base_salary_usd] > 0 then [base_salary_usd] else null,
        type number
    ),
    Dropped = Table.RemoveColumns(CleanSalary, {"base_salary_usd"}),
    Renamed = Table.RenameColumns(Dropped, {{"base_salary_clean", "base_salary_usd"}}),
    Typed = Table.TransformColumnTypes(
        Renamed,
        {
            {"snapshot_month", type date},
            {"snapshot_date", type date},
            {"DateKey", Int64.Type},
            {"employee_id", Int64.Type},
            {"org_id", Int64.Type},
            {"department_id", Int64.Type},
            {"job_level", type text},
            {"employment_type", type text},
            {"is_active", type logical},
            {"base_salary_usd", type number},
            {"hire_date", type date},
            {"termination_date", type date},
            {"termination_reason", type text},
            {"is_data_error", type logical}
        }
    )
in
    Typed

// =============================================================================
// Query: fact_leave
// Days that cross a month boundary stay on the start date. Say so if you
// describe the monthly trend: it is days approved, booked to the start month.
// =============================================================================
let
    Source = Database,
    Table = Source{[Schema = "hr", Item = "leave_records"]}[Data],
    Typed = Table.TransformColumnTypes(
        Table,
        {
            {"leave_id", Int64.Type},
            {"employee_id", Int64.Type},
            {"org_id", Int64.Type},
            {"department_id", Int64.Type},
            {"employment_type", type text},
            {"leave_type", type text},
            {"start_date", type date},
            {"end_date", type date},
            {"days_taken", Int64.Type},
            {"approved_by", Int64.Type}
        }
    ),
    WithDateKey = Table.AddColumn(
        Typed,
        "DateKey",
        each Date.Year([start_date]) * 10000 + Date.Month([start_date]) * 100 + Date.Day([start_date]),
        Int64.Type
    )
in
    WithDateKey

// =============================================================================
// Query: fact_performance
// Do not relate this table to dim_date. A review is an annual event; the
// Performance Rating Avg measure filters review_year from dim_date[Year].
// A relationship on 1 January would make the Quarter slicer hide the review.
// =============================================================================
let
    Source = Database,
    Table = Source{[Schema = "hr", Item = "performance_reviews"]}[Data],
    Typed = Table.TransformColumnTypes(
        Table,
        {
            {"review_id", Int64.Type},
            {"employee_id", Int64.Type},
            {"org_id", Int64.Type},
            {"department_id", Int64.Type},
            {"employment_type", type text},
            {"review_year", Int64.Type},
            {"rating", Int64.Type},
            {"reviewer_id", Int64.Type}
        }
    )
in
    Typed

// =============================================================================
// Query: leave_entitlement
// Disconnected lookup. The utilization measure reads it with LOOKUPVALUE.
// Do not relate it to the facts. Enable load, then hide the table.
// =============================================================================
let
    Source = Database,
    Table = Source{[Schema = "hr", Item = "leave_entitlement"]}[Data],
    Typed = Table.TransformColumnTypes(
        Table,
        {
            {"leave_type", type text},
            {"employment_type", type text},
            {"annual_entitlement_days", Int64.Type}
        }
    )
in
    Typed

// =============================================================================
// Query: security_mapping
// Lab copy is hard-coded. Do not relate this table to dim_organisation.
// Enable load, hide it, and do not put a visual on it.
//
// Production replacement, once the warehouse is the source of truth:
//   let
//       Source = Database,
//       Table = Source{[Schema = "hr", Item = "security_mapping"]}[Data],
//       Typed = Table.TransformColumnTypes(
//           Table,
//           {
//               {"user_email", type text},
//               {"org_id", Int64.Type},
//               {"access_level", type text}
//           }
//       )
//   in
//       Typed
// user_email must equal the Entra ID user principal name, one row per person.
// =============================================================================
let
    Source = #table(
        type table [user_email = text, org_id = Int64.Type, access_level = text],
        {
            {"ada.mensah@acme-labs.example", 1, "HR_ADMIN"},
            {"ben.owusu@brightpath.example", 2, "HR_VIEWER"},
            {"cara.boateng@cedarhealth.example", 3, "HR_VIEWER"},
            {"dana.asante@acme-labs.example", 1, "HR_VIEWER"}
        }
    )
in
    Source
