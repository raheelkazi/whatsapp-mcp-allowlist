const BASE = "http://localhost:8000";
async function j(path, opts) {
  const r = await fetch(BASE + path, { headers: { "Content-Type": "application/json" }, ...opts });
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
  return r.json();
}
export const api = {
  status: () => j("/api/status"),
  allowlist: () => j("/api/allowlist"),
  addAllow: (e) => j("/api/allowlist", { method: "POST", body: JSON.stringify(e) }),
  removeAllow: (jid) => j(`/api/allowlist/${encodeURIComponent(jid)}`, { method: "DELETE" }),
  searchContacts: (q) => j(`/api/contacts/search?q=${encodeURIComponent(q)}`),
  activity: (limit = 100) => j(`/api/activity?limit=${limit}`),
  send: (recipient, message) => j("/api/send", { method: "POST", body: JSON.stringify({ recipient, message }) }),
};
