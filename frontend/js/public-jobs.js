import { api } from "./api.js?v=20261026-3";

const jobsList = document.querySelector("#public-jobs-list");
const jobsView = document.querySelector("#candidate-jobs-view");
const jobsMessage = document.querySelector("#public-jobs-message");
const authForm = document.querySelector("#candidate-auth-form");
const authMessage = document.querySelector("#candidate-auth-message");
const authCopy = document.querySelector("#candidate-access-copy");
const nameField = document.querySelector("#candidate-name-field");
const phoneField = document.querySelector("#candidate-phone-field");
const passwordInput = document.querySelector("#candidate-password");
const authSubmit = document.querySelector("#candidate-auth-submit");
const authToggle = document.querySelector("#candidate-auth-toggle");
const candidateLogoutButton = document.querySelector("#candidate-logout-button");
const candidateNavigation = document.querySelector("#candidate-navigation");
const profileSection = document.querySelector("#candidate-profile");
const profileMessage = document.querySelector("#candidate-profile-message");
const profileDetails = document.querySelector("#candidate-profile-details");
const profileEditButton = document.querySelector("#candidate-profile-edit");
const profileForm = document.querySelector("#candidate-profile-form");
const profileFormFields = document.querySelector("#candidate-profile-fields");
const profileFormMessage = document.querySelector("#candidate-profile-form-message");
const profileCancelButton = document.querySelector("#candidate-profile-cancel");
const dashboard = document.querySelector("#candidate-dashboard");
const dashboardMessage = document.querySelector("#candidate-dashboard-message");
const applicationsList = document.querySelector("#candidate-applications-list");
const candidateChat = document.querySelector("#candidate-chat");
const chatMessages = document.querySelector("#candidate-chat-messages");
const chatForm = document.querySelector("#candidate-chat-form");
const chatInput = document.querySelector("#candidate-chat-input");
const chatSubmit = document.querySelector("#candidate-chat-submit");
const biometricConsent = document.querySelector("#biometric-consent");
const biometricPreview = document.querySelector("#biometric-preview");
const biometricStatus = document.querySelector("#biometric-status");
const biometricCapture = document.querySelector("#biometric-capture");
let biometricStream = null;
let isSignIn = false;
let candidateSignedIn = false;
let applicationsRefreshInProgress = false;
let candidateProfile = null;
const applyParam = Number(new URLSearchParams(window.location.search).get("apply"));
let requestedApplicationJobId = Number.isInteger(applyParam) && applyParam > 0 ? applyParam : null;
const jobParam = Number(new URLSearchParams(window.location.search).get("job"));
let requestedJobId = Number.isInteger(jobParam) && jobParam > 0 ? jobParam : null;
const hasPublicJobDeepLink = Number.isInteger(jobParam) && jobParam > 0;

const profileFields = [
  ["full_name", "Full name (as on certificate)"],
  ["email", "Contact email"],
  ["phone_number", "Phone number"],
  ["education_qualification", "Education qualification"],
  ["institution_name", "School / university"],
  ["department", "Department"],
  ["graduation_year", "Graduation year"],
];

// [name, label, input type, required] — email is intentionally excluded
// because it is the candidate's sign-in identity.
const editableProfileFields = [
  ["full_name", "Full name (as on certificate)", "text", true],
  ["phone_number", "Phone number", "tel", false],
  ["education_qualification", "Education qualification", "text", false],
  ["institution_name", "School / university", "text", false],
  ["department", "Department", "text", false],
  ["graduation_year", "Graduation year", "number", false],
];

function safeExternalUrl(value) {
  if (typeof value !== "string" || !value) return "";
  try {
    const url = new URL(value);
    return url.protocol === "https:" && url.hostname && !url.username && !url.password
      ? url.href
      : "";
  } catch {
    return "";
  }
}

function setCandidateView(view) {
  profileSection.hidden = view !== "profile";
  jobsView.hidden = view !== "jobs";
  dashboard.hidden = view !== "dashboard";
  candidateNavigation.querySelectorAll("[data-candidate-view]").forEach((button) => {
    const active = button.dataset.candidateView === view;
    button.classList.toggle("is-active", active);
    if (active) button.setAttribute("aria-current", "page");
    else button.removeAttribute("aria-current");
  });
}

function renderProfile(profile) {
  candidateProfile = profile;
  const items = profileFields.map(([key, label]) => {
    const term = document.createElement("dt");
    term.textContent = label;
    const value = document.createElement("dd");
    value.textContent = profile[key] === null || profile[key] === undefined || profile[key] === ""
      ? "Not provided"
      : String(profile[key]);
    return [term, value];
  }).flat();
  profileDetails.replaceChildren(...items);
  const incomplete = profileFields
    .filter(([key]) => key !== "graduation_year" && !profile[key])
    .map(([, label]) => label);
  profileMessage.textContent = incomplete.length
    ? "Some information is still missing. Use Edit profile to add it, or complete it when you apply for a role."
    : "Only you can view this profile.";
}

function buildProfileFormFields(profile) {
  const fragment = document.createDocumentFragment();
  for (const [name, label, type, required] of editableProfileFields) {
    const wrapper = document.createElement("div");
    wrapper.className = "form-field";
    const inputId = `profile-${name}`;
    const labelElement = document.createElement("label");
    labelElement.htmlFor = inputId;
    labelElement.textContent = required ? `${label} *` : `${label} (optional)`;
    const input = document.createElement("input");
    input.id = inputId;
    input.name = name;
    input.type = type;
    input.required = required;
    if (type === "number") {
      input.min = "1950";
      input.max = "2100";
    } else {
      input.maxLength = type === "tel" ? 30 : 255;
    }
    const value = profile ? profile[name] : "";
    input.value = value === null || value === undefined ? "" : String(value);
    wrapper.append(labelElement, input);
    fragment.append(wrapper);
  }
  profileFormFields.replaceChildren(fragment);
}

function openProfileForm() {
  buildProfileFormFields(candidateProfile);
  profileFormMessage.textContent = "";
  profileForm.hidden = false;
  profileEditButton.hidden = true;
  profileFormFields.querySelector("input")?.focus();
}

function closeProfileForm() {
  profileForm.hidden = true;
  profileEditButton.hidden = false;
  profileFormMessage.textContent = "";
}

profileEditButton.addEventListener("click", openProfileForm);
profileCancelButton.addEventListener("click", closeProfileForm);

profileForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = new FormData(profileForm);
  const fullName = String(data.get("full_name") || "").trim();
  if (!fullName) {
    profileFormMessage.textContent = "Full name cannot be blank.";
    return;
  }
  const gradYear = String(data.get("graduation_year") || "").trim();
  const payload = {
    full_name: fullName,
    phone_number: String(data.get("phone_number") || "").trim() || null,
    education_qualification: String(data.get("education_qualification") || "").trim() || null,
    institution_name: String(data.get("institution_name") || "").trim() || null,
    department: String(data.get("department") || "").trim() || null,
    graduation_year: gradYear ? Number(gradYear) : null,
  };
  const submitButton = profileForm.querySelector("button[type=submit]");
  submitButton.disabled = true;
  profileFormMessage.textContent = "Saving…";
  try {
    const updated = await api.updateCandidateProfile(payload);
    renderProfile(updated);
    closeProfileForm();
    profileMessage.textContent = "Profile updated.";
  } catch (error) {
    profileFormMessage.textContent = error?.detail || error?.message || "Could not save your profile. Please try again.";
  } finally {
    submitButton.disabled = false;
  }
});

function applicationField(jobId, name, label, type, required, value = "") {
  const wrapper = document.createElement("div");
  wrapper.className = "form-field";
  const inputId = `application-${jobId}-${name}`;
  const labelElement = document.createElement("label");
  labelElement.htmlFor = inputId;
  labelElement.textContent = required ? `${label} *` : `${label} (optional)`;
  const input = document.createElement("input");
  input.id = inputId;
  input.name = name;
  input.type = type;
  if (type !== "number" && type !== "file") input.maxLength = 255;
  input.required = required;
  input.value = value === null || value === undefined ? "" : String(value);
  if (name === "phone_number") {
    input.maxLength = 30;
    input.autocomplete = "tel";
  }
  if (name === "email") input.autocomplete = "email";
  if (name === "full_name") input.autocomplete = "name";
  if (name === "resume_file") {
    input.accept = ".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document";
  }
  if (type === "number") {
    input.min = "1950";
    input.max = "2100";
    input.step = "1";
    input.placeholder = "Optional";
  }
  wrapper.append(labelElement, input);
  return wrapper;
}

function applicationValidationMessage(error) {
  if (typeof error.detail === "string") return error.detail;
  if (Array.isArray(error.detail)) {
    const fieldLabels = {
      request: "application details",
      full_name: "full name",
      email: "contact email",
      phone_number: "phone number",
      education_qualification: "education qualification",
      institution_name: "school / university name",
      department: "department",
      graduation_year: "graduation year",
      resume_file: "resume",
    };
    const fields = [...new Set(error.detail.map((issue) => {
      const field = Array.isArray(issue.loc) ? issue.loc.at(-1) : null;
      return fieldLabels[field] || null;
    }).filter(Boolean))];
    if (fields.length) return `Please check these fields: ${fields.join(", ")}.`;
  }
  return "RecruitO could not accept the application. Check the required details and upload a valid PDF or DOCX resume under 10 MB.";
}

function createApplicationForm(job, applyButton) {
  const form = document.createElement("form");
  form.className = "candidate-application-form";
  form.hidden = true;
  const formHint = document.createElement("p");
  formHint.className = "public-jobs-message";
  formHint.textContent = "Fields marked * are required. Upload a valid PDF or DOCX resume (10 MB max). Graduation year is optional.";
  form.append(formHint);
  form.append(
    applicationField(job.id, "full_name", "Full name as shown on your certificate", "text", true, candidateProfile?.full_name),
    applicationField(job.id, "email", "Contact email", "email", true, candidateProfile?.email),
    applicationField(job.id, "phone_number", "Phone number", "tel", true, candidateProfile?.phone_number),
    applicationField(job.id, "education_qualification", "Education qualification", "text", true, candidateProfile?.education_qualification),
    applicationField(job.id, "institution_name", "School / university name", "text", true, candidateProfile?.institution_name),
    applicationField(job.id, "department", "Department", "text", true, candidateProfile?.department),
    applicationField(job.id, "graduation_year", "Graduation year", "number", false, candidateProfile?.graduation_year),
    applicationField(job.id, "resume_file", "Resume (PDF or DOCX, up to 10 MB)", "file", true),
  );
  const submit = document.createElement("button");
  submit.className = "button button-primary";
  submit.type = "submit";
  submit.textContent = "Submit application";
  const cancel = document.createElement("button");
  cancel.className = "button button-secondary";
  cancel.type = "button";
  cancel.textContent = "Cancel";
  const formMessage = document.createElement("p");
  formMessage.className = "public-jobs-message";
  formMessage.setAttribute("role", "status");
  const actions = document.createElement("div");
  actions.className = "candidate-application-actions";
  actions.append(submit, cancel);
  form.append(actions, formMessage);

  cancel.addEventListener("click", () => {
    form.hidden = true;
    applyButton.hidden = false;
  });
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    submit.disabled = true;
    formMessage.textContent = "Submitting your application…";
    const payload = new FormData(form);
    for (const name of ["full_name", "email", "phone_number", "education_qualification", "institution_name", "department"]) {
      payload.set(name, String(payload.get(name) || "").trim());
    }
    if (!String(payload.get("graduation_year") || "").trim()) {
      payload.delete("graduation_year");
    }

    try {
      const result = await api.applyToJob(job.id, payload);
      formMessage.textContent = result.confirmation_email_queued
        ? `Your application for ${job.title} was submitted. A confirmation email is on its way, and LangGraph is assessing your CV automatically.`
        : `Your application for ${job.title} was submitted. LangGraph is assessing your CV automatically; check your email later for confirmation.`;
      applyButton.textContent = "Applied";
      applyButton.disabled = true;
      const refreshResults = await Promise.allSettled([loadProfile(), loadMyApplications()]);
      if (refreshResults[0].status === "rejected") {
        profileMessage.textContent = `Application submitted. Could not refresh profile: ${refreshResults[0].reason.message}`;
      }
      window.setTimeout(() => {
        form.hidden = true;
        setCandidateView("dashboard");
      }, 700);
    } catch (error) {
      formMessage.textContent = error.status === 409
        ? "You have already applied for this role."
        : error.status === 401
          ? "Your sign-in has expired. Sign in again to apply."
          : error.status === 404
            ? "This role is no longer open. Refresh the page to see current roles."
            : error.status === 422
              ? applicationValidationMessage(error)
              : error.message;
      submit.disabled = false;
    }
  });
  return form;
}

function renderJobs(jobs) {
  if (!Array.isArray(jobs)) throw new Error("The API returned an unexpected jobs list.");
  if (jobs.length === 0) {
    jobsMessage.textContent = "There are no open roles right now.";
    jobsList.replaceChildren();
    return;
  }

  const cards = jobs.map((job) => {
    const card = document.createElement("article");
    card.className = "public-job-card";
    card.id = `public-job-${job.id}`;
    card.dataset.publicJobId = String(job.id);
    const title = document.createElement("h2");
    title.textContent = job.title;
    const experience = document.createElement("p");
    experience.className = "public-job-date";
    experience.textContent = job.seniority;
    const externalLink = document.createElement("a");
    externalLink.className = "button button-secondary public-apply-button";
    const externalUrl = safeExternalUrl(job.external_post_url);
    externalLink.href = externalUrl || "#";
    externalLink.target = "_blank";
    externalLink.rel = "noopener noreferrer";
    externalLink.textContent = job.external_post_provider === "blogger"
      ? "View job on Blogger"
      : "View external job post";
    externalLink.hidden = !externalUrl;
    const descriptionNote = document.createElement("p");
    descriptionNote.className = "public-job-date";
    descriptionNote.textContent = externalUrl
      ? "Open the full job description on Blogger using the link below."
      : "The full job description is published on Blogger.";
    const applyButton = document.createElement("button");
    applyButton.className = "button button-primary public-apply-button";
    applyButton.type = "button";
    applyButton.textContent = "Open application form";
    applyButton.hidden = false;
    const applicationForm = createApplicationForm(job, applyButton);
    applyButton.addEventListener("click", () => {
      if (!candidateSignedIn) {
        authMessage.textContent = "Create an account or sign in above before applying.";
        authForm.scrollIntoView({ behavior: "smooth", block: "center" });
        return;
      }
      for (const [name, value] of Object.entries({
        full_name: candidateProfile?.full_name,
        email: candidateProfile?.email,
        phone_number: candidateProfile?.phone_number,
        education_qualification: candidateProfile?.education_qualification,
        institution_name: candidateProfile?.institution_name,
        department: candidateProfile?.department,
        graduation_year: candidateProfile?.graduation_year,
      })) {
        const input = applicationForm.elements.namedItem(name);
        if (input && !input.value && value) input.value = String(value);
      }
      applicationForm.hidden = false;
      applyButton.hidden = true;
      applicationForm.scrollIntoView({ behavior: "smooth", block: "center" });
    });
    card.append(title, experience, descriptionNote, externalLink, applyButton, applicationForm);
    applyButton.dataset.jobId = String(job.id);
    return card;
  });
  jobsMessage.textContent = "";
  jobsList.replaceChildren(...cards);
  openRequestedJob();
  openRequestedApplication();
}

function openRequestedJob() {
  if (requestedJobId === null) return;
  const card = jobsList.querySelector(`[data-public-job-id="${requestedJobId}"]`);
  if (!card) return;
  requestedJobId = null;
  card.classList.add("is-shared-job");
  card.scrollIntoView({ behavior: "smooth", block: "center" });
}

function openRequestedApplication() {
  if (!candidateSignedIn || requestedApplicationJobId === null) return;
  const card = jobsList.querySelector(`[data-public-job-id="${requestedApplicationJobId}"]`);
  const applyButton = card?.querySelector(".public-apply-button[type='button']");
  if (!applyButton) return;
  requestedApplicationJobId = null;
  applyButton.click();
}

function renderApplications(applications) {
  if (!Array.isArray(applications)) throw new Error("The API returned an unexpected applications list.");
  applications.sort((a, b) => {
    const aTime = a.interview_scheduled_at ? Date.parse(a.interview_scheduled_at) : Number.POSITIVE_INFINITY;
    const bTime = b.interview_scheduled_at ? Date.parse(b.interview_scheduled_at) : Number.POSITIVE_INFINITY;
    return aTime - bTime || Date.parse(b.applied_at) - Date.parse(a.applied_at);
  });
  if (applications.length === 0) {
    dashboardMessage.textContent = "You have not applied to any roles yet.";
    applicationsList.replaceChildren();
    return;
  }

  dashboardMessage.textContent = "Interview-scheduled applications appear first. These applications are linked to your account.";
  const cards = applications.map((application) => {
    const card = document.createElement("article");
    card.className = "public-job-card";
    if (application.interview_scheduled_at) card.classList.add("has-interview");
    const title = document.createElement("h3");
    title.textContent = application.job_title;
    const status = document.createElement("p");
    status.className = "candidate-application-status";
    status.textContent = `Status: ${application.status}`;
    const appliedDate = document.createElement("small");
    appliedDate.className = "public-job-date";
    appliedDate.textContent = `Applied ${new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
    }).format(new Date(application.applied_at))}`;
    const removeButton = document.createElement("button");
    removeButton.className = "button button-secondary";
    removeButton.type = "button";
    removeButton.textContent = "Remove application";
    removeButton.addEventListener("click", async () => {
      const confirmed = window.confirm(
        `Withdraw your application for ${application.job_title}? It will be removed from your dashboard. The hiring team will see it as withdrawn, and RecruitO will retain the assessment history.`
      );
      if (!confirmed) return;
      removeButton.disabled = true;
      dashboardMessage.textContent = "Withdrawing your application…";
      try {
        await api.removeMyApplication(application.id);
        dashboardMessage.textContent = `Your application for ${application.job_title} was withdrawn and removed from your dashboard.`;
        await loadMyApplications();
      } catch (error) {
        dashboardMessage.textContent = `Could not remove the application: ${error.message}`;
        removeButton.disabled = false;
      }
    });
    card.append(title, status, appliedDate, removeButton);
    if (!application.interview_scheduled_at && application.interview_scheduling_status === "manager_notified") {
      const scheduling = document.createElement("p");
      scheduling.className = "candidate-interview-details";
      scheduling.textContent = "Good news — you've been shortlisted for an interview. The hiring team is arranging it and will email you the date, time, and a join link.";
      card.append(scheduling);
    } else if (!application.interview_scheduled_at && application.interview_scheduling_status === "not_queued") {
      const scheduling = document.createElement("p");
      scheduling.className = "candidate-interview-details";
      scheduling.textContent = "Your application is being reviewed. If you are shortlisted, the hiring team will arrange an interview and email you the details.";
      card.append(scheduling);
    } else if (!application.interview_scheduled_at && application.interview_scheduling_status === "not_eligible") {
      const scheduling = document.createElement("p");
      scheduling.className = "candidate-interview-details";
      scheduling.textContent = "Your application remains under review at this stage.";
      card.append(scheduling);
    }
    if (application.interview_scheduled_at) {
      const schedule = document.createElement("p");
      schedule.className = "candidate-interview-details";
      const localDateTime = new Intl.DateTimeFormat(undefined, {
        dateStyle: "full",
        timeStyle: "short",
      }).format(new Date(application.interview_scheduled_at));
      schedule.textContent = `Interview scheduled: ${localDateTime} · ${application.interview_duration_minutes} minutes`;
      const joinButton = document.createElement("button");
      joinButton.className = "button button-secondary candidate-join-button";
      joinButton.type = "button";
      joinButton.textContent = "Join interview";
      joinButton.disabled = !application.join_available;
      joinButton.title = application.join_available
        ? "Join your scheduled interview"
        : "Joining opens 15 minutes before the scheduled time.";
      joinButton.addEventListener("click", async () => {
        if (!application.join_available || !application.interview_id) return;
        joinButton.disabled = true;
        joinHint.textContent = "Preparing your secure interview link…";
        try {
          const link = await api.createInterviewJoinLink(application.interview_id);
          window.location.assign(`./interview.html?token=${encodeURIComponent(link.token)}`);
        } catch (error) {
          joinHint.textContent = error.message;
          joinButton.disabled = false;
        }
      });
      const joinHint = document.createElement("small");
      joinHint.className = "candidate-join-hint";
      joinHint.textContent = application.join_available
        ? "Your interview room is ready."
        : "Join becomes available 15 minutes before the scheduled time.";
      card.append(schedule, joinButton, joinHint);
    }
    return card;
  });
  applicationsList.replaceChildren(...cards);
}

async function loadProfile() {
  renderProfile(await api.getCandidateProfile());
}

async function loadMyApplications() {
  if (!candidateSignedIn || applicationsRefreshInProgress) return;
  applicationsRefreshInProgress = true;
  dashboardMessage.textContent = "Loading your applications…";
  try {
    renderApplications(await api.listMyApplications());
  } catch (error) {
    dashboardMessage.textContent = error.message;
  } finally {
    applicationsRefreshInProgress = false;
  }
}

async function loadJobs() {
  jobsMessage.textContent = "Loading open roles…";
  try {
    renderJobs(await api.listPublicJobs());
  } catch {
    jobsMessage.textContent = "Could not load open roles. Please try again later.";
    jobsList.replaceChildren();
  }
}

async function showSignedInCandidate(fullName, loadedProfile = null) {
  candidateSignedIn = true;
  authCopy.textContent = `Signed in as ${fullName}. Your profile is shown first.`;
  authMessage.textContent = "Signed in successfully.";
  authForm.hidden = true;
  authToggle.hidden = true;
  candidateLogoutButton.hidden = false;
  candidateNavigation.hidden = false;
  candidateChat.hidden = false;
  profileMessage.textContent = "Loading your profile…";
  setCandidateView("profile");
  const [profileResult] = await Promise.allSettled([
    loadedProfile ? Promise.resolve(renderProfile(loadedProfile)) : loadProfile(),
    loadMyApplications(),
  ]);
  loadBiometricStatus();
  if (profileResult.status === "rejected") {
    profileMessage.textContent = profileResult.reason.message;
  }
  if (hasPublicJobDeepLink || requestedApplicationJobId !== null) {
    setCandidateView("jobs");
  }
  openRequestedJob();
  openRequestedApplication();
}

async function loadBiometricStatus() {
  try {
    const result = await api.getBiometricEnrollment();
    biometricStatus.textContent = result.enrolled
      ? `Enrolled until ${new Date(result.retention_until).toLocaleDateString()}. You may revoke consent at any time.`
      : "You are not enrolled. This optional check is not required to apply or interview.";
    document.querySelector("#biometric-revoke").hidden = !result.enrolled;
  } catch (error) {
    biometricStatus.textContent = error.message;
  }
}

document.querySelector("#biometric-start-camera").addEventListener("click", async () => {
  try {
    biometricStream?.getTracks().forEach((track) => track.stop());
    biometricStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    biometricPreview.srcObject = biometricStream;
    biometricPreview.hidden = false;
    biometricCapture.disabled = !biometricConsent.checked;
    biometricStatus.textContent = "Camera is ready. Capture only when you have checked the consent box.";
  } catch {
    biometricStatus.textContent = "Camera access was not granted. You can use RecruitO without biometric enrollment.";
  }
});
biometricConsent.addEventListener("change", () => {
  biometricCapture.disabled = !biometricConsent.checked || !biometricStream;
});
biometricCapture.addEventListener("click", async () => {
  if (!biometricConsent.checked || !biometricStream) return;
  biometricCapture.disabled = true;
  biometricStatus.textContent = "Creating your face representation…";
  const videoTrack = biometricStream.getVideoTracks()[0];
  const settings = videoTrack.getSettings();
  const canvas = document.createElement("canvas");
  const scale = Math.min(1, 1280 / (settings.width || 640), 1280 / (settings.height || 480));
  canvas.width = Math.round((settings.width || 640) * scale);
  canvas.height = Math.round((settings.height || 480) * scale);
  const context = canvas.getContext("2d");
  context.drawImage(biometricPreview, 0, 0, canvas.width, canvas.height);
  canvas.toBlob(async (blob) => {
    try {
      await api.enrollBiometricProfile(blob);
      biometricStatus.textContent = "Enrollment saved. The captured photo was not stored.";
      biometricConsent.checked = false;
      await loadBiometricStatus();
    } catch (error) {
      biometricStatus.textContent = error.message;
      biometricCapture.disabled = false;
    } finally {
      biometricStream?.getTracks().forEach((track) => track.stop());
      biometricStream = null;
      biometricPreview.srcObject = null;
      biometricPreview.hidden = true;
    }
  }, "image/jpeg", 0.88);
});
document.querySelector("#biometric-revoke").addEventListener("click", async () => {
  try {
    await api.revokeBiometricConsent();
    biometricStatus.textContent = "Consent revoked and stored face representation deleted.";
    await loadBiometricStatus();
  } catch (error) {
    biometricStatus.textContent = error.message;
  }
});

authToggle.addEventListener("click", () => {
  isSignIn = !isSignIn;
  nameField.hidden = isSignIn;
  phoneField.hidden = isSignIn;
  document.querySelector("#candidate-name").required = !isSignIn;
  document.querySelector("#candidate-phone").required = !isSignIn;
  passwordInput.autocomplete = isSignIn ? "current-password" : "new-password";
  authSubmit.textContent = isSignIn ? "Sign in" : "Create candidate account";
  authToggle.textContent = isSignIn ? "New to RecruitO? Create an account" : "Already registered? Sign in";
  authCopy.textContent = isSignIn
    ? "Sign in to your candidate account."
    : "Create an account with your name, email, and phone number.";
  authMessage.textContent = "";
});

authForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  authSubmit.disabled = true;
  authMessage.textContent = isSignIn ? "Signing in…" : "Creating your account…";
  const form = new FormData(authForm);
  const email = String(form.get("email")).trim();
  const password = String(form.get("password"));
  const fullName = String(form.get("full_name") || "").trim();
  const phoneNumber = String(form.get("phone_number") || "").trim();
  let accountCreated = false;
  try {
    if (!isSignIn) {
      await api.registerCandidate(email, password, fullName, phoneNumber);
      accountCreated = true;
    }
    const user = await api.login(email, password);
    if (user.role !== "candidate") {
      await api.logout();
      throw new Error("This page is for candidate accounts. Use a candidate account to apply.");
    }
    await showSignedInCandidate(user.full_name);
  } catch (error) {
    if (accountCreated) {
      authToggle.click();
      authMessage.textContent = `Your account was created, but automatic sign-in did not complete. Sign in with that account. ${error.message}`;
    } else {
      authMessage.textContent = error.status === 409
        ? "This email is already registered. Switch to sign in."
        : error.status === 422
          ? "Check the form. Use a valid email, name, phone number, and a password between 8 and 128 characters."
          : error.message;
    }
  } finally {
    authSubmit.disabled = false;
  }
});

candidateNavigation.querySelectorAll("[data-candidate-view]").forEach((button) => {
  button.addEventListener("click", () => setCandidateView(button.dataset.candidateView));
});

candidateLogoutButton.addEventListener("click", async () => {
  candidateLogoutButton.disabled = true;
  candidateLogoutButton.textContent = "Signing out…";
  authMessage.textContent = "Signing out…";
  try {
    await api.logout();
    window.location.replace(`./index.html?logged_out=${Date.now()}`);
  } catch (error) {
    candidateLogoutButton.disabled = false;
    candidateLogoutButton.textContent = "Sign out";
    authMessage.textContent = `Could not sign out: ${error.message}`;
  }
});

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const messageText = chatInput.value.trim();
  if (!messageText) return;
  const question = document.createElement("p");
  question.className = "candidate-chat-message candidate-chat-user";
  question.textContent = `You: ${messageText}`;
  chatMessages.append(question);
  chatInput.value = "";
  chatSubmit.disabled = true;
  const answer = document.createElement("p");
  answer.className = "candidate-chat-message candidate-chat-assistant";
  answer.textContent = "RecruitO is checking your information…";
  chatMessages.append(answer);
  try {
    const result = await api.sendCandidateChat(messageText);
    answer.textContent = `RecruitO: ${result.reply}`;
  } catch (error) {
    answer.textContent = `RecruitO: ${error.message}`;
  } finally {
    chatSubmit.disabled = false;
    chatInput.focus();
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }
});

async function restoreCandidateSession() {
  try {
    const profile = await api.getCandidateProfile();
    await showSignedInCandidate("your candidate account", profile);
  } catch {
    // No active candidate session; registration and sign-in remain available.
  }
}

jobsView.hidden = false;
loadJobs();
restoreCandidateSession();
window.setInterval(() => {
  if (candidateSignedIn && document.visibilityState === "visible") {
    loadMyApplications();
  }
}, 30_000);
