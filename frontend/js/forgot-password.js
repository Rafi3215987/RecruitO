import { api } from "./api.js";

const form = document.querySelector("#forgot-form");
const button = document.querySelector("#forgot-button");
const feedback = document.querySelector("#forgot-feedback");

function setFeedback(message, ok = true) {
  feedback.textContent = message;
  feedback.classList.toggle("is-success", ok);
  feedback.hidden = !message;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!form.reportValidity()) return;
  button.disabled = true;
  button.textContent = "Sending…";
  setFeedback("");
  try {
    const result = await api.forgotPassword(form.elements.email.value.trim());
    setFeedback(result.message || "If an account with that email exists, a reset link has been sent.", true);
    form.reset();
  } catch (error) {
    setFeedback(error.message, false);
  } finally {
    button.disabled = false;
    button.textContent = "Send reset link";
  }
});
