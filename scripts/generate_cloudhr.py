"""Generate the CloudHR source data for the SK-06 capstone.

Writes CSV files into --out (default: data) and a control-totals file the
Power BI measures can be checked against. Only the Python standard library
is used. The random seed is fixed, so every run produces the same rows.

The employee_count_band on each organisation is the active headcount at
2025-12-31. Monthly snapshots cover January 2024 through December 2025.
"""

import argparse
import csv
import datetime as dt
import random
from collections import defaultdict
from pathlib import Path

SEED = 20261119
WINDOW_START = dt.date(2024, 1, 1)
WINDOW_END = dt.date(2025, 12, 31)

# (band label, min active headcount, max, number of organisations)
# 130 + 50 + 15 + 4 + 1 = 200 organisations.
BANDS = [
    ("50-99", 50, 99, 130),
    ("100-249", 100, 180, 50),
    ("250-499", 250, 360, 15),
    ("500-999", 500, 700, 4),
    ("1000-2499", 1000, 1200, 1),
]

FIXED_ORGS = {
    1: ("Acme Labs", "Technology", "United States", 1.00),
    2: ("BrightPath Logistics", "Logistics", "United States", 1.00),
    3: ("Cedar Health", "Healthcare", "United States", 1.00),
}

INDUSTRIES = [
    "Technology",
    "Healthcare",
    "Financial Services",
    "Manufacturing",
    "Retail",
    "Education",
    "Professional Services",
    "Logistics",
    "Energy",
    "Hospitality",
]

# country, salary multiplier versus US, draw weight
COUNTRIES = [
    ("United States", 1.00, 50),
    ("United Kingdom", 0.92, 10),
    ("Germany", 0.95, 8),
    ("Canada", 0.90, 8),
    ("Netherlands", 0.96, 5),
    ("Ireland", 0.93, 4),
    ("Australia", 0.94, 4),
    ("Ghana", 0.35, 4),
    ("Kenya", 0.32, 3),
    ("Nigeria", 0.30, 2),
    ("India", 0.28, 5),
    ("South Africa", 0.40, 3),
]

NAME_A = [
    "Northline", "Harbor", "Summit", "Copper", "Fieldstone", "Silveroak",
    "Brightwater", "Kindred", "Lumen", "Pinnacle", "Redwood", "Stonebridge",
    "Vantage", "Westbrook", "Alden", "Marlow", "Halcyon", "Oakmont",
    "Rivermark", "Cinder", "Fairbank", "Highlane", "Lowell", "Meridian",
]
NAME_B = [
    "Ridge", "Forge", "Harbor", "Peak", "Field", "Works", "Point", "Line",
    "Gate", "Shore", "Vale", "Crest", "Hill", "Bay", "Park",
]
NAME_C = ["Group", "Holdings", "Partners", "Systems", "Collective", "Industries", "Co"]

DEPT_CATALOG = [
    ("Finance", "Corporate"),
    ("Legal", "Corporate"),
    ("Executive Office", "Corporate"),
    ("Sales", "Commercial"),
    ("Marketing", "Commercial"),
    ("Customer Success", "Commercial"),
    ("Operations", "Operations"),
    ("Customer Support", "Operations"),
    ("Engineering", "Technology"),
    ("IT", "Technology"),
    ("People & Culture", "People"),
]

LEVELS = ["L1", "L2", "L3", "L4", "L5", "L6"]
LEVEL_WEIGHTS = [28, 26, 22, 15, 7, 2]
LEVEL_RANK = {name: i + 1 for i, name in enumerate(LEVELS)}
LEVEL_PAY = {
    "L1": (45000, 62000),
    "L2": (60000, 82000),
    "L3": (78000, 108000),
    "L4": (105000, 145000),
    "L5": (140000, 190000),
    "L6": (185000, 280000),
}
NEXT_LEVEL = {"L1": "L2", "L2": "L3", "L3": "L4", "L4": "L5", "L5": "L6", "L6": "L6"}

EMPLOYMENT_TYPES = ["Full-time", "Part-time", "Contract", "Intern"]
EMPLOYMENT_WEIGHTS = [80, 9, 8, 3]
TYPE_FACTOR = {"Full-time": 1.00, "Part-time": 0.60, "Contract": 1.05, "Intern": 0.42}

# Annual entitlement days. Contractors are not entitled; the leave generator
# skips a type whose entitlement is 0 so utilization stays interpretable.
ENTITLEMENT = [
    ("Annual", "Full-time", 20),
    ("Annual", "Part-time", 12),
    ("Annual", "Contract", 0),
    ("Annual", "Intern", 10),
    ("Sick", "Full-time", 10),
    ("Sick", "Part-time", 6),
    ("Sick", "Contract", 0),
    ("Sick", "Intern", 5),
    ("Parental", "Full-time", 60),
    ("Parental", "Part-time", 30),
    ("Parental", "Contract", 0),
    ("Parental", "Intern", 0),
    ("Other", "Full-time", 5),
    ("Other", "Part-time", 3),
    ("Other", "Contract", 0),
    ("Other", "Intern", 0),
]
ENTITLEMENT_DAYS = {(t, e): d for t, e, d in ENTITLEMENT}

LEAVE_RULES = [
    ("Annual", 0.72, 5, 15),
    ("Sick", 0.45, 1, 5),
    ("Parental", 0.025, 20, 60),
    ("Other", 0.08, 1, 3),
]

FIRST_NAMES = [
    "Ama", "Kwame", "Efua", "Kofi", "Abena", "Yaw", "Akosua", "Kojo",
    "Amara", "Malik", "Zuri", "Jelani", "Nia", "Kofi", "Esi", "Adwoa",
    "Sarah", "James", "Linda", "David", "Grace", "Michael", "Daniel",
    "Rita", "Paul", "Naomi", "Victor", "Samuel", "Hannah", "Owen",
    "Priya", "Arun", "Mei", "Noah", "Sofia", "Elena", "Jonas", "Leila",
    "Omar", "Chloe", "Isaac", "Maya", "Felix", "Aisha", "Hugo", "Ines",
]
LAST_NAMES = [
    "Mensah", "Owusu", "Boateng", "Asante", "Osei", "Appiah", "Addo",
    "Agyeman", "Ansah", "Frimpong", "Diallo", "Abebe", "Okeke", "Nwosu",
    "Johnson", "Smith", "Brown", "Williams", "Davis", "Miller", "Wilson",
    "Taylor", "Clark", "Lewis", "Walker", "Hall", "Young", "King",
    "Patel", "Sharma", "Nguyen", "Keller", "Rossi", "Almeida", "Berg",
]

SECURITY_ROWS = [
    ("ada.mensah@acme-labs.example", 1, "HR_ADMIN"),
    ("ben.owusu@brightpath.example", 2, "HR_VIEWER"),
    ("cara.boateng@cedarhealth.example", 3, "HR_VIEWER"),
    ("dana.asante@acme-labs.example", 1, "HR_VIEWER"),
]


def month_ends(start, end):
    """Last calendar day of each month from start through end, inclusive."""
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        if month == 12:
            nxt = dt.date(year + 1, 1, 1)
        else:
            nxt = dt.date(year, month + 1, 1)
        last = nxt - dt.timedelta(days=1)
        first = dt.date(year, month, 1)
        yield first, last
        year, month = nxt.year, nxt.month


def weighted_country(rng):
    names = [c[0] for c in COUNTRIES]
    weights = [c[2] for c in COUNTRIES]
    name = rng.choices(names, weights=weights, k=1)[0]
    for country, mult, _weight in COUNTRIES:
        if country == name:
            return country, mult
    raise RuntimeError(name)


def tier_for(headcount, rng):
    if headcount < 100:
        return rng.choices(["Starter", "Growth"], weights=[80, 20], k=1)[0]
    if headcount < 500:
        return rng.choices(["Starter", "Growth", "Enterprise"], weights=[10, 70, 20], k=1)[0]
    return rng.choices(["Growth", "Enterprise"], weights=[25, 75], k=1)[0]


def org_names(rng):
    pool = [f"{a} {b} {c}" for a in NAME_A for b in NAME_B for c in NAME_C]
    reserved = {row[0] for row in FIXED_ORGS.values()}
    pool = [name for name in pool if name not in reserved]
    rng.shuffle(pool)
    return pool


def dept_slice(headcount):
    if headcount < 100:
        return DEPT_CATALOG[:4]
    if headcount < 250:
        return [DEPT_CATALOG[i] for i in (0, 3, 4, 6, 8, 10)]
    if headcount < 500:
        return DEPT_CATALOG[:8]
    return list(DEPT_CATALOG)


def pick_level(rng, employment_type):
    if employment_type == "Intern":
        return "L1"
    return rng.choices(LEVELS, weights=LEVEL_WEIGHTS, k=1)[0]


def pick_employment(rng, level):
    employment = rng.choices(EMPLOYMENT_TYPES, weights=EMPLOYMENT_WEIGHTS, k=1)[0]
    if level == "L6":
        return "Full-time"
    if employment == "Intern":
        return "Intern"
    return employment


def termination_reason(rng, employment_type, hire_date):
    if employment_type == "Contract":
        choices = ["Resignation", "Performance", "Redundancy", "End of Contract"]
        weights = [15, 10, 10, 65]
    elif employment_type == "Intern":
        choices = ["Resignation", "End of Contract"]
        weights = [30, 70]
    else:
        choices = ["Resignation", "Retirement", "Performance", "Redundancy", "End of Contract"]
        weights = [58, 8, 14, 15, 5]
    reason = rng.choices(choices, weights=weights, k=1)[0]
    if reason == "Retirement" and hire_date.year > 2015:
        return "Resignation"
    return reason


def version_at(versions, day):
    for start, end, department_id, level in versions:
        if start <= day and (end is None or end > day):
            return department_id, level
    _start, _end, department_id, level = versions[-1]
    return department_id, level


def salary_on(emp, org, level, month_end):
    lo, hi = LEVEL_PAY[level]
    annual = lo + (hi - lo) * emp["pay_factor"]
    annual *= TYPE_FACTOR[emp["employment_type"]] * org["multiplier"]
    if org["subscription_tier"] == "Enterprise":
        annual *= 1.04
    elif org["subscription_tier"] == "Growth":
        annual *= 1.02
    if month_end.year >= 2025:
        annual *= 1.03
    return round(annual, 2)


def active_on(emp, day):
    if emp["is_data_error"]:
        return False
    if emp["hire_date"] > day:
        return False
    term = emp["termination_date"]
    return term is None or term > day


def random_day(rng, start, end):
    span = (end - start).days
    if span < 0:
        raise ValueError("empty date range")
    return start + dt.timedelta(days=rng.randint(0, span))


def write_csv(path, header, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)
    print(f"  {path.name:<32} {len(rows):>8,} rows")


def build(rng):
    names = org_names(rng)
    name_cursor = 0
    organisations = []
    departments = []
    department_id = 0
    org_id = 0

    for band, lo, hi, count in BANDS:
        for _ in range(count):
            org_id += 1
            target = rng.randint(lo, hi)
            if org_id in FIXED_ORGS:
                name, industry, country, multiplier = FIXED_ORGS[org_id]
            else:
                name = names[name_cursor]
                name_cursor += 1
                industry = rng.choice(INDUSTRIES)
                country, multiplier = weighted_country(rng)
            org = {
                "org_id": org_id,
                "org_name": name,
                "industry": industry,
                "employee_count_band": band,
                "country": country,
                "multiplier": multiplier,
                "subscription_tier": tier_for(target, rng),
                "target": target,
                "departments": [],
            }
            for offset, (dept_name, group) in enumerate(dept_slice(target), start=1):
                department_id += 1
                department = (
                    department_id,
                    org_id,
                    dept_name,
                    group,
                    f"CC{org_id:03d}-{offset:02d}",
                )
                departments.append(department)
                org["departments"].append(department)
            organisations.append(org)

    if len(organisations) != 200:
        raise RuntimeError(f"expected 200 organisations, got {len(organisations)}")
    if len({org['org_name'] for org in organisations}) != 200:
        raise RuntimeError("organisation names are not unique")

    employees = []
    employee_id = 100000
    by_org = defaultdict(list)

    for org in organisations:
        cohort = []
        for _ in range(org["target"]):
            employee_id += 1
            employment_type = rng.choices(EMPLOYMENT_TYPES, weights=EMPLOYMENT_WEIGHTS, k=1)[0]
            level = pick_level(rng, employment_type)
            employment_type = pick_employment(rng, level)
            if employment_type == "Intern":
                level = "L1"
            if rng.random() < 0.78:
                hire_date = random_day(rng, dt.date(2012, 1, 1), dt.date(2023, 12, 15))
            else:
                hire_date = random_day(rng, dt.date(2024, 1, 8), dt.date(2025, 11, 20))
            department = rng.choice(org["departments"])
            emp = {
                "employee_id": employee_id,
                "org_id": org["org_id"],
                "first_name": rng.choice(FIRST_NAMES),
                "last_name": rng.choice(LAST_NAMES),
                "employment_type": employment_type,
                "hire_date": hire_date,
                "termination_date": None,
                "termination_reason": None,
                "pay_factor": rng.uniform(0.08, 0.95),
                "is_data_error": False,
                "versions": [(hire_date, None, department[0], level)],
            }
            cohort.append(emp)

        leavers = round(org["target"] * rng.uniform(0.16, 0.34))
        for _ in range(leavers):
            employee_id += 1
            employment_type = rng.choices(EMPLOYMENT_TYPES, weights=EMPLOYMENT_WEIGHTS, k=1)[0]
            level = pick_level(rng, employment_type)
            employment_type = pick_employment(rng, level)
            if employment_type == "Intern":
                level = "L1"
            termination_date = random_day(rng, dt.date(2024, 1, 10), dt.date(2025, 12, 20))
            tenure_days = rng.randint(200, 2800)
            hire_date = termination_date - dt.timedelta(days=tenure_days)
            department = rng.choice(org["departments"])
            emp = {
                "employee_id": employee_id,
                "org_id": org["org_id"],
                "first_name": rng.choice(FIRST_NAMES),
                "last_name": rng.choice(LAST_NAMES),
                "employment_type": employment_type,
                "hire_date": hire_date,
                "termination_date": termination_date,
                "termination_reason": termination_reason(rng, employment_type, hire_date),
                "pay_factor": rng.uniform(0.08, 0.95),
                "is_data_error": False,
                "versions": [(hire_date, None, department[0], level)],
            }
            cohort.append(emp)

        for emp in cohort:
            maybe_promote(rng, emp, org["departments"])
            employees.append(emp)
            by_org[org["org_id"]].append(emp)

    # Twelve employees whose hire date is after their termination date.
    # They are outside every organisation's target headcount.
    for org in organisations[:12]:
        employee_id += 1
        department = org["departments"][0]
        hire_date = dt.date(2024, 6, 1)
        emp = {
            "employee_id": employee_id,
            "org_id": org["org_id"],
            "first_name": rng.choice(FIRST_NAMES),
            "last_name": rng.choice(LAST_NAMES),
            "employment_type": "Full-time",
            "hire_date": hire_date,
            "termination_date": dt.date(2023, 6, 1),
            "termination_reason": "Resignation",
            "pay_factor": 0.5,
            "is_data_error": True,
            "versions": [(hire_date, None, department[0], "L2")],
        }
        employees.append(emp)
        by_org[org["org_id"]].append(emp)

    stable = [
        emp for emp in employees
        if emp["termination_date"] is None
        and emp["hire_date"] < WINDOW_START
        and not emp["is_data_error"]
    ]
    rng.shuffle(stable)
    corrupt = {}
    for index, emp in enumerate(stable[:65]):
        corrupt[(emp["employee_id"], rng.randrange(24))] = 0.0 if index < 40 else -1.0

    return organisations, departments, employees, by_org, corrupt


def maybe_promote(rng, emp, departments):
    if emp["is_data_error"] or rng.random() > 0.12:
        return
    hire_date = emp["hire_date"]
    term = emp["termination_date"] or WINDOW_END
    earliest = hire_date + dt.timedelta(days=180)
    latest = min(term - dt.timedelta(days=30), dt.date(2025, 9, 30))
    if earliest >= latest:
        return
    promo = random_day(rng, earliest, latest)
    start, _end, department_id, level = emp["versions"][0]
    if level != "L6" and rng.random() < 0.65:
        new_level = NEXT_LEVEL[level]
        new_department = department_id
    else:
        new_level = level
        choices = [dept[0] for dept in departments if dept[0] != department_id]
        if not choices:
            return
        new_department = rng.choice(choices)
    emp["versions"] = [
        (start, promo, department_id, level),
        (promo, None, new_department, new_level),
    ]


def employee_rows(employees):
    rows = []
    surrogate = 0
    for emp in employees:
        is_active = emp["termination_date"] is None and not emp["is_data_error"]
        for start, end, department_id, level in emp["versions"]:
            surrogate += 1
            rows.append((
                surrogate,
                emp["employee_id"],
                emp["org_id"],
                emp["first_name"],
                emp["last_name"],
                department_id,
                level,
                emp["employment_type"],
                emp["hire_date"].isoformat(),
                "" if emp["termination_date"] is None else emp["termination_date"].isoformat(),
                "" if emp["termination_reason"] is None else emp["termination_reason"],
                start.isoformat(),
                "" if end is None else end.isoformat(),
                "true" if end is None else "false",
                "true" if is_active else "false",
            ))
    return rows


def write_snapshots(path, organisations, employees, corrupt):
    months = list(month_ends(WINDOW_START, WINDOW_END))
    org_by_id = {org["org_id"]: org for org in organisations}
    # org_id -> YYYYMM -> [active count, salary sum, salary rows]
    monthly = defaultdict(lambda: defaultdict(lambda: [0, 0.0, 0]))
    row_count = 0
    corrupt_hits = 0
    header = [
        "snapshot_month", "employee_id", "org_id", "is_active",
        "base_salary_usd", "job_level", "department_id", "employment_type",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        for emp in employees:
            org = org_by_id[emp["org_id"]]
            for month_index, (month_start, month_end) in enumerate(months):
                if emp["is_data_error"]:
                    include = True
                    is_active = False
                else:
                    hired = emp["hire_date"] <= month_end
                    term = emp["termination_date"]
                    still_in_month = term is None or term >= month_start
                    include = hired and still_in_month
                    is_active = hired and (term is None or term > month_end)
                if not include:
                    continue
                department_id, level = version_at(emp["versions"], month_end)
                pay = salary_on(emp, org, level, month_end)
                key = (emp["employee_id"], month_index)
                if key in corrupt and is_active:
                    pay = corrupt[key]
                    corrupt_hits += 1
                writer.writerow([
                    month_start.isoformat(),
                    emp["employee_id"],
                    emp["org_id"],
                    "true" if is_active else "false",
                    f"{pay:.2f}",
                    level,
                    department_id,
                    emp["employment_type"],
                ])
                row_count += 1
                if is_active:
                    bucket = monthly[emp["org_id"]][month_end.year * 100 + month_end.month]
                    bucket[0] += 1
                    if pay > 0:
                        bucket[1] += pay
                        bucket[2] += 1
    print(f"  {path.name:<32} {row_count:>8,} rows")
    if corrupt_hits != len(corrupt):
        raise RuntimeError(f"expected {len(corrupt)} bad salaries, wrote {corrupt_hits}")
    return monthly, row_count, corrupt_hits


def write_events(leave_path, review_path, organisations, by_org, rng):
    leave_rows = []
    review_rows = []
    leave_id = 0
    review_id = 0
    leave_days_2025 = defaultdict(int)

    for org in organisations:
        people = by_org[org["org_id"]]
        leaders = [
            other["employee_id"]
            for other in people
            if not other["is_data_error"] and LEVEL_RANK[other["versions"][-1][3]] >= 4
        ]
        for emp in people:
            if emp["is_data_error"]:
                continue
            for year in (2024, 2025):
                review_day = dt.date(year, 11, 30)
                if active_on(emp, review_day):
                    department_id, level = version_at(emp["versions"], review_day)
                    bonus = {"L1": -0.2, "L2": 0.0, "L3": 0.2, "L4": 0.35, "L5": 0.5, "L6": 0.6}[level]
                    rating = min(5, max(1, round(3.3 + bonus + rng.gauss(0, 0.65))))
                    reviewer_pool = [leader for leader in leaders if leader != emp["employee_id"]]
                    reviewer = rng.choice(reviewer_pool) if reviewer_pool else emp["employee_id"]
                    review_id += 1
                    review_rows.append((
                        review_id,
                        emp["employee_id"],
                        emp["org_id"],
                        department_id,
                        emp["employment_type"],
                        year,
                        rating,
                        reviewer,
                    ))

                for leave_type, probability, lo, hi in LEAVE_RULES:
                    entitlement = ENTITLEMENT_DAYS[(leave_type, emp["employment_type"])]
                    if entitlement <= 0 or rng.random() > probability:
                        continue
                    days = min(rng.randint(lo, hi), entitlement)
                    window_start = max(emp["hire_date"], dt.date(year, 1, 1))
                    year_end = dt.date(year, 12, 31)
                    if emp["termination_date"] is None:
                        window_end = year_end
                    else:
                        window_end = min(year_end, emp["termination_date"] - dt.timedelta(days=1))
                    if window_end < window_start:
                        continue
                    last_start = window_end - dt.timedelta(days=days - 1)
                    if last_start < window_start:
                        days = (window_end - window_start).days + 1
                        if days <= 0:
                            continue
                        last_start = window_start
                    start = random_day(rng, window_start, last_start)
                    end = start + dt.timedelta(days=days - 1)
                    department_id, _level = version_at(emp["versions"], start)
                    approver_pool = [leader for leader in leaders if leader != emp["employee_id"]]
                    approved_by = rng.choice(approver_pool) if approver_pool else emp["employee_id"]
                    leave_id += 1
                    leave_rows.append((
                        leave_id,
                        emp["employee_id"],
                        emp["org_id"],
                        department_id,
                        emp["employment_type"],
                        leave_type,
                        start.isoformat(),
                        end.isoformat(),
                        days,
                        approved_by,
                    ))
                    if year == 2025:
                        leave_days_2025[org["org_id"]] += days

    write_csv(
        leave_path,
        ["leave_id", "employee_id", "org_id", "department_id", "employment_type",
         "leave_type", "start_date", "end_date", "days_taken", "approved_by"],
        leave_rows,
    )
    write_csv(
        review_path,
        ["review_id", "employee_id", "org_id", "department_id", "employment_type",
         "review_year", "rating", "reviewer_id"],
        review_rows,
    )
    return leave_rows, review_rows, leave_days_2025


def event_counts(employees):
    """New hires and terminations for 2024 and 2025, excluding data errors."""
    hires = defaultdict(lambda: defaultdict(int))
    terms = defaultdict(lambda: defaultdict(int))
    voluntary = defaultdict(lambda: defaultdict(int))
    for emp in employees:
        if emp["is_data_error"]:
            continue
        hire_year = emp["hire_date"].year
        if hire_year in (2024, 2025):
            hires[emp["org_id"]][hire_year] += 1
        term = emp["termination_date"]
        if term is not None and term.year in (2024, 2025):
            terms[emp["org_id"]][term.year] += 1
            if emp["termination_reason"] in ("Resignation", "Retirement"):
                voluntary[emp["org_id"]][term.year] += 1
    return hires, terms, voluntary


def write_totals(path, organisations, employees, departments, monthly, snapshots, corrupt_hits, leaves, reviews, leave_days_2025):
    hires, terms, voluntary = event_counts(employees)
    current_versions = 0
    data_errors = 0
    for emp in employees:
        if emp["is_data_error"]:
            data_errors += 1
        if emp["versions"][-1][1] is None:
            current_versions += 1
    lines = [
        "CloudHR control totals",
        f"Seed: {SEED}",
        "Snapshot window: 2024-01-01 through 2025-12-31 (month-end grain)",
        "Headcount is active employees at month end. It excludes the 12 hire/termination data errors.",
        "Average salary excludes zero and negative salary rows.",
        "",
        "Row counts",
        f"  organisations                  {len(organisations):>8,}",
        f"  departments                    {len(departments):>8,}",
        f"  employees (business keys)      {len(employees):>8,}",
        f"  employee SCD versions          {sum(len(emp['versions']) for emp in employees):>8,}",
        f"  current SCD versions           {current_versions:>8,}",
        f"  employee_monthly_snapshots     {snapshots:>8,}",
        f"  leave_records                  {len(leaves):>8,}",
        f"  performance_reviews            {len(reviews):>8,}",
        f"  security_mapping               {len(SECURITY_ROWS):>8,}",
        f"  leave_entitlement              {len(ENTITLEMENT):>8,}",
        f"  zero or negative salaries      {corrupt_hits:>8,}",
        f"  hire_date after termination    {data_errors:>8,}",
        "",
        "RLS test organisations (active headcount and avg salary at month end)",
        "  org_id  name                    month     headcount   avg_salary   new_hires  terminations  voluntary  leave_days",
    ]
    for org in organisations[:3]:
        for year, label in ((2024, "2024-12"), (2025, "2025-12")):
            key = year * 100 + 12
            count, sal_sum, sal_n = monthly[org["org_id"]][key]
            avg = sal_sum / sal_n if sal_n else 0
            lines.append(
                f"  {org['org_id']:<7} {org['org_name']:<23} {label}  "
                f"{count:>9,}   {avg:>10,.2f}   {hires[org['org_id']][year]:>9,}  "
                f"{terms[org['org_id']][year]:>12,}  {voluntary[org['org_id']][year]:>9,}  "
                f"{(leave_days_2025[org['org_id']] if year == 2025 else 0):>10,}"
            )
        bop = monthly[org["org_id"]][202412][0]
        eop = monthly[org["org_id"]][202512][0]
        separations = terms[org["org_id"]][2025]
        avg_hc = (bop + eop) / 2
        turnover = (separations / avg_hc * 100) if avg_hc else 0
        lines.append(
            f"  {org['org_name']} 2025 turnover check: "
            f"BOP {bop:,}  EOP {eop:,}  terminations {separations:,}  "
            f"rate {turnover:.2f}"
        )
    lines.append("")
    lines.append("Security mapping (lab users)")
    for email, mapped_org, access in SECURITY_ROWS:
        org_name = next(org["org_name"] for org in organisations if org["org_id"] == mapped_org)
        lines.append(f"  {email:<40} org {mapped_org} {org_name:<23} {access}")
    lines.append("  nora.nobody@example.com                  not in the mapping; must see no rows")
    lines.append("")
    lines.append("Band check: active headcount at 2025-12-31 falls inside employee_count_band")
    mismatches = 0
    for org in organisations:
        actual = monthly[org["org_id"]][202512][0]
        if actual != org["target"]:
            mismatches += 1
            lines.append(f"  MISMATCH org {org['org_id']} target {org['target']} actual {actual}")
    if mismatches:
        raise RuntimeError(f"{mismatches} organisations failed the headcount band check")
    lines.append(f"  all {len(organisations)} organisations match their target headcount")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  wrote {path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data")
    parser.add_argument("--totals", default="control_totals.txt")
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    print(f"Generating CloudHR data (seed {SEED}) into {out.resolve()}")

    organisations, departments, employees, by_org, corrupt = build(rng)

    write_csv(
        out / "organisations.csv",
        ["org_id", "org_name", "industry", "employee_count_band", "country", "subscription_tier"],
        [
            (org["org_id"], org["org_name"], org["industry"], org["employee_count_band"],
             org["country"], org["subscription_tier"])
            for org in organisations
        ],
    )
    write_csv(
        out / "departments.csv",
        ["department_id", "org_id", "department_name", "department_group", "cost_centre"],
        departments,
    )
    emp_rows = employee_rows(employees)
    write_csv(
        out / "employees.csv",
        ["employee_sk", "employee_id", "org_id", "first_name", "last_name", "department_id",
         "job_level", "employment_type", "hire_date", "termination_date", "termination_reason",
         "effective_start", "effective_end", "is_current", "is_active"],
        emp_rows,
    )
    monthly, snapshots, corrupt_hits = write_snapshots(
        out / "employee_monthly_snapshots.csv", organisations, employees, corrupt
    )
    leaves, reviews, leave_days_2025 = write_events(
        out / "leave_records.csv",
        out / "performance_reviews.csv",
        organisations,
        by_org,
        rng,
    )
    write_csv(
        out / "security_mapping.csv",
        ["user_email", "org_id", "access_level"],
        SECURITY_ROWS,
    )
    write_csv(
        out / "leave_entitlement.csv",
        ["leave_type", "employment_type", "annual_entitlement_days"],
        ENTITLEMENT,
    )
    write_totals(
        Path(args.totals),
        organisations,
        employees,
        departments,
        monthly,
        snapshots,
        corrupt_hits,
        leaves,
        reviews,
        leave_days_2025,
    )
    print("Done.")


if __name__ == "__main__":
    main()
