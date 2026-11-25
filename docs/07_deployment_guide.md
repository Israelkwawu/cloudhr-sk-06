# Deployment guide

One dataset and one report serve all clients. A new client is a row in the data and a row in `security_mapping`, not a new workspace.

## Workspaces

| Workspace | Who is a member | What is published |
|---|---|---|
| CloudHR Analytics — Dev | Dataset authors: Admin. Other engineers: Member. | Desktop publishes here. RLS is on, but Members can still see every tenant, so this is not a place client users are invited. |
| CloudHR Analytics — Test | Authors: Member. The analytics lead: Member. QA: Viewer on the workspace is not enough to test RLS; give QA the app and the test accounts below. | The pipeline promotes Dev into here. Parameters point at the test database. |
| CloudHR Analytics — Prod | One break-glass Admin (the analytics lead) and the deployment pipeline identity. Nobody else. | The app that clients open. Authors do not have Member rights here, so they cannot bypass RLS by opening the workspace. |

Client HR users are not members of any of these workspaces. They receive the Prod app only. App permission is required to open the report. It does not turn RLS off. Build permission is not granted to clients; Build would let them download a copy or query `security_mapping`.

Dev is where a broken measure is allowed to exist. Test is where the three lab users are checked after a promotion. Prod is the only place a client principal is assigned the Tenant Access role.

## How a change moves

1. The author changes the PBIP or the Desktop file on a branch and publishes to Dev.
2. A second author reviews the model: relationships still match the design doc, the employee relationship is still inactive, and the Acme Labs 2025 checks still hit 84, 7.45, and 91,107.63.
3. The analytics lead approves the Dev → Test promotion in the deployment pipeline. This is the gate. Test is not refreshed from someone's laptop.
4. In Test, View as / Test as role for Ada, Ben, and Nora. Ben's average salary must be 82,695.26 and must not be 91,107.63. The promotion stops here if that fails.
5. The same lead approves Test → Prod. Prod's deployment rules are the only thing that should differ: the server and database parameters, and the gateway or cloud data source mapping. Measures, RLS expressions, and page layout are not edited in Prod.

Deployment rules:

| Parameter | Dev | Test | Prod |
|---|---|---|---|
| Server | `localhost:5435` while you are on a laptop; a shared dev host once more than one author refreshes | Test warehouse host | Production warehouse host |
| Database | `cloudhr` | `cloudhr_test` | `cloudhr` |

The local container cannot be the refresh source for the Power BI service. The service does not see `localhost` on your machine. Dev refreshes from Desktop against the container are for building. Scheduled refresh starts when the parameter points at a host the service can reach.

## Refresh

Refresh weekly, Sunday at 02:00 in the region where the warehouse sits. The business asked for weekly, not monthly, and a Sunday night run finishes before Monday morning in the US and before the working day in Europe. Do not schedule it for Monday 09:00; a failure then is discovered by clients.

The lab container does not need a gateway for Desktop. Production does not need an on-premises gateway if the warehouse is Azure Database for PostgreSQL (or another cloud host) and the Power BI tenant is allowed through the firewall or a private endpoint. Use an on-premises data gateway only if the database remains on a network the service cannot reach. One gateway cluster, two members, so a reboot does not miss the Sunday run.

Failure mail goes to the data-platform on-call list and to the analytics lead. The dataset owner in Prod is the lead, not a client. A failed refresh keeps the previous model, which is the right failure mode: clients see last week's numbers, not an empty report. The on-call note should say to fix the pipeline and re-run, not to turn RLS off to "see if that helps."

## Onboarding the 201st organisation

There is no new report.

1. The application database creates the organisation, its departments, and its employees. That is an application change, upstream of Power BI.
2. The warehouse load includes the new org on its normal run. Confirm `organisations`, `departments`, and `employee_monthly_snapshots` contain the new `org_id`.
3. Insert one `security_mapping` row per HR user: their user principal name, the new `org_id`, and `HR_ADMIN` or `HR_VIEWER`.
4. Add those users to the Prod app audience.
5. Refresh on demand if they must see data before Sunday. Otherwise the Sunday refresh is enough.
6. Test as role with the new admin's email. Confirm headcount matches the warehouse for that org and that Ada still sees only Acme Labs.
7. Tell the client.

The Power BI portion of that list is a mapping row, an app assignment, a refresh, and a test. Budget under one business day, and most of that is waiting for the identity to exist in Entra ID and for the warehouse load. It is not a two-week spreadsheet cycle.

If the test user sees every tenant, they are a workspace Member. Remove that access before you continue. If they see nothing, the email does not match, or the snapshot load has not landed their `org_id` yet.
