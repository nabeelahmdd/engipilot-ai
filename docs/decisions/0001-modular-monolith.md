# ADR-0001: Web-first modular monolith

Status: Accepted for scaffold

Context: Engineering AI platform spans PR review, RAG, tests, agents and multi-tenant access. A single short-lived demo can become fragile if every module owns authentication and integrations separately.

Decision: Use React/TypeScript web client, FastAPI modular Python server, PostgreSQL. Keep domain modules isolated behind application services; extract separate workers/services only when necessary. No VS Code extension in the primary plan.

Consequences: Less operational complexity initially, but domain boundaries and permission tests become important. Each new capability must have separate authorization, tests, evaluation criteria and release evidence.
