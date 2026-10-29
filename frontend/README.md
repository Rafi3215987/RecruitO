# RecruitO frontend

A dependency-free HTML, CSS, and JavaScript client for RecruitO's hiring-manager and candidate workflows.

The frontend uses these API endpoints:

- `GET /health`
- `POST /auth/login`
- `POST /auth/logout` (clear the HttpOnly session cookie)
- `POST /auth/register` (candidate registration)
- `GET /me/profile` (signed-in candidate's own profile)
- `GET /auth/profile` and `PUT /auth/profile` (hiring-manager profile)
- `GET /public/jobs` (approved jobs for the public listing)
- `POST /public/jobs/{job_id}/apply` (candidate application and profile details)
- `GET /me/applications` (signed-in candidate's applications)
- `POST /chat/candidate` (candidate assistant for own application/interview data and public jobs)
- `GET /applications` (hiring-manager application list)
- `PUT /applications/{application_id}/interview` (schedule or update an interview)
- `GET /jobs` (hiring-manager access)
- `POST /jobs/generate`
- `POST /jobs/assistant/chat` (LangGraph hiring-manager conversation and draft generation)
- `GET /jobs/{job_id}`
- `PUT /jobs/{job_id}`
- `POST /jobs/{job_id}/approve`
- `POST /jobs/{job_id}/publish-blogger` (MCP-backed Mail2Blogger email publishing; sends a new post)

The hiring workspace uses a LangGraph conversational assistant to collect a manager's job brief in natural language, clarify missing details, and generate a policy-checked draft. Managers review and edit the draft and explicitly approve it before it appears on RecruitO's public candidate page. An approved job can be emailed to Blogger through the bundled MCP service; the Blogger post includes the description and a RecruitO application link. Blogger's email flow creates a new post each time and RecruitO links to the blog homepage. The public candidate card shows only the role title and experience level. Other websites can still be linked manually, and LinkedIn, Facebook, and X sharing composers remain available.

Configure `BLOGGER_SITE_URL`, `BLOGGER_POST_EMAIL`, and the `SMTP_*` settings in `.env`. Set up the private Mail2Blogger address in Blogger settings. Set `PUBLIC_BASE_URL` to RecruitO's publicly accessible HTTPS frontend address so candidates can open application links. Run `docker compose up --build` to start the API, frontend, database, and Blogger MCP service.

Candidates register with their name, email, and phone number. The candidate site opens on their private profile after sign-in, and provides separate profile, jobs, and dashboard views. Each application form collects the name shown on the candidate's certificate, contact details, qualification, institution, department, and (optionally) graduation year. Submitting an application updates that candidate's profile and creates the application. The dashboard lists the candidate's own application statuses, prioritizes scheduled interviews, and shows interview date/time and duration. Candidates can also ask the candidate assistant about their own applications and public job posts. Video sessions, CV screening, and assessments are outside the current scope.

## Authentication and roles

- `POST /auth/register` creates candidate accounts only. The frontend then signs the candidate in with `POST /auth/login`.
- Hiring-manager accounts are created by the backend's `app.scripts.seed_staff` script from the `HIRING_MANAGER_*` environment settings; there is no public manager registration.
- Login verifies the submitted email and password hash, then sets a signed JWT in an `HttpOnly`, `SameSite=Lax` cookie. The browser does not read or save the token; fetch requests send the cookie with `credentials: "include"`.
- Protected requests decode the cookie, load the active user from the database, and enforce the role on the endpoint. Candidate data routes require `candidate`; job administration, hiring-manager profiles, application review, and interview scheduling require `hiring_manager`. Public approved-job listing does not require a session.
- `POST /auth/logout` expires the browser cookie. Tokens are stateless and are not revoked server-side, so a copied token could remain valid until its configured expiry.
- For local HTTP, keep `COOKIE_SECURE=false`; set `COOKIE_SECURE=true` when using HTTPS. Open the frontend and API using the same local hostname to ensure the browser sends the `SameSite=Lax` cookie.

## Run locally

To run the frontend with Docker Compose, start the stack from the repository root:

```powershell
docker compose up --build
```

Open `http://localhost:5500`. The Compose frontend service serves the static site and includes the root `background2.png` landing-page image.

For a local frontend/API setup without Docker, use these steps:

1. Configure `GEMINI_API_KEY` for the existing Gemini-backed LangGraph workflows, then start the API and database using the repository's existing backend setup.
2. From the backend directory, apply database migrations before starting the updated API:

   ```powershell
   alembic upgrade head
   ```

   The candidate profile workflow adds columns to `candidate_profiles`; existing profile rows remain valid and candidates can complete their details on their next application.
3. From the repository root, serve `frontend` on an allowed local origin, for example:

   ```powershell
   cd frontend
   py -m http.server 5500 --bind 127.0.0.1
   ```

4. Open `http://127.0.0.1:5500` in the browser. The home page signs candidates in or lets them create an account, then routes by account role. Hiring managers sign in with their provided work account. For cookie-based sign-in, the UI uses the same local hostname as the API (`127.0.0.1:8000` here).
5. Sign in with the hiring-manager account configured through `HIRING_MANAGER_EMAIL` and `HIRING_MANAGER_PASSWORD` in `.env`. If the account has not been created, run the backend's `app.scripts.seed_staff` script once.
6. Candidate accounts are routed to `public-jobs.html` and open on their personal profile, with navigation to approved jobs and their private application dashboard.
7. Open `http://127.0.0.1:5500/manager-applications.html` to review applications and schedule interviews as a hiring manager.

For same-Wi-Fi development, open the frontend at `http://<computer-lan-ip>:5500`; the client will use the same IP on port 8000 for the API. Set `FRONTEND_LAN_HOST=<computer-lan-ip>` in the root `.env`, and keep the private-network `CORS_ORIGIN_REGEX` from `.env.example`. These settings permit HTTP only for private IPv4 addresses and the LAN API host. Remove the regex allowance for deployments on untrusted networks. Camera and microphone access from another device requires HTTPS; HTTP LAN mode is for basic UI/API access. Public job links shared outside RecruitO must use the public HTTPS deployment URL; local development URLs are not reachable by external candidates.

## Security notes

- Do not use real candidate personal information in this prototype.
- The UI does not store job data, passwords, or bearer tokens in browser storage. Login uses the backend's HttpOnly cookie and API requests include that cookie.
- User-controlled content is assigned as text/value through DOM APIs, not interpreted as HTML.
- The API URL is restricted to HTTPS except on localhost and private IPv4 addresses used for local LAN development; API errors are shown as safe, generic messages.
- For local development, use matching hosts: both `localhost`, both `127.0.0.1`, or the same private LAN IPv4 address. The frontend and API can use different ports on that host.
- The browser policy blocks inline scripts/styles, plugins, and external connections other than the local API.
- Local HTTP is only for development. Use HTTPS for any non-local deployment.
- Backend authorization remains authoritative; the UI hides the workspace until the protected hiring-manager job list succeeds. Signing out calls `POST /auth/logout` to clear the HttpOnly session cookie; the page reloads only after the API confirms success.
