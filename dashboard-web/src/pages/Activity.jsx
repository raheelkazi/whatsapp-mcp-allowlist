import { useEffect, useState } from "react";
import { api } from "../api";
export default function Activity() {
  const [rows, setRows] = useState([]);
  useEffect(() => { api.activity(200).then(setRows); }, []);
  return (
    <div>
      <h1>Activity</h1>
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
