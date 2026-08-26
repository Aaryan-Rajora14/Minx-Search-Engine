const TOPICS = [
  ["all", "All tea"],
  ["friends", "Friends"],
  ["family", "Family"],
  ["study", "Study"],
  ["gossip", "Gossip"],
  ["work", "Work"],
  ["neighbors", "Neighbors"],
  ["fantasy", "Fantasy"],
  ["politics", "Politics"],
  ["secrets", "Secrets"],
];
const THEMES = ["salon", "ink", "midnight", "matcha", "rose"];

const state = {
  mode: localStorage.getItem("minx-mode") || "family",
  theme: localStorage.getItem("minx-theme") || "salon",
  topic: "all",
  result: null,
};

const $ = (id) => document.getElementById(id);

function applyTheme() {
  document.documentElement.setAttribute("data-theme", state.theme);
  localStorage.setItem("minx-theme", state.theme);
  document.querySelectorAll("[data-theme-id]").forEach((b) => {
    b.classList.toggle("on", b.dataset.themeId === state.theme);
  });
}

function applyMode() {
  localStorage.setItem("minx-mode", state.mode);
  document.querySelectorAll("[data-mode]").forEach((b) => {
    b.classList.toggle("on", b.dataset.mode === state.mode);
  });
  $("tag").textContent =
    state.mode === "unhinged"
      ? "Unhinged pours: politics, secrets, fantasy, and sharper gossip — plus Google results."
      : "Family-friendly pours. Switch to Unhinged for darker tea. Google results included.";
}

function renderChips() {
  $("chips").innerHTML = TOPICS.map(
    ([id, label]) =>
      '<button type="button" class="chip' +
      (state.topic === id ? " on" : "") +
      '" data-topic="' +
      id +
      '">' +
      label +
      "</button>"
  ).join("");
}

function renderThemes() {
  const host = $("themes");
  THEMES.forEach((t) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "theme-btn";
    b.dataset.themeId = t;
    b.textContent = t[0].toUpperCase() + t.slice(1);
    b.addEventListener("click", () => {
      state.theme = t;
      applyTheme();
    });
    host.appendChild(b);
  });
}

function hostOf(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch (e) {
    return "";
  }
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "\u0026amp;")
    .replace(/</g, "\u0026lt;")
    .replace(/>/g, "\u0026gt;")
    .replace(/"/g, "\u0026quot;");
}

function renderResults() {
  const data = state.result;
  $("photo-hint").hidden = !!data;
  $("photos").classList.toggle("compact", !!data);
  if (!data) {
    $("out").innerHTML = "";
    return;
  }
  const cards = data.stories
    .map((s) => {
      const cite = hostOf(s.url);
      return (
        "<li><a class=\"card\" href=\"" +
        s.url +
        "\" target=\"_blank\" rel=\"noreferrer\">" +
        '<div class="cite">' +
        cite +
        "</div>" +
        '<div class="badges"><span>' +
        escapeHtml(s.source) +
        "</span><span>" +
        escapeHtml(s.topic) +
        "</span>" +
        (s.heat === "unhinged" ? "<span>Unhinged</span>" : "") +
        "</div>" +
        "<h2>" +
        escapeHtml(s.title) +
        "</h2><p>" +
        escapeHtml(s.snippet) +
        "</p></a></li>"
      );
    })
    .join("");
  $("out").innerHTML =
    '<div class="meta"><p>' +
    data.stories.length +
    " pours · " +
    (data.liveCount || 0) +
    " live · " +
    (data.archiveCount || 0) +
    " archive · " +
    data.mode +
    '</p><div class="links">' +
    '<a href="' +
    data.googleUrl +
    '" target="_blank" rel="noreferrer">Google</a>' +
    '<a href="' +
    data.redditUrl +
    '" target="_blank" rel="noreferrer">Reddit</a>' +
    '<a href="' +
    data.quoraUrl +
    '" target="_blank" rel="noreferrer">Quora</a>' +
    "</div></div>" +
    (data.stories.length
      ? '<ul class="results">' + cards + "</ul>"
      : '<p class="hint">No tea on that topic yet.</p>');
}

async function minxIt() {
  const q = $("q").value.trim();
  $("go").disabled = true;
  $("err").hidden = true;
  try {
    const url =
      "/api/search?q=" +
      encodeURIComponent(q) +
      "&topic=" +
      encodeURIComponent(state.topic) +
      "&mode=" +
      encodeURIComponent(state.mode);
    const res = await fetch(url);
    if (!res.ok) throw new Error("bad");
    state.result = await res.json();
    renderResults();
  } catch (e) {
    $("err").hidden = false;
    $("err").textContent = "Could not pour the tea just now. Try again in a moment.";
  } finally {
    $("go").disabled = false;
  }
}

document.querySelectorAll("[data-mode]").forEach((b) => {
  b.addEventListener("click", () => {
    state.mode = b.dataset.mode;
    applyMode();
    if (state.result) minxIt();
  });
});

$("chips").addEventListener("click", (e) => {
  const t = e.target.closest("[data-topic]");
  if (!t) return;
  state.topic = t.dataset.topic;
  renderChips();
  minxIt();
});

$("form").addEventListener("submit", (e) => {
  e.preventDefault();
  minxIt();
});

$("home").addEventListener("click", () => {
  state.result = null;
  renderResults();
});

renderChips();
renderThemes();
applyTheme();
applyMode();
