import { api } from "./api.js";

const params = new URLSearchParams(window.location.search);
const token = params.get("token") || "";
const info = document.querySelector("#interview-room-info");
const status = document.querySelector("#interview-room-status");
const joinButton = document.querySelector("#join-room");
const transcriptConsent = document.querySelector("#transcript-consent");
const identityConsent = document.querySelector("#identity-consent");
const identityLabel = document.querySelector("#identity-consent-label");

function redirectToLogin() {
  const next = `./interview.html?token=${encodeURIComponent(token)}`;
  window.location.replace(`./index.html?auth=signin&next=${encodeURIComponent(next)}`);
}

joinButton.addEventListener("click", () => {
  // Carry the consent choices to the dedicated meeting room page.
  const tx = transcriptConsent.checked ? "1" : "0";
  const bio = identityConsent.checked ? "1" : "0";
  window.location.assign(
    `./meeting-room.html?token=${encodeURIComponent(token)}&tx=${tx}&bio=${bio}`
  );
});

try {
  if (!token) throw Object.assign(new Error("Missing interview link"), { status: 404 });
  const room = await api.validateInterviewToken(token);
  if (room.role !== "candidate") identityLabel?.setAttribute("hidden", "");
  else identityLabel?.removeAttribute("hidden");
  document.querySelector("#interview-room-title").textContent = `${room.job_title} interview`;
  info.textContent = `Candidate: ${room.candidate_name} · ${new Intl.DateTimeFormat(undefined, { dateStyle: "full", timeStyle: "short" }).format(new Date(room.scheduled_at))} · ${room.duration_minutes} minutes`;
  joinButton.disabled = false;
  status.textContent = "Choose your options above, then join when you're ready.";
} catch (error) {
  if (error.status === 401) {
    redirectToLogin();
  } else {
    info.textContent = "This interview link is invalid or expired. Go back to your dashboard and click Join again to get a fresh link.";
    status.textContent = error.message;
  }
}
