const ITEMS = [["home", "🏠 Home"], ["summaries", "📋 Summaries"], ["suggestions", "✍️ Suggestions"], ["reminders", "🔔 Reminders"], ["allowlist", "🔐 Allowlist"], ["activity", "🪵 Activity"], ["compose", "✍️ Compose"]];
export default function Sidebar({ page, setPage }) {
  return (
    <nav className="sidebar">
      <div className="brand">WhatsApp</div>
      {ITEMS.map(([k, label]) => (
        <button key={k} className={page === k ? "nav active" : "nav"} onClick={() => setPage(k)}>{label}</button>
      ))}
    </nav>
  );
}
