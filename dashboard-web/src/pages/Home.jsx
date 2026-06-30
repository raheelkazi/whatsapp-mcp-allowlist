import { useEffect, useState } from "react";
import { api } from "../api";
export default function Home() {
  const [s, setS] = useState(null), [err, setErr] = useState(null);
  const [rem, setRem] = useState([]), [sug, setSug] = useState([]), [sum, setSum] = useState([]);
  useEffect(() => {
    api.status().then(setS).catch((e) => setErr(e.message));
    api.reminders(0).then((r) => setRem(r.items || [])).catch(() => {});
    api.suggestions(0).then((r) => setSug(r.items || [])).catch(() => {});
    api.summaries(0).then((r) => setSum(r.items || [])).catch(() => {});
  }, []);
  if (err) return <div className="banner error">Backend unreachable: {err}</div>;
  return (
    <div>
      <h1>Home</h1>
      {s && (
        <div className="strip">
          <span>{s.bridge_reachable ? "🟢 Bridge linked" : "🔴 Bridge down"}</span>
          <span>{s.read_only ? "🚫 Read-only" : "✉️ Sends ON"}</span>
          <span>⏱ ≤{s.rate_limit.max_per_hour}/hr</span>
        </div>
      )}
      <h3>🔔 Reminders</h3>
      {rem.length ? rem.map((r, i) => <div key={i} className="card2">{r.text}</div>) : <p className="muted">Nothing flagged (or set ANTHROPIC_API_KEY).</p>}
      <h3>✍️ Suggested messages</h3>
      {sug.length ? sug.map((x, i) => <div key={i} className="card2">To {x.label}: <em>{x.draft}</em></div>) : <p className="muted">No suggestions right now.</p>}
      <h3>📋 Summaries</h3>
      {sum.map((x, i) => <div key={i} className="card2"><strong>{x.label}</strong> — <span className="muted">{x.summary}</span></div>)}
    </div>
  );
}
