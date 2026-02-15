const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");
const modelInfo = document.getElementById("modelInfo");
const startBtn = document.getElementById("startBtn");
const stopBtn = document.getElementById("stopBtn");
const timer = document.getElementById("timer");
const liveState = document.getElementById("liveState");
const liveTranscript = document.getElementById("liveTranscript");
const itemsContainer = document.getElementById("items");
const itemsMoreBtn = document.getElementById("itemsMoreBtn");
const jobsContainer = document.getElementById("jobs");
const fileInput = document.getElementById("fileInput");
const uploadBtn = document.getElementById("uploadBtn");

let mediaRecorder = null;
let chunks = [];
let timerInterval = null;
let startTime = null;
let busy = false;
let itemsSocket = null;
let itemsSocketRetry = null;
let itemsState = {};
let jobsState = {};
const ITEMS_PAGE_SIZE = 3;
let visibleItemsCount = ITEMS_PAGE_SIZE;
const ICONS = {
  play: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5v14l11-7-11-7z"/></svg>',
  download: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3v11m0 0 4-4m-4 4-4-4M5 20h14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  txt: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3h9l5 5v13H6z" fill="none" stroke="currentColor" stroke-width="2"/><path d="M15 3v5h5" fill="none" stroke="currentColor" stroke-width="2"/><path d="M8 17h8M8 13h5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>',
  copy: '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="9" y="9" width="11" height="11" rx="2" fill="none" stroke="currentColor" stroke-width="2"/><rect x="4" y="4" width="11" height="11" rx="2" fill="none" stroke="currentColor" stroke-width="2"/></svg>',
  refresh: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 4v6h-6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><path d="M20 10a8 8 0 1 0 2 5.5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>',
  trash: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 6h18M8 6V4h8v2m-9 0 1 14h8l1-14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
};

function formatTime(seconds) {
  const minutes = String(Math.floor(seconds / 60)).padStart(2, "0");
  const rest = String(seconds % 60).padStart(2, "0");
  return `${minutes}:${rest}`;
}

function formatDuration(totalSeconds) {
  const safe = Number.isFinite(Number(totalSeconds)) ? Math.max(0, Math.floor(Number(totalSeconds))) : 0;
  const h = String(Math.floor(safe / 3600)).padStart(2, "0");
  const m = String(Math.floor((safe % 3600) / 60)).padStart(2, "0");
  const s = String(safe % 60).padStart(2, "0");
  return `${h}:${m}:${s}`;
}

function formatTimestamp(value) {
  if (!value) {
    return "-";
  }
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) {
    return "-";
  }
  return d.toLocaleString();
}

function setLiveState(text) {
  liveState.textContent = text;
}

function setLiveTranscript(text) {
  liveTranscript.textContent = text || "En attente de transcription...";
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

function renderItems(items) {
  itemsContainer.innerHTML = "";
  const visibleItems = items.slice(0, visibleItemsCount);
  visibleItems.forEach((item) => {
    const card = document.createElement("div");
    card.className = "item";
    const when = new Date(item.created_at).toLocaleString();
    const submittedAt = formatTimestamp(item.submitted_at || item.created_at);
    const startedAt = formatTimestamp(item.transcribe_started_at);
    const finishedAt = formatTimestamp(item.transcribe_finished_at);
    const durationLabel = formatDuration(item.audio_duration_seconds || 0);
    const audioUrl = `/audio/${item.id}`;
    const transcriptUrl = `/api/items/${item.id}/transcript.txt`;
    card.innerHTML = `
      <div class="item-head">
        <span>${when}</span>
        <span>${item.id.slice(0, 8)}</span>
      </div>
      <div class="item-meta">
        <span>Soumission: ${submittedAt}</span>
        <span>Debut transcription: ${startedAt}</span>
        <span>Fin transcription: ${finishedAt}</span>
      </div>
      <div class="item-actions">
        <div class="action-group" aria-label="Actions audio">
          <button class="action-btn play-audio" data-id="${item.id}" data-audio="${audioUrl}" title="Lire l'audio" aria-label="Lire l'audio">
            <span class="action-icon">${ICONS.play}</span>
          </button>
          <a class="action-btn download-audio" href="${audioUrl}" download title="Telecharger l'audio" aria-label="Telecharger l'audio">
            <span class="action-icon">${ICONS.download}</span>
          </a>
          <span class="audio-duration" title="Duree audio">${durationLabel}</span>
        </div>
        <div class="action-group" aria-label="Actions transcript">
          <a class="action-btn download-txt" href="${transcriptUrl}" download title="Telecharger le transcript .txt" aria-label="Telecharger le transcript .txt">
            <span class="action-icon">${ICONS.txt}</span>
          </a>
          <button class="action-btn copy-transcript" data-id="${item.id}" title="Copier le transcript" aria-label="Copier le transcript">
            <span class="action-icon">${ICONS.copy}</span>
          </button>
          <button class="action-btn regenerate-transcript" data-id="${item.id}" title="Regenerer le transcript" aria-label="Regenerer le transcript">
            <span class="action-icon">${ICONS.refresh}</span>
          </button>
        </div>
        <div class="action-group delete-group" aria-label="Suppression">
          <button class="action-btn delete delete-btn" data-id="${item.id}" title="Supprimer l'enregistrement" aria-label="Supprimer l'enregistrement">
            <span class="action-icon">${ICONS.trash}</span>
          </button>
        </div>
      </div>
      <audio controls preload="none" data-audio-id="${item.id}" style="display:none;"></audio>
      <div class="transcript transcript-collapsed"></div>
    `;
    const transcriptDiv = card.querySelector(".transcript");
    const transcriptText = item.transcript || "Transcription en cours...";
    transcriptDiv.textContent = transcriptText;
    const isLongTranscript = transcriptText.length > 260;
    if (isLongTranscript) {
      transcriptDiv.classList.add("transcript-clickable");
      transcriptDiv.title = "Cliquer pour voir plus/moins";
      transcriptDiv.dataset.expanded = "false";
    }
    itemsContainer.appendChild(card);
  });

  document.querySelectorAll(".play-audio").forEach((button) => {
    button.addEventListener("click", async (event) => {
      const target = event.currentTarget;
      const itemId = target.dataset.id;
      const audioUrl = target.dataset.audio;
      const audio = itemsContainer.querySelector(`audio[data-audio-id="${itemId}"]`);
      if (!audio) {
        return;
      }
      if (!audio.src) {
        audio.src = audioUrl;
      }
      audio.style.display = "block";
      try {
        await audio.play();
      } catch (err) {
        setLiveState("Impossible de lire l'audio.");
      }
    });
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
        if (!itemsSocket || itemsSocket.readyState !== WebSocket.OPEN) {
          await fetchItems();
          await fetchJobs();
        }
      } else {
        setLiveState("Erreur pendant la suppression.");
      }
    });
  });

  document.querySelectorAll(".copy-transcript").forEach((button) => {
    button.addEventListener("click", async (event) => {
      const id = event.currentTarget.dataset.id;
      const item = itemsState[id];
      const transcript = item?.transcript || "";
      if (!transcript) {
        setLiveState("Transcript vide.");
        return;
      }
      try {
        await navigator.clipboard.writeText(transcript);
        setLiveState("Transcript copie.");
      } catch (err) {
        setLiveState("Impossible de copier.");
      }
    });
  });

  document.querySelectorAll(".regenerate-transcript").forEach((button) => {
    button.addEventListener("click", async (event) => {
      const trigger = event.currentTarget;
      if (!trigger) {
        return;
      }
      const id = trigger.dataset.id;
      trigger.disabled = true;
      setLiveState("Regeneration du transcript en cours...");
      try {
        const response = await fetch(`/api/items/${id}/regenerate`, { method: "POST" });
        if (!response.ok) {
          setLiveState("Erreur regeneration.");
          trigger.disabled = false;
          return;
        }
        if (!itemsSocket || itemsSocket.readyState !== WebSocket.OPEN) {
          await fetchJobs();
        }
        setLiveState("Regeneration lancee.");
      } catch (err) {
        setLiveState("Erreur regeneration.");
      } finally {
        trigger.disabled = false;
      }
    });
  });

  document.querySelectorAll(".transcript-clickable").forEach((node) => {
    node.addEventListener("click", (event) => {
      const transcript = event.currentTarget;
      const expanded = transcript.dataset.expanded === "true";
      transcript.dataset.expanded = expanded ? "false" : "true";
      transcript.classList.toggle("transcript-expanded", !expanded);
      transcript.classList.toggle("transcript-collapsed", expanded);
    });
  });

  if (itemsMoreBtn) {
    const hasMore = items.length > visibleItemsCount;
    itemsMoreBtn.style.display = hasMore ? "inline-block" : "none";
  }
}

function renderJobs(jobs) {
  jobsContainer.innerHTML = "";
  if (!jobs || !jobs.length) {
    jobsContainer.textContent = "Aucune transcription en attente.";
    return;
  }

  jobs.forEach((job) => {
    const node = document.createElement("div");
    node.className = "job";
    const submitted = job.submitted_at ? new Date(job.submitted_at).toLocaleString() : "-";
    const started = job.started_at ? new Date(job.started_at).toLocaleString() : "en attente";
    const errorLine = job.error ? `<div class="job-meta">Erreur: ${job.error}</div>` : "";
    node.innerHTML = `
      <div class="job-head">
        <span>Job ${job.id.slice(0, 8)}</span>
        <span class="status ${job.status}">${job.status}</span>
      </div>
      <div class="job-meta">Lancement: ${submitted}</div>
      <div class="job-meta">Demarrage: ${started}</div>
      ${errorLine}
    `;
    jobsContainer.appendChild(node);
  });
}

function sortItems(items) {
  return [...items].sort((a, b) => (b.created_at || "").localeCompare(a.created_at || ""));
}

function sortJobs(jobs) {
  return [...jobs].sort((a, b) => (a.submitted_at || "").localeCompare(b.submitted_at || ""));
}

function setItemsState(items) {
  itemsState = {};
  items.forEach((item) => {
    itemsState[item.id] = item;
  });
  if (visibleItemsCount < ITEMS_PAGE_SIZE) {
    visibleItemsCount = ITEMS_PAGE_SIZE;
  }
  if (items.length && visibleItemsCount > items.length) {
    visibleItemsCount = items.length;
  }
  if (!items.length) {
    visibleItemsCount = ITEMS_PAGE_SIZE;
  }
  renderItems(sortItems(Object.values(itemsState)));
}

function setJobsState(jobs) {
  jobsState = {};
  jobs.forEach((job) => {
    jobsState[job.id] = job;
  });
  renderJobs(sortJobs(Object.values(jobsState)));
}

function applyOps(ops) {
  ops.forEach((op) => {
    if (op.entity === "item") {
      if (op.action === "upsert" && op.item) {
        itemsState[op.item.id] = op.item;
      }
      if (op.action === "delete" && op.id) {
        delete itemsState[op.id];
      }
      return;
    }
    if (op.entity === "job") {
      if (op.action === "upsert" && op.job) {
        jobsState[op.job.id] = op.job;
      }
      if (op.action === "delete" && op.id) {
        delete jobsState[op.id];
      }
    }
  });
  renderItems(sortItems(Object.values(itemsState)));
  renderJobs(sortJobs(Object.values(jobsState)));
}

async function fetchItems() {
  const response = await fetch("/api/items");
  const items = await response.json();
  setItemsState(items);
}

async function fetchJobs() {
  const response = await fetch("/api/jobs");
  const jobs = await response.json();
  setJobsState(jobs);
}

function openItemsSocket() {
  if (itemsSocket && itemsSocket.readyState === WebSocket.OPEN) {
    return;
  }
  if (itemsSocketRetry) {
    clearTimeout(itemsSocketRetry);
    itemsSocketRetry = null;
  }

  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  itemsSocket = new WebSocket(`${protocol}://${window.location.host}/ws/items`);

  itemsSocket.onmessage = (event) => {
    let payload = null;
    try {
      payload = JSON.parse(event.data);
    } catch (err) {
      return;
    }
    if (payload.type === "init") {
      if (Array.isArray(payload.items)) {
        setItemsState(payload.items);
      }
      if (Array.isArray(payload.jobs)) {
        setJobsState(payload.jobs);
      }
      return;
    }
    if (payload.type === "ops" && Array.isArray(payload.ops)) {
      applyOps(payload.ops);
    }
  };

  itemsSocket.onclose = () => {
    itemsSocketRetry = setTimeout(() => {
      openItemsSocket();
    }, 2000);
  };

  itemsSocket.onerror = () => {
    if (!itemsSocket || itemsSocket.readyState === WebSocket.OPEN) {
      return;
    }
    fetchItems().catch(() => {});
    fetchJobs().catch(() => {});
  };
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
  const data = await response.json();
  if (response.status === 202 && data.status === "processing") {
    setLiveState("Upload termine. Transcription en cours...");
    await fetchJobs();
  } else {
    setLiveState("Transcription terminee.");
  }
  if (!itemsSocket || itemsSocket.readyState !== WebSocket.OPEN) {
    await fetchItems();
    await fetchJobs();
  }
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

function setBusy(state) {
  busy = state;
  startBtn.disabled = state;
  uploadBtn.disabled = state;
  fileInput.disabled = state;
  stopBtn.disabled = !state;
}

async function startRecording() {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  chunks = [];
  setLiveTranscript("");
  mediaRecorder = new MediaRecorder(stream);
  mediaRecorder.ondataavailable = (event) => {
    if (event.data.size > 0) {
      chunks.push(event.data);
    }
  };
  mediaRecorder.onstop = async () => {
    const blob = new Blob(chunks, { type: "audio/webm" });
    setLiveState("Upload en cours...");
    await uploadBlob(blob);
    setBusy(false);
    setLiveState("Pret.");
  };
  mediaRecorder.start(500);
  setBusy(true);
  setLiveState("Transmission en cours...");
  startTimer();
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    mediaRecorder.stop();
    mediaRecorder.stream.getTracks().forEach((track) => track.stop());
  }
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

if (itemsMoreBtn) {
  itemsMoreBtn.addEventListener("click", () => {
    visibleItemsCount += ITEMS_PAGE_SIZE;
    renderItems(sortItems(Object.values(itemsState)));
  });
}

checkHealth();
fetchItems();
fetchJobs();
openItemsSocket();
