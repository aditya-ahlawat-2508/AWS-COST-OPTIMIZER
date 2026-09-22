from fastapi import FastAPI

from .routers import accounts, auth, findings

app = FastAPI(title="CloudWise API")

app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(findings.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
