-- CloudHR source database for the SK-06 capstone.
-- Run inside the container:
--   psql -U postgres -d cloudhr -f /sql/01_create_and_load_cloudhr.sql
-- Safe to re-run: it drops and recreates the hr schema.
\set ON_ERROR_STOP on

DROP SCHEMA IF EXISTS hr CASCADE;
CREATE SCHEMA hr;

CREATE TABLE hr.organisations (
    org_id                INT PRIMARY KEY,
    org_name              TEXT NOT NULL UNIQUE,
    industry              TEXT NOT NULL,
    employee_count_band   TEXT NOT NULL,
    country               TEXT NOT NULL,
    subscription_tier     TEXT NOT NULL
);

CREATE TABLE hr.departments (
    department_id      INT PRIMARY KEY,
    org_id             INT NOT NULL REFERENCES hr.organisations (org_id),
    department_name    TEXT NOT NULL,
    department_group   TEXT NOT NULL,
    cost_centre        TEXT NOT NULL UNIQUE
);

-- SCD Type 2. employee_id is the business key and repeats once per version.
-- employee_sk is the surrogate primary key.
CREATE TABLE hr.employees (
    employee_sk          INT PRIMARY KEY,
    employee_id          INT NOT NULL,
    org_id               INT NOT NULL REFERENCES hr.organisations (org_id),
    first_name           TEXT NOT NULL,
    last_name            TEXT NOT NULL,
    department_id        INT NOT NULL REFERENCES hr.departments (department_id),
    job_level            TEXT NOT NULL,
    employment_type      TEXT NOT NULL,
    hire_date            DATE NOT NULL,
    termination_date     DATE,
    termination_reason   TEXT,
    effective_start      DATE NOT NULL,
    effective_end        DATE,
    is_current           BOOLEAN NOT NULL,
    is_active            BOOLEAN NOT NULL
);

-- One row per employee per month. snapshot_month is the first day of the month.
-- employment_type is part of the month-end state, so it lives here as well as
-- on the employee version that was in force.
CREATE TABLE hr.employee_monthly_snapshots (
    snapshot_month     DATE NOT NULL,
    employee_id        INT NOT NULL,
    org_id             INT NOT NULL REFERENCES hr.organisations (org_id),
    is_active          BOOLEAN NOT NULL,
    base_salary_usd    NUMERIC(12,2) NOT NULL,
    job_level          TEXT NOT NULL,
    department_id      INT NOT NULL REFERENCES hr.departments (department_id),
    employment_type    TEXT NOT NULL,
    PRIMARY KEY (employee_id, snapshot_month)
);

-- department_id and employment_type are the values in force on start_date.
-- The capstone source list does not include them; the leave page cannot
-- slice by department without them.
CREATE TABLE hr.leave_records (
    leave_id           INT PRIMARY KEY,
    employee_id        INT NOT NULL,
    org_id             INT NOT NULL REFERENCES hr.organisations (org_id),
    department_id      INT NOT NULL REFERENCES hr.departments (department_id),
    employment_type    TEXT NOT NULL,
    leave_type         TEXT NOT NULL,
    start_date         DATE NOT NULL,
    end_date           DATE NOT NULL,
    days_taken         INT NOT NULL,
    approved_by        INT NOT NULL
);

CREATE TABLE hr.performance_reviews (
    review_id          INT PRIMARY KEY,
    employee_id        INT NOT NULL,
    org_id             INT NOT NULL REFERENCES hr.organisations (org_id),
    department_id      INT NOT NULL REFERENCES hr.departments (department_id),
    employment_type    TEXT NOT NULL,
    review_year        INT NOT NULL,
    rating             INT NOT NULL,
    reviewer_id        INT NOT NULL,
    UNIQUE (employee_id, review_year)
);

CREATE TABLE hr.security_mapping (
    user_email     TEXT PRIMARY KEY,
    org_id         INT NOT NULL REFERENCES hr.organisations (org_id),
    access_level   TEXT NOT NULL
);

-- Supporting lookup for Leave Utilization %. Not a source transaction table.
CREATE TABLE hr.leave_entitlement (
    leave_type                  TEXT NOT NULL,
    employment_type             TEXT NOT NULL,
    annual_entitlement_days     INT NOT NULL,
    PRIMARY KEY (leave_type, employment_type)
);

COPY hr.organisations              FROM '/data/organisations.csv'              WITH (FORMAT csv, HEADER true, NULL '');
COPY hr.departments                FROM '/data/departments.csv'                WITH (FORMAT csv, HEADER true, NULL '');
COPY hr.employees                  FROM '/data/employees.csv'                  WITH (FORMAT csv, HEADER true, NULL '');
COPY hr.employee_monthly_snapshots FROM '/data/employee_monthly_snapshots.csv' WITH (FORMAT csv, HEADER true, NULL '');
COPY hr.leave_records              FROM '/data/leave_records.csv'              WITH (FORMAT csv, HEADER true, NULL '');
COPY hr.performance_reviews        FROM '/data/performance_reviews.csv'        WITH (FORMAT csv, HEADER true, NULL '');
COPY hr.security_mapping           FROM '/data/security_mapping.csv'           WITH (FORMAT csv, HEADER true, NULL '');
COPY hr.leave_entitlement          FROM '/data/leave_entitlement.csv'          WITH (FORMAT csv, HEADER true, NULL '');

CREATE INDEX ix_employees_business_key ON hr.employees (employee_id);
CREATE INDEX ix_employees_current ON hr.employees (employee_id) WHERE is_current;
CREATE INDEX ix_snapshots_org_month ON hr.employee_monthly_snapshots (org_id, snapshot_month);
CREATE INDEX ix_leave_org ON hr.leave_records (org_id, start_date);
CREATE INDEX ix_reviews_org ON hr.performance_reviews (org_id, review_year);
ANALYZE;

SELECT 'hr.organisations' AS table_name, COUNT(*) AS row_count FROM hr.organisations
UNION ALL SELECT 'hr.departments',                COUNT(*) FROM hr.departments
UNION ALL SELECT 'hr.employees',                  COUNT(*) FROM hr.employees
UNION ALL SELECT 'hr.employee_monthly_snapshots', COUNT(*) FROM hr.employee_monthly_snapshots
UNION ALL SELECT 'hr.leave_records',              COUNT(*) FROM hr.leave_records
UNION ALL SELECT 'hr.performance_reviews',        COUNT(*) FROM hr.performance_reviews
UNION ALL SELECT 'hr.security_mapping',           COUNT(*) FROM hr.security_mapping
UNION ALL SELECT 'hr.leave_entitlement',          COUNT(*) FROM hr.leave_entitlement
ORDER BY table_name;
