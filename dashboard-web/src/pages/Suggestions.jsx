import { useEffect, useState } from "react";
import { api } from "../api";
export default function Suggestions() {
  const [res, setRes] = useState(null), [busy, setBusy] = useState(false);
  const [confirm, setConfirm] = useState(null), [sent, setSent] = useState({});
  const load = (refresh = 0) => { setBusy(true); api.suggestions(refresh).then(setRes).finally(() => setBusy(false)); };
  useEffect(() => { load(0); }, []);
  const doSend = async (s) => {
    setConfirm(null);
    try { const r = await api.send(s.chat_jid, s.draft); setSent((m) => ({ ...m, [s.chat_jid + s.draft]: r.message })); }
    catch (e) { setSent((m) => ({ ...m, [s.chat_jid + s.draft]: e.message })); }
  };
  return (
    <div>
      <h1>Suggestions <button onClick={() => load(1)} disabled={busy}>{busy ? "…" : "Refresh"}</button></h1>
      {res?.error && <div className="error">{res.error}</div>}
      {res?.generated_at && <p className="muted">Generated {new Date(res.generated_at).toLocaleString()}</p>}
      {(res?.items || []).map((s, i) => (
        <div key={i} className="card2">
          <div className="muted">To <strong>{s.label}</strong>{s.context ? ` — ${s.context}` : ""}</div>
          <blockquote>{s.draft}</blockquote>
          <button onClick={() => setConfirm(s)}>Send…</button>
          {sent[s.chat_jid + s.draft] && <span className="ok"> {sent[s.chat_jid + s.draft]}</span>}
        </div>
      ))}
      {confirm && (
        <div className="dialog">
          <p>Send to <strong>{confirm.label}</strong>?</p>
          <blockquote>{confirm.draft}</blockquote>
          <button onClick={() => doSend(confirm)}>Confirm send</button>
          <button onClick={() => setConfirm(null)}>Cancel</button>
        </div>
      )}
    </div>
  );
}
