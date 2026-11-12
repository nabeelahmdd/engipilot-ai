import { useEffect, useState } from "react";

type ApiStatus = "checking" | "online" | "offline";

export default function App() {
  const [status, setStatus] = useState<ApiStatus>("checking");

  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/v1/health", { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error("API unavailable");
        setStatus("online");
      })
      .catch((error: unknown) => {
        if (!(error instanceof DOMException && error.name === "AbortError")) {
          setStatus("offline");
        }
      });
    return () => controller.abort();
  }, []);

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">✦ <strong>EngiPilot AI</strong></div>
        <div className="navitem active">Overview</div>
        <div className="navitem muted">Organizations · next task</div>
        <div className="navitem muted">Projects · next task</div>
        <div className="navitem muted">Code review · V0 module</div>
      </aside>
      <main className="content">
        <div className="eyebrow">ENGINEERING AI PLATFORM</div>
        <h1>Build useful AI engineering workflows.</h1>
        <p>Day 1 foundation. Authentication, organizations, project access and AI reviews are not yet implemented.</p>
        <section className="status-card">
          <div className="status-heading">Backend connectivity</div>
          <div className={`status ${status}`}>{status === "online" ? "Connected to FastAPI" : status === "offline" ? "API unavailable" : "Checking API..."}</div>
          <code>GET /api/v1/health</code>
        </section>
      </main>
    </div>
  );
}
