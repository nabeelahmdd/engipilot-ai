# Architecture — backend-first, AI second

## Boundaries

```text
               CLI (initially) / optional future React
                                 |
                          FastAPI routes
                                 |
                        Application services
                         /              \
                 repositories          policies
                      |               (pure code)
                 PostgreSQL
                                 ^
                                 |
                  AI tool adapters (later)
                    |           |
            LangChain tools   MCP server <— MCP client
                    \           /
                      LangGraph
                  supervisor & agents
                         /       \
                  RAG retrieval   memory/checkpoints
                         |
                  evaluation and tracing
```

The backend should be independently useful **before** any LLM exists. The AI agents are additional clients of the domain services, never privileged side channels.

## Ownership and domain modules

`src/commercepilot_ai/` target modules (create each incrementally):

```text
core/                # config, DB connection/session, cross-cutting errors
modules/catalog/     # models, DTOs, repository, service, HTTP routes
modules/cart/        # cart lines, quantities, ownership, pricing
modules/orders/      # simulated checkout, order states, inventory changes
modules/identity/    # authenticated actor and authorization (when needed)
ai/llm/              # prompts, model factory, structured outputs
ai/tools/            # validated adapters into domain services
ai/graphs/           # LangGraph states, nodes, supervisor, checkpoints
ai/agents/           # specialist roles, contracts and handoffs
ai/mcp/              # MCP server/client, tool/resource contracts
ai/rag/              # ingestion, chunking, retrieval, reranking
ai/memory/           # durable workflow state and user preferences
ai/observability/    # traces, token/cost metrics and alarms
ai/evals/            # evaluators and regression datasets
```

## Rules

1. HTTP routes validate HTTP payloads, never contain inventory/pricing algorithms.
2. Domain services enforce invariants and permissions, regardless of caller.
3. Repositories handle DB read/write; avoid LLM-specific schemas in core business models.
4. One transaction owns checkout and stock decrement.
5. AI tools validate arguments and pass actor identity; they do not query arbitrary SQL.
6. MCP exposes the same tool layer; never duplicate business logic into MCP server.
7. RAG is knowledge retrieval, not the source of truth for stock, price or order status.
8. Trace identifiers flow end-to-end, with sensitive fields redacted.
9. Long-term memory requires separate consent/retention design.
10. Keep single-agent baseline as a comparison before adding multi-agent complexity.

## Integration readiness

Everything under `ai/` is **planned, not implemented** at the repository-reset stage. No API or persistence exists in the reset PR.
