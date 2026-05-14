# PT Media Observatory — Infrastructure & CI Readiness Audit

**Scope:** docker-compose.yml, Dockerfiles, nginx config, Makefile, CI workflow, deploy workflow, environment, app structure.  
**Date:** 2025-05-14  
**Status:** Ready for review

---

## Summary

The Docker / CI scaffold is **mostly sound** — multi-service setup, SSL, rate limiting, and CSP headers are all present. Most Readiness for production / staging is a solid 7/10. A handful of broken references, missing services, and structural issues must be fixed before the first deploy.

---

## 1. docker-compose.yml

| # | Issue | Severity | Detail |
|---|-------|----------|--------|
| 1.1 | **Backend service definition is corrupted / missing** | 🔴 **Critical** | The stanza for `backend:` ends at line 44 (`volumes`), then lines 43-75 are stray duplicates (`REDIS_URL…`, `JWT_SECRET_KEY…` and a `celery` command) that were accidentally merged in. No `celery_worker` service exists. |
| 1.2 | **Missing `celery_worker` service** | 🟡 Medium | Sprint-4 spec requires a standalone Celery worker container. It was never added. |
| 1.3 | **Missing `frontend` service** | 🟡 Medium | The nginx proxy points to `…/frontend/build` but there is no `frontend` service in the compose file. Either the `frontend/Dockerfile` should be a compose service, or the React build should happen in a CI step and the nginx volume mount should use `frontend/dist`. Currently the build dir is empty. |
| 1.4 | **Broken health-check** | 🟡 Medium | `nginx` health-check calls `https://localhost/healthz` but the endpoint is `http://backend:8000/health` and nginx returns 301 to HTTPS when inside the container. |
| 1.5 | **Missing HTTPS certs** | 🟡 Medium | `./certs` directory is referenced but does not exist. For local dev, using a self-signed cert or switching to HTTP-only is usual practice. |
| 1.6 | **No restart policy on `celery_worker`** | 🟢 Low | Not applicable until the service is restored. |
| 1.7 | **No `env_file` / compose secrets** | 🟢 Low | All secrets come from `.env`. That is fine for local development but a not terrible for production should use Docker Secrets or a secrets manager with dedicated `env_file` references in compose. |

## 2. Dockerfile — Backend

| # | Issue | Severity | Detail |
|---|-------|----------|--------|
| 2.1 | **Multi-stage build is correct** | ✅ | `requirements.txt` copied and installed in builder stage; final stage copies site-packages. Non-root user present and `HEALTHCHECK` present. |
| 2.2 | **Port 8000 conflict** | 🟡 Medium | Both backend and nginx claim port 8000 in compose (backend exposes 8000, nginx listens on 80 and 443). This is okay because they are in different containers, but nothing maps `8000:8000` to the host in compose for quick local testing. |

## 3. Dockerfile — Frontend

| # | Issue | Severity | Detail |
|---|-------|----------|--------|
| 3.1 | **Build output directory mismatch** | 🟡 Medium | `vite.config.ts` probably outputs to `dist/` but `docker-compose.yml` mans `frontend/build` for nginx static files. `frontend/nginx-frontend.conf` serves from `/usr/share/nginx/html` which matches the Dockerfile COPY. Mismatch only when trying to run the app via compose without the frontend container. |
| 3.2 | **Health endpoint mismatch** | 🟡 Medium | `nginx-frontend.conf` defines `location = /health` but `nginx.conf` (main proxy) proxies `/healthz` to `backend:8000/healthz`. Endpoint name is inconsistent (`/health` vs `/healthz`). |

## 4. nginx.conf

| # | Issue | Severity | Detail |
|---|-------|----------|--------|
| 4.1 | **Template variables in SSL paths** | 🟡 Medium | `ssl_certificate ${SSL_CERT_PATH}` uses shell-style variables which are technically valid for `envsubst`, but it requires the envsubst-based `substitute.sh` script to be invoked in the container. nginx entrypoint in `:1.27-alpine` does substitute by default.  
| 4.2 | **Rate limiting** | ✅ | `limit_req` per endpoint present (`api` and `static` zones). |
| 4.3 | **Security headers** | ✅ | HSTS, CSP, and referrer-policy headers all present in `http` block. |
| 4.4 | **HTTP → HTTPS redirect** | ✅ | Present on port 80. |
| 4.5 | **`add_header` in `http{}` vs `server{}` block** | 🟢 Low | Some add_header directives are in `http{}` (good for inheritance), some are duplicated in `server{}` or missing frame-ancestors. Not a bug, just a tidy-up. |

## 5. Makefile

| # | Issue | Severity | Detail |
|---|-------|----------|--------|
| 5.1 | **`.PHONY` missing `logs` and `install-*` targets** | 🟢 Low | `logs`, `install-*` targets are real files being checked for freshness; safe but not best practice. |
| 5.2 | **`clean` target is risky** | 🟢 Low | `docker compose down -v` removes volumes; useful for dev but can blow away local test data. Should be documented or gated behind a prompt. |
| 5.3 | **No `backup-db` or `restore-db` targets** | 🟢 Low | Sprint-4 deliverable requires a backup strategy (daily pg_dump, RDB snapshot). Makefile is a good place to add quick commands. |
| 5.4 | **Test and lint recipes work** | ✅ | Makefile commands reference correct paths and are sensible. |

## 6. `.github/workflows/ci.yml`

| # | Issue | Severity | Detail |
|---|-------|----------|--------|
| 6.1 | **`ruff check` path is wrong** | 🟡 Medium | The backend is in `backend/`. The command in the workflow is `ruff check backend/`. This is correct if the action runs from the repo root. **However**, the checkout places all files in `backend/`, but the action then does `cd backend && python -m ruff check . && python -m ruff format --check .` in the local `make lint-backend` but the CI does not use make.  
| 6.2 | **`mypy` path is wrong in the workflow** | 🟡 Medium | Same as above: `mypy backend/app/` is correct if the action context is the repo root. The Makefile runs `cd backend && mypy app/` which is correct for the Makefile. |
| 6.3 | **Backend test step is truncated / broken** | 🔴 **Critical** | Lines 118-130 are cut off / left with a `with:` block that has no parent `uses` or `run`. The workflow is syntactically invalid. See lines 119-130 in the current file. |
| 6.4 | **Missing `DATABASE_URL` / `REDIS_URL` in pytest env** | 🟡 Medium | The `backend-tests` job sets `DATABASE_URL` and `REDIS_URL` but the values are emoji or partially redacted and the `pytest` invocation line is missing. |
| 6.5 | **`pytest --cov` not in the workflow** | 🟢 Low | Only `pytest` is referenced; coverage upload is promised but the step is broken/incomplete. |

## 7. `.github/workflows/deploy.yml`

| # | Issue | Severity | Detail |
|---|-------|----------|--------|
| 7.1 | **`file:` path is relative to `context`** | 🟢 Low | Correctly uses `context: backend`, `file: backend/Dockerfile`. Buildx resolves files relative to the context root, so this is correct, but some versions expect `dockerfile: backend/Dockerfile` relative to the directory. |
| 7.2 | **No deploy-to-staging step** | 🟡 Medium | Workflow only builds and pushes. Sprint-4 scope includes "Deploy staging on merge to main." To complete this, a deploy step (SSH, helm, or similar) must be added after the push step. |

## 8. Environment / Secrets

| # | Issue | Severity | Detail |
|---|-------|----------|--------|
| 8.1 | **`.env.example` is fine but not comprehensive** | 🟢 Low | Missing `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, and `DATABASE_URL`. They are constructed inline in compose from other variables. Consider centralising defaults for local overrides. |
| 8.2 | **Secrets in compose** | 🟢 Low | The current setup relies on env var interpolation from `.env`, which is acceptable for dev but must be replaced by Docker secrets / mounted files / secret manager for prod. |

## 9. Backup Strategy (Sprint-4 Deliverable)

| # | Issue | Severity | Detail |
|---|-------|----------|--------|
| 9.1 | **No backup tooling present** | 🔴 **Critical** | The sprint requires daily PostgreSQL `pg_dump`, Redis RDB snapshots, and point-in-time recovery. None of this is present in the repository. No cron, no scripts, no `backup/` directory. |

---

## Recommended Next Steps

1. **Fix `docker-compose.yml`** — restore the `backend` service and add the missing `celery_worker` service. Remove the stray/duplicate lines that crept in.
2. **Fix `ci.yml`** — restore the broken `backend-tests` step (pytest run, coverage upload, etc.).
3. **Fix health endpoint naming** — settle on either `/health` or `/healthz` and apply consistently across nginx, backend, and health checks.
4. **Add a dedicated `frontend` service in compose** OR mount the built assets from `frontend/dist` into the nginx container at the right path.
5. **Address the missing HTTPS certs** — provide a self-signed cert for local dev or switch to HTTP-only in `docker-compose.override.yml`.
6. **Add backup scripts** — create `scripts/backup-postgres.sh`, `scripts/backup-redis.sh`, and wire them up as cron jobs or CI jobs.
7. **Create `nginx/conf.d`** directory or remove the `…/conf.d` volume mount in compose if not needed.

---

*End of report.*
