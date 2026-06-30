import { useState } from "react";
import Sidebar from "./components/Sidebar";
import Home from "./pages/Home";
import Summaries from "./pages/Summaries";
import Suggestions from "./pages/Suggestions";
import Reminders from "./pages/Reminders";
import Allowlist from "./pages/Allowlist";
import Activity from "./pages/Activity";
import Compose from "./pages/Compose";
import "./styles.css";

export default function App() {
  const [page, setPage] = useState("home");
  const Page = { home: Home, summaries: Summaries, suggestions: Suggestions, reminders: Reminders, allowlist: Allowlist, activity: Activity, compose: Compose }[page];
  return (
    <div className="app">
      <Sidebar page={page} setPage={setPage} />
      <main className="main"><Page /></main>
    </div>
  );
}
