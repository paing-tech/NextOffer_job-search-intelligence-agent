"""NextOffer API. Google connections and agent tools arrive in later milestones."""

from fastapi import FastAPI

app = FastAPI(title="NextOffer API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "nextoffer-api"}
