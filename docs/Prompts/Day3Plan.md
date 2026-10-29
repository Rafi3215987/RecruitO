# RecruitO: Scope Update, Hiring Manager and Candidate Roles

RecruitO | Scope update | 9 October 2026

Only two accounts need to work end to end for now: hiring manager and candidate. Only the hiring manager creates job profiles, and a candidate sees only their own dashboard.

## What changes

- **Interviewer is deferred.** Keep it in the role list so the schema stays stable, but build no screens for it. For now the hiring manager can act as the interviewer in the video session. That still satisfies the BID's access separation (N9), because candidates stay locked away from scoring and assessment data.
- **Staff accounts are still seeded by script.** Candidates self-register.

## Permission matrix

| Action | Hiring manager | Candidate |
| --- | --- | --- |
| Create, edit, approve, publish job profiles (including the JD agent) | Yes | No |
| View the public job post and apply | Yes | Yes |
| View applications, rankings, evaluations | Yes | No |
| Schedule an interview for an application | Yes | No |
| View own dashboard (applied jobs, status, interview schedule) | No | Yes |
| View another candidate's data | Yes | Never |

Enforce this with `require_roles("hiring_manager")` on every job-creation route (`generate`, create, edit, approve, publish). Store `created_by` on each job.

## Hiring manager profile

Keep it small: a page to view and edit name and contact details, plus the dashboard that lists jobs and their statuses. Do not add fields you do not use.

## Candidate dashboard

`GET /me/applications` is scoped by the user ID inside the JWT. Never take a candidate ID from the URL. For each application it returns:

- Job title and public job info only (no requirements, weights, or scores).
- A candidate-friendly status.
- The interview schedule, if one exists.

### Status mapping

Keep internal statuses private and show a simple label:

| Internal | Candidate sees |
| --- | --- |
| Submitted, parsing, screening, ranked | Under review |
| Selected for interview | Interview stage |
| Interview scheduled | Interview scheduled (with date and time) |
| Interview completed | Awaiting decision |
| Decision made | Decision available (wording is your call) |

This avoids leaking scores or rank position through the dashboard. Decide with your trainer how outcomes such as rejection should be shown.

## Interview schedule

Add an `interviews` table: id, application\_id, scheduled\_at (store UTC), duration, status, and later a session or room link.

- The hiring manager sets the date and time from the application's page.
- The candidate dashboard shows it, converted to their local time. A "Join" button stays disabled until the video session exists.
- Keep this to a plain date and time record. Calendar sync and email invites are out of scope in the BID.

## Build order and time

| Order | Work | Time |
| --- | --- | --- |
| 1 | Users, `candidate_profiles`, JWT login, role dependencies | as planned |
| 2 | Gate all job routes to hiring manager, add `created_by`, hiring dashboard listing jobs | 1 h |
| 3 | Public job page, Apply button, on-site form saved to the candidate profile, `applications` table | Block 1 |
| 4 | `GET /me/applications` and the candidate dashboard (status cards) | 2 to 3 h |
| 5 | `interviews` table, hiring manager scheduling UI, schedule shown on the dashboard | 1.5 h |

## Tests that prove the rules

- A candidate calling any job-creation route gets 403.
- Candidate A requesting candidate B's application gets 404, not 403, so IDs cannot be probed.
- The dashboard response contains no scores, requirements, or rank.
- A hiring manager token can create and publish a job.

## Candidate chatbot

Its tool list now matches the dashboard exactly: own applications, status, and interview time, plus public job posts. Nothing else.

## Open question

Should every hiring manager see all jobs, or only the ones they created? For a single-company demo the default is all, and `created_by` keeps the option open.
