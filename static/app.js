const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");
const modelInfo = document.getElementById("modelInfo");
const startBtn = document.getElementById("startBtn");
const stopBtn = document.getElementById("stopBtn");
const timer = document.getElementById("timer");
const liveState = document.getElementById("liveState");
const itemsContainer = document.getElementById("items");
const fileInput = document.getElementById("fileInput");
const uploadBtn = document.getElementById("uploadBtn");

let mediaRecorder = null;
let chunks = [];
let timerInterval = null;
let startTime = null;

function formatTime(seconds) {
  const minutes = String(Math.floor(seconds / 60)).padStart(2, "0");
  const rest = String(seconds % 60).padStart(2, "0");
  return `${minutes}:${rest}`;
}

function setLiveState(text) {
  liveState.textContent = text;
}

async function checkHealth() {
  try {
    const response = await fetch("/api/health");
    const data = await response.json();
    statusDot.classList.add("online");
    statusText.textContent = "En ligne";
    modelInfo.textContent = `Modele: ${data.model} (${data.device})`;
  } catch (err) {
    statusDot.classList.remove("online");
    statusText.textContent = "Hors ligne";
    modelInfo.textContent = "Modele: -";
  }
}

async function fetchItems() {
  const response = await fetch("/api/items");
  const items = await response.json();
  itemsContainer.innerHTML = "";
  items.forEach((item) => {
    const card = document.createElement("div");
    card.className = "item";
    const when = new Date(item.created_at).toLocaleString();
    card.innerHTML = `
      <div class="item-head">
        <span>${when}</span>
        <span>${item.id.slice(0, 8)}</span>
      </div>
      <audio controls src="${item.audio_url}"></audio>
      <div class="transcript">${item.transcript || "Transcription en cours..."}</div>
      <button class="btn ghost delete" data-id="${item.id}">Supprimer</button>
    `;
    itemsContainer.appendChild(card);
  });
  document.querySelectorAll(".delete").forEach((button) => {
    button.addEventListener("click", async (event) => {
      const id = event.currentTarget.dataset.id;
      const ok = confirm("Supprimer cet enregistrement et son transcript ?");
      if (!ok) {
        return;
      }
      const response = await fetch(`/api/items/${id}`, { method: "DELETE" });
      if (response.ok) {
        await fetchItems();
      } else {
        setLiveState("Erreur pendant la suppression.");
      }
    });
  });
}

async function uploadBlob(blob) {
  const form = new FormData();
  form.append("audio", blob, "dictation.webm");
  setLiveState("Transcription en cours...");
  const response = await fetch("/api/upload", {
    method: "POST",
    body: form,
  });
  if (!response.ok) {
    setLiveState("Erreur pendant l'upload.");
    return;
  }
  await response.json();
  setLiveState("Transcription terminee.");
  await fetchItems();
}

function startTimer() {
  startTime = Date.now();
  timerInterval = setInterval(() => {
    const elapsed = Math.floor((Date.now() - startTime) / 1000);
    timer.textContent = formatTime(elapsed);
  }, 500);
}

function stopTimer() {
  clearInterval(timerInterval);
  timerInterval = null;
  timer.textContent = "00:00";
}

async function startRecording() {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  chunks = [];
  mediaRecorder = new MediaRecorder(stream);
  mediaRecorder.ondataavailable = (event) => {
    if (event.data.size > 0) {
      chunks.push(event.data);
    }
  };
  mediaRecorder.onstop = async () => {
    const blob = new Blob(chunks, { type: "audio/webm" });
    await uploadBlob(blob);
  };
  mediaRecorder.start();
  startBtn.disabled = true;
  stopBtn.disabled = false;
  setLiveState("Enregistrement en cours...");
  startTimer();
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    mediaRecorder.stop();
    mediaRecorder.stream.getTracks().forEach((track) => track.stop());
  }
  startBtn.disabled = false;
  stopBtn.disabled = true;
  stopTimer();
}

startBtn.addEventListener("click", () => {
  startRecording().catch(() => {
    setLiveState("Micro non disponible.");
  });
});

stopBtn.addEventListener("click", () => {
  stopRecording();
});

uploadBtn.addEventListener("click", async () => {
  if (!fileInput.files.length) {
    setLiveState("Choisis un fichier audio.");
    return;
  }
  await uploadBlob(fileInput.files[0]);
});

checkHealth();
fetchItems();
setInterval(fetchItems, 8000);
