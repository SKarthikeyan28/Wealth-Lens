from fastapi import FastAPI

app = FastAPI(
    title="Wealth-Lens",
    description="SG Personal Finance Optimizer — educational analysis tool, not financial advice.",
    version="0.1.0",
)


@app.get("/")
def root():
    return {"status": "ok", "version": "0.1.0"}
