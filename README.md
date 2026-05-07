# AI Support Agent

A modular Python FastAPI scaffold for an AI-driven customer support agent. This repository is designed to support conversational workflows, knowledge retrieval, agent orchestration, and external tool integrations.

## What this repo contains

- `main.py` — application entrypoint
- `app/` — FastAPI app, API routes, middleware, schemas, dependency wiring
- `agents/` — specialized agents for intent, knowledge, orders, tickets, escalation
- `domain/` — business models and rules for orders, tickets, users, and policies
- `orchestration/` — routing, execution planning, ambiguity handling, and confidence scoring
- `execution/` — dispatcher, validators, retries, circuit breakers, tool invocations, workflow execution
- `knowledge/` — document ingestion, chunking, embeddings, retrieval, and vector store adapters
- `llm/` — LLM provider routing, fallback logic, prompts, and guardrails
- `memory/` — session/context memory manager, store, summarizer, and validation
- `observability/` — logging, tracing, metrics, cost tracking, and alerting helpers
- `events/` — event publisher/consumer support and event schemas
- `config/` — YAML configuration for LLMs, RAG, tools, and rollout flags
- `scripts/` — utility scripts for ingestion, index rebuilds, backfills, and chaos testing
- `tests/` — test suites for unit, integration, end-to-end, and chaos testing
- `docs/` — documentation, runbooks, deployment guides, and design notes

## Documentation

- [Deployment](docs/deployment.md) — deployment and operational guidance
- [Monitoring](docs/monitoring.md) — observability and alerting practices
- [Incident Response](docs/incident_response.md) — incident handling and response playbooks
- [Failure Scenarios](docs/failure_scenarios.md) — expected failure modes and mitigation
- [Cost Management](docs/cost_management.md) — cost monitoring and optimization
- [Technical Design](docs/technical_design.md) — repository design and implementation details
- `docs/sample/getting_started.txt` — example onboarding and usage notes

## Quick start

1. Copy environment variables from `.env.example` to `.env`
2. Set required secrets (for example, `OPENAI_API_KEY`)
3. Install dependencies:

```bash
python -m pip install -r requirements.txt
```

4. Run locally:

```bash
python main.py
```

or with Uvicorn:

```bash
uvicorn main:app --reload --port 8000
```

5. Run with Docker:

```bash
docker build -t ai-support-agent .
docker run -p 8000:80 --env-file .env ai-support-agent
```

## Repository structure

```
├── .env.example             # example environment variables
├── docker-compose.yml       # container composition for local or staging environments
├── Dockerfile               # Docker image build configuration
├── main.py                  # application entrypoint
├── pyproject.toml           # project metadata and dependency settings
├── requirements.txt         # runtime and development dependencies
├── README.md                # repository overview and usage guide
├── app/                     # FastAPI application, routers, middleware, schemas
├── agents/                  # modular agent implementations and prompts
├── config/                  # YAML configuration for LLMs, tools, and rollout flags
├── domain/                  # domain models, business logic, policies
├── execution/               # orchestration, dispatch, retries, validators, workflows
├── events/                  # event schemas, publisher, consumer support
├── knowledge/               # ingestion, embeddings, retrieval, vector stores
├── llm/                     # LLM routing, fallback, provider integrations, guardrails
├── memory/                  # session memory store, summarization, validation
├── observability/           # logging, metrics, tracing, alerting
├── scripts/                 # CLI helpers and maintenance scripts
├── tests/                   # unit, integration, e2e, and chaos tests
└── docs/                    # architecture, deployment, incident, and cost docs
```

## Key concepts

- `app/` is the HTTP and API layer, including middleware, request validation, and route wiring.
- `agents/` contains capability-specific agents that define prompts, schemas, and logic for conversational behavior.
- `domain/` holds pure business logic with zero external IO.
- `orchestration/` decides which agent runs and how execution is planned.
- `execution/` executes planned actions with retries, circuit breakers, and tool integrations.
- `knowledge/` manages document ingestion and retrieval for RAG-style knowledge access.
- `llm/` centralizes LLM provider selection, fallback behavior, prompt templates, and safety guardrails.
- `memory/` maintains conversational context and produces summaries for longer sessions.
- `observability/` captures telemetry, logs, tracing, and cost metrics.

## Notes

- This repo is intended as a production-minded scaffold for AI support workflows.
- The codebase is organized to separate API, business logic, agent behavior, orchestration, and retrieval.
- The `docs/` folder contains operational and design documentation for developers and operators.

## Next steps

- Complete LLM provider connectors and integrations under `llm/`
- Wire agent workflows through `orchestration/` and `execution/`
- Expand tests in `tests/unit`, `tests/integration`, and `tests/e2e`
- Add CI/CD automation for linting, testing, and deployment
