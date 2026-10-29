# Synthetic interview transcripts

These transcripts are synthetic demonstration inputs, not real candidate records. They use a generic application API scenario and contain only the request fields accepted by `MockTranscriptImportRequest`.

## Import and analyze

1. Start RecruitO with `APP_ENV=development` and sign in as a hiring manager.
2. Create or choose a job with requirements and schedule an interview for each transcript.
3. Send one JSON file to `POST /admin/interviews/{interview_id}/mock-transcript` with the hiring manager's authenticated session. The import endpoint is disabled outside development.
4. Run `POST /admin/interviews/{interview_id}/analysis` for each imported transcript. This invokes the F5 graph and requires the configured Gemini assessment service. If the application has a readable CV, the graph also attempts F8-F10.

The files represent strong, average, and weak evidence. They are prompts for human review and do not represent hiring decisions or expected numeric scores.
