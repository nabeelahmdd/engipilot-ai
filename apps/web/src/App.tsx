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
        <div className="brand">✦ <strong>CommercePilot AI</strong></div>
        <div className="navitem active">Overview</div>
        <div className="navitem muted">Catalog · planned</div>
        <div className="navitem muted">Cart & orders · planned</div>
        <div className="navitem muted">AI assistants · planned</div>
      </aside>
      <main className="content">
        <div className="eyebrow">E-COMMERCE + AGENTIC AI</div>
        <h1>Build a reliable AI shopping platform.</h1>
        <p>Backend-first development: shared API, identity and database foundations are in place. Catalog, checkout and AI assistants are not implemented yet.</p>
        <section className="status-card">
          <div className="status-heading">Backend connectivity</div>
          <div className={`status ${status}`}>{status === "online" ? "Connected to FastAPI" : status === "offline" ? "API unavailable" : "Checking API..."}</div>
          <code>GET /api/v1/health</code>
        </section>
      </main>
    </div>
  );
}
