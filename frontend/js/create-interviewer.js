import { api } from "./api.js";

const gate = document.querySelector("#manager-gate-message");
const panel = document.querySelector("#interviewer-panel");
const form = document.querySelector("#create-interviewer-form");
const message = document.querySelector("#create-interviewer-message");
const logoutButton = document.querySelector("#manager-logout-button");
const logoutMessage = document.querySelector("#manager-logout-message");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!form.reportValidity()) return;
  const data = form.elements;
  message.textContent = "Creating interviewer account…";
  try {
    const user = await api.createStaffAccount({
      full_name: data.full_name.value.trim(),
      email: data.email.value.trim(),
      password: data.password.value,
      role: "interviewer",
      reason: data.reason.value,
    });
    message.textContent = `Interviewer account created for ${user.email}. Share the temporary password securely.`;
    form.reset();
  } catch (error) {
    message.textContent = error.message;
  }
});

logoutButton.addEventListener("click", async () => {
  logoutButton.disabled = true;
  logoutMessage.textContent = "Signing out…";
  try {
    await api.logout();
    window.location.replace(`./index.html?logged_out=${Date.now()}`);
  } catch (error) {
    logoutButton.disabled = false;
    logoutMessage.textContent = `Could not sign out: ${error.message}`;
  }
});

async function restore() {
  try {
    const user = await api.getManagerProfile();
    if (user.role !== "hiring_manager") {
      throw new Error("not a manager");
    }
    gate.hidden = true;
    panel.hidden = false;
    logoutButton.hidden = false;
  } catch {
    gate.textContent = "Sign in as a hiring manager first. Redirecting…";
    window.setTimeout(() => window.location.replace("./index.html?auth=signin"), 1500);
  }
}

restore();
