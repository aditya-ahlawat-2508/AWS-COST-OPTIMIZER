from fastapi import FastAPI

from .routers import accounts, auth, billing, change_requests, copilot, demo, findings, spend

app = FastAPI(title="CloudWise API")

app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(findings.router)
app.include_router(spend.router)
app.include_router(copilot.router)
app.include_router(change_requests.router)
app.include_router(billing.router)
app.include_router(demo.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
