// Lecteur de parcours vidéo — lit la file déposée par le catalogue (localStorage)
const QUEUE_KEY = "oplit_player_queue";
let queue = [];
try { queue = JSON.parse(localStorage.getItem(QUEUE_KEY) || "[]"); } catch (e) {}

const $ = (s) => document.querySelector(s);
const video = $("#video");
let idx = 0;

if (!queue.length) {
  $("#stageTitle").textContent = "Aucune vidéo dans le parcours";
  $("#playlist").innerHTML =
    `<p style="color:var(--ink-soft);font-size:13.5px;padding:8px 2px">Revenez au catalogue et sélectionnez des articles disposant d'une vidéo (📦 Stock).</p>`;
  $("#prevBtn").disabled = $("#nextBtn").disabled = true;
} else {
  renderPlaylist();
  load(0);
}

function renderPlaylist() {
  $("#plCount").textContent = `${queue.length} vidéo${queue.length > 1 ? "s" : ""}`;
  const wrap = $("#playlist");
  wrap.innerHTML = "";
  queue.forEach((q, i) => {
    const row = document.createElement("button");
    row.className = "pl-row";
    row.dataset.i = i;
    row.innerHTML = `
      <span class="pl-num">${i + 1}</span>
      <span class="pl-thumb"><svg viewBox="0 0 24 24" width="16" height="16"><path d="M8 5v14l11-7z" fill="currentColor"/></svg></span>
      <span class="pl-info">
        <span class="pl-row-title">${q.title}</span>
        <span class="pl-row-sub">${q.cat || ""}${q.section ? " · " + q.section : ""}</span>
      </span>`;
    row.onclick = () => load(i);
    wrap.appendChild(row);
  });
}

// Encode un chemin (avec dossiers) en URL servie par http.server
const encPath = (p) => p.split("/").map(encodeURIComponent).join("/");

function load(i) {
  if (i < 0 || i >= queue.length) return;
  idx = i;
  const q = queue[i];
  video.src = encPath(q.video);
  video.play().catch(() => {});
  $("#stageTitle").textContent = q.title;
  $("#stageCat").textContent = `${q.cat || ""}${q.section ? "  ·  " + q.section : ""}`;
  $("#stagePos").textContent = `${i + 1} / ${queue.length}`;
  $("#prevBtn").disabled = i === 0;
  $("#nextBtn").disabled = i === queue.length - 1;
  $("#pdfBtn").style.display = q.pdf ? "" : "none";
  document.querySelectorAll(".pl-row").forEach((r) =>
    r.classList.toggle("active", Number(r.dataset.i) === i)
  );
}

$("#prevBtn").onclick = () => load(idx - 1);
$("#nextBtn").onclick = () => load(idx + 1);
// Enchaînement automatique
video.addEventListener("ended", () => { if (idx < queue.length - 1) load(idx + 1); });

// ---- Visionneuse PDF ----
const pdfOverlay = $("#pdfOverlay");
function openPdf() {
  const q = queue[idx];
  if (!q || !q.pdf) return;
  const url = encPath(q.pdf);
  $("#pdfTitle").textContent = q.title;
  $("#pdfFrame").src = url;
  $("#pdfOpen").href = url;
  pdfOverlay.classList.add("show");
}
function closePdf() {
  pdfOverlay.classList.remove("show");
  $("#pdfFrame").src = "";
}
$("#pdfBtn").onclick = openPdf;
$("#pdfClose").onclick = closePdf;
pdfOverlay.onclick = (e) => { if (e.target === pdfOverlay) closePdf(); };
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closePdf(); });
