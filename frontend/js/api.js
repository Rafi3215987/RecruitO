const REQUEST_TIMEOUT_MS = 60_000;

function isPrivateLanIpv4(hostname) {
  const octets = hostname.split(".").map(Number);
  if (octets.length !== 4 || octets.some((octet) => !Number.isInteger(octet) || octet < 0 || octet > 255)) {
    return false;
  }

  return octets[0] === 10
    || (octets[0] === 172 && octets[1] >= 16 && octets[1] <= 31)
    || (octets[0] === 192 && octets[1] === 168);
}

function getApiBase() {
  // The site and the API share one origin: nginx serves the static files and
  // reverse-proxies the API under /api. This works the same on localhost, a LAN
  // IP, and a public Cloudflare tunnel, with no cross-origin or per-host setup.
  const override = window.RECRUITO_CONFIG && window.RECRUITO_CONFIG.apiBaseUrl;
  if (override) return override.replace(/\/$/, "");
  return `${window.location.origin}/api`;
}

// Once an authenticated (non-public) request has succeeded we know a session is
// active; a later 401 then means that session expired, so we send the user to
// sign in. We never do this during the public/login calls or before any
// authenticated success, which keeps the sign-in page itself from looping.
let hasAuthenticatedSession = false;
let redirectingToSignIn = false;
const PUBLIC_PATH_PREFIXES = ["/health", "/public/", "/auth/login", "/auth/register", "/auth/logout"];

function isPublicPath(path) {
  return PUBLIC_PATH_PREFIXES.some((prefix) => path.startsWith(prefix));
}

function redirectToSignIn() {
  if (redirectingToSignIn) return;
  redirectingToSignIn = true;
  hasAuthenticatedSession = false;
  try {
    window.location.replace("./index.html?auth=signin&expired=1");
  } catch {
    // Navigation failures are non-fatal; the ApiError is still thrown to the caller.
  }
}

async function request(path, options = {}) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  const headers = new Headers(options.headers);

  if (options.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  try {
    const response = await fetch(`${getApiBase()}${path}`, {
      ...options,
      headers,
      signal: controller.signal,
      credentials: "include",
      cache: "no-store",
      redirect: "error"
    });

    if (response.ok && !isPublicPath(path)) {
      hasAuthenticatedSession = true;
    }

    if (!response.ok) {
      let responseBody = null;
      try {
        responseBody = await response.clone().json();
      } catch {
        // Keep the status-based message when the API did not return JSON.
      }
      if (
        response.status === 401
        && hasAuthenticatedSession
        && !path.startsWith("/auth/login")
        && !path.startsWith("/auth/register")
      ) {
        redirectToSignIn();
      }
      throw new ApiError(response.status, responseBody?.detail);
    }

    if (response.status === 204) {
      return null;
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    if (error.name === "AbortError") {
      throw new Error("The request took too long. Please try again.");
    }
    throw new Error(
      "Could not reach the RecruitO API. Check that it is running, that CORS_ORIGINS includes this frontend origin, and that local frontend/API hostnames match."
    );
  } finally {
    window.clearTimeout(timeoutId);
  }
}

export class ApiError extends Error {
  constructor(status, detail = null) {
    super(status >= 500
      ? "The server could not complete the request. Please try again."
      : status === 404
        ? "The requested resource could not be found."
        : status === 409
          ? "This job is no longer a draft and cannot be changed."
        : status === 401
          ? "Your sign-in has expired or the email and password were not accepted."
        : status === 403
          ? "This account does not have permission to manage jobs."
        : status === 413
          ? "The upload is too large. Each CV must be 10 MB or smaller, and very large batches may exceed the server limit."
        : status === 502
          ? "Blogger could not publish the job. Check the Blogger MCP service, blog ID, and Google OAuth settings."
        : status === 503
          ? "Set PUBLIC_BASE_URL to RecruitO's public HTTPS address before publishing a job externally."
          : "The request was not accepted. Check the details and try again.");
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

export const api = Object.freeze({
  health: () => request("/health"),
  listPublicJobs: () => request("/public/jobs"),
  registerCandidate: (email, password, fullName, phoneNumber) => request("/auth/register", {
    method: "POST",
    body: JSON.stringify({
      email,
      password,
      full_name: fullName,
      phone_number: phoneNumber
    })
  }),
  applyToJob: (jobId, payload) => request(`/public/jobs/${encodeURIComponent(jobId)}/apply`, {
    method: "POST",
    body: payload
  }),
  applicationResumeUrl: (applicationId) => `${getApiBase()}/applications/${encodeURIComponent(applicationId)}/resume`,
  getCandidateProfile: () => request("/me/profile"),
  updateCandidateProfile: (payload) => request("/me/profile", {
    method: "PUT",
    body: JSON.stringify(payload)
  }),
  getBiometricEnrollment: () => request("/me/biometric-enrollment"),
  enrollBiometricProfile: (image) => {
    const form = new FormData();
    form.append("consent", "true");
    form.append("reference_photo", image, "biometric-reference.jpg");
    return request("/me/biometric-enrollment", { method: "POST", body: form });
  },
  revokeBiometricConsent: () => request("/me/biometric-enrollment", { method: "DELETE" }),
  listMyApplications: () => request("/me/applications"),
  removeMyApplication: (applicationId) => request(`/me/applications/${encodeURIComponent(applicationId)}`, {
    method: "DELETE"
  }),
  sendCandidateChat: (message) => request("/chat/assistant", {
    method: "POST",
    body: JSON.stringify({ message })
  }),
  sendRoleChat: (message) => request("/chat/assistant", {
    method: "POST",
    body: JSON.stringify({ message })
  }),
  getManagerProfile: () => request("/auth/profile"),
  updateManagerProfile: (payload) => request("/auth/profile", {
    method: "PUT",
    body: JSON.stringify(payload)
  }),
  listApplications: () => request("/applications"),
  removePastInterview: (interviewId) => request(`/applications/interviews/${encodeURIComponent(interviewId)}`, {
    method: "DELETE"
  }),
  listInterviewers: () => request("/admin/staff"),
  createStaffAccount: (payload) => request("/admin/staff", {
    method: "POST",
    body: JSON.stringify(payload)
  }),
  changeApplicationStatus: (applicationId, payload) => request(`/admin/applications/${applicationId}/status`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  }),
  deleteCandidate: (candidateId, reason) => request(`/admin/candidates/${candidateId}?reason=${encodeURIComponent(reason)}`, {
    method: "DELETE",
  }),
  rescoreApplication: (applicationId, reason) => request(`/admin/applications/${encodeURIComponent(applicationId)}/rescore`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  }),
  rescoreJobApplications: (jobId, reason) => request(`/jobs/${encodeURIComponent(jobId)}/rescore`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  }),
  importJobResumes: (jobId, files) => {
    const form = new FormData();
    for (const file of files) form.append("resume_files", file);
    return request(`/jobs/${encodeURIComponent(jobId)}/applications/batch`, { method: "POST", body: form });
  },
  getRescoreProgress: (jobId) => request(`/jobs/${encodeURIComponent(jobId)}/rescore-progress`),
  getInterviewCandidateInfo: (interviewId) => request(`/interviews/${encodeURIComponent(interviewId)}/candidate-info`),
  getJobRanking: (jobId) => request(`/jobs/${jobId}/ranking`),
  finalizeJobSelection: (jobId, payload) => request(`/jobs/${encodeURIComponent(jobId)}/finalize-selection`, {
    method: "POST",
    body: JSON.stringify(payload),
  }),
  getAssessment: (applicationId) => request(`/applications/${encodeURIComponent(applicationId)}/assessment`),
  getAssessmentComparison: (jobId) => request(`/jobs/${encodeURIComponent(jobId)}/assessment-comparison`),
  getInterviewerProfile: () => request("/me/interviewer-profile"),
  updateInterviewerProfile: (payload) => request("/me/interviewer-profile", {
    method: "PUT",
    body: JSON.stringify(payload)
  }),
  uploadInterviewerPhoto: (file) => {
    const form = new FormData();
    form.append("photo", file);
    return request("/me/interviewer-profile/photo", { method: "POST", body: form });
  },
  interviewerPhotoUrl: () => `${getApiBase()}/me/interviewer-profile/photo`,
  listMyInterviews: () => request("/me/interviews"),
  listJobApplicationsForInterviewer: () => request("/me/interviewer-applications"),
  createInterviewJoinLink: (interviewId) => request(`/interviews/${encodeURIComponent(interviewId)}/join-link`, { method: "POST" }),
  validateInterviewToken: (token) => request("/interviews/validate-token", {
    method: "POST",
    body: JSON.stringify({ token })
  }),
  getInterviewTranscript: (interviewId) => request(`/interviews/${encodeURIComponent(interviewId)}/transcript`),
  getLivekitToken: (interviewId) => request(`/interviews/${encodeURIComponent(interviewId)}/livekit-token`, { method: "POST" }),
  scheduleInterview: (applicationId, payload) => request(
    `/applications/${encodeURIComponent(applicationId)}/interview`,
    { method: "PUT", body: JSON.stringify(payload) }
  ),
  login: (email, password) => {
    const body = new URLSearchParams({ username: email, password });
    return request("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body
    });
  },
  logout: () => request("/auth/logout", { method: "POST" }),
  forgotPassword: (email) => request("/auth/forgot-password", {
    method: "POST",
    body: JSON.stringify({ email })
  }),
  resetPassword: (token, newPassword) => request("/auth/reset-password", {
    method: "POST",
    body: JSON.stringify({ token, new_password: newPassword })
  }),
  listJobs: () => request("/jobs"),
  generateJob: (payload) => request("/jobs/generate", {
    method: "POST",
    body: JSON.stringify(payload)
  }),
  getJob: (id) => request(`/jobs/${encodeURIComponent(id)}`),
  updateJob: (id, payload) => request(`/jobs/${encodeURIComponent(id)}`, {
    method: "PUT",
    body: JSON.stringify(payload)
  }),
  approveJob: (id) => request(`/jobs/${encodeURIComponent(id)}/approve`, {
    method: "POST"
  }),
  publishJobToBlogger: (id) => request(`/jobs/${encodeURIComponent(id)}/publish-blogger`, {
    method: "POST"
  }),
  chatWithJobAssistant: (messages, action = "message") => request(
    "/jobs/assistant/chat",
    { method: "POST", body: JSON.stringify({ messages, action }) }
  )
});
