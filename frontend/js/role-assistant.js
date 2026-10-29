import { api } from "./api.js";

const toggle = document.querySelector("#assistant-toggle");
const panel = document.querySelector("#assistant-panel");
const closeButton = document.querySelector("#assistant-close");
if (toggle && panel) {
  const setOpen = (open) => {
    panel.hidden = !open;
    toggle.setAttribute("aria-expanded", String(open));
    if (open) panel.querySelector("#role-assistant-message")?.focus();
  };
  toggle.addEventListener("click", () => setOpen(panel.hidden));
  closeButton?.addEventListener("click", () => {
    setOpen(false);
    toggle.focus();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !panel.hidden) setOpen(false);
  });
}

const form = document.querySelector("#role-assistant-form");
if (form) {
  const input = form.elements.message;
  const log = document.querySelector("#role-assistant-log");
  const status = document.querySelector("#role-assistant-status");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = input.value.trim();
    if (!message) return;
    const question = document.createElement("p");
    question.className = "assistant-user-message";
    question.textContent = `You: ${message}`;
    log.append(question);
    input.value = "";
    status.textContent = "Checking your workspace…";
    const button = form.querySelector("button[type=submit]");
    button.disabled = true;
    try {
      const response = await api.sendRoleChat(message);
      const answer = document.createElement("p");
      answer.className = "assistant-reply-message";
      answer.textContent = `RecruitO: ${response.reply}`;
      log.append(answer);
      status.textContent = "";
    } catch (error) {
      status.textContent = error.message;
    } finally {
      button.disabled = false;
      input.focus();
    }
  });
}
