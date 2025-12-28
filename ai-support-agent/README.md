# AI Support Agent

Opinionated scaffold for an AI-driven customer support agent (ai-support-agent).

Overview
-	Purpose: Provide a modular, production-minded Python/ FastAPI project layout for building conversational support agents that orchestrate LLMs, knowledge retrieval (RAG), and external tools (Shopify, Helpdesk, Notifications).
-	Goals: clear separation of concerns, testable agents, pluggable LLM providers, and observability.

Quickstart
-	Copy environment variables from `.env.example` to `.env` and set secrets (e.g., `OPENAI_API_KEY`).
-	Install dependencies:

```bash
python -m pip install -r requirements.txt
```

-	Run locally:

```bash
python main.py
# or with uvicorn
uvicorn main:app --reload --port 8000
```

-	Docker (build & run):

```bash
docker build -t ai-support-agent .
docker run -p 8000:80 --env-file .env ai-support-agent
```

Project Layout (top-level)

ai-support-agent/
├── .env.example             # example environment variables
├── .gitignore
├── README.md                # this file
├── requirements.txt         # pip deps for the app
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── main.py                  # app entrypoint

High-level packages

- `app/` — HTTP layer, routers, middleware, pydantic schemas, dependency wiring.
  - `app/main.py` exposes `create_app()` building FastAPI and registering routes.

- `domain/` — Pure business rules and domain models (orders, tickets, users, policies).

- `orchestration/` — Intent routing, execution planning, ambiguity resolution, and confidence scoring.

- `agents/` — Agent implementations grouped by capability (intent, knowledge, orders, tickets, escalation). Each agent contains `agent.py`, `prompts.py`, and `schemas.py`.

- `execution/` — Dispatcher, validators, retries, circuit breaker, external tool wrappers (Shopify, helpdesk, notifications) and workflow handlers.

- `knowledge/` — Document ingestion, chunking, embeddings, retrieval, vector store adapters, and freshness rules.

- `llm/` — LLM routing, fallbacks, provider integrations, prompts, and guardrails (json validation, content filtering, retry/degradation strategies).

- `memory/` — Session/context memory manager, store, summarizer, and validators.

- `observability/` — Logger, tracer, metrics, cost tracker, and alerting helpers.

- `events/` — Optional event publisher/consumer layer and event schemas.

- `config/` — YAML configs for LLMs, RAG, tools, and rollout flags.

- `scripts/` — Helpful CLI scripts (ingest docs, rebuild index, backfill embeddings, chaos tests).

- `tests/` — Unit, integration, e2e and chaos test suites.

- `docs/` — Architecture, API, deployment, runbooks and failure scenarios.

Design notes & conventions
-	Keep `domain/` pure: no IO, only deterministic business logic and policies.
-	Agents are small, single-responsibility units: they take structured inputs and return structured outputs.
-	Execution layer handles retries, circuit-breaking, and idempotency.
-	Knowledge layer enforces freshness rules before serving RAG results.
-	LLM calls are routed through `llm/router.py` to allow provider failover and guardrails.
-	Use `pydantic` models (`app/schemas`) for all external and internal interfaces.
-	Add observability hooks in entrypoints (fastapi middleware, dispatcher, and agent runners).

Next steps / TODO
- Implement concrete LLM provider connectors in `llm/providers/`.
- Wire agents into `orchestration/router.py` and build `execution/dispatcher.py` flows.
- Add test coverage under `tests/unit` for domain logic and `tests/integration` for end-to-end flows.
- Configure CI to run linting and tests.

Contacts & Resources
-	This scaffold is intended to be adapted — rename modules to fit product conventions. If you want, I can:
  - add a minimal `docker-compose` dev stack (Postgres, Redis)
  - implement a simple `llm/providers/openai.py` adapter and a sample agent flow

License
-	Add your preferred license file.
