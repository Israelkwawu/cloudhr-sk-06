# RLS administration guide

Role name: **Tenant Access**. One role is used for every client user. The filter is the same expression on each table that carries `org_id`:

```dax
[org_id] =
LOOKUPVALUE (
    security_mapping[org_id],
    security_mapping[user_email],
    USERPRINCIPALNAME ()
)
```

Paste it onto `dim_organisation`, `dim_department`, `dim_employee`, `fact_employee_monthly`, `fact_leave`, `fact_performance`, and `salary_data_errors`. Do not paste it onto `security_mapping`. A filter on the mapping table can hide the row `LOOKUPVALUE` needs.

`access_level` does not change what the user sees. `HR_ADMIN` and `HR_VIEWER` at the same organisation see the same rows. The column is stored so a later object-level or page-level rule can tell them apart. It must not be turned into a cross-tenant bypass. CloudHR staff who need every client belong in a separate internal role that is never assigned to a client account.

`user_email` has to be unique and has to equal the user's Entra ID user principal name, including the domain. `LOOKUPVALUE` fails the query if two rows share an email.

## Add a user

1. Confirm the organisation already exists in `hr.organisations` and that its snapshots have refreshed. A mapping row for an org with no data shows an empty report, which is easy to misread as a security bug.
2. Insert one row into `security_mapping`: email, `org_id`, `HR_ADMIN` or `HR_VIEWER`. In this lab the table is hard-coded in Power Query, so add the row to the `security_mapping` query and refresh. In production, insert it in the warehouse and refresh the dataset. Do not publish a second dataset.
3. Refresh, then test with View as before you tell the user the report is ready.

## Revoke access

Delete that person's row, or stop publishing them to the table. Refresh. The next time they open the report, `LOOKUPVALUE` returns blank and the filter matches no organisation.

Removing them from the Power BI app audience is a second step, not a substitute. A user who can still open the dataset and whose row is still in the mapping can still see their tenant.

## Test after every mapping change

Desktop: Modeling → View as → Other user. Type the full email. Also tick the Tenant Access role. "Other user" alone does not apply the role.

| User | Organisation | Must see at December 2025 | Must not see |
|---|---|---|---|
| ada.mensah@acme-labs.example | Acme Labs (HR admin) | Headcount 84, average salary 91,107.63 | 82,695.26 or 85,166.33 |
| dana.asante@acme-labs.example | Acme Labs (viewer) | The same figures as Ada | Another tenant |
| ben.owusu@brightpath.example | BrightPath Logistics | Headcount 86, average salary 82,695.26 | Acme's 91,107.63 |
| cara.boateng@cedarhealth.example | Cedar Health | Headcount 66, average salary 85,166.33 | Acme or BrightPath |
| nora.nobody@example.com | Not in the mapping | Blank cards and empty charts | Any organisation's numbers |

The critical negative test is Ben. Filter nothing, read Avg Base Salary, and confirm it is BrightPath's 82,695.26. Then look at a table of `org_name`. It must contain only BrightPath Logistics. Acme's average salary must not appear in any card, chart, or tooltip. Repeat with the salary chart and the employee table: no Acme names, no Acme departments.

Nora should see blanks, not an error dialog and not a mix of tenants. A blank result is the safe outcome: no `org_id` equals blank. It is not a license to remove the role.

In the service, use Test as role on the dataset with the same emails, after the dataset has refreshed. View as in Desktop does not prove the published copy.

## If a user reports seeing the wrong data

1. Stop and do not ask them to screenshot the other tenant's pay.
2. Read their user principal name from Entra ID and compare it, character for character, with `security_mapping`.
3. Confirm they have only the Tenant Access role, and that no one has assigned them an internal role.
4. Confirm the dataset they opened is the app in Prod, not a Desktop file or a workspace copy where RLS is not enforced. Workspace Members see all rows. Client users get app access, never workspace access.
5. If the mapping row is wrong, fix it, refresh, and re-run Ben's negative test plus the affected user before you reopen the ticket.
