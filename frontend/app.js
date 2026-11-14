// Shared helpers for the dashboards
const S = {token: sessionStorage.getItem("token"), role: sessionStorage.getItem("role"), name: sessionStorage.getItem("name")};
function guard(role) { if (!S.token || S.role !== role) location.replace("login.html"); }
function fmtErr(d) {
  if (!d) return "Request failed.";
  if (d.detail) return d.detail;
  return Object.entries(d).map(([k, v]) => k + ": " + [].concat(v).join(" ")).join("; ");
}
async function api(path, opts = {}) {
  const h = {Authorization: "Token " + S.token};
  if (typeof opts.body === "string") h["Content-Type"] = "application/json";
  const r = await fetch(API_BASE + path, {...opts, headers: h});
  if (r.status === 401) { sessionStorage.clear(); location.replace("login.html"); throw new Error("Session expired."); }
  const d = r.status === 204 ? null : await r.json().catch(() => null);
  if (!r.ok) throw new Error(fmtErr(d));
  return d;
}
function toast(msg, type = "ok") {
  const t = document.createElement("div");
  t.className = "toast " + type; t.textContent = msg; document.body.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}
async function logout() {
  try { await api("/auth/logout/", {method: "POST"}); } catch (e) {}
  sessionStorage.clear(); location.href = "login.html";
}
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
function loadSchool() {
  return fetch(API_BASE + "/school/").then(r => r.json()).then(s => {
    document.querySelectorAll(".sname").forEach(e => e.textContent = s.name);
    document.title = s.name + " · " + document.title;
    const box = document.getElementById("logoBox");
    if (s.logo && box) { const i = document.createElement("img"); i.src = s.logo; i.alt = ""; box.replaceWith(i); }
    return s;
  }).catch(() => ({}));
}
