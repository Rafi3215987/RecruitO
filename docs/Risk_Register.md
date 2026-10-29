# RecruitO Risk Register

| Risk | Likelihood / impact | Mitigation | State |
|---|---|---|---|
| Docker may differ on another machine, affecting migrations and integration checks | Medium / High | Docker Compose, Alembic upgrade, and health checks succeeded on this machine; repeat them from a clean clone or clean Docker environment | Reduced; clean-machine verification pending |
| WebRTC fails behind restrictive networks | Medium / High | Keep manual phone/video fallback; add and verify a TURN service if deployment permits; test with two browsers on separate networks | Active; no TURN configured |
| Gemini model, key, quota, or output validation fails | Medium / High | Keep model names configurable, validate structured responses, return generic errors, and demo with mock transcripts where appropriate | Active; live provider verification pending |
| Biometric false match, privacy harm, or unclear model provenance | Medium / High | Keep enrollment optional, require explicit consent, store only embeddings for 30 days, allow revocation, never automate hiring, use synthetic data, and seek trainer review before real-candidate use | Active; approval pending |
| Audio transcription delay or errors disrupt interview | Medium / Medium | Keep transcription consent separate from the call, continue the WebRTC call when transcription stops, and retain manual note-taking | Active; chunked rather than low-latency streaming |
| Candidate data retained longer than intended | Medium / High | Restrict access, use synthetic demo data, delete candidates through the audited deletion route, and obtain a trainer-approved retention schedule before real data | Active |
| Calendar tier 2 requires unavailable Google Cloud setup | High / Medium | Use the implemented `.ics` file and Google event-template link (tier 1); disclose that OAuth event sync is not included | Accepted constraint |
| Email delivery fails or duplicates | Medium / Medium | Use a deduplicated outbox with bounded retries and inspect Mailpit during integration checks | Active; live check pending |
| Plan changes are not approved by the trainer | Medium / High | Send the clarification note and record written decisions before claiming conformance | Active; owner action required |
