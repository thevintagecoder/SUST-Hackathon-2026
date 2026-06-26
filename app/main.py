from fastapi import FastAPI

app = FastAPI(
    title="QueueStorm Investigator",
    version="1.0.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}