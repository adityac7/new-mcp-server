# MCP Analytics Server – Production Architecture

## 1. Goals & Scope
- Deliver an internal, production-grade MCP (Model Context Protocol) server that lets analysts register multiple Postgres-compatible datasets, enrich them with LLM-generated metadata, and run complex analytical queries (up to ~30 sub-queries per prompt) with persona-based outputs.
- Build on the existing FastMCP/Render blueprint while adding a scalable control plane for dataset onboarding, metadata curation, orchestration, and observability.
- Keep deployment simple enough to start on Render (or similar PaaS) while leaving a clear path to containerized autoscaling on managed cloud infra when users and workloads grow.

## 2. Personas & Usage Targets
- **CMI analysts (initial 5–10 → 100 users)**: need fast, guided insights without wrestling with schema complexity; expect weighted, persona-level answers.
- **Data ops/solution engineer (1–2 power users)**: manage dataset onboarding, monitor health, triage LLM output quality, ensure connectors stay healthy.
- **Leadership / QA**: review query logs, track which tools/LLMs are used, validate governance instructions (weighting, sample limits).
- Workload assumptions: ≤10 concurrent power users today, possibly 100 with bursty querying; mixed event-level and aggregated tables of 10^8+ rows; latency budget <10s for most prompts, with a stretch goal of <5s for pre-indexed paths.

## 3. System Overview
- **Control plane**: dataset registration UI/API, metadata generation & validation, schema normalization, LLM prompt templating logic, dataset health monitoring.
- **Data plane**: connection manager, query planner/executor, caching layer, persona-aware result shaper with guardrails (weights, aggregation limits).
- **LLM orchestration**: OpenAI GPT-4.1-Mini (primary) via well-structured prompts, fallback strategy, progressive context loading to stay within token budgets.
- **MCP server**: FastMCP-based service exposing tools/endpoints to external LLM clients (ChatGPT, Claude, Manus, etc.), dynamically driven by the dataset registry.
- **UI**: lightweight web app for dataset onboarding, metadata review, query logs dashboard, health status.
- **Infra**: git-driven CI/CD, containerized deployment, managed Postgres for metadata, optional Redis for caching/queues, centralized logging/metrics.

## 4. Architecture Layers

### 4.1 Control Plane Services
- **Dataset Registry API (FastAPI service)**: CRUD endpoints for datasets; stores connection strings, access credentials (via secrets manager), dataset classification tags, weight-related flags, default personas; lives in `metadata_db`.
- **Secrets Broker**: integrate with Render environment variables initially; plan to graduate to cloud secret manager (AWS Secrets Manager / GCP Secret Manager) when moving off Render.
- **Schema Profiler Worker**:
  - Connects to new dataset, infers schema, stats (row counts, null %, date ranges, sample values).
  - Stores normalized schema (tables, columns, FKs) in registry (JSONB + vector embeddings for semantic search).
- **LLM Metadata Service**:
  - Uses GPT-4.1-Mini to draft dataset description, data dictionary, recommended use cases, data quality observations, improvement suggestions.
  - Prompt includes global business context (panel, weighting rules, max 5 raw rows) and profiler output.
  - Presents draft to human for validation in UI; stores final description + structured tags.
- **Data Quality Heuristics**:
  - Static checks (naming conventions, date format consistency, weight presence).
  - Rule engine to flag issues for LLM to comment on; results surfaced in onboarding UI.
- **Approval Workflow**:
  - Dataset states: `draft → metadata_pending → human_review → approved → active`.
  - Once approved, emits event (message queue) to reload connectors in the data plane without redeploy.

### 4.2 Data Plane Components
- **Connection Manager**:
  - Maintains pool of SQLAlchemy/asyncpg connections per dataset; uses DSNs from registry.
  - Supports read-only credentials; enforces connection limits per dataset.
- **Query Planner & Orchestrator**:
  - Receives structured query plan from LLM (e.g., list of sub-queries referencing dataset aliases).
  - Validates dataset IDs against registry, ensures required joins/aggregations respect weighting/business rules.
  - Executes sub-queries sequentially or in parallel via async tasks; merges results with Pandas/Polars for light transformations.
  - Applies limit/aggregation guardrails (max 5 raw rows, persona-level shaping).
- **Result Shaper**:
  - Applies weight calculations (sum(weights) vs. sum(weighted_metric)).
  - Converts results into persona narratives (Female 25-34 NCCS A, etc.).
  - Normalizes categorical merges (A/A1, C, D/E → C/D/E) before returning to LLM.
- **Caching Strategy**:
  - Metadata cache (Redis) keyed by dataset ID, invalidated on registry updates.
  - Query result cache for repeated prompts (short TTL, keyed by normalized query payload + persona).
- **Guardrails & Sanitizers**:
  - SQL linting (sqlglot/sqlparse) to block non-SELECT, DDL, cross-dataset unapproved operations.
  - Token budget estimator: refuses to return giant payloads, suggests query refinement to LLM.

### 4.3 LLM Orchestration & Context Layering
- **Context Graph**:
  - Level 0 (global): business rules, weighting principles, global guardrails.
  - Level 1 (dataset summary): short descriptions, high-level schema, usage tags (pulled dynamically based on user prompt classification).
  - Level 2 (table detail): per-table schemas, column stats only fetched when LLM selects datasets.
  - Level 3 (sample values, quality notes): fetched on-demand after user confirmation or deeper drill downs.
- **Prompt Router**:
  - Detects tasks (dataset suggestion, query planning, narrative generation) to load minimal context.
  - For multi-step queries, uses ReAct-style messaging with MCP tools: `list_datasets`, `describe_table`, `run_query`.
- **Function Registry Exposure**:
  - Define MCP tools dynamically from registry (e.g., `execute_sql(dataset_id, sql, limit)`).
  - Provide `list_available_tools` MCP capability so clients discover functions; if tool missing, respond with available list.
- **LLM Provider Strategy**:
  - Primary: OpenAI GPT-4.1-Mini.
  - Optional fallback: GPT-4-Turbo (for generative narrative) or local/in-house model once available.
  - Rate limiting & cost control via API gateway with per-user quotas.
- **Telemetry**:
  - Log prompt/response metadata (not raw data unless necessary) for audit/troubleshooting.

### 4.4 UI & UX Surfaces
- **Frontend Stack**: lightweight React/Next.js or Remix app deployed separately (Render static site or Vercel); communicates with control-plane APIs.
- **Dataset Onboarding Wizard**:
  - Step 1: enter connection string/credentials (secured input).
  - Step 2: preview inferred schema & LLM-generated metadata; allow edits, add category tags, dataset owner.
  - Step 3: review quality suggestions & approve.
- **Dataset Explorer**:
  - Card/grid view with short description, date coverage, persona usage tags, last refreshed.
  - Search/filter across semantic tags (LLM embedding search).
- **Query Workspace**:
  - Chat-style interface showing LLM conversation, executed sub-queries (with dataset references), response narratives.
  - Option to pin persona context (e.g., “Female 25-34”).
- **Observability Dashboard**:
  - Table and charts for questions asked by timestamp, LLM tool (ChatGPT/Claude/Manus), dataset usage, latency, errors.
  - Drill into individual sessions, view sanitized prompts/responses, SQL snippets, execution stats.

### 4.5 Shared Infrastructure
- **Metadata Database**: Managed Postgres (Render PostgreSQL to start; plan to migrate to AWS RDS/Azure Flexible Server). Tables for datasets, schemas, tables, columns, LLM metadata, connection secrets (encrypted), query logs.
- **Message Queue / Task Runner**: Redis-backed Celery/RQ for async profiling & LLM metadata generation; double as cache.
- **File/Object Storage**: Optional S3-compatible bucket for larger schema exports or logs.
- **Infra as Code**: Dockerfile + Render.yaml today; plan to introduce Terraform or Pulumi for multi-env cloud deployment.
- **CI/CD**: GitHub Actions pipeline to run tests (unit, integration with ephemeral Postgres), linting, container build, deployment triggers to Render (web service + worker).

## 5. Key Data Flows

### 5.1 Dataset Onboarding
1. Analyst enters connection info in UI; backend validates connectivity with read-only credentials.
2. Registry stores dataset in `draft` state; secrets kept encrypted (KMS/Env).
3. Async job runs schema profiler → captures schema stats, sample rows, data volume, weight column presence.
4. Profiler triggers LLM Metadata Service; GPT-4.1-Mini produces description, usage suggestions, improvement notes.
5. Human reviewer edits/approves metadata in UI; dataset transitions to `approved`.
6. Control plane publishes `dataset_activated` event; data plane reloads connection config, invalidates caches.
7. MCP server updates dynamic tool registry (dataset list now exposed immediately, no redeploy).

### 5.2 Analyst Query Workflow
1. User asks question via connected LLM (e.g., ChatGPT with MCP connector).
2. MCP server routes request to prompt router; quick intent classification using global context only.
3. System selects candidate datasets (Level 1 context) based on semantic match and usage tags.
4. LLM drafts query plan referencing dataset IDs; if deeper detail needed, server fetches Level 2 schema snippets on-demand.
5. Query orchestrator validates plan, supplements weight logic, executes SQL sub-queries.
6. Result shaper aggregates, applies persona weighting rules, trims raw rows to ≤5 if necessary.
7. LLM produces narrative output; conversation logged with metadata (latency, datasets, tool).
8. Logs available in dashboard; alerts fired on failures/slow queries.

### 5.3 Metadata Refresh Cycle
- Scheduled job re-runs schema profiler nightly/weekly to detect drift.
- Major changes (new columns, data volume shifts) trigger notification + optional LLM metadata refresh.
- If dataset deprecated, mark inactive → MCP tool registry automatically hides it; connections closed gracefully.

## 6. Technology Selections & Decision Points
- **API stack**: FastAPI + Pydantic for control plane; keep FastMCP server for MCP transport. Consider splitting into two services (control-api + mcp-gateway) for clarity.
- **Database layer**: SQLAlchemy 2.0 with async support; alembic for migrations.
- **Workers**: Celery (with Redis broker) or Prefect/Temporal if workflow orchestration becomes complex.
- **LLM integration**: OpenAI SDK with retry/backoff, cache prompt templates in Git, store prompt/response IDs for traceability.
- **Schema profiling**: Use `sqlalchemy-inspect` + `pandas-profiling`-style stats; for huge tables, sample using `TABLESAMPLE BERNOULLI`.
- **Deployment**:
  - **Phase 1 (current)**: Render Web Service + Render Background Worker + Render PostgreSQL.
  - **Phase 2**: Containerize (Docker), deploy to AWS ECS Fargate or Azure Container Apps; use managed Postgres, Elasticache, CloudWatch/Prometheus for logging/metrics.
  - Provide Terraform modules for repeatable setup once moving beyond Render.
- **Observability**: OpenTelemetry instrumentation → export to Honeycomb/DataDog; structured logs (JSON) shipped via Logtail/Papertrail initially.
- **Testing**: Unit tests for query planning, metadata generation prompts; integration tests using ephemeral Postgres with seeded synthetic datasets; contract tests for MCP tools.

## 7. MCP Integration Strategy
- Expose MCP tools:
  - `list_datasets()` → returns active dataset summaries (ID, description, date range, usage tags).
  - `describe_dataset(dataset_id)` → Level 2 schema + key metrics.
  - `execute_sql(dataset_id, sql, limit, persona)` → enforces guardrails, injects weighting hints.
  - `run_query_plan(plan_json)` → advanced multi-dataset orchestration (LLM sends structured plan).
  - `get_recent_queries(dataset_id, limit)` → supports follow-up questions with context.
- Tools registered dynamically from registry; changes reflected immediately in MCP handshake response (no redeploy).
- Provide capability discovery endpoint so external LLMs know available tools; handle unsupported tool requests by returning list of valid ones.
- Maintain compatibility with ChatGPT/Claude HTTP transport; consider websockets later for streaming progress tokens on long-running queries.

## 8. Scaling & Performance Considerations
- Connection pooling per dataset with async execution to support ~30 sub-queries per prompt.
- Pre-compute common aggregates/personas and cache narratives for high-traffic questions.
- Use read replicas or materialized views for heavy event-level tables; optionally ingest summaries into dedicated analytics schema.
- Implement circuit breakers per dataset (if slow/failing, degrade gracefully and notify user).
- Token optimization: progressive disclosure, summarizing large schemas, instruct LLM to request targeted info instead of full dumps.
- Future-proof for multi-tenant (namespaces per team) by tagging datasets and scoping MCP tools.

## 9. Security & Governance
- Network: restrict outbound access from data plane to whitelisted database hosts; use TLS.
- Secrets: store encrypted at rest; rotate credentials automatically where possible.
- Authentication: MVP can rely on shared internal login; plan for SSO (Okta/Azure AD) and dataset-level access rules.
- Auditing: retain query logs (metadata + hashed prompt) for ≥90 days; capture who executed, which datasets, duration, resulting row counts.
- Data minimization: enforce 5-row limit, persona aggregation; filter PII fields in metadata summaries before passing to LLM.
- Compliance readiness: document data flows, implement deletion hooks if required.

## 10. Operational Plan
- **Environments**: dev (local Docker Compose), staging (Render free tier), prod (Render paid tier or managed cloud).
- **CI/CD pipeline**:
  - Lint/type check (ruff, mypy), unit/integration tests.
  - Build/push Docker image.
  - Deploy via Render API or GitHub Actions workflow dispatch.
- **Monitoring**:
  - Health checks at `/health` (control) and `/mcp/health`.
  - Metrics: request latency, query duration, LLM response time, token usage, cache hit rates.
  - Alerts on high error rate, slow queries, LLM failures.
- **Incident Response**:
  - On-call playbook with runbooks for common failures (DB connection, LLM quota).
  - Rollback strategy: previous container image + database migrations rollback steps.
- **Governance Cadence**:
  - Weekly metadata QA review.
  - Monthly dataset audit (weight validation, coverage).
  - Quarterly security review (dependabot, vulnerability scans).

## 11. Open Questions & Next Steps
- Confirm long-term deployment target (Render vs. AWS/Azure) to scope IaC investment.
- Decide whether cross-dataset queries should be federated live or pre-modeled into a unified analytics warehouse.
- Evaluate need for role-based access once user count rises (dataset-specific permissions).
- Determine retention/obfuscation strategy for query logs to balance analytics with privacy.
- Prototype dataset onboarding flow → validate LLM metadata quality and edit UX.
- Build initial backlog:
  1. Set up metadata DB schema & control-plane API.
  2. Implement dataset onboarding job + LLM metadata generation (GPT-4.1-Mini).
  3. Extend FastMCP server to use registry-driven tools and progressive context logic.
  4. Ship minimal UI (dataset list, onboarding wizard, query log table).
  5. Add observability pipeline (logging, metrics).

