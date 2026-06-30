import { useEffect, useState } from "react";
import { api } from "../api";
export default function Summaries() {
  const [res, setRes] = useState(null), [busy, setBusy] = useState(false);
  const load = (refresh = 0) => { setBusy(true); api.summaries(refresh).then(setRes).finally(() => setBusy(false)); };
  useEffect(() => { load(0); }, []);
  return (
    <div>
      <h1>Summaries <button onClick={() => load(1)} disabled={busy}>{busy ? "…" : "Refresh"}</button></h1>
      {res?.error && <div className="error">{res.error}</div>}
      {(res?.items || []).map((s, i) => (
        <div key={i} className="card2"><strong>{s.label}</strong><p className="muted">{s.summary}</p></div>
      ))}
    </div>
  );
}
