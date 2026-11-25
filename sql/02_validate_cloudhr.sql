-- Figures to compare with control_totals.txt and with the Power BI measures.
-- Active headcount is is_active at the month. Average salary ignores pay <= 0.
-- Data-error employees are loaded with is_active = false, so they are already
-- out of the headcount.
\set ON_ERROR_STOP on

SELECT o.org_id,
       o.org_name,
       COUNT(*) FILTER (WHERE s.is_active) AS active_headcount,
       ROUND(
           AVG(s.base_salary_usd) FILTER (WHERE s.is_active AND s.base_salary_usd > 0),
           2
       ) AS avg_base_salary
FROM hr.employee_monthly_snapshots AS s
JOIN hr.organisations AS o ON o.org_id = s.org_id
WHERE s.snapshot_month = DATE '2025-12-01'
  AND s.org_id IN (1, 2, 3)
GROUP BY o.org_id, o.org_name
ORDER BY o.org_id;

SELECT o.org_id,
       o.org_name,
       COUNT(*) FILTER (WHERE s.is_active) AS active_headcount_bop
FROM hr.employee_monthly_snapshots AS s
JOIN hr.organisations AS o ON o.org_id = s.org_id
WHERE s.snapshot_month = DATE '2024-12-01'
  AND s.org_id IN (1, 2, 3)
GROUP BY o.org_id, o.org_name
ORDER BY o.org_id;

SELECT e.org_id,
       COUNT(DISTINCT e.employee_id) FILTER (
           WHERE e.hire_date BETWEEN DATE '2025-01-01' AND DATE '2025-12-31'
       ) AS new_hires_2025,
       COUNT(DISTINCT e.employee_id) FILTER (
           WHERE e.termination_date BETWEEN DATE '2025-01-01' AND DATE '2025-12-31'
       ) AS terminations_2025,
       COUNT(DISTINCT e.employee_id) FILTER (
           WHERE e.termination_date BETWEEN DATE '2025-01-01' AND DATE '2025-12-31'
             AND e.termination_reason IN ('Resignation', 'Retirement')
       ) AS voluntary_terminations_2025
FROM hr.employees AS e
WHERE e.is_current
  AND e.org_id IN (1, 2, 3)
  AND NOT (e.termination_date IS NOT NULL AND e.hire_date > e.termination_date)
GROUP BY e.org_id
ORDER BY e.org_id;

SELECT org_id, SUM(days_taken) AS leave_days_2025
FROM hr.leave_records
WHERE start_date BETWEEN DATE '2025-01-01' AND DATE '2025-12-31'
  AND org_id IN (1, 2, 3)
GROUP BY org_id
ORDER BY org_id;

SELECT COUNT(*) AS non_positive_salaries
FROM hr.employee_monthly_snapshots
WHERE base_salary_usd <= 0;

SELECT COUNT(*) AS hire_after_termination
FROM hr.employees
WHERE is_current
  AND termination_date IS NOT NULL
  AND hire_date > termination_date;
