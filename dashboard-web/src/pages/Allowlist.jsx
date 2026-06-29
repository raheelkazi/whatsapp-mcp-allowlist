import { useEffect, useState } from "react";
import { api } from "../api";
export default function Allowlist() {
  const [rows, setRows] = useState([]), [q, setQ] = useState(""), [hits, setHits] = useState([]);
  const [err, setErr] = useState(null);
  const load = () => api.allowlist().then(setRows).catch(e => setErr(e.message));
  useEffect(() => { load(); }, []);
  const search = async () => setHits(await api.searchContacts(q));
  const add = async (jid, label, mode) => { await api.addAllow({ jid, label, mode }); setHits([]); setQ(""); load(); };
  return (
    <div>
      <h1>Allowlist &amp; Permissions</h1>
      {err && <div className="error">Backend error: {err}</div>}
      <div className="row">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search contacts/groups…" />
        <button onClick={search}>Search</button>
      </div>
      {hits.map((h) => (
        <div key={h.jid} className="row hit">
          <span>{h.name} <code>{h.jid}</code></span>
          <button onClick={() => add(h.jid, h.name, "read+send")}>Add read+send</button>
          <button onClick={() => add(h.jid, h.name, "read")}>Add read-only</button>
        </div>
      ))}
      <table className="tbl">
        <thead><tr><th>Label</th><th>JID</th><th>Mode</th><th></th></tr></thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.jid}>
              <td>{r.label}</td><td><code>{r.jid}</code></td><td>{r.mode}</td>
              <td><button onClick={() => api.removeAllow(r.jid).then(load)}>Remove</button></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
