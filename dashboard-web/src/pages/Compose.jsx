import { useEffect, useState } from "react";
import { api } from "../api";
export default function Compose() {
  const [chats, setChats] = useState([]), [to, setTo] = useState(""), [msg, setMsg] = useState("");
  const [confirm, setConfirm] = useState(false), [result, setResult] = useState(null);
  useEffect(() => { api.allowlist().then((r) => setChats(r.filter((c) => c.mode === "read+send"))); }, []);
  const doSend = async () => {
    setConfirm(false);
    try {
      setResult(await api.send(to, msg));
      setMsg("");
    } catch (e) {
      setResult({ success: false, message: e.message });
    }
  };
  return (
    <div>
      <h1>Compose</h1>
      <select value={to} onChange={(e) => setTo(e.target.value)}>
        <option value="">Select an allowlisted chat…</option>
        {chats.map((c) => <option key={c.jid} value={c.jid}>{c.label}</option>)}
      </select>
      <textarea value={msg} onChange={(e) => setMsg(e.target.value)} placeholder="Message…" />
      <button disabled={!to || !msg} onClick={() => setConfirm(true)}>Send…</button>
      {confirm && (
        <div className="dialog">
          <p>Send to <strong>{chats.find((c) => c.jid === to)?.label}</strong>?</p>
          <blockquote>{msg}</blockquote>
          <button onClick={doSend}>Confirm send</button>
          <button onClick={() => setConfirm(false)}>Cancel</button>
        </div>
      )}
      {result && <p className={result.success ? "ok" : "error"}>{result.message}</p>}
    </div>
  );
}
