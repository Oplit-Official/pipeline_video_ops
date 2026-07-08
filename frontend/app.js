// ---- État ----
const CATALOG = window.CATALOG;
let activeCat = CATALOG[0].id;
let searchQ = "";
const selected = new Map(); // exId -> exercise (+catName)

const STORE = "oplit_ops_parcours";
try {
  const saved = JSON.parse(localStorage.getItem(STORE) || "[]");
  saved.forEach((id) => {
    for (const c of CATALOG) {
      const ex = c.exercises.find((e) => e.id === id);
      if (ex) selected.set(id, { ...ex, catName: c.name, catIcon: c.icon });
    }
  });
} catch (e) {}

// ---- Helpers ----
const $ = (s) => document.querySelector(s);
const catById = (id) => CATALOG.find((c) => c.id === id);
// Encode un chemin (avec sous-dossiers) en URL servie par le serveur
const encPath = (p) => p.split("/").map(encodeURIComponent).join("/");
// URL média : absolue (Supabase) telle quelle, sinon chemin local encodé
const mediaURL = (p) => (/^https?:\/\//.test(p || "") ? p : encPath(p));
const fmtTime = (m) => (m >= 60 ? `${Math.floor(m / 60)}h${String(m % 60).padStart(2, "0")}` : `${m}`);
const fmtDur = (s) => `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, "0")}`;  // mm:ss

function persist() {
  localStorage.setItem(STORE, JSON.stringify([...selected.keys()]));
}

// ---- Rendu nav catégories ----
function renderNav() {
  const nav = $("#catNav");
  nav.innerHTML = "";
  CATALOG.forEach((c) => {
    const selCount = c.exercises.filter((e) => selected.has(e.id)).length;
    const btn = document.createElement("button");
    btn.className = "cat-item" + (c.id === activeCat ? " active" : "");
    btn.innerHTML = `
      <span class="ci-icon">${c.icon}</span>
      <span class="ci-name">${c.name}</span>
      <span class="ci-count">${selCount ? selCount + "/" : ""}${c.exercises.length}</span>`;
    btn.onclick = () => { activeCat = c.id; render(); };
    nav.appendChild(btn);
  });
}

// ---- Rendu grille d'articles (groupés par section) ----
function makeCard(e, cat) {
  const isSel = selected.has(e.id);
  const hasVideo = !!e.video;
  const card = document.createElement("div");
  card.className = "card" + (isSel ? " selected" : "");
  card.innerHTML = `
    <div class="card-top">
      <h3>${e.title}</h3>
      <div class="checkbox">
        <svg viewBox="0 0 24 24" width="14" height="14"><path d="M5 13l4 4L19 7" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg>
      </div>
    </div>
    <div class="card-meta">
      <span class="badge time">
        <svg viewBox="0 0 24 24" width="12" height="12"><circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="2"/><path d="M12 7v5l3 2" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
        ${e.dur ? fmtDur(e.dur) + " de vidéo" : e.min + " min de lecture"}
      </span>
      ${hasVideo ? `<button class="badge video-badge" title="Lire la vidéo">
        <svg viewBox="0 0 24 24" width="12" height="12"><path d="M8 5v14l11-7z" fill="currentColor"/></svg>
        Vidéo
      </button>` : ""}
      <button class="card-manage" title="Gérer (renommer, catégorie, supprimer)">⋯</button>
    </div>`;
  card.onclick = () => toggle(e, cat);
  if (hasVideo) {
    card.querySelector(".video-badge").onclick = (ev) => {
      ev.stopPropagation();
      window.open(mediaURL(e.video), "_blank");
    };
  }
  card.querySelector(".card-manage").onclick = (ev) => { ev.stopPropagation(); openManage(e, cat); };
  return card;
}

function renderGrid() {
  const cat = catById(activeCat);
  $("#catTitle").textContent = `${cat.icon}  ${cat.name}`;
  $("#catDesc").textContent = cat.desc;

  const grid = $("#exerciseGrid");
  grid.innerHTML = "";

  const list = cat.exercises.filter((e) =>
    !searchQ || (e.title + " " + e.section).toLowerCase().includes(searchQ)
  );

  if (!list.length) {
    grid.innerHTML = `<p style="color:var(--ink-soft);grid-column:1/-1;padding:30px 4px">Aucun article ne correspond à la recherche.</p>`;
    return;
  }

  // Regroupement par section, dans l'ordre d'apparition
  const sections = [];
  const bySection = new Map();
  list.forEach((e) => {
    const key = e.section || "Général";
    if (!bySection.has(key)) { bySection.set(key, []); sections.push(key); }
    bySection.get(key).push(e);
  });

  sections.forEach((sec) => {
    const items = bySection.get(sec);
    const allSel = items.every((e) => selected.has(e.id));
    const head = document.createElement("div");
    head.className = "sec-head";
    head.innerHTML = `
      <span class="sec-title">${sec}</span>
      <span class="sec-meta">${items.length} article${items.length > 1 ? "s" : ""}</span>
      <button class="sec-toggle">${allSel ? "Tout retirer" : "Tout sélectionner"}</button>`;
    head.querySelector(".sec-toggle").onclick = () => {
      items.forEach((e) => {
        if (allSel) selected.delete(e.id);
        else selected.set(e.id, { ...e, catName: cat.name, catIcon: cat.icon });
      });
      persist();
      render();
    };
    grid.appendChild(head);
    items.forEach((e) => grid.appendChild(makeCard(e, cat)));
  });
}

// ---- Rendu panneau sélection ----
function renderPanel() {
  const count = selected.size;
  const total = [...selected.values()].reduce((s, e) => s + e.min, 0);
  $("#statCount").textContent = count;
  $("#statTime").innerHTML = `${fmtTime(total)}<small>${total >= 60 ? "" : "min"}</small>`;

  const list = $("#panelList");
  $("#generateBtn").disabled = count === 0;

  if (!count) {
    list.innerHTML = `<div class="panel-empty"><div class="empty-ill">🎯</div><p>Aucun article sélectionné.<br/>Cliquez sur les cartes pour composer le parcours.</p></div>`;
    return;
  }

  list.innerHTML = "";
  [...selected.values()].forEach((e) => {
    const row = document.createElement("div");
    row.className = "pl-item";
    row.innerHTML = `
      <span class="pl-icon">${e.catIcon}</span>
      <div class="pl-body">
        <div class="pl-title">${e.title}</div>
        <div class="pl-sub">${e.catName} · ${e.dur ? fmtDur(e.dur) : e.min + " min"}</div>
      </div>
      <button class="pl-remove" title="Retirer">×</button>`;
    row.querySelector(".pl-remove").onclick = () => { selected.delete(e.id); persist(); render(); };
    list.appendChild(row);
  });
}

function render() {
  renderNav();
  renderGrid();
  renderPanel();
}

// ---- Actions ----
function toggle(ex, cat) {
  if (selected.has(ex.id)) selected.delete(ex.id);
  else selected.set(ex.id, { ...ex, catName: cat.name, catIcon: cat.icon });
  persist();
  render();
}

function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(t._t);
  t._t = setTimeout(() => t.classList.remove("show"), 3200);
}

$("#clearBtn").onclick = () => { selected.clear(); persist(); render(); };

$("#searchInput").oninput = (e) => { searchQ = e.target.value.toLowerCase().trim(); renderGrid(); };

// ---- Clients (persistés) ----
const CLI_STORE = "oplit_ops_clients";
let clients;
try {
  clients = JSON.parse(localStorage.getItem(CLI_STORE) || "null") || [...window.CLIENTS_SEED];
} catch (e) { clients = [...window.CLIENTS_SEED]; }
const persistClients = () => localStorage.setItem(CLI_STORE, JSON.stringify(clients));

function renderClients() {
  const sel = $("#clientSelect");
  sel.innerHTML = "";
  clients.forEach((c) => {
    const o = document.createElement("option");
    o.value = c.id;
    o.textContent = c.name;
    sel.appendChild(o);
  });
  updateClientEmail();
}
function currentClient() {
  return clients.find((c) => c.id === $("#clientSelect").value) || clients[0];
}
function updateClientEmail() {
  const c = currentClient();
  $("#clientEmail").textContent = c ? `✉  ${c.email}` : "";
}

// ---- Construction du parcours ----
function buildParcours() {
  const items = [...selected.values()];
  const total = items.reduce((s, e) => s + e.min, 0);
  return {
    items,
    total,
    data: {
      genere_le: new Date().toISOString(),
      nb_articles: items.length,
      duree_min: total,
      articles: items.map((e, i) => ({
        ordre: i + 1, id: e.id, titre: e.title, categorie: e.catName,
        section: e.section || "", duree_min: e.min,
      })),
    },
  };
}

// ---- Modale ----
const modal = $("#modal");
function openModal() {
  if (!selected.size) return;
  const { items, total } = buildParcours();
  $("#modalSub").textContent = `${items.length} articles · ${fmtTime(total)} min`;
  renderClients();
  showView("compose");
  modal.classList.add("show");
}
function closeModal() {
  modal.classList.remove("show");
  $("#addClientForm").hidden = true;
}

$("#generateBtn").onclick = openPdfBuilder;
$("#modalClose").onclick = closeModal;
modal.onclick = (e) => { if (e.target === modal) closeModal(); };
$("#clientSelect").onchange = updateClientEmail;

// Ajout d'un client
$("#addClientToggle").onclick = () => {
  const f = $("#addClientForm");
  f.hidden = !f.hidden;
  if (!f.hidden) $("#newClientName").focus();
};
$("#cancelClient").onclick = () => { $("#addClientForm").hidden = true; };
$("#saveClient").onclick = () => {
  const name = $("#newClientName").value.trim();
  const email = $("#newClientEmail").value.trim();
  if (!name || !email) { toast("⚠️  Renseignez un nom et un email."); return; }
  const id = "c" + Date.now();
  clients.push({ id, name, email });
  persistClients();
  $("#newClientName").value = "";
  $("#newClientEmail").value = "";
  $("#addClientForm").hidden = true;
  renderClients();
  $("#clientSelect").value = id;
  updateClientEmail();
  toast(`✅ Client « ${name} » ajouté.`);
};

// Téléchargement local (JSON)
$("#downloadBtn").onclick = () => {
  const { items, data } = buildParcours();
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `parcours_ops_${items.length}articles.json`;
  a.click();
  URL.revokeObjectURL(url);
  toast(`💾 Parcours téléchargé (${items.length} articles).`);
  closeModal();
};

// Message court hardcodé, personnalisé selon le nom du client
function buildMessage(clientName) {
  const prenom = clientName.split(/[\s—-]/)[0]; // 1er mot du nom client
  return (
    `Bonjour l'équipe ${prenom},\n\n` +
    `Suite à nos échanges, voici le parcours de formation Oplit que nous avons préparé ` +
    `spécialement pour ${clientName}.\n\n` +
    `Vous trouverez ci-dessous la liste des articles sélectionnés, à suivre dans l'ordre indiqué. ` +
    `N'hésitez pas à revenir vers nous pour toute question.\n\n` +
    `Bonne formation,\nL'équipe Ops Oplit`
  );
}

// Vues de la modale
function showView(name) {
  $("#viewCompose").hidden = name !== "compose";
  $("#viewPreview").hidden = name !== "preview";
}

// Étape 1 → aperçu
$("#sendBtn").onclick = () => {
  const c = currentClient();
  if (!c) { toast("⚠️  Sélectionnez un client."); return; }
  $("#previewTo").textContent = `${c.name} · ${c.email}`;
  $("#previewBody").value = buildMessage(c.name);
  showView("preview");
};

$("#backBtn").onclick = () => showView("compose");

// Étape 2 → envoi via client mail (message d'intro + liste des articles)
$("#confirmSendBtn").onclick = () => {
  const c = currentClient();
  const { items, total } = buildParcours();
  const subject = `Votre parcours de formation Oplit — ${items.length} articles`;
  const intro = $("#previewBody").value;
  const lines = items.map((e, i) => `${i + 1}. ${e.title}  [${e.catName}${e.section ? " · " + e.section : ""}]`);
  const body =
    intro +
    `\n\n— — —\nParcours (${items.length} articles · ${fmtTime(total)} min) :\n\n` +
    lines.join("\n");
  window.location.href =
    `mailto:${encodeURIComponent(c.email)}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
  toast(`📧 Email préparé pour ${c.name}.`);
  closeModal();
};

// ---- Landing / navigation accueil <-> catalogue ----
const landing = $("#landing");
$("#enterBtn").onclick = () => landing.classList.add("hidden");
// Retour à l'accueil en cliquant sur le logo de la sidebar
const brand = document.querySelector(".sidebar .brand");
brand.style.cursor = "pointer";
brand.title = "Retour à l'accueil";
brand.onclick = () => landing.classList.remove("hidden");

render();

// ====== Builder Parcours PDF ======
const pdfModal = $("#pdfModal");
let pbOrder = []; // ordre courant des articles dans le PDF

function openPdfBuilder() {
  if (!selected.size) return;
  pbOrder = [...selected.values()];
  // préremplissage des champs
  const cats = [...new Set(pbOrder.map((e) => e.catName))];
  const secs = [...new Set(pbOrder.map((e) => e.section).filter(Boolean))];
  $("#pbTitle").value = cats.length === 1 ? `Parcours — ${cats[0]}` : "Parcours de formation Oplit";
  $("#pbSubtitle").value = (secs.length ? secs : cats).join(" · ");
  $("#pbIntro").value = "Bienvenue dans ce parcours de formation Oplit. Suivez les articles dans l'ordre proposé pour monter en compétence pas à pas.";
  $("#pbObjectives").value = "";   // pas de doublon : la liste des vidéos (avec liens) suffit
  $("#pbConclTitle").value = "Conclusion";
  $("#pbConclText").value = "Félicitations, vous avez terminé ce parcours ! N'hésitez pas à revenir vers l'équipe Oplit pour toute question. À très bientôt !";
  renderPbList();
  pdfModal.classList.add("show");
}
function closePdfBuilder() { pdfModal.classList.remove("show"); }

function renderPbList() {
  $("#pdfModalSub").textContent = `${pbOrder.length} article${pbOrder.length > 1 ? "s" : ""} · intro + conclusion générées`;
  const list = $("#pbList");
  list.innerHTML = "";
  pbOrder.forEach((e, i) => {
    const li = document.createElement("li");
    li.className = "pb-item";
    li.draggable = true;
    li.dataset.i = i;
    li.innerHTML = `
      <span class="pb-grip">⠿</span>
      <span class="pb-pos">${i + 1}</span>
      <span class="pb-info">
        <span class="pb-title">${e.title}</span>
        <span class="pb-sub">${e.catName}${e.section ? " · " + e.section : ""}${e.video ? "  · 🎬" : ""}</span>
      </span>
      <button class="pb-remove" title="Retirer">×</button>`;
    li.querySelector(".pb-remove").onclick = () => {
      pbOrder.splice(i, 1);
      if (!pbOrder.length) { closePdfBuilder(); return; }
      renderPbList();
    };
    list.appendChild(li);
  });

  // note vidéos
  const vids = pbOrder.filter((e) => e.video);
  const note = $("#pbVideoNote");
  if (vids.length) {
    note.hidden = false;
    note.innerHTML = `🎬 ${vids.length} article${vids.length > 1 ? "s" : ""} avec vidéo — les vidéos ne sont pas incluses dans le PDF. <button class="link-btn" id="pbOpenPlayer">Ouvrir le lecteur vidéo</button>`;
    note.querySelector("#pbOpenPlayer").onclick = () => {
      const q = vids.map((e) => ({ title: e.title, video: e.video, pdf: e.pdf || "", cat: e.catName, section: e.section || "" }));
      localStorage.setItem("oplit_player_queue", JSON.stringify(q));
      window.location.href = "player.html";
    };
  } else {
    note.hidden = true;
  }
}

// Drag & drop (réordonnancement)
let dragFrom = null;
$("#pbList").addEventListener("dragstart", (e) => {
  const li = e.target.closest(".pb-item");
  if (!li) return;
  dragFrom = Number(li.dataset.i);
  li.classList.add("dragging");
});
$("#pbList").addEventListener("dragend", (e) => {
  const li = e.target.closest(".pb-item");
  if (li) li.classList.remove("dragging");
});
$("#pbList").addEventListener("dragover", (e) => {
  e.preventDefault();
  const li = e.target.closest(".pb-item");
  document.querySelectorAll(".pb-item.over").forEach((x) => x.classList.remove("over"));
  if (li) li.classList.add("over");
});
$("#pbList").addEventListener("drop", (e) => {
  e.preventDefault();
  const li = e.target.closest(".pb-item");
  if (li == null || dragFrom == null) return;
  const to = Number(li.dataset.i);
  if (to === dragFrom) return;
  const [moved] = pbOrder.splice(dragFrom, 1);
  pbOrder.splice(to, 0, moved);
  dragFrom = null;
  renderPbList();
});

$("#pdfModalClose").onclick = closePdfBuilder;
pdfModal.onclick = (e) => { if (e.target === pdfModal) closePdfBuilder(); };
$("#pbEmailBtn").onclick = () => { closePdfBuilder(); openModal(); };

// Génération du PDF (POST backend)
$("#pbGenerateBtn").onclick = async () => {
  const btn = $("#pbGenerateBtn");
  const cfg = {
    title: $("#pbTitle").value.trim() || "Parcours de formation Oplit",
    subtitle: $("#pbSubtitle").value.trim(),
    intro_text: $("#pbIntro").value.trim(),
    objectives: $("#pbObjectives").value.split("\n").map((s) => s.trim()).filter(Boolean),
    conclusion_title: $("#pbConclTitle").value.trim() || "Conclusion",
    conclusion_text: $("#pbConclText").value.trim(),
    articles: pbOrder.map((e) => e.pdf).filter(Boolean),
    video_links: pbOrder.filter((e) => e.drive).map((e) => ({ titre: e.title, url: e.drive })),
  };
  if (!cfg.articles.length) { toast("⚠️  Aucun PDF d'article dans la sélection."); return; }

  btn.disabled = true;
  const label = btn.innerHTML;
  btn.innerHTML = "Génération…";
  try {
    const res = await fetch("/api/parcours-pdf", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(cfg),
    });
    if (!res.ok) {
      let msg = "Erreur serveur.";
      try { msg = (await res.json()).error || msg; } catch (e) {}
      throw new Error(msg);
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = cfg.title + ".pdf";
    a.click();
    URL.revokeObjectURL(url);
    toast(`📄 PDF généré — ${cfg.articles.length} articles + intro + conclusion.`);
    closePdfBuilder();
  } catch (err) {
    toast("⚠️  " + err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = label;
  }
};

// ====== Import d'exercice (PDF -> vidéo) ======
const importModal = $("#importModal");
let importFileData = null; // base64

// ---- Catégories personnalisées (persistées) ----
const CAT_STORE = "oplit_custom_cats";
let customCats = [];
try { customCats = JSON.parse(localStorage.getItem(CAT_STORE) || "[]"); } catch (e) {}
const persistCats = () => localStorage.setItem(CAT_STORE, JSON.stringify(customCats));
function mergeCustomCats() {
  customCats.forEach((cc) => {
    if (!CATALOG.some((c) => c.name === cc.name))
      CATALOG.push({ id: cc.id, name: cc.name, icon: cc.icon || "📁",
                     desc: "Catégorie personnalisée.", exercises: [] });
  });
}
function renderCatSelect(selectName) {
  const sel = $("#importCategory");
  const prev = selectName || sel.value;
  sel.innerHTML = "";
  CATALOG.forEach((c) => {
    const o = document.createElement("option");
    o.value = c.name;
    o.textContent = `${c.icon}  ${c.name}`;
    sel.appendChild(o);
  });
  if (prev && CATALOG.some((c) => c.name === prev)) sel.value = prev;
}

function openImport() {
  importFileData = null;
  $("#importFileName").textContent = "Aucun fichier sélectionné";
  $("#importTitle").value = "";
  $("#importSection").value = "";
  $("#catForm").hidden = true;
  renderCatSelect("Mes imports");
  $("#importForm").hidden = false;
  $("#importProgress").hidden = true;
  importModal.classList.add("show");
  refreshEleven();
}

async function refreshEleven() {
  const box = $("#elevenBox"), val = $("#elevenVal");
  box.className = "eleven-box";
  val.textContent = "…";
  let c;
  try { c = await (await fetch("/api/eleven-credits")).json(); }
  catch (e) { c = { ok: false, reason: "offline" }; }
  if (c.ok && c.remaining != null) {
    val.textContent = `${c.remaining.toLocaleString("fr-FR")} crédits · ~${c.minutes} min de vidéo`;
    if (c.minutes != null && c.minutes < 5) box.classList.add("low");   // alerte solde bas
  } else if (c.reason === "missing_permission") {
    box.classList.add("warn");
    val.textContent = "Solde indisponible — activez la permission « user_read » sur la clé.";
  } else if (c.reason === "no_key") {
    box.classList.add("warn");
    val.textContent = "Aucune clé ElevenLabs configurée.";
  } else {
    box.classList.add("warn");
    val.textContent = "Solde indisponible.";
  }
}
function closeImport() { importModal.classList.remove("show"); }

$("#importBtn").onclick = openImport;
$("#importClose").onclick = closeImport;
importModal.onclick = (e) => { if (e.target === importModal) closeImport(); };
$("#importPick").onclick = () => $("#importFile").click();
$("#importDrop").onclick = (e) => { if (e.target.id !== "importPick") $("#importFile").click(); };

$("#importFile").onchange = (e) => {
  const f = e.target.files[0];
  if (!f) return;
  $("#importFileName").textContent = f.name;
  if (!$("#importTitle").value.trim())
    $("#importTitle").value = f.name.replace(/\.pdf$/i, "").replace(/_/g, " ");
  const r = new FileReader();
  r.onload = () => { importFileData = r.result; };
  r.readAsDataURL(f);
};

function setStep(active, pct) {
  const order = ["reading", "extract", "spec", "render", "done"];
  const ai = order.indexOf(active);
  document.querySelectorAll("#importSteps li").forEach((li) => {
    const i = order.indexOf(li.dataset.step);
    li.classList.toggle("done", i < ai);
    li.classList.toggle("active", i === ai);
  });
  if (pct != null) $("#importBar").style.width = Math.max(4, pct) + "%";
}

let importPoll = null;
$("#importLaunch").onclick = async () => {
  const title = $("#importTitle").value.trim();
  if (!importFileData) { toast("⚠️  Choisissez un PDF."); return; }
  if (!title) { toast("⚠️  Donnez un titre."); return; }
  const section = $("#importSection").value.trim();
  const category = $("#importCategory").value || "Mes imports";
  const catObj = CATALOG.find((c) => c.name === category);
  const category_icon = catObj ? catObj.icon : "📥";

  $("#importForm").hidden = true;
  $("#importProgress").hidden = false;
  setStep("reading", 6);
  $("#importHint").textContent = "";

  let job;
  try {
    const res = await fetch("/api/import-exercise", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, section, category, category_icon,
                             live: $("#importLive").checked && !$("#importLive").disabled,
                             pdf_base64: importFileData }),
    });
    const j = await res.json();
    if (!res.ok) throw new Error(j.error || "Erreur serveur.");
    job = j.job;
  } catch (err) {
    toast("⚠️  " + err.message); closeImport(); return;
  }

  importPoll = setInterval(async () => {
    let st;
    try { st = await (await fetch("/api/import-status?job=" + job)).json(); }
    catch (e) { return; }
    if (st.phase === "error") {
      clearInterval(importPoll);
      $("#importHint").textContent = "❌ " + (st.error || "Échec de la génération.");
      $("#importProgSub").textContent = "La génération a échoué.";
      toast("⚠️  Import échoué.");
      return;
    }
    setStep(st.phase === "queued" ? "reading" : st.phase, st.pct);
    $("#importHint").textContent = st.label || "";
    if (st.shots) $("#importHint").textContent += `  ·  ${st.shots} capture(s)`;
    if (st.phase === "done") {
      clearInterval(importPoll);
      setStep("done", 100);
      if (st.article) addImported(st.article);
      const n = st.shots, t = st.targets;
      const detail = (n != null && t != null)
        ? `🎯 ${t}/${n} étapes avec curseur ciblé · ${n - t} sans curseur`
        : "";
      $("#importHint").textContent = detail;
      toast(`✅ Vidéo générée${detail ? " · " + detail : " et ajoutée au catalogue"}`);
      setTimeout(closeImport, 2600);
    }
  }, 2000);
};

// Ajoute un article importé au catalogue, dans la catégorie choisie
function addImported(article) {
  const name = article.category || "Mes imports";
  let cat = CATALOG.find((c) => c.name === name);
  if (!cat) {
    cat = { id: "imp-cat-" + name.replace(/\W+/g, ""), name, icon: article.icon || "📥",
            desc: "Exercices importés et générés depuis vos PDF.", exercises: [] };
    CATALOG.push(cat);
  }
  if (!cat.exercises.some((e) => e.id === article.id)) cat.exercises.push(article);
  render();
}

// ---- Ajout / renommage de catégorie ----
let catFormMode = "add";
$("#catAddToggle").onclick = () => {
  catFormMode = "add";
  $("#catEmoji").value = ""; $("#catName").value = "";
  $("#catForm").hidden = false;
  $("#catName").focus();
};
$("#catEditToggle").onclick = () => {
  const name = $("#importCategory").value;
  const cc = customCats.find((c) => c.name === name);
  if (!cc) { toast("✏️  Seules les catégories ajoutées sont modifiables."); return; }
  catFormMode = "edit";
  $("#catEmoji").value = cc.icon || ""; $("#catName").value = cc.name;
  $("#catForm").dataset.old = cc.name;
  $("#catForm").hidden = false;
  $("#catName").focus();
};
$("#catCancel").onclick = () => { $("#catForm").hidden = true; };
$("#catSave").onclick = async () => {
  const name = $("#catName").value.trim();
  const icon = ($("#catEmoji").value.trim() || "📁");
  if (!name) { toast("⚠️  Donnez un nom de catégorie."); return; }
  if (catFormMode === "add") {
    if (CATALOG.some((c) => c.name === name)) { toast("⚠️  Cette catégorie existe déjà."); return; }
    customCats.push({ id: "cat-" + Date.now(), name, icon });
    persistCats(); mergeCustomCats();
  } else {
    const old = $("#catForm").dataset.old;
    const cc = customCats.find((c) => c.name === old);
    const cat = CATALOG.find((c) => c.name === old);
    if (cc) { cc.name = name; cc.icon = icon; }
    if (cat) { cat.name = name; cat.icon = icon; }
    persistCats();
    try {  // persiste le renommage sur les imports déjà générés
      await fetch("/api/rename-category", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ old, new: name, icon }),
      });
    } catch (e) {}
  }
  $("#catForm").hidden = true;
  renderCatSelect(name);
  render();
  toast(catFormMode === "add" ? "✅ Catégorie ajoutée." : "✅ Catégorie renommée.");
};

// Au chargement : catégories perso + imports déjà générés
mergeCustomCats();
render();
(async () => {
  try {
    const items = await (await fetch("/api/imports")).json();
    items.forEach(addImported);
  } catch (e) {}
})();

// ====== Gérer une vidéo (renommer / catégorie / supprimer) ======
const OVR_STORE = "oplit_overrides";   // surcharges pour articles du catalogue de base
let overrides = {};
try { overrides = JSON.parse(localStorage.getItem(OVR_STORE) || "{}"); } catch (e) {}
const persistOverrides = () => localStorage.setItem(OVR_STORE, JSON.stringify(overrides));

// Applique les surcharges (renommage / recatégorisation / masquage) au chargement
function applyOverrides() {
  Object.entries(overrides).forEach(([id, o]) => {
    let art, from;
    for (const c of CATALOG) { const a = c.exercises.find((e) => e.id === id); if (a) { art = a; from = c; break; } }
    if (!art) return;
    if (o.hidden) { from.exercises = from.exercises.filter((e) => e.id !== id); return; }
    if (o.title) art.title = o.title;
    if (o.section !== undefined) art.section = o.section;
    if (o.category && o.category !== from.name) {
      from.exercises = from.exercises.filter((e) => e.id !== id);
      let tc = CATALOG.find((c) => c.name === o.category);
      if (!tc) { tc = { id: "ovr-" + Date.now(), name: o.category, icon: o.icon || "📁", desc: "", exercises: [] }; CATALOG.push(tc); }
      tc.exercises.push(art);
    }
  });
}

const manageModal = $("#manageModal");
let manageRef = null; // {article, cat}

// Liste des sous-catégories (sections) existantes d'une catégorie
function sectionsOf(catName) {
  const c = CATALOG.find((x) => x.name === catName);
  if (!c) return [];
  return [...new Set(c.exercises.map((e) => e.section).filter(Boolean))];
}
function fillSectionSelect(catName, current) {
  const sel = $("#manageSection");
  sel.innerHTML = "";
  const list = sectionsOf(catName);
  if (current && !list.includes(current)) list.unshift(current);
  const opts = [["", "(Aucune)"], ...list.map((s) => [s, s]), ["__new__", "➕ Nouvelle sous-catégorie…"]];
  opts.forEach(([v, t]) => {
    const o = document.createElement("option");
    o.value = v; o.textContent = t;
    sel.appendChild(o);
  });
  sel.value = current || "";
  $("#manageSectionNew").hidden = true;
  $("#manageSectionNew").value = "";
}

function openManage(article, cat) {
  manageRef = { article, cat };
  $("#manageSub").textContent = (cat.icon || "") + "  " + cat.name;
  $("#manageTitle").value = article.title;
  const sel = $("#manageCategory");
  sel.innerHTML = "";
  CATALOG.forEach((c) => {
    const o = document.createElement("option");
    o.value = c.name; o.textContent = `${c.icon}  ${c.name}`;
    sel.appendChild(o);
  });
  sel.value = cat.name;
  fillSectionSelect(cat.name, article.section || "");
  sel.onchange = () => fillSectionSelect(sel.value, "");
  $("#manageSection").onchange = (e) => {
    const isNew = e.target.value === "__new__";
    $("#manageSectionNew").hidden = !isNew;
    if (isNew) $("#manageSectionNew").focus();
  };
  manageModal.classList.add("show");
}
function closeManage() { manageModal.classList.remove("show"); manageRef = null; }
$("#manageClose").onclick = closeManage;
manageModal.onclick = (e) => { if (e.target === manageModal) closeManage(); };

const isImported = (a) => (a.id || "").startsWith("imp-");
const currentCatOf = (a) => CATALOG.find((c) => c.exercises.some((e) => e.id === a.id));

// ---- Pile d'annulation (undo) ----
const undoStack = [];
function pushUndo(label, fn) {
  undoStack.push({ label, fn });
  if (undoStack.length > 30) undoStack.shift();
  refreshUndo();
}
function refreshUndo() {
  const b = $("#undoBtn");
  b.disabled = undoStack.length === 0;
  b.title = undoStack.length ? "Annuler : " + undoStack[undoStack.length - 1].label : "Rien à annuler";
}
$("#undoBtn").onclick = async () => {
  const a = undoStack.pop();
  if (!a) return;
  refreshUndo();
  try { await a.fn(); toast("↩  Annulé : " + a.label); }
  catch (e) { toast("⚠️  Annulation impossible."); }
};

// Persiste + applique un état (titre/section/catégorie) d'un article
async function applyArticleState(article, state) {
  if (isImported(article)) {
    await fetch("/api/update-import", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: article.id, title: state.title, category: state.category,
                             icon: state.icon, section: state.section || " " }),
    });
  } else {
    overrides[article.id] = { ...(overrides[article.id] || {}), title: state.title,
                              category: state.category, icon: state.icon, section: state.section };
    persistOverrides();
  }
  const from = currentCatOf(article);
  const target = CATALOG.find((c) => c.name === state.category) || from;
  article.title = state.title;
  article.section = state.section;
  if (target && from && target !== from) {
    from.exercises = from.exercises.filter((e) => e.id !== article.id);
    article.category = state.category; article.icon = state.icon;
    target.exercises.push(article);
  }
  render();
}

$("#manageSave").onclick = async () => {
  const { article, cat } = manageRef;
  let newSection = $("#manageSection").value;
  if (newSection === "__new__") newSection = $("#manageSectionNew").value.trim();
  const newCatName = $("#manageCategory").value;
  const newCat = CATALOG.find((c) => c.name === newCatName) || cat;
  const prev = { title: article.title, section: article.section || "", category: cat.name, icon: cat.icon };
  const next = { title: $("#manageTitle").value.trim() || article.title, section: newSection,
                 category: newCatName, icon: newCat.icon };
  try {
    await applyArticleState(article, next);
  } catch (err) { toast("⚠️  " + err.message); return; }
  pushUndo("modification de « " + next.title + " »", () => applyArticleState(article, prev));
  closeManage(); toast("✅ Vidéo mise à jour.");
};

$("#manageDelete").onclick = async () => {
  const { article, cat } = manageRef;
  if (!confirm(`Supprimer « ${article.title} » ? (annulable)`)) return;
  const snapshot = { ...article };
  if (isImported(article)) {
    try {
      const res = await fetch("/api/delete-import", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: article.id }),
      });
      if (!res.ok) throw new Error((await res.json()).error || "Erreur");
    } catch (err) { toast("⚠️  " + err.message); return; }
  } else {
    overrides[article.id] = { hidden: true };
    persistOverrides();
  }
  cat.exercises = cat.exercises.filter((e) => e.id !== article.id);
  selected.delete(article.id); persist();
  closeManage(); render(); toast("🗑️  Vidéo supprimée.");

  pushUndo("suppression de « " + snapshot.title + " »", async () => {
    if (isImported(snapshot)) {
      await fetch("/api/restore-import", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ article: snapshot }),
      });
    } else {
      delete overrides[snapshot.id]; persistOverrides();
    }
    let c = CATALOG.find((x) => x.name === (snapshot.category || cat.name)) || cat;
    if (!CATALOG.includes(c)) CATALOG.push(c);
    if (!c.exercises.some((e) => e.id === snapshot.id)) c.exercises.push(snapshot);
    render();
  });
};

applyOverrides();
render();
refreshUndo();

// ====== Connexion Oplit (statut + reconnexion) + toggle capture live ======
async function refreshOplit() {
  let st;
  try { st = await (await fetch("/api/oplit-status")).json(); }
  catch (e) { st = { connected: false }; }
  const dot = $("#oplitDot"), sub = $("#oplitSub"), reco = $("#oplitReco");
  const live = $("#importLive"), hint = $("#liveHint"), wrap = $("#liveToggleWrap");
  if (st.logging_in) {
    dot.style.background = "#f5a524"; sub.textContent = "connexion en cours…";
  } else if (st.connected) {
    dot.style.background = "var(--accent)"; sub.textContent = "connecté · staging.oplit.fr";
  } else {
    dot.style.background = "var(--rose)"; sub.textContent = "non connecté";
  }
  reco.disabled = !!st.logging_in;
  // toggle capture live
  if (live) {
    live.disabled = !st.connected;
    if (!st.connected) { live.checked = false; }
    if (wrap) wrap.style.opacity = st.connected ? "1" : ".5";
    if (hint) hint.textContent = st.connected
      ? "" : "Connectez-vous à Oplit (bouton ↻ en bas à gauche) pour activer la capture live.";
  }
  return st;
}

$("#oplitReco").onclick = async () => {
  try { await fetch("/api/oplit-login", { method: "POST" }); } catch (e) {}
  toast("🌐 Fenêtre Oplit ouverte — connectez-vous, je détecte automatiquement.");
  // poll le statut le temps de la connexion
  let n = 0;
  const t = setInterval(async () => {
    const st = await refreshOplit();
    if ((!st.logging_in && st.connected) || ++n > 120) { clearInterval(t); }
  }, 3000);
};

refreshOplit();
