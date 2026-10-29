# Trainer Clarifications and Plan Changes

This note records the plan changes that need written trainer confirmation before RecruitO is presented as meeting the updated requirements. No approval is assumed until the trainer responds.

## Decisions to request

| Topic | Proposed change | Trainer response |
|---|---|---|
| New mandatory features | Confirm the interviewer role, manager audit controls, status emails, Calendar tier 1, role-aware chatbot, and F7-F10 are required for this submission. | Pending |
| Innovation feature | Confirm whether the Blogger MCP publishing workflow and recruitment assistant count as F11, and whether the JD assistant is supporting functionality. Note the scope risk: BID section 4.2 lists job-board publishing as out of scope, and the revised plan makes the role chatbot mandatory, so neither may be creditable as F11. Calendar integration and automated scheduling are the one out-of-scope area the BID allows as an innovation feature, and the scheduling agent with Google Calendar sync is implemented. | Pending |
| Scope | Confirm that the implemented thin slices are acceptable given the time limit and that Google Calendar tier 1 meets the calendar requirement when Google Cloud OAuth tier 2 is unavailable. | Pending |
| Biometrics | Confirm whether a local SFace prototype may be demonstrated with synthetic users only, and whether any real-candidate biometric processing is prohibited. | Pending |
| Consent and retention | Approve or replace the 30-day biometric embedding retention, consent wording, transcript handling, and other data-retention periods. | Pending |

## Manual action

The project owner must send this clarification request to the trainer and record the response in the table. RecruitO currently avoids assuming approval for the changes identified in the revised plan.

## Current implementation distinction

Source code exists for the interviewer role, manager audit actions and rescoring, notifications, Calendar tier 1 links and `.ics`, Google Calendar tier 2 OAuth event creation with interviewer free/busy checks, role-scoped chat, consented transcription, batch CV import, F6 reports, F7 biometric prototype, and F8-F10 assessment. Live provider, Google OAuth, and browser verification remain pending; tier 2 needs a Google Cloud project and organiser credentials before it can be demonstrated.
