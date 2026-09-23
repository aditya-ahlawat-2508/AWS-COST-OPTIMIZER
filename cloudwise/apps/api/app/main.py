import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import (
    accounts,
    anomalies,
    audit_log,
    auth,
    billing,
    budgets,
    change_requests,
    copilot,
    demo,
    findings,
    notifications,
    schedules,
    spend,
)

app = FastAPI(title="CloudWise API")

# apps/web (Next.js) calls this API directly from the browser, so it needs
# CORS — without it every fetch's preflight OPTIONS request gets a plain 405
# and the browser reports it to JS as an opaque "Failed to fetch", not the
# actual reason. CORS_ALLOWED_ORIGINS lets a real deployment restrict this to
# exact origins; the allow_origin_regex below covers any localhost dev port
# (`next dev` picks a different one whenever 3000 is taken), which is fine
# for local dev but never matches a real deployed origin.
_allowed_origins = {o for o in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",") if o}

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(_allowed_origins),
    allow_origin_regex=r"http://localhost:\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(findings.router)
app.include_router(spend.router)
app.include_router(copilot.router)
app.include_router(change_requests.router)
app.include_router(billing.router)
app.include_router(demo.router)
app.include_router(audit_log.router)
app.include_router(budgets.router)
app.include_router(anomalies.router)
app.include_router(schedules.router)
app.include_router(notifications.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
