import { useEffect, useState } from "react";
import { api } from "../api";
export default function Home() {
  const [s, setS] = useState(null), [err, setErr] = useState(null);
  useEffect(() => { api.status().then(setS).catch((e) => setErr(e.message)); }, []);
  if (err) return <div className="banner error">Backend unreachable: {err}</div>;
  if (!s) return <p>Loading…</p>;
  return (
    <div>
      <h1>Home</h1>
      <div className="strip">
        <span>{s.bridge_reachable ? "🟢 Bridge linked" : "🔴 Bridge down"}</span>
        <span>{s.read_only ? "🚫 Read-only" : "✉️ Sends ON"}</span>
        <span>⏱ ≤{s.rate_limit.max_per_hour}/hr</span>
      </div>
      <p className="muted">Summaries, suggestions, and reminders arrive in Phase 2.</p>
    </div>
  );
}
