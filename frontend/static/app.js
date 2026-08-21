// Manufacturing Maintenance Assistant - frontend logic.
// Predefined - not a student TODO area.
//
// BACKEND_URL and LANGFUSE_URL are injected at container start time by
// docker-entrypoint substituting env.js (see Dockerfile / env.js.template).

const chatWindow = document.getElementById("chat-window");
const composer = document.getElementById("composer");
const promptInput = document.getElementById("prompt-input");
const sendButton = document.getElementById("send-button");
const statusDot = document.getElementById("status-dot");
const statusText = document.getElementById("status-text");
const langfuseLink = document.getElementById("langfuse-link");

const BACKEND_URL = (window.APP_CONFIG && window.APP_CONFIG.BACKEND_URL) || "http://localhost:8080";
const LANGFUSE_URL = (window.APP_CONFIG && window.APP_CONFIG.LANGFUSE_URL) || "http://localhost:3030";

langfuseLink.href = LANGFUSE_URL;

function addMessage(role, content) {
  const wrap = document.createElement("div");
  wrap.className = `message ${role}`;
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = content;
  wrap.appendChild(bubble);
  chatWindow.appendChild(wrap);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  return wrap;
}

function addAssistantPlaceholder() {
  const wrap = document.createElement("div");
  wrap.className = "message assistant";
  wrap.innerHTML = `<div class="bubble"><span class="typing"><span></span><span></span><span></span></span></div>`;
  chatWindow.appendChild(wrap);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  return wrap;
}

function renderMeta(container, data) {
  const meta = document.createElement("div");
  meta.className = "meta";

  if (data.success === false) {
    meta.innerHTML = `<span class="chip error">error: ${escapeHtml(data.error || "request failed")}</span>`;
    container.appendChild(meta);
    return;
  }

  const chips = [
    `<span class="chip model">model: ${data.model}</span>`,
    `<span class="chip">latency: ${data.latency_ms} ms</span>`,
    `<span class="chip">tokens: ${data.input_tokens} in / ${data.output_tokens} out / ${data.total_tokens} total</span>`,
  ];
  if (typeof data.estimated_cost === "number") {
    chips.push(`<span class="chip">est. cost: $${data.estimated_cost.toFixed(6)}</span>`);
  }
  meta.innerHTML = chips.join("");
  container.appendChild(meta);
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

async function checkBackend() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/health`);
    if (res.ok) {
      statusDot.classList.add("ok");
      statusDot.classList.remove("bad");
      statusText.textContent = "Backend connected";
      return;
    }
    throw new Error("bad status");
  } catch (e) {
    statusDot.classList.add("bad");
    statusDot.classList.remove("ok");
    statusText.textContent = "Backend unreachable";
  }
}

composer.addEventListener("submit", async (e) => {
  e.preventDefault();
  const prompt = promptInput.value.trim();
  if (!prompt) return;

  addMessage("user", prompt);
  promptInput.value = "";
  sendButton.disabled = true;

  const placeholder = addAssistantPlaceholder();

  try {
    const res = await fetch(`${BACKEND_URL}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }),
    });
    const data = await res.json();

    placeholder.querySelector(".bubble").textContent = data.success
      ? data.response
      : `Sorry, something went wrong: ${data.error || "unknown error"}`;
    renderMeta(placeholder, data);
  } catch (err) {
    placeholder.querySelector(".bubble").textContent = `Request failed: ${err.message}`;
  } finally {
    sendButton.disabled = false;
    chatWindow.scrollTop = chatWindow.scrollHeight;
  }
});

checkBackend();
setInterval(checkBackend, 15000);
