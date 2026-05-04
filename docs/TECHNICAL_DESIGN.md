# Technical Design Document — AI Support Agent

Date: 2026-05-02
Author: Audit Assistant (technical design derived from repository audit)

## Purpose
This document transforms the audit findings into a prioritized, actionable Technical Design Document (TDD) to guide work required to reach production readiness for the AI Support Agent repository.

## Scope
Covers architecture alignment, missing components, production risks, recommended fixes, and a prioritized roadmap to remediate gaps discovered during the code audit.

## Source of Truth
The README is treated as the intended architecture. Refer to the README for the declared architecture and expectations: [README.md](README.md)

---

**Executive Summary**
- Current readiness: Pre-production.
- Core control-plane components exist (FastAPI entrypoint, `orchestration/router.py`, `llm/router.py`, agent implementations), but multiple critical gaps prevent safe production rollout.
- Highest priority risks: committed secrets in repository, absent observability instrumentation, missing automated tests and CI, and many placeholder/stub implementations for core adapters.

---

**Intended Architecture (from README)**
- HTTP layer: `app/` — routers, middleware, schemas
- Domain logic: `domain/`
- Orchestration: `orchestration/`
- Agents: `agents/*/agent.py`
- Execution: `execution/` (dispatcher, executor, registry, strategies)
- Knowledge / RAG: `knowledge/` (ingestion, embeddings, vector_store, retrieval)
- LLM: `llm/` (providers, router)
- Memory: `memory/` (manager, store, summarizer)
- Observability: `observability/` (logger, tracer, metrics)
- Events, config, scripts, tests, docs

---

## Current Implementation Mapping (component-by-component)
Format: Component — Status — Evidence

- HTTP layer (`app/`) — Implemented — See [app/main.py](app/main.py) and [app/api/chat.py](app/api/chat.py).
- Domain (`domain/`) — Present but minimal — [domain/orders.py](domain/orders.py), [domain/tickets.py](domain/tickets.py) are placeholders.
- Orchestration (`orchestration/`) — Substantially implemented — [orchestration/router.py](orchestration/router.py), [orchestration/execution_plan.py](orchestration/execution_plan.py), [orchestration/context.py](orchestration/context.py).
- Agents (`agents/`) — Mostly implemented as LLM-backed stubs — e.g., [agents/intent/agent.py](agents/intent/agent.py), [agents/knowledge/agent.py](agents/knowledge/agent.py). Agents call `llm` and return structured `AgentResult`.
- Execution (`execution/core/`) — Implemented core dispatcher/executor/registry — [execution/core/dispatcher.py](execution/core/dispatcher.py), [execution/core/executor.py](execution/core/executor.py), but some top-level files are empty duplicates ([execution/dispatcher.py](execution/dispatcher.py)).
- Knowledge/RAG (`knowledge/`) — Many pieces implemented: Chroma store ([knowledge/vector_store/chroma_store.py](knowledge/vector_store/chroma_store.py)), OpenAI embedder ([knowledge/embeddings/openai_embedder.py](knowledge/embeddings/openai_embedder.py)), retriever ([knowledge/retrieval/retriever.py](knowledge/retrieval/retriever.py)), ingestor ([knowledge/ingestion/ingestor.py](knowledge/ingestion/ingestor.py)). However base interfaces contain `pass` stubs ([knowledge/vector_store/base.py](knowledge/vector_store/base.py), [knowledge/embeddings/base.py](knowledge/embeddings/base.py)).
- LLM routing/providers (`llm/`) — Router and provider implementations exist ([llm/router.py](llm/router.py), [llm/providers/openai.py](llm/providers/openai.py), [llm/providers/anthropic.py](llm/providers/anthropic.py)), but README TODOs mention connectors not complete.
- Memory (`memory/`) — `MemoryManager` and `InMemoryStore` implemented ([memory/manager.py](memory/manager.py), [memory/store.py](memory/store.py)), Redis store constructor present but incomplete.
- Observability (`observability/`) — Missing/empty implementations: [observability/logger.py](observability/logger.py), [observability/tracer.py](observability/tracer.py), [observability/metrics.py](observability/metrics.py), [observability/cost_tracker.py](observability/cost_tracker.py).
- Config files — YAML files are stubs: [config/llm.yaml](config/llm.yaml), [config/rag.yaml](config/rag.yaml), [config/tools.yaml](config/tools.yaml), [config/rollout.yaml](config/rollout.yaml). Runtime settings are in [config/settings.py](config/settings.py).
- Scripts — Some scripts implemented (ingest, rebuild); others are placeholders: [scripts/ingest_docs.py](scripts/ingest_docs.py) implemented; [scripts/rebuild_index.py](scripts/rebuild_index.py) is a no-op; others empty.
- Tests — Present but empty packages: [tests/unit](tests/unit), [tests/integration](tests/integration), [tests/e2e](tests/e2e), [tests/chaos](tests/chaos).

---

## Detailed Issues (structured)
For each: Title, Description, Evidence, Impact, Severity, Recommended Fix, Estimated Effort

### Critical Issues

1) Committed secrets present in repository
- Description: A `.env` file with production-looking `DATABASE_URL` is committed.
- Evidence: `/.env` contains `DATABASE_URL=postgres://user:pass@prod-db-host:5432/dbname` (present in repo root).
- Impact: Immediate security leak; credentials may be live and compromised.
- Severity: Critical
- Recommended Fix:
  - Immediately remove `.env` from repo and its history (git rm --cached .env; create PR to remove file), rotate any exposed credentials and secrets.
  - Add `.env` to `.gitignore` and update README to instruct use of `.env.example` only.
  - Add pre-commit/CI secret scanning (e.g., `detect-secrets`, GitHub secret scanning) and a policy to prevent secrets in commits.
- Estimated Effort: <1 day for removal + credential rotation and CI rule.

2) Observability absent (logging, tracing, metrics, cost tracking)
- Description: No structured logging/tracing/metrics implementation; files are placeholders.
- Evidence: [observability/logger.py](observability/logger.py), [observability/tracer.py](observability/tracer.py), [observability/metrics.py](observability/metrics.py) contain no code.
- Impact: No operational visibility, difficult to monitor outages, no LLM cost telemetry.
- Severity: Critical
- Recommended Fix:
  - Implement structured logging (JSON) and a logger factory; wire logger into `app` middleware and `execution`/`orchestration` layers.
  - Add OpenTelemetry tracing with automatic FastAPI instrumentation; create span boundaries in `orchestration/router.py` and `execution/core/*`.
  - Implement Prometheus metrics and expose `/metrics` endpoint.
  - Implement `observability/cost_tracker.py` to record tokens/cost per request from `LLMResponse` objects.
- Estimated Effort: 3–7 days (initial instrumentation), additional 1–2 days to tune alerts.

3) No automated tests or CI
- Description: Tests directories exist but are empty; no CI configured.
- Evidence: [tests/unit/__init__.py](tests/unit/__init__.py) and others are empty; README notes tests missing.
- Impact: No safety net for regressions; risky for production changes.
- Severity: Critical
- Recommended Fix:
  - Add unit tests for `domain/*`, `agents/intent`, `llm/router` fallback behavior, and `memory/manager` logic.
  - Add integration tests for orchestration happy/failure paths (use a mocked LLM provider and in-memory stores).
  - Add GitHub Actions workflow to run `pytest`, lint, and type checks on PRs.
- Estimated Effort: 1–2 weeks to cover core paths.

### Major Issues

4) Core adapter/base classes contain unimplemented methods
- Description: Base interfaces for vector store, embeddings, memory store, and tools contain `pass`/`NotImplementedError`; concrete implementations are partial or inconsistent.
- Evidence: [knowledge/vector_store/base.py](knowledge/vector_store/base.py) (pass), [knowledge/embeddings/base.py](knowledge/embeddings/base.py) (pass), [execution/tools/base.py](execution/tools/base.py) raises NotImplementedError, [memory/store.py](memory/store.py) contains abstract methods with `pass`.
- Impact: Incomplete contract enforcement across adapters, making pluggability fragile.
- Severity: High
- Recommended Fix:
  - Define explicit base interfaces with typed method signatures and docstrings.
  - Add unit tests verifying that concrete implementations conform to base contracts (interface tests).
  - Complete missing methods or mark intentionally abstract and ensure every provider implements them.
- Estimated Effort: 3–7 days.

5) Unsafe default settings
- Description: `config/settings.py` sets `debug=True`, `allowed_origins=['*']`, and `rate_limit_enabled=False` by default.
- Evidence: [config/settings.py](config/settings.py) (defaults visible).
- Impact: If deployed without env overrides, app could expose debug endpoints, open CORS, and disable rate limiting.
- Severity: High
- Recommended Fix:
  - Set safer defaults (debug=False, allowed_origins=[], rate_limit_enabled=True).
  - Add `settings.validate_production()` invoked on startup to fail-fast when unsafe defaults are used in `is_production` mode.
- Estimated Effort: 1 day.

6) Partial RAG and ingestion workflows
- Description: While Chroma and OpenAI embedder exist, the base interfaces and some scripts (rebuild/backfill) are incomplete or no-op.
- Evidence: [knowledge/vector_store/chroma_store.py](knowledge/vector_store/chroma_store.py) implemented; [knowledge/vector_store/base.py](knowledge/vector_store/base.py) stubbed; [scripts/rebuild_index.py](scripts/rebuild_index.py) is a no-op.
- Impact: No robust operational path for full ingestion/backfill and index rebuilds.
- Severity: Medium
- Recommended Fix:
  - Finalize base interfaces, implement backfill and rebuild scripts, and add integration tests for ingest→embed→index→retrieve flow.
- Estimated Effort: 1–2 weeks.

7) Memory persistence: InMemoryStore only; Redis incomplete
- Description: `InMemoryStore` works for dev, but `RedisStore` is incomplete and some manager features rely on store iteration/advanced ops (TODOs).
- Evidence: [memory/store.py](memory/store.py) InMemoryStore present; `RedisStore` constructor present but not fully implemented; TODO comments in [memory/manager.py](memory/manager.py).
- Impact: In-memory only is not production-suitable; session TTL, persistence, and scaling missing.
- Severity: Medium
- Recommended Fix:
  - Implement `RedisStore` (save/load/delete/list operations), TTL, and optional encryption/ACL handling.
  - Add migration tests and an operational runbook for session cleanup/backfill.
- Estimated Effort: 3–5 days.

### Minor Issues

8) Duplicate/empty files causing confusion
- Description: Some top-level files are empty or duplicate implemented versions (e.g., `execution/dispatcher.py` empty while `execution/core/dispatcher.py` has code).
- Evidence: [execution/dispatcher.py](execution/dispatcher.py) empty; core implementation in [execution/core/dispatcher.py](execution/core/dispatcher.py).
- Impact: Developer confusion; maintainability issues.
- Severity: Low
- Recommended Fix: Consolidate and remove dead duplicates; update README to reflect true layout.
- Estimated Effort: <1 day.

9) Documentation gaps and runbooks incomplete
- Description: `docs/` contains architecture and runbooks but stubs in other places referenced by README.
- Evidence: [docs/stubs.md](docs/stubs.md) references placeholders.
- Impact: Onboarding and operational readiness hindered.
- Severity: Low
- Recommended Fix: Expand `docs/` with operational runbooks for ingestion, deployment, monitoring, incident response.
- Estimated Effort: 3–7 days depending on depth.

---

## Cross-cutting Recommendations
- Security
  - Remove secrets and rotate; add secret scanning to CI and pre-commit hooks.
  - Harden default configuration and require explicit production env variables.
- Observability
  - Implement structured logging, OpenTelemetry tracing, and Prometheus metrics. Expose `/metrics`. Add cost reporting tied to LLM responses.
- Testing & CI
  - Add unit, integration, and e2e tests. Use a mocked LLM provider for fast tests. Build a GitHub Actions pipeline.
- Resilience
  - Fully exercise and test circuit breakers, retry strategies, and rate limiting. Add chaos tests (simulate provider failures and identify fallback correctness).
- Documentation & Runbooks
  - Provide clear runbooks for ingestion, index rebuild, session cleanup, and secrets handling. Add developer onboarding docs.

---

## Prioritized Roadmap (milestones & acceptance criteria)

Milestone 0 — Emergency fixes (Blockers)
- Remove `.env` from repo and rotate secrets.
- Add `.env` to `.gitignore` and update README.
- Acceptance: No secrets in repo; credential rotation confirmed.
- Time: 1 day.

Milestone 1 — Observability & Safety
- Implement structured logger and basic OpenTelemetry tracing instrumentation in `app` and `orchestration` paths.
- Add Prometheus metrics and `/metrics` endpoint.
- Add `settings.validate_production()` and safer defaults.
- Acceptance: Traces visible in local OTLP collector; `/metrics` returns metrics; production startup fails when unsafe defaults detected.
- Time: 3–7 days.

Milestone 2 — Tests & CI
- Add unit tests for domain logic and core agent parsing.
- Add integration tests for orchestration using a shimbed LLM provider.
- Add GitHub Actions workflow for lint + tests.
- Acceptance: PRs must pass CI with tests and linting.
- Time: 1–2 weeks.

Milestone 3 — Adapter completion & RAG operations
- Finalize base interfaces for vector store/embeddings/memory stores and complete `RedisStore`.
- Implement ingestion backfill and index rebuild scripts with tests.
- Acceptance: End-to-end ingest → embed → index → retrieve validated in integration tests.
- Time: 2–3 weeks.

Milestone 4 — Resilience & Chaos
- Build chaos tests to simulate provider outages and assert fallback and escalation behavior.
- Acceptance: Orchestration meets defined SLOs and fallback policies in simulated failures.
- Time: 2–4 weeks.

Milestone 5 — Production-readiness checklist & runbooks
- Finalize docs: deployment steps, monitoring, alert thresholds, runbooks for incidents, cost management.
- Acceptance: Runbook reviewed and tested during a rehearsal incident.
- Time: 1–2 weeks.

---

## Tactical Next Steps (immediate actionable PRs)
1. Remove committed `.env` and add `.env` to `.gitignore` (Critical) — create PR now.
2. Add `settings.validate_production()` and change unsafe defaults in `config/settings.py` (High) — small PR.
3. Add a minimal structured logger implementation in `observability/logger.py` and wire it into `app/main.py` startup (Critical → Observability baseline).
4. Add a mocked LLM provider for tests (e.g., `llm/providers/mock.py`) and a minimal unit test for `agents/intent/agent.py` parsing flow.

If you want, I can implement PR (1) now (remove `.env` from repo and add `.gitignore` entry) and PR (3) (create a minimal `observability/logger.py` and wire to `app/main.py`). Which would you like me to start with?

---

## Appendix: Audit methodology
- Scanned repository structure and README as ground-truth.
- Performed regex searches for `TODO`, `pass`, and `NotImplementedError` to locate stubs.
- Mapped implemented modules to README's expected components and collected file-level evidence.
- Avoided speculation: every gap is tied to specific files or README assertions.

## Appendix: Quick evidence index (selected files)
- FastAPI entrypoint: [app/main.py](app/main.py)
- Orchestration: [orchestration/router.py](orchestration/router.py)
- LLM Router: [llm/router.py](llm/router.py)
- Chroma store: [knowledge/vector_store/chroma_store.py](knowledge/vector_store/chroma_store.py)
- OpenAI embedder: [knowledge/embeddings/openai_embedder.py](knowledge/embeddings/openai_embedder.py)
- Memory manager: [memory/manager.py](memory/manager.py)
- Observability stubs: [observability/logger.py](observability/logger.py)
- Config defaults: [config/settings.py](config/settings.py)
- Committed `.env`: `/.env`

---

End of document.
