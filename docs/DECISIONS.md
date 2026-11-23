# Architecture decision log

| ID | Decision | Rationale | Trade-off |
|---|---|---|---|
| ADR-001 | Repurpose the existing `engipilot-ai` Git repository for CommercePilot AI | Preserve established Git history and workflow; remove unrelated code-review scope | Requires manual GitHub repo rename; old PRs become obsolete |
| ADR-002 | Backend first, AI later | Build trustworthy, testable domain operations before connecting model-driven actions | Larger timeline than using only mock APIs |
| ADR-003 | Use Python 3.12 and `uv` | Pinned interpreter and reproducible dependency management | `uv.lock` must be recreated after reset |
| ADR-004 | Modular monolith and single `src/` Python package | Clear business/AI boundaries without deployment complexity | Requires discipline around imports/ownership |
| ADR-005 | PostgreSQL owns e-commerce state | Transactions, consistency, authorization and persistence | Requires DB setup/migrations |
| ADR-006 | Domain services enforce every business policy | AI/MCP and HTTP callers share the same security boundary | Some adapter plumbing needed |
| ADR-007 | No real financial or shipment effects in portfolio demo | Safe testing without payment/compliance integration | All checkout/returns are simulations |
| ADR-008 | Incremental dependency installation and manual implementation | User learns each directory and package decision | Takes more focused time |
| ADR-009 | Separate state, memory, RAG and operational logs | Access, freshness, retention and trust requirements differ | More data lifecycle definitions |

### Decisions to defer

- UI framework and deployment target
- Auth provider/flow and tenant strategy
- LLM provider and model router
- Vector store and embedding model
- Trace/evaluation platform
- Celery/Redis vs simpler background execution

Decide when a measurable acceptance criterion requires the capability, not during reset.
