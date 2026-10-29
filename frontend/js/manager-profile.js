import { api } from "./api.js";

const gate = document.querySelector("#manager-gate-message");
const panel = document.querySelector("#manager-profile-panel");
const form = document.querySelector("#manager-profile-form");
const message = document.querySelector("#manager-profile-message");
const logoutButton = document.querySelector("#manager-logout-button");
const logoutMessage = document.querySelector("#manager-logout-message");

function fill(user) {
  form.elements.full_name.value = user.full_name;
  form.elements.email.value = user.email;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!form.reportValidity()) return;
  message.textContent = "Saving profile…";
  try {
    const user = await api.updateManagerProfile({
      full_name: form.elements.full_name.value.trim(),
      email: form.elements.email.value.trim(),
    });
    fill(user);
    message.textContent = "Profile saved. Notifications now go to this email.";
  } catch (error) {
    message.textContent = error.status === 409
      ? "That email address is already in use."
      : error.message;
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
    fill(user);
  } catch {
    gate.textContent = "Sign in as a hiring manager first. Redirecting…";
    window.setTimeout(() => window.location.replace("./index.html?auth=signin"), 1500);
  }
}

restore();
