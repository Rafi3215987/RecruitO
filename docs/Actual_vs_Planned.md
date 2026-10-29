# Planned and Actual Work

This is a status snapshot against the revised RecruitO six-day plan (13 to 20 October 2026), updated 22 October 2026. Actual hours were not recorded consistently, so this note reports implementation evidence and outstanding checks rather than inventing hour totals.

## Work completed in source

| Plan area | Current result | Evidence or remaining check |
|---|---|---|
| CV screening and ranking (Day 5) | PDF/DOCX extraction, evidence-quoted requirement scoring at temperature 0, versioned score cache, ranking with a skills-then-experience tie-breaker, and an in-graph retry when model output fails validation | Unit tests cover scoring, evidence checks, and retry routing; live Gemini run pending |
| Batch intake and N1 timing (BID F1, N1) | Hiring-manager batch import of up to 50 CVs with per-file failure isolation and duplicate detection; `app.scripts.import_cvs` measures the 20-CV run; screening runs on a bounded thread pool | Unit tests cover validation, isolation, and the route; the 20-CV timing figure still needs a live run |
| Interviewer profile and assignment (Day 5) | Interviewer account/profile, photo processing, assigned interview list, role-scoped join token | Browser verification pending |
| Manager controls / god mode (Days 5 and 9) | Reasoned, audited correction; status change; CV replacement with rescore; per-application and per-job rescore that keeps earlier versions; candidate deletion; staff management; interview changes | Route permission tests pass; live audit-flow checks pending |
| Email and Calendar (Day 6) | Notification outbox with retries, Mailpit Compose service, `.ics` and template links (tier 1), and Google OAuth event creation with free/busy checks (tier 2) | Mailbox end-to-end and Google OAuth checks pending |
| Interview room and F4 (Days 7 and 8) | WebRTC signalling, session timestamps, explicit audio-consent record, chunk transcription in memory, stored segments, bounded transcript-socket reconnects | No TURN relay; two-browser and Gemini checks pending |
| F5 and F6 (Days 8 and 9) | LangGraph analysis/persistence flow, F8-F10 conditional extension, report and comparison pages, and strong/average/weak synthetic transcript fixtures | Gemini analysis output and browser print layout need a live run |
| Role chatbot (Days 8 and 9) | Candidate, interviewer, and hiring-manager allowlists; manager tools now include job profiles and consolidated assessments (Day 9 block 6); manual red-team checklist in `docs/Day8_Chatbot_RedTeam.md` | Allowlist unit tests pass; live red-team prompts pending |
| F7 (Day 7) | Optional enrollment, embedding-only storage, per-interview consent, one-frame matching, revocation, and 30-day expiry worker | Manual fallback and trainer/privacy approval pending |
| Blogger MCP | Mail2Blogger publisher and setup guide | Public publishing flow not exercised; see the F11 scope question in `Trainer_Clarifications_and_Plan_Changes.md` |

## Repository repair on 22 October

The 16 October merge commit (`50c354c`) carried unresolved conflict markers in 29 files, including `backend/app/main.py`, so the API could not start from the default branch. The files were restored from the clean resolution of the same merge (`dbe302a`); the previous state is kept on the `backup/pre-conflict-fix` branch. Three Day 3 tests that already failed on the clean commit were updated to the current design (jobs are approved by the policy-checked JD graph; the candidate-scoping check now uses the withdraw route).

## Planned work not verified yet

A clean-machine run, two-browser/WebRTC and webcam/microphone checks, real provider calls, end-to-end email and Blogger publishing, measured response latency, the 20-CV scoring demonstration, final presentation materials, the `v1.0-final` tag, and trainer confirmation remain outstanding.

## Actual-time record

Add actual hours to the WBS after the team reviews its work logs. This status note intentionally does not estimate time from code volume.
