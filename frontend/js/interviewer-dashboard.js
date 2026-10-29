import { api } from "./api.js";

const status = document.querySelector("#interviewer-status");
const profileForm = document.querySelector("#interviewer-profile-form");
const profileMessage = document.querySelector("#interviewer-profile-message");
const photoForm = document.querySelector("#interviewer-photo-form");
const photoPreview = document.querySelector("#interviewer-photo-preview");
const interviewsRoot = document.querySelector("#interviewer-interviews");
const applicationsRoot = document.querySelector("#interviewer-applications");
const applicationsStatus = document.querySelector("#interviewer-applications-status");

function formatStatus(value) {
  return String(value || "unknown")
    .replaceAll("_", " ")
    .replace(/\b[a-z]/g, (letter) => letter.toUpperCase());
}

function fillProfile(profile) {
  for (const name of ["full_name", "email", "institute", "experience_years", "experience_summary", "education"]) {
    profileForm.elements[name].value = profile[name] ?? "";
  }
  if (profile.photo_url) {
    photoPreview.src = `${api.interviewerPhotoUrl()}?v=${Date.now()}`;
    photoPreview.hidden = false;
  }
}

function renderInterviews(interviews) {
  if (!interviews.length) {
    interviewsRoot.replaceChildren();
    status.textContent = "You have no upcoming or in-progress interviews right now.";
    return;
  }
  status.textContent = "Past and cancelled interviews are hidden from this list.";
  interviewsRoot.replaceChildren(...interviews.map((item) => {
    const card = document.createElement("article");
    card.className = "public-job-card manager-application-card";
    const title = document.createElement("h3");
    title.textContent = item.candidate_name;
    const role = document.createElement("p");
    role.textContent = `Role: ${item.job_title}`;
    const time = document.createElement("p");
    time.className = "candidate-interview-details";
    time.textContent = `${new Intl.DateTimeFormat(undefined, { dateStyle: "full", timeStyle: "short" }).format(new Date(item.scheduled_at))} · ${item.duration_minutes} minutes`;
    const join = document.createElement("button");
    join.className = "button button-primary";
    join.textContent = "Join interview";
    join.type = "button";
    join.disabled = !item.join_url;
    join.title = item.join_url ? "Join your assigned interview" : "Join opens 15 minutes before the scheduled time.";
    join.addEventListener("click", async () => {
      join.disabled = true;
      try {
        const link = await api.createInterviewJoinLink(item.interview_id);
        window.location.assign(`./interview.html?token=${encodeURIComponent(link.token)}`);
      } catch (error) {
        status.textContent = error.message;
        join.disabled = false;
      }
    });
    card.append(title, role, time, join);
    return card;
  }));
}

async function loadInterviews() {
  try {
    renderInterviews(await api.listMyInterviews());
  } catch (error) {
    status.textContent = error.status === 401 || error.status === 403
      ? "Sign in with an interviewer account to see your schedule."
      : error.message;
  }
}

function renderApplications(applications) {
  if (!applications.length) {
    applicationsRoot.replaceChildren();
    applicationsStatus.textContent = "There are no job applications right now.";
    return;
  }
  applicationsStatus.textContent = `${applications.length} job application${applications.length === 1 ? "" : "s"}.`;
  applicationsRoot.replaceChildren(...applications.map((item) => {
    const card = document.createElement("article");
    card.className = "public-job-card manager-application-card";
    const title = document.createElement("h3");
    title.textContent = item.candidate_name;
    const role = document.createElement("p");
    role.textContent = `Role: ${item.job_title} · ${item.seniority}`;
    const currentStatus = document.createElement("p");
    currentStatus.textContent = `Application status: ${formatStatus(item.status)}`;
    const applied = document.createElement("p");
    applied.textContent = `Applied: ${new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(item.applied_at))}`;
    card.append(title, role, currentStatus, applied);
    return card;
  }));
}

async function loadApplications() {
  applicationsStatus.textContent = "Loading job applications…";
  try {
    renderApplications(await api.listJobApplicationsForInterviewer());
  } catch (error) {
    applicationsRoot.replaceChildren();
    applicationsStatus.textContent = error.status === 401 || error.status === 403
      ? "Sign in with an interviewer account to see job applications."
      : error.message;
  }
}

profileForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  profileMessage.textContent = "Saving profile…";
  try {
    const form = profileForm.elements;
    const profile = await api.updateInterviewerProfile({
      full_name: form.full_name.value.trim(),
      email: form.email.value.trim(),
      institute: form.institute.value.trim() || null,
      experience_years: form.experience_years.value ? Number(form.experience_years.value) : null,
      experience_summary: form.experience_summary.value.trim() || null,
      education: form.education.value.trim() || null,
    });
    fillProfile(profile);
    profileMessage.textContent = "Profile saved.";
  } catch (error) {
    profileMessage.textContent = error.message;
  }
});

photoForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = photoForm.elements.photo.files[0];
  if (!file) return;
  profileMessage.textContent = "Uploading photo…";
  try {
    fillProfile(await api.uploadInterviewerPhoto(file));
    profileMessage.textContent = "Photo uploaded. Image metadata was removed.";
    photoForm.reset();
  } catch (error) {
    profileMessage.textContent = error.message;
  }
});

document.querySelector("#refresh-interviews").addEventListener("click", loadInterviews);
document.querySelector("#refresh-applications").addEventListener("click", loadApplications);
document.querySelector("#interviewer-logout").addEventListener("click", async (event) => {
  event.currentTarget.disabled = true;
  try {
    await api.logout();
    window.location.replace("./index.html?logged_out=" + Date.now());
  } catch (error) {
    status.textContent = `Could not sign out: ${error.message}`;
    event.currentTarget.disabled = false;
  }
});

try {
  fillProfile(await api.getInterviewerProfile());
} catch {
  status.textContent = "Sign in with an interviewer account to use this dashboard.";
}
await loadInterviews();
await loadApplications();
window.setInterval(() => {
  if (document.visibilityState === "visible") {
    loadInterviews();
    loadApplications();
  }
}, 30_000);
