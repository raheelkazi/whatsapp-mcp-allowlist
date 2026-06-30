import { useEffect, useState } from "react";
import { api } from "../api";
export default function Reminders() {
  const [res, setRes] = useState(null), [busy, setBusy] = useState(false);
  const load = (refresh = 0) => { setBusy(true); api.reminders(refresh).then(setRes).finally(() => setBusy(false)); };
  useEffect(() => { load(0); }, []);
  return (
    <div>
      <h1>Reminders <button onClick={() => load(1)} disabled={busy}>{busy ? "…" : "Refresh"}</button></h1>
      {res?.error && <div className="error">{res.error}</div>}
      {(res?.items || []).map((r, i) => (
        <div key={i} className="card2">🔔 <strong>{r.kind}</strong> — {r.text}</div>
      ))}
    </div>
  );
}
