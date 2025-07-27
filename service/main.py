from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from contextlib import asynccontextmanager
from transformers import pipeline
import os
import logging

logger = logging.getLogger(__name__)
sentiment_analyzer = None

class TextIn(BaseModel):
    text: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    global sentiment_analyzer
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    model_name = os.environ.get("MODEL_NAME", "ProsusAI/finbert")
    logger.info(f"Loading sentiment analysis model {model_name}...")
    sentiment_analyzer = pipeline(
        "sentiment-analysis",
        model=model_name,
        device=-1,
        top_k=None
    )
    logger.info("Model loaded successfully")
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/health")
def health():
    return {
        "success": sentiment_analyzer is not None
    }

@app.head("/health")
def health_head():
    return

@app.post("/analyze")
async def analyse(input: TextIn):
    global sentiment_analyzer
    if sentiment_analyzer is None:
        return {
            "success": False,
            "message": "Model not loaded"
        }
    results = sentiment_analyzer(input.text)
    return {
        "success": True,
        "data": results
    }

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), reload=False)