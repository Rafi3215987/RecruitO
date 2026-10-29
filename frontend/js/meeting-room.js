import { api } from "./api.js";

const params = new URLSearchParams(window.location.search);
const token = params.get("token") || "";
// Consent choices were made in the lobby (interview.html) and passed here.
const transcriptionAllowed = params.get("tx") === "1";
const identityAllowed = params.get("bio") === "1";

const info = document.querySelector("#interview-room-info");
const status = document.querySelector("#interview-room-status");
const micButton = document.querySelector("#toggle-mic");
const cameraButton = document.querySelector("#toggle-camera");
const endButton = document.querySelector("#end-room");
const localVideo = document.querySelector("#local-video");
const remoteVideo = document.querySelector("#remote-video");
const identityStatus = document.querySelector("#identity-status");
const identityProfile = document.querySelector("#identity-profile");
const transcriptList = document.querySelector("#interview-transcript");

const ICON = {
  mic: '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0"/><line x1="12" y1="18" x2="12" y2="22"/></svg>',
  micOff: '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 9v2a3 3 0 0 0 5 2.1"/><path d="M15 10.5V6a3 3 0 0 0-5.8-1.1"/><path d="M5 11a7 7 0 0 0 10.7 6"/><line x1="12" y1="18" x2="12" y2="22"/><line x1="3" y1="3" x2="21" y2="21"/></svg>',
  cam: '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 10l5-3v10l-5-3z"/><rect x="3" y="6" width="12" height="12" rx="2"/></svg>',
  camOff: '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M16 16H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h1"/><path d="M10 6h4a2 2 0 0 1 2 2v3l4-3v8"/><line x1="2" y1="2" x2="22" y2="22"/></svg>',
};

let room = null;
let localStream = null;
let socket = null;
let peer = null;
let pendingIce = [];
let joined = false;
let livekitRoom = null;
let useLivekit = false;
let transcriptSocket = null;
let mediaRecorder = null;
let transcriptionRequested = false;
let transcriptionReconnectTimer = null;
let transcriptionSegmentTimer = null;
let transcriptionReconnectAttempts = 0;
const MAX_TRANSCRIPTION_RECONNECTS = 4;
let identityFrameSent = false;

function renderCandidateInfo(info) {
  const panel = document.querySelector("#candidate-info-panel");
  if (!panel || !info) return;
  const roleEl = panel.querySelector("#candidate-info-role");
  if (roleEl) {
    roleEl.textContent = info.seniority ? `${info.job_title} · ${info.seniority}` : info.job_title || "";
  }

  const contact = panel.querySelector("#candidate-info-contact");
  if (contact) {
    const rows = [
      ["Name", info.candidate_name],
      ["Email", info.email],
      ["Phone", info.phone],
    ].filter(([, value]) => value);
    contact.replaceChildren(...rows.flatMap(([label, value]) => {
      const dt = document.createElement("dt");
      dt.textContent = label;
      const dd = document.createElement("dd");
      dd.textContent = value;
      return [dt, dd];
    }));
  }

  const highlights = panel.querySelector("#candidate-info-highlights");
  if (highlights) {
    const education = [info.education, info.institution, info.graduation_year]
      .filter(Boolean)
      .join(" · ");
    const items = [];
    if (info.pre_interview_score !== null && info.pre_interview_score !== undefined) {
      items.push(`Pre-interview score: ${info.pre_interview_score}/100`);
    }
    if (education) items.push(`Education: ${education}`);
    if ((info.key_skills || []).length) items.push(`Skills matched: ${info.key_skills.join(", ")}`);
    if ((info.areas_to_probe || []).length) items.push(`Areas to probe: ${info.areas_to_probe.join(", ")}`);
    if (!items.length) items.push("No CV highlights were extracted for this candidate.");
    highlights.replaceChildren(...items.map((text) => {
      const li = document.createElement("li");
      li.textContent = text;
      return li;
    }));
  }

  panel.hidden = false;
}

function renderIdentityResult(message) {
  if (!message.matched || !message.profile) {
    identityStatus.textContent = message.reason === "no_active_consent"
      ? "No biometric match available. The candidate has not enrolled or has revoked consent."
      : "No confident biometric match. Verify identity manually; this check is optional.";
    identityProfile.hidden = true;
    return;
  }
  identityStatus.textContent = "Face match found. Confirm identity with the candidate before proceeding.";
  const profile = message.profile;
  const items = [
    ["Candidate", profile.candidate_name],
    ["Education / experience", profile.headline_experience],
    ["Pre-interview score", profile.pre_interview_score === null ? "Not available" : `${profile.pre_interview_score}/100`],
    ["Skills marked met", (profile.key_skills || []).join(", ") || "Not available"],
    ["Areas to probe", (profile.areas_to_probe || []).join(", ") || "None recorded"],
  ];
  identityProfile.replaceChildren(...items.flatMap(([label, value]) => {
    const rowEl = document.createElement("p");
    const title = document.createElement("strong");
    title.textContent = `${label}: `;
    const content = document.createElement("span");
    content.textContent = String(value ?? "Not available");
    rowEl.append(title, content);
    return [rowEl];
  }));
  identityProfile.hidden = false;
}

function sendBiometricFrame() {
  if (!identityAllowed || room?.role !== "candidate" || identityFrameSent
      || !localVideo.videoWidth || socket?.readyState !== WebSocket.OPEN) return;
  const canvas = document.createElement("canvas");
  const scale = Math.min(1, 1280 / localVideo.videoWidth);
  canvas.width = Math.round(localVideo.videoWidth * scale);
  canvas.height = Math.round(localVideo.videoHeight * scale);
  canvas.getContext("2d").drawImage(localVideo, 0, 0, canvas.width, canvas.height);
  socket.send(JSON.stringify({ type: "identity_frame", data: canvas.toDataURL("image/jpeg", 0.8) }));
  identityFrameSent = true;
  identityStatus.textContent = "Checking one frame against your enrolled representation…";
}

function apiWebsocketUrl(interviewId, channel = "signal") {
  const base = window.RECRUITO_CONFIG?.apiBaseUrl || `${window.location.origin}/api`;
  const url = new URL(base, window.location.href);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = `${url.pathname.replace(/\/$/, "")}/interviews/${encodeURIComponent(interviewId)}/${channel}`;
  url.search = "";
  return url.href;
}

function stopTranscription() {
  transcriptionRequested = false;
  transcriptionReconnectAttempts = 0;
  window.clearTimeout(transcriptionReconnectTimer);
  transcriptionReconnectTimer = null;
  window.clearTimeout(transcriptionSegmentTimer);
  transcriptionSegmentTimer = null;
  const recorder = mediaRecorder;
  mediaRecorder = null;
  if (recorder && recorder.state !== "inactive") recorder.stop();
  const currentSocket = transcriptSocket;
  transcriptSocket = null;
  if (currentSocket && currentSocket.readyState < WebSocket.CLOSING) currentSocket.close();
}

function appendTranscript(segment) {
  // Candidate view hides the transcript panel; never render transcript text for them.
  const panelEl = transcriptList.closest(".interview-transcript-panel");
  if (panelEl && panelEl.hidden) return;
  const isInterviewer = segment.speaker_role === "interviewer";
  const item = document.createElement("li");
  item.className = isInterviewer ? "transcript-line transcript-interviewer" : "transcript-line transcript-candidate";
  const time = document.createElement("time");
  const totalSeconds = Math.floor(segment.started_at_seconds || 0);
  time.textContent = `${String(Math.floor(totalSeconds / 60)).padStart(2, "0")}:${String(totalSeconds % 60).padStart(2, "0")}`;
  const speaker = document.createElement("strong");
  speaker.className = isInterviewer ? "speaker speaker-interviewer" : "speaker speaker-candidate";
  speaker.textContent = isInterviewer ? "Interviewer" : "Candidate";
  const words = document.createElement("span");
  words.className = "transcript-text";
  words.textContent = segment.text;
  item.append(time, speaker, words);
  transcriptList.append(item);
  const panel = transcriptList.closest(".interview-transcript-panel");
  if (panel) panel.scrollTop = panel.scrollHeight;
}

function startTranscription(interviewId) {
  if (!transcriptionAllowed || !joined || !localStream?.getAudioTracks().length) return;
  if (transcriptionRequested) return;
  if (!window.MediaRecorder) return;
  const supportedTypes = ["audio/webm;codecs=opus", "audio/ogg;codecs=opus", "audio/mp4"];
  const mimeType = supportedTypes.find((type) => MediaRecorder.isTypeSupported(type));
  if (!mimeType) return;
  transcriptionRequested = true;
  transcriptionReconnectAttempts = 0;

  const connectTranscriptSocket = () => {
    if (!transcriptionRequested || !joined
        || transcriptSocket?.readyState === WebSocket.OPEN
        || transcriptSocket?.readyState === WebSocket.CONNECTING) return;

    const currentSocket = new WebSocket(apiWebsocketUrl(interviewId, "transcript"));
    transcriptSocket = currentSocket;
    currentSocket.addEventListener("open", () => {
      currentSocket.send(JSON.stringify({ type: "consent", consent: true, mime_type: mimeType }));
    });
    currentSocket.addEventListener("message", (event) => {
      if (transcriptSocket !== currentSocket) return;
      const message = JSON.parse(event.data);
      if (message.type === "transcription_ready") {
        transcriptionReconnectAttempts = 0;
        const SEGMENT_MS = 3500;
        // Record ONLY the audio track as a complete, self-contained file each ~3.5s.
        const audioStream = new MediaStream(localStream.getAudioTracks());
        const beginSegment = () => {
          if (!transcriptionRequested || !joined
              || currentSocket !== transcriptSocket || currentSocket.readyState !== WebSocket.OPEN) return;
          let recorder;
          try {
            recorder = new MediaRecorder(audioStream, { mimeType });
          } catch {
            status.textContent = "This browser could not start audio recording for transcription.";
            return;
          }
          mediaRecorder = recorder;
          recorder.addEventListener("dataavailable", async (recorded) => {
            if (recorded.data.size && transcriptionRequested && currentSocket === transcriptSocket
                && currentSocket.readyState === WebSocket.OPEN) {
              try {
                const chunk = await recorded.data.arrayBuffer();
                if (currentSocket.readyState === WebSocket.OPEN) currentSocket.send(chunk);
              } catch {
                if (currentSocket.readyState < WebSocket.CLOSING) currentSocket.close();
                return;
              }
            }
            beginSegment();
          });
          recorder.addEventListener("error", () => {
            if (currentSocket.readyState < WebSocket.CLOSING) currentSocket.close();
          });
          recorder.start();
          transcriptionSegmentTimer = window.setTimeout(() => {
            if (mediaRecorder === recorder && recorder.state === "recording") recorder.stop();
          }, SEGMENT_MS);
        };
        beginSegment();
      } else if (message.type === "transcript") appendTranscript(message.segment);
      else if (message.type === "transcription_error") status.textContent = message.message;
    });
    currentSocket.addEventListener("close", () => {
      if (transcriptSocket === currentSocket) transcriptSocket = null;
      window.clearTimeout(transcriptionSegmentTimer);
      transcriptionSegmentTimer = null;
      const recorder = mediaRecorder;
      mediaRecorder = null;
      if (recorder && recorder.state !== "inactive") recorder.stop();
      if (!transcriptionRequested || !joined) return;
      transcriptionReconnectAttempts += 1;
      if (transcriptionReconnectAttempts > MAX_TRANSCRIPTION_RECONNECTS) {
        transcriptionRequested = false;
        return;
      }
      const delay = Math.min(1000 * (2 ** (transcriptionReconnectAttempts - 1)), 8000);
      transcriptionReconnectTimer = window.setTimeout(connectTranscriptSocket, delay);
    });
    currentSocket.addEventListener("error", () => {
      if (currentSocket.readyState < WebSocket.CLOSING) currentSocket.close();
    });
  };

  connectTranscriptSocket();
}

function redirectToLogin() {
  const next = `./interview.html?token=${encodeURIComponent(token)}`;
  window.location.replace(`./index.html?auth=signin&next=${encodeURIComponent(next)}`);
}

async function connectLivekit(lk) {
  const LK = window.LivekitClient;
  if (!LK || !lk || !lk.url || !lk.token) return false;
  try {
    livekitRoom = new LK.Room({ adaptiveStream: true, dynacast: true });
    livekitRoom.on(LK.RoomEvent.TrackSubscribed, (track) => {
      if (track.kind === "video") track.attach(remoteVideo);
      else if (track.kind === "audio") track.attach();
    });
    await livekitRoom.connect(lk.url, lk.token);
    for (const track of localStream.getTracks()) {
      await livekitRoom.localParticipant.publishTrack(track);
    }
    return true;
  } catch {
    try { await livekitRoom?.disconnect(); } catch { /* ignore */ }
    livekitRoom = null;
    return false;
  }
}

async function connectRoom() {
  if (joined || !room) return;
  status.textContent = "Requesting camera and microphone access…";
  try {
    localStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: { width: { ideal: 960 }, height: { ideal: 540 } } });
  } catch {
    try {
      localStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
      status.textContent = "Camera was unavailable, so you joined audio-only.";
    } catch {
      status.textContent = "Microphone access was not granted. Allow access in the browser (padlock icon), then reload this page.";
      return;
    }
  }
  localVideo.srcObject = localStream;
  const livekitToken = await api.getLivekitToken(room.interview_id).catch(() => null);
  useLivekit = livekitToken ? await connectLivekit(livekitToken) : false;
  socket = new WebSocket(apiWebsocketUrl(room.interview_id));
  socket.addEventListener("open", () => {
    status.textContent = "Connected to the secure room. Waiting for the other participant…";
    joined = true;
    micButton.disabled = endButton.disabled = false;
    cameraButton.disabled = !localStream.getVideoTracks().length;
    startTranscription(room.interview_id);
    if (room.role === "candidate" && identityAllowed) {
      socket.send(JSON.stringify({ type: "identity_consent", consent: true }));
    }
  });
  socket.addEventListener("message", async (event) => {
    const message = JSON.parse(event.data);
    if (message.type === "ready") {
      if (!useLivekit) {
        peer = new RTCPeerConnection({ iceServers: [{ urls: ["stun:stun.l.google.com:19302"] }] });
        for (const track of localStream.getTracks()) peer.addTrack(track, localStream);
        peer.ontrack = (trackEvent) => { remoteVideo.srcObject = trackEvent.streams[0]; };
        peer.onicecandidate = (candidateEvent) => {
          if (candidateEvent.candidate && socket?.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ type: "ice", data: candidateEvent.candidate }));
          }
        };
        if (room.role === "interviewer") {
          const offer = await peer.createOffer();
          await peer.setLocalDescription(offer);
          socket.send(JSON.stringify({ type: "offer", data: peer.localDescription }));
        }
      }
      status.textContent = "Both participants are connected.";
      window.setTimeout(sendBiometricFrame, 500);
      return;
    }
    if (!useLivekit && message.type === "offer" && room.role === "candidate") {
      await peer.setRemoteDescription(message.data);
      const answer = await peer.createAnswer();
      await peer.setLocalDescription(answer);
      socket.send(JSON.stringify({ type: "answer", data: peer.localDescription }));
      for (const candidate of pendingIce) await peer.addIceCandidate(candidate);
      pendingIce = [];
    } else if (!useLivekit && message.type === "answer" && room.role === "interviewer") {
      await peer.setRemoteDescription(message.data);
      for (const candidate of pendingIce) await peer.addIceCandidate(candidate);
      pendingIce = [];
    } else if (!useLivekit && message.type === "ice") {
      if (peer?.remoteDescription) await peer.addIceCandidate(message.data);
      else pendingIce.push(message.data);
    } else if (message.type === "end") {
      status.textContent = "The other participant ended the interview.";
      cleanup(false);
    } else if (message.type === "identity_result") {
      renderIdentityResult(message);
    }
  });
  socket.addEventListener("close", (event) => {
    if (event.code === 4401) redirectToLogin();
    else if (event.code !== 1000) status.textContent = "The interview connection ended. You can return to your dashboard.";
    cleanup(false);
  });
  socket.addEventListener("error", () => { status.textContent = "The interview connection could not be established."; });
}

function cleanup(updateStatus = true) {
  stopTranscription();
  try { livekitRoom?.disconnect(); } catch { /* ignore */ }
  livekitRoom = null;
  useLivekit = false;
  localStream?.getTracks().forEach((track) => track.stop());
  peer?.close();
  peer = null;
  localStream = null;
  joined = false;
  localVideo.srcObject = null;
  remoteVideo.srcObject = null;
  micButton.disabled = cameraButton.disabled = endButton.disabled = true;
  if (updateStatus) status.textContent = "Interview ended. You can close this page.";
}

micButton.addEventListener("click", () => {
  const track = localStream?.getAudioTracks()[0];
  if (!track) return;
  track.enabled = !track.enabled;
  micButton.innerHTML = track.enabled ? ICON.mic : ICON.micOff;
  micButton.title = micButton.ariaLabel = track.enabled ? "Mute microphone" : "Unmute microphone";
  micButton.classList.toggle("is-off", !track.enabled);
});
cameraButton.addEventListener("click", () => {
  const track = localStream?.getVideoTracks()[0];
  if (!track) return;
  track.enabled = !track.enabled;
  cameraButton.innerHTML = track.enabled ? ICON.cam : ICON.camOff;
  cameraButton.title = cameraButton.ariaLabel = track.enabled ? "Turn camera off" : "Turn camera on";
  cameraButton.classList.toggle("is-off", !track.enabled);
});
endButton.addEventListener("click", () => {
  if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ type: "end" }));
  socket?.close();
  cleanup();
});

try {
  if (!token) throw Object.assign(new Error("Missing interview link"), { status: 404 });
  room = await api.validateInterviewToken(token);
  const isInterviewer = room.role === "interviewer";
  if (isInterviewer) {
    try {
      const savedTranscript = await api.getInterviewTranscript(room.interview_id);
      savedTranscript.forEach(appendTranscript);
    } catch { /* transcript appears live */ }
    try {
      renderCandidateInfo(await api.getInterviewCandidateInfo(room.interview_id));
    } catch { /* panel stays hidden if details are unavailable */ }
  } else {
    // Candidates see only the call: the live transcript and the identity / candidate-info
    // panels are for the interviewer. (The candidate's own audio is still transcribed.)
    document.querySelector(".interview-transcript-panel")?.setAttribute("hidden", "");
    document.querySelector("#identity-panel")?.setAttribute("hidden", "");
    document.querySelector("#candidate-info-panel")?.setAttribute("hidden", "");
    document.querySelector(".interview-layout")?.classList.add("candidate-view");
  }
  document.querySelector("#interview-room-title").textContent = `${room.job_title} interview`;
  info.textContent = `Candidate: ${room.candidate_name} · ${new Intl.DateTimeFormat(undefined, { dateStyle: "full", timeStyle: "short" }).format(new Date(room.scheduled_at))} · ${room.duration_minutes} minutes`;
  // Consent was already given in the lobby, so join the room immediately.
  await connectRoom();
} catch (error) {
  if (error.status === 401) {
    redirectToLogin();
  } else {
    info.textContent = "This interview link is invalid or expired. Go back to your dashboard and click Join again to get a fresh link.";
    status.textContent = error.message;
  }
}
