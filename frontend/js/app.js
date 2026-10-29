import { api } from "./api.js";

const elements = {
  homeScreen: document.querySelector("#home-screen"),
  authScreen: document.querySelector("#auth-screen"),
  authHeading: document.querySelector("#auth-heading"),
  appShell: document.querySelector(".app-shell"),
  authFeedback: document.querySelector("#auth-feedback"),
  loginForm: document.querySelector("#login-form"),
  loginButton: document.querySelector("#login-button"),
  loginEmail: document.querySelector("#login-email"),
  loginPassword: document.querySelector("#login-password"),
  authCopy: document.querySelector("#auth-copy"),
  authModeToggle: document.querySelector("#auth-mode-toggle"),
  registerNameField: document.querySelector("#register-name-field"),
  loginFullName: document.querySelector("#login-full-name"),
  registerPhoneField: document.querySelector("#register-phone-field"),
  loginPhoneNumber: document.querySelector("#login-phone-number"),
  userAvatar: document.querySelector("#user-avatar"),
  logoutButton: document.querySelector("#logout-button"),
  jobsList: document.querySelector("#jobs-list"),
  refreshJobs: document.querySelector("#refresh-jobs"),
  apiStatus: document.querySelector("#api-status"),
  apiStatusLabel: document.querySelector("#api-status .status-label"),
  feedback: document.querySelector("#feedback"),
  openJobForm: document.querySelector("#open-job-form"),
  jobIdInput: document.querySelector("#job-id"),
  draftEmpty: document.querySelector("#draft-empty"),
  draftContent: document.querySelector("#draft-content"),
  draftSubtitle: document.querySelector("#draft-subtitle"),
  jobStatus: document.querySelector("#job-status"),
  jobIdLabel: document.querySelector("#job-id-label"),
  draftUpdated: document.querySelector("#draft-updated"),
  jdText: document.querySelector("#jd-text"),
  externalPostUrl: document.querySelector("#external-post-url"),
  publishBlogger: document.querySelector("#publish-blogger"),
  bloggerPostMessage: document.querySelector("#blogger-post-message"),
  copyApplicationLink: document.querySelector("#copy-application-link"),
  applicationLinkMessage: document.querySelector("#application-link-message"),
  freeSharePanel: document.querySelector("#free-share-panel"),
  shareLinkedIn: document.querySelector("#share-linkedin"),
  shareFacebook: document.querySelector("#share-facebook"),
  shareX: document.querySelector("#share-x"),
  copySocialPost: document.querySelector("#copy-social-post"),
  socialShareMessage: document.querySelector("#social-share-message"),
  requirements: document.querySelector("#requirements-list"),
  addRequirement: document.querySelector("#add-requirement"),
  saveButton: document.querySelector("#save-button"),
  approveButton: document.querySelector("#approve-button")
};

let currentJob = null;
let busy = false;
let isRegistering = false;
const requestedAuthPage = new URLSearchParams(window.location.search).get("auth");
const isAuthPage = requestedAuthPage === "signin" || requestedAuthPage === "signup";

function continueToInterview(user) {
  const next = new URLSearchParams(window.location.search).get("next") || "";
  if (
    next.startsWith("./interview.html?token=")
    && ["candidate", "interviewer"].includes(user.role)
  ) {
    window.location.replace(next);
    return true;
  }
  return false;
}

function setFeedback(message, kind = "error") {
  elements.feedback.textContent = message;
  elements.feedback.classList.toggle("is-success", kind === "success");
  elements.feedback.hidden = !message;
}

function setAuthFeedback(message) {
  elements.authFeedback.textContent = message;
  elements.authFeedback.hidden = !message;
}

function setAuthBusy(isBusy) {
  elements.loginButton.disabled = isBusy;
  elements.loginButton.textContent = isBusy
    ? (isRegistering ? "Creating account…" : "Signing in…")
    : (isRegistering ? "Create candidate account" : "Sign in");
}

function setRegistrationMode(enabled) {
  isRegistering = enabled;
  elements.registerNameField.hidden = !enabled;
  elements.registerPhoneField.hidden = !enabled;
  elements.loginFullName.disabled = !enabled;
  elements.loginFullName.required = enabled;
  elements.loginPhoneNumber.disabled = !enabled;
  elements.loginPhoneNumber.required = enabled;
  elements.loginPassword.autocomplete = enabled ? "new-password" : "current-password";
  elements.loginPassword.minLength = enabled ? 8 : 0;
  elements.loginButton.textContent = enabled ? "Create candidate account" : "Sign in";
  elements.authHeading.textContent = enabled ? "Create your candidate account." : "Welcome back.";
  elements.authModeToggle.textContent = enabled
    ? "Already have an account? Sign in"
    : "New candidate? Create an account";
  elements.authModeToggle.href = enabled
    ? "./index.html?auth=signin"
    : "./index.html?auth=signup";
  elements.authCopy.textContent = enabled
    ? "Create a candidate account to explore roles, apply, and track your applications."
    : "Sign in to continue. Candidates can create an account here; hiring-manager accounts are provided by the RecruitO team.";
}

elements.homeScreen.hidden = isAuthPage;
elements.authScreen.hidden = !isAuthPage;
if (isAuthPage) {
  const isSignUpPage = requestedAuthPage === "signup";
  document.title = isSignUpPage ? "RecruitO — Create an account" : "RecruitO — Sign in";
  setRegistrationMode(isSignUpPage);
  if (new URLSearchParams(window.location.search).get("expired") === "1") {
    setAuthFeedback("Your session expired. Please sign in again.");
  }
  if (new URLSearchParams(window.location.search).get("reset") === "1") {
    setAuthFeedback("Your password has been reset. Please sign in with your new password.");
  }
}

function setBusy(nextBusy) {
  busy = nextBusy;
  elements.publishBlogger.disabled = busy || !currentJob || currentJob.status !== "approved";
  elements.saveButton.disabled = busy || !currentJob || currentJob.status !== "draft";
  elements.approveButton.disabled = busy || !currentJob || currentJob.status !== "draft";
  elements.addRequirement.disabled = busy || !currentJob || currentJob.status !== "draft";
  elements.jdText.disabled = busy || currentJob?.status !== "draft";
  elements.requirements.querySelectorAll(".requirement-control, .remove-requirement").forEach((control) => {
    control.disabled = busy || currentJob?.status !== "draft";
  });
}

function renderJobs(jobs) {
  if (!Array.isArray(jobs)) {
    throw new Error("The API returned an unexpected jobs list.");
  }
  if (jobs.length === 0) {
    const emptyState = document.createElement("p");
    emptyState.className = "jobs-empty";
    emptyState.textContent = "No saved jobs yet.";
    elements.jobsList.replaceChildren(emptyState);
    return;
  }

  const items = jobs.map((job) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "saved-job";
    button.dataset.jobId = String(job.id);

    const title = document.createElement("span");
    title.className = "saved-job-title";
    title.textContent = job.title;

    const meta = document.createElement("span");
    meta.className = "saved-job-meta";
    meta.textContent = `#${job.id} · ${statusLabel(job.status)}`;

    button.append(title, meta);
    return button;
  });
  elements.jobsList.replaceChildren(...items);
}

async function refreshJobs() {
  renderJobs(await api.listJobs());
}

function showWorkspace(user) {
  elements.homeScreen.hidden = true;
  elements.authScreen.hidden = true;
  elements.appShell.hidden = false;
  if (user && user.full_name) {
    const initials = user.full_name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0].toUpperCase())
      .join("");
    elements.userAvatar.textContent = initials || "HM";
    elements.userAvatar.setAttribute("aria-label", user.full_name);
  }
}

function statusLabel(status) {
  if (status === "filled") return "Filled";
  return status === "approved" ? "Published" : "Draft";
}

function setWorkflowStage(stage) {
  const steps = document.querySelectorAll(".workflow-step");
  steps.forEach((step, index) => {
    const isCurrent = index === stage;
    step.classList.toggle("is-current", isCurrent);
    step.classList.toggle("is-complete", index < stage);
    if (isCurrent) {
      step.setAttribute("aria-current", "step");
    } else {
      step.removeAttribute("aria-current");
    }
  });
}

function createSelect(value, choices, label) {
  const select = document.createElement("select");
  select.className = "requirement-control";
  select.setAttribute("aria-label", label);
  for (const optionValue of choices) {
    const option = document.createElement("option");
    option.value = optionValue;
    option.textContent = optionValue[0].toUpperCase() + optionValue.slice(1);
    select.append(option);
  }
  select.value = choices.includes(value) ? value : choices[0];
  return select;
}

function createRequirementRow(requirement = {}) {
  const row = document.createElement("div");
  row.className = "requirement-row";
  row.dataset.requirementRow = "";

  const text = document.createElement("input");
  text.type = "text";
  text.className = "requirement-control";
  text.maxLength = 500;
  text.placeholder = "Requirement";
  text.value = typeof requirement.text === "string" ? requirement.text : "";
  text.setAttribute("aria-label", "Requirement text");

  const kind = createSelect(requirement.kind, ["required", "preferred"], "Requirement type");
  const category = createSelect(requirement.category, ["skills", "experience", "qualification"], "Requirement category");
  const weight = document.createElement("select");
  weight.className = "requirement-control";
  weight.setAttribute("aria-label", "Requirement weight");
  for (let score = 1; score <= 5; score += 1) {
    const option = document.createElement("option");
    option.value = String(score);
    option.textContent = `Weight ${score}`;
    weight.append(option);
  }
  weight.value = String(Number.isInteger(requirement.weight) ? requirement.weight : 3);

  const remove = document.createElement("button");
  remove.type = "button";
  remove.className = "remove-requirement";
  remove.setAttribute("aria-label", "Remove requirement");
  remove.textContent = "×";
  remove.addEventListener("click", () => row.remove());

  row.append(text, kind, category, weight, remove);
  return row;
}

function collectRequirements() {
  return Array.from(elements.requirements.querySelectorAll("[data-requirement-row]"), (row) => ({
    text: row.querySelector('input[type="text"]').value.trim(),
    kind: row.querySelector('select[aria-label="Requirement type"]').value,
    category: row.querySelector('select[aria-label="Requirement category"]').value,
    weight: Number(row.querySelector('select[aria-label="Requirement weight"]').value)
  })).filter((item) => item.text.length > 0);
}

function renderJob(job) {
  currentJob = job;
  elements.freeSharePanel.hidden = job.status !== "approved";
  elements.publishBlogger.hidden = job.status !== "approved";
  elements.publishBlogger.textContent = job.external_post_provider === "blogger"
    ? "Send another post to Blogger"
    : "Email post to Blogger";
  elements.bloggerPostMessage.textContent = job.external_post_provider === "blogger"
    ? `Sent to Blogger by email. Blog homepage: ${job.external_post_url}`
    : job.status === "approved"
      ? "Not posted to Blogger yet. Automatic posting needs a public HTTPS RecruitO address and working Blogger mail settings; you can retry with the button."
      : "";
  elements.draftEmpty.hidden = true;
  elements.draftContent.hidden = false;
  elements.draftSubtitle.textContent = job.title;
  elements.jobIdLabel.textContent = `Job #${job.id}`;
  elements.draftUpdated.textContent = job.created_at
    ? `Created ${new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(job.created_at))}`
    : "";
  elements.jdText.value = job.jd_text || "";
  elements.externalPostUrl.value = job.external_post_url || "";
  elements.externalPostUrl.disabled = job.status !== "draft";
  elements.jobStatus.textContent = statusLabel(job.status);
  elements.jobStatus.classList.toggle("is-approved", job.status === "approved");
  elements.jobStatus.hidden = false;
  elements.jobIdInput.value = String(job.id);
  elements.requirements.replaceChildren(...(job.requirements || []).map(createRequirementRow));
  elements.requirements.querySelectorAll(".remove-requirement").forEach((button) => {
    button.hidden = job.status !== "draft";
  });
  elements.requirements.querySelectorAll(".requirement-control").forEach((control) => {
    control.disabled = job.status !== "draft";
  });
  elements.addRequirement.hidden = job.status !== "draft";
  elements.jdText.readOnly = job.status !== "draft";
  document.querySelector(".draft-actions").hidden = job.status !== "draft";
  updateShareLinks(job);
  setWorkflowStage(["approved", "filled"].includes(job.status) ? 3 : 1);
  setBusy(false);
  document.querySelector("#draft-heading").focus({ preventScroll: true });
}

function validateDraft() {
  const jdText = elements.jdText.value.trim();
  const requirements = collectRequirements();
  if (!jdText) return { error: "Add a job description before saving." };
  if (requirements.length === 0) return { error: "Add at least one non-empty selection requirement." };
  if (requirements.some((item) => item.text.length > 500 || item.weight < 1 || item.weight > 5)) {
    return { error: "Check requirement text and weights. Text must be 500 characters or fewer; weights must be 1–5." };
  }
  const externalPostUrl = elements.externalPostUrl.value.trim();
  if (externalPostUrl && !/^https:\/\//i.test(externalPostUrl)) {
    return { error: "Enter a valid HTTPS external job-post URL." };
  }
  return { payload: { jd_text: jdText, requirements, external_post_url: externalPostUrl || null } };
}

async function saveJob() {
  if (!currentJob || currentJob.status !== "draft" || busy) return;
  setFeedback("");
  const { payload, error } = validateDraft();
  if (error) {
    setFeedback(error);
    return;
  }

  setBusy(true);
  try {
    const savedJob = await api.updateJob(currentJob.id, payload);
    renderJob(savedJob);
    await refreshJobs();
    setFeedback("Draft changes saved.", "success");
  } catch (requestError) {
    setFeedback(requestError.message);
  } finally {
    setBusy(false);
  }
}

async function approveJob() {
  if (!currentJob || currentJob.status !== "draft" || busy) return;
  setFeedback("");
  const { payload, error } = validateDraft();
  if (error) {
    setFeedback(error);
    return;
  }
  if (!window.confirm("Save your latest edits and approve this job profile?")) return;

  setBusy(true);
  try {
    await api.updateJob(currentJob.id, payload);
    const approvedJob = await api.approveJob(currentJob.id);
    renderJob(approvedJob);
    await refreshJobs();
    setFeedback("Job approved and published on RecruitO. You can now share its application page using the free social-site options below.", "success");
  } catch (requestError) {
    setFeedback(requestError.message);
  } finally {
    setBusy(false);
  }
}

async function openJob(event) {
  event.preventDefault();
  setFeedback("");
  if (!elements.openJobForm.reportValidity()) return;

  const jobId = Number(elements.jobIdInput.value);
  if (!Number.isSafeInteger(jobId) || jobId < 1) {
    setFeedback("Enter a valid positive job ID.");
    return;
  }

  setBusy(true);
  try {
    renderJob(await api.getJob(jobId));
    setFeedback("Job profile loaded.", "success");
  } catch (error) {
    setFeedback(error.message);
  } finally {
    setBusy(false);
  }
}

async function checkHealth() {
  try {
    const health = await api.health();
    const apiOnline = health.status === "ok";
    elements.apiStatus.classList.toggle("is-online", apiOnline);
    elements.apiStatus.classList.toggle("is-offline", !apiOnline);
    elements.apiStatus.classList.toggle("is-warning", apiOnline && health.db !== "up");
    elements.apiStatusLabel.textContent = apiOnline
      ? (health.db === "up" ? "API & database connected" : "API online · database unavailable")
      : "API unavailable";
  } catch {
    elements.apiStatus.classList.remove("is-online");
    elements.apiStatus.classList.add("is-offline");
    elements.apiStatus.classList.remove("is-warning");
    elements.apiStatusLabel.textContent = "API unavailable";
  }

}

function updateShareLinks(job) {
  const applicationLink = new URL("./public-jobs.html", window.location.href);
  applicationLink.searchParams.set("job", String(job.id));
  const url = applicationLink.href;
  const title = job.title;
  const description = elements.jdText.value.trim();
  const postText = `${title}\n\n${description}\n\nView the role and apply: ${url}`;
  elements.shareLinkedIn.href = `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(url)}`;
  elements.shareFacebook.href = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}`;
  elements.shareX.href = `https://twitter.com/intent/tweet?text=${encodeURIComponent(`${title} — View role and apply: ${url}`)}`;
  elements.copySocialPost.dataset.postText = postText;
}

async function signIn(event) {
  event.preventDefault();
  setAuthFeedback("");
  if (!elements.loginForm.reportValidity()) return;

  setAuthBusy(true);
  let accountCreated = false;
  try {
    const email = elements.loginEmail.value.trim();
    const password = elements.loginPassword.value;
    if (isRegistering) {
      const fullName = elements.loginFullName.value.trim();
      const phoneNumber = elements.loginPhoneNumber.value.trim();
      if (!fullName) {
        setAuthFeedback("Enter your name without leaving it blank.");
        return;
      }
      if (!phoneNumber) {
        setAuthFeedback("Enter your phone number to complete registration.");
        return;
      }
      await api.registerCandidate(email, password, fullName, phoneNumber);
      accountCreated = true;
    }
    const user = await api.login(
      email,
      password
    );
    elements.loginPassword.value = "";
    if (continueToInterview(user)) return;
    if (user.role === "candidate") {
      window.location.assign("./public-jobs.html");
      return;
    }
    if (user.role === "interviewer") {
      window.location.assign("./interviewer-dashboard.html");
      return;
    }
    if (user.role !== "hiring_manager") throw new Error("This account role is not supported.");
    await refreshJobs();
    showWorkspace(user);
  } catch (error) {
    if (accountCreated) {
      setRegistrationMode(false);
      setAuthFeedback(`Your candidate account was created, but automatic sign-in did not complete. Sign in with that account. ${error.message}`);
    } else {
      setAuthFeedback(error.status === 409
        ? "This email is already registered. Switch to sign in."
        : error.status === 422
          ? "Check the form. Use a valid email, a name, and a password between 8 and 128 characters."
          : error.message);
    }
  } finally {
    setAuthBusy(false);
  }
}

async function restoreSession() {
  checkHealth();
  try {
    const user = await api.getManagerProfile();
    if (continueToInterview(user)) return;
    if (user.role !== "hiring_manager") throw new Error("This account role is not supported.");
    await refreshJobs();
    showWorkspace(user);
  } catch (error) {
    if (error instanceof Error && error.status === 403) {
      try {
        const candidateData = await api.listMyApplications();
        const interviewNext = new URLSearchParams(window.location.search).get("next");
        if (interviewNext && continueToInterview({ role: "candidate" })) return;
        window.location.replace("./public-jobs.html");
        return;
      } catch {
        try {
          const interviewer = await api.getInterviewerProfile();
          if (continueToInterview({ role: "interviewer" })) return;
          window.location.replace("./interviewer-dashboard.html");
          return;
        } catch {
          setAuthFeedback("This account cannot access the requested workspace.");
        }
      }
    } else if (error instanceof Error && error.status === 404) {
      setAuthFeedback("This backend version does not expose the jobs list yet. Restart the updated API and reload.");
    } else if (!(error instanceof Error && error.status === 401)) {
      setAuthFeedback(error.message);
    }
  }
}

elements.openJobForm.addEventListener("submit", openJob);
elements.loginForm.addEventListener("submit", signIn);
elements.logoutButton.addEventListener("click", async () => {
  elements.logoutButton.disabled = true;
  elements.logoutButton.textContent = "Signing out…";
  setFeedback("Signing out…", "success");
  try {
    await api.logout();
    window.location.replace(`./index.html?logged_out=${Date.now()}`);
  } catch (error) {
    elements.logoutButton.disabled = false;
    elements.logoutButton.textContent = "Sign out";
    setFeedback(`Could not sign out: ${error.message}`);
  }
});
elements.copyApplicationLink.addEventListener("click", async () => {
  if (!currentJob) return;
  const link = new URL("./public-jobs.html", window.location.href);
  link.searchParams.set("apply", String(currentJob.id));
  try {
    await navigator.clipboard.writeText(link.href);
    elements.applicationLinkMessage.textContent = "Candidate application link copied. Add it to your external job post or share it directly.";
  } catch {
    elements.applicationLinkMessage.textContent = `Candidate application link: ${link.href}`;
  }
});
elements.publishBlogger.addEventListener("click", async () => {
  if (!currentJob || currentJob.status !== "approved" || busy) return;
  setBusy(true);
  elements.bloggerPostMessage.textContent = "Sending job post to Blogger by email…";
  try {
    const publishedJob = await api.publishJobToBlogger(currentJob.id);
    renderJob(publishedJob);
    await refreshJobs();
    setFeedback("Job post email sent to Blogger. The public job card links to the blog homepage.", "success");
  } catch (error) {
    elements.bloggerPostMessage.textContent = error.message;
  } finally {
    setBusy(false);
  }
});
elements.copySocialPost.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(elements.copySocialPost.dataset.postText || "");
    elements.socialShareMessage.textContent = "The job description and public application link were copied. Paste them into your free social post.";
  } catch {
    elements.socialShareMessage.textContent = `Copy the job description and application link from the review panel, then paste them into your post.`;
  }
});
document.addEventListener("manager-draft-created", async (event) => {
  try {
    const job = await api.getJob(event.detail.jobId);
    await refreshJobs();
    renderJob(job);
    setFeedback(
      job.external_post_provider === "blogger"
        ? "Automated policy checks passed. The job is live on RecruitO and the Blogger post was sent."
        : "Automated policy checks passed. The job is live on RecruitO; Blogger posting needs setup or a retry.",
      "success",
    );
  } catch (error) {
    setFeedback(`Draft created, but the job could not be loaded: ${error.message}`);
  }
});
elements.refreshJobs.addEventListener("click", async () => {
  try {
    await refreshJobs();
    setFeedback("Saved jobs refreshed.", "success");
  } catch (error) {
    setFeedback(error.message);
  }
});
elements.jobsList.addEventListener("click", (event) => {
  const button = event.target.closest("[data-job-id]");
  if (!button) return;
  elements.jobIdInput.value = button.dataset.jobId;
  elements.openJobForm.requestSubmit();
});
elements.saveButton.addEventListener("click", saveJob);
elements.approveButton.addEventListener("click", approveJob);
elements.addRequirement.addEventListener("click", () => {
  if (currentJob?.status === "draft") {
    const row = createRequirementRow({ kind: "required", category: "skills", weight: 3 });
    elements.requirements.append(row);
    row.querySelector('input[type="text"]').focus();
  }
});

if (isAuthPage) restoreSession();
