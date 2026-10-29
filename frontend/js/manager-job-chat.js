import { api } from "./api.js";

const messagesElement = document.querySelector("#manager-job-chat-messages");
const form = document.querySelector("#manager-job-chat-form");
const input = document.querySelector("#manager-job-chat-input");
const sendButton = document.querySelector("#manager-job-chat-send");
const generateButton = document.querySelector("#manager-job-chat-generate");
const newBriefButton = document.querySelector("#manager-job-chat-new");
const INITIAL_GREETING = "Tell me about the role you want to hire for. Include any responsibilities, must-have skills, experience, location, employment type, pay range, or benefits you already know. I’ll ask about anything essential that is missing.";

let messages = [];
let busy = false;
let draftCreated = false;

function addMessage(role, text, isError = false) {
  const message = document.createElement("p");
  message.className = `manager-job-chat-message manager-job-chat-${role}`;
  if (isError) message.classList.add("is-error");
  message.textContent = `${role === "user" ? "You" : "RecruitO"}: ${text}`;
  messagesElement.append(message);
  messagesElement.scrollTop = messagesElement.scrollHeight;
}

function resetConversation() {
  messages = [];
  busy = false;
  draftCreated = false;
  messagesElement.replaceChildren();
  addMessage("assistant", INITIAL_GREETING);
  input.disabled = false;
  sendButton.hidden = false;
  generateButton.hidden = false;
  generateButton.disabled = true;
  newBriefButton.hidden = true;
  input.value = "";
  input.focus();
}

async function sendToAssistant(action, content = "") {
  if (busy || draftCreated) return;
  if (action === "message" && !content.trim()) return;
  if (messages.length >= 30) {
    addMessage("assistant", "This conversation has reached its message limit. Start a new brief to continue.", true);
    return;
  }

  busy = true;
  input.disabled = true;
  sendButton.disabled = true;
  generateButton.disabled = true;
  const userContent = action === "generate"
    ? "Please generate the job-description draft now."
    : content.trim();
  messages.push({ role: "user", content: userContent });
  addMessage("user", userContent);
  if (action === "message") input.value = "";
  sendButton.textContent = "Thinking…";

  try {
    const response = await api.chatWithJobAssistant(messages, action);
    messages.push({ role: "assistant", content: response.assistant_message });
    addMessage("assistant", response.assistant_message);
    if (response.status === "draft_created" && response.job_id) {
      draftCreated = true;
      input.disabled = true;
      sendButton.hidden = true;
      generateButton.hidden = true;
      newBriefButton.hidden = false;
      document.dispatchEvent(new CustomEvent("manager-draft-created", {
        detail: { jobId: response.job_id },
      }));
    }
  } catch (error) {
    addMessage("assistant", error.message, true);
  } finally {
    busy = false;
    sendButton.disabled = false;
    sendButton.textContent = "Send message";
    if (!draftCreated) {
      input.disabled = false;
      generateButton.disabled = messages.length === 0 || messages.length >= 30;
    }
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  void sendToAssistant("message", input.value);
});

generateButton.addEventListener("click", () => {
  void sendToAssistant("generate");
});

newBriefButton.addEventListener("click", resetConversation);
