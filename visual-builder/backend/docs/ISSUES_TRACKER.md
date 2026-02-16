# AgentWeave Visual Builder - Issues Tracker

> Generated: 2026-02-15 | Reviewed: 2026-02-15
> Source: 5-agent deep analysis (Security, Data Integrity, Frontend, Infra/DevOps, Test Coverage)
> Review: Architect verification + rebuttal (H9 삭제, H8/H12 재분류, H4/M7 유지 근거 확인)
> Total: 43 issues (7 CRITICAL / 11 HIGH / 13 MEDIUM / 9 LOW) + Test Gaps

---

## Batch 1 - CRITICAL (Emergency) - COMPLETED

| # | Issue | Files | Status |
|---|-------|-------|--------|
| C1 | AuditLogger broken - `?` positional params + tuple, SQLAlchemyDBAdapter expects named `:params` + dict | `services/workflow_service.py:107-124` | DONE |
| C2 | JWT hardcoded fallback `"dev-secret-change-in-production"` allows token forgery | `auth/jwt.py:24-30` | DONE |
| C3 | `.gitignore` missing `.env`, `__pycache__/`, `*.db`, `*.pem`, `*.key` | `.gitignore` | DONE |
| C4 | IDOR - no ownership verification on webhooks, schedules, AB tests, versions, secrets | `api/webhooks.py`, `api/schedules.py`, `api/ab_tests.py`, `api/versions.py`, `api/secrets.py` | DONE |
| C5 | Debug WebSocket no workflow ownership check - any user can debug any workflow | `api/debug_ws.py:276-283` | DONE |
| C6 | `datetime.now()` naive local time in executor (13 locations) - duration calculation errors | `core/executor.py` (10), `services/workflow_service.py` (1), `dtos/execution.py` (1) | DONE |
| C7 | SQLite-only SQL: `datetime('now')` x6, `INSERT OR REPLACE` x1 - breaks on PostgreSQL | `core/executor.py`, `core/secret_store.py`, `services/workflow_service.py` | DONE |

**Resolution**: 6 parallel agents, 23 new tests, 357 backend tests passing. Architect APPROVED.

---

## Batch 2 - HIGH (Production Blockers) - COMPLETED

| # | Issue | Files | Status |
|---|-------|-------|--------|
| H1 | No TLS/SSL in Nginx - HTTP only (port 80) | `nginx/nginx.conf` | DONE |
| H2 | Dockerfile missing Alembic migration step | `Dockerfile`, `backend/docker-entrypoint.sh` | DONE |
| H3 | Docker-compose weak default passwords | `docker-compose.yml`, `.env.example` | DONE |
| H4 | Zustand full store subscription (5 components) - no selector used | `Canvas.tsx`, `PropertiesPanel.tsx`, `DataFlowPanel.tsx` | DONE |
| H5 | Horizontal scaling impossible - in-memory state | `config.py`, `main.py`, `background_executor.py`, `gunicorn.conf.py` | DONE |
| H6 | Token refresh endpoint no rate limit | `api/auth.py` | DONE |
| H7 | SSE streaming no connection limit per user | `api/executions.py` | DONE |
| H8 | `alert()` used in admin components (6 instances) | `Admin/UserManagement.tsx`, `Admin/ABTestDashboard.tsx` | DONE |
| H9 | `useSelectedNode` uses `JSON.stringify` equality - O(n) on every store update | `stores/workflowStore.ts:335-342` | DONE |
| H10 | Missing composite DB indexes | 5 models + Alembic migration `855d6a3cbef6` | DONE |
| H11 | Production code has `console.log` statements | `utils/codeGenerator/demo.ts` | DONE |

**Resolution**: 6 parallel agents + 2 post-review fixes, 6 new tests, 363 backend + 940 frontend tests passing. Architect APPROVED (9/11 first pass, 2 fixes applied).

---

## Batch 3 - MEDIUM (Quality/Stability) - COMPLETED

| # | Issue | Files | Status |
|---|-------|-------|--------|
| M1 | JWT token in WebSocket URL query parameter - visible in logs | `hooks/useDebugWebSocket.ts`, `api/debug_ws.py` | DONE |
| M2 | Auth token in localStorage (XSS risk) | `stores/authStore.ts` | DONE (documented trade-off) |
| M3 | `as any` type casts scattered (8+ in workflowStore) | `stores/workflowStore.ts` | DONE |
| M4 | CSP header duplication (nginx + backend) | `nginx/nginx.conf` | DONE |
| M5 | No per-route ErrorBoundary | `App.tsx` | DONE |
| M6 | Auth rehydration flash - login page flickers | `App.tsx` | DONE |
| M7 | UserAccount model uses timezone-aware datetime, all others use naive | `models/user.py` | DONE |
| M8 | CSV export formula injection risk | `Admin/AuditLogViewer.tsx` | DONE |
| M9 | Dual audit logging systems (AuditLogger raw SQL + AuditService ORM) | `services/workflow_service.py` | DONE |
| M10 | CORS allows all methods/headers (`*`), origins properly restricted | `main.py` | DONE |
| M11 | Undo snapshot on EVERY node change including drag | `stores/workflowStore.ts` | DONE |
| M12 | AuditLogViewer fetches on every filter keystroke | `Admin/AuditLogViewer.tsx` | DONE |
| M13 | Secrets not multi-tenant - currently admin-only (temp fix from C4) | `core/secret_store.py`, `api/secrets.py`, `models/secret.py` | DONE |

**Resolution**: 6+2 parallel agents, 21 new tests (M13), 384 backend + 941 frontend tests passing. Test fixes: App.test.tsx (persist mock), AuditLogViewer.test.tsx (debounce timing).

---

## Batch 4 - LOW (Polish/Hardening) - COMPLETED

| # | Issue | Files | Status |
|---|-------|-------|--------|
| L1 | No database backup strategy | `backend/docs/BACKUP_STRATEGY.md` | DONE |
| L2 | No test coverage thresholds in CI | `.github/workflows/ci.yml`, `vitest.config.ts` | DONE |
| L3 | No security scanning in CI | `.github/workflows/ci.yml` | DONE |
| L4 | Nginx container runs as root | `nginx/Dockerfile` | DONE |
| L5 | Missing `server_tokens off` in Nginx | `nginx/nginx.conf` | DONE |
| L6 | No health check readiness probe for Redis | `main.py` `/health/ready` endpoint | DONE |
| L7 | Gunicorn access log disabled | `gunicorn.conf.py` | DONE |
| L8 | Docker image size optimization | `Dockerfile`, `.dockerignore` | DONE (already optimized) |
| L9 | MCP health endpoint unauthenticated | `main.py` docstring | DONE (documented as intentional) |

**Resolution**: 6 parallel agents, 134 new tests (49 executor core + 41 security + 44 frontend pages/hooks), 474 backend + 985 frontend tests passing. Architect APPROVED (10/10 first pass).

---

## Test Coverage Critical Gaps - COMPLETED

| Area | Coverage | Status |
|------|----------|--------|
| `executor.py` core logic (`_topological_sort`, `_run_condition`, template engine, validation) | 49 tests | DONE |
| Webhook HMAC verification + replay prevention | 9 tests | DONE |
| MCP manager command injection prevention | 6 tests | DONE |
| SecretStore encryption/decryption | 8 tests | DONE |
| `WorkflowEditor` page | 6 tests | DONE |
| `WorkflowList` page | 27 tests | DONE |
| WebSocket hooks (`useDebugWebSocket`, `useExecutionUpdates`) | 11 tests | DONE |
| JWT security (expired, invalid sig, wrong algo, manipulated) | 7 tests | DONE |
| Input validation (SQL injection, XSS, null byte, oversized) | 6 tests | DONE |
| E2E user journeys (auth, workflow CRUD, editor, search/sort) | 36 Playwright tests | DONE |

---

## Review Log

### 2026-02-15: Architect Verification
- **H9 (execution_states duplicate migration)**: DELETED - reviewer confirmed only 1 migration exists
- **H8 (secrets multi-tenant)**: Downgraded HIGH → M13 (MEDIUM) - admin-only temp fix is documented, conscious decision
- **H12 (MCP health unauthenticated)**: Downgraded HIGH → L9 (LOW) - health checks typically public per k8s standard
- **H4 (Zustand store subscription)**: Kept HIGH - rebuttal accepted. `useWorkflowStore()` without selector subscribes to ENTIRE store regardless of destructured fields. Canvas is most performance-critical component.
- **M7 (UserAccount datetime)**: Kept MEDIUM - rebuttal accepted. `models/user.py` was NOT in C6 scope. Uses `datetime.now(UTC)` (aware) vs all other models using `datetime.now(UTC).replace(tzinfo=None)` (naive).

---

## Summary

| Batch | Issues | Status | Tests After |
|-------|--------|--------|-------------|
| Batch 1 (Critical) | 7 (C1-C7) | COMPLETED | 357 backend |
| Batch 2 (High) | 11 (H1-H11) | COMPLETED | 363 backend, 940 frontend |
| Batch 3 (Medium) | 13 (M1-M13) | COMPLETED | 384 backend, 941 frontend |
| Batch 4 (Low) | 9 (L1-L9) + Test Gaps | COMPLETED | 474 backend, 985 frontend |
| **Total** | **43** | **43/43 done** | **1,459 tests** |

### Changes from Original (45 → 43)
- Deleted: H9 (false positive - duplicate migration not found)
- Reclassified: H8 → M13, H12 → L9
- Renumbered: H13→H8, H14→H9, remaining shifted accordingly
