import { useEffect, useState } from "react";
import { api } from "../api";
export default function Activity() {
  const [rows, setRows] = useState([]);
  const [err, setErr] = useState(null);
  useEffect(() => { api.activity(200).then(setRows).catch(e => setErr(e.message)); }, []);
  return (
    <div>
      <h1>Activity</h1>
      {err && <div className="error">Backend error: {err}</div>}
      <table className="tbl">
        <thead><tr><th>Time</th><th>Tool</th><th>Target</th><th>Decision</th><th>Reason</th></tr></thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className={r.decision === "denied" ? "denied" : ""}>
              <td>{r.ts}</td><td>{r.tool}</td><td><code>{r.target || ""}</code></td>
              <td>{r.decision}</td><td>{r.reason || ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
