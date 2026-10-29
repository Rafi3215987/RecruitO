import { api } from "./api.js";

const form = document.querySelector("#reset-form");
const button = document.querySelector("#reset-button");
const feedback = document.querySelector("#reset-feedback");
const token = new URLSearchParams(window.location.search).get("token") || "";

function setFeedback(message, ok = true) {
  feedback.textContent = message;
  feedback.classList.toggle("is-success", ok);
  feedback.hidden = !message;
}

if (!token) {
  setFeedback("This reset link is incomplete. Request a new one from the sign-in page.", false);
  button.disabled = true;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!form.reportValidity()) return;
  const password = form.elements.new_password.value;
  if (password !== form.elements.confirm.value) {
    setFeedback("The two passwords do not match.", false);
    return;
  }
  button.disabled = true;
  button.textContent = "Resetting…";
  setFeedback("");
  try {
    const result = await api.resetPassword(token, password);
    // The endpoint signs the user in (sets the session cookie), so send them
    // straight to their dashboard instead of the login page.
    const home = { candidate: "./public-jobs.html", interviewer: "./interviewer-dashboard.html", hiring_manager: "./manager-applications.html" }[result.role] || "./index.html";
    setFeedback((result.message || "Your password has been set.") + " Taking you to your dashboard…", true);
    form.reset();
    window.setTimeout(() => window.location.replace(home), 1400);
  } catch (error) {
    setFeedback(error.message, false);
    button.disabled = false;
    button.textContent = "Reset password";
  }
});
