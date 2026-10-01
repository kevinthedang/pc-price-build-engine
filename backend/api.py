from fastapi import FastAPI

app = FastAPI(title = "PC Building Optimizer API")

@app.get("/api/health")
def health_check():
    return {"status": "ok"}