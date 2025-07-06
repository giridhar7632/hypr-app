import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import aiohttp
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import feedparser
from transformers import pipeline
import re
import os
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Heartbeat interval (seconds)
PING_INTERVAL = 20

# Global variables for model and data
sentiment_analyzer = None
all_news: List[dict] = []
news_cache: List[dict] = []
sentiment_history: Dict[str, List[dict]] = {}
news_task: Optional[asyncio.Task] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global sentiment_analyzer, news_task
    # Startup: load model
    logger.info("Loading sentiment analysis model...")
    sentiment_analyzer = pipeline(
        "sentiment-analysis",
        model="ProsusAI/finbert",
        return_all_scores=True
    )
    logger.info("Model loaded successfully!")

    # Start news collection background task
    news_task = asyncio.create_task(news_collector_task())
    logger.info("News collector task started")

    yield

    # Shutdown: cancel background task
    logger.info("Shutting down...")
    if news_task and not news_task.done():
        news_task.cancel()
        try:
            await news_task
        except asyncio.CancelledError:
            logger.info("News collector task cancelled")

app = FastAPI(title="Market Sentiment API", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data models
class NewsItem(BaseModel):
    title: str
    summary: str
    published: str
    source: str
    sentiment_score: float
    sentiment_label: str
    symbols: List[str]

# WebSocket manager
typing_dict = Optional[Dict]
class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        if not self.active_connections:
            return
        disconnected = []
        text = json.dumps(message)
        for ws in self.active_connections:
            try:
                await ws.send_text(text)
            except Exception as e:
                logger.error(f"Error sending message: {e}")
                disconnected.append(ws)
        for ws in disconnected:
            if ws in self.active_connections:
                self.active_connections.remove(ws)

manager = WebSocketManager()

# News sources and tracked symbols
# RSS_FEEDS = {
#     "MarketWatch": "https://feeds.marketwatch.com/marketwatch/topstories/",
#     "Yahoo Finance": "https://feeds.finance.yahoo.com/rss/2.0/headline",
#     "CNN Business": "http://rss.cnn.com/rss/money_latest.rss",
#     "Bloomberg": "https://feeds.bloomberg.com/markets/news.rss"
# }
TRACKED_SYMBOLS = ["AAPL","GOOGL","MSFT","TSLA","AMZN","META","NVDA","SPY","QQQ"]
def get_symbol_feeds(symbols: List[str]) -> Dict[str, str]:
    base = "https://feeds.finance.yahoo.com/rss/2.0/headline?s={}&region=US&lang=en-US"
    return {f"Yahoo Finance {sym}": base.format(sym) for sym in symbols}

RSS_FEEDS = {
    # "Finviz": "https://finviz.com/feed.ashx",
    # "Seeking Alpha": "https://seekingalpha.com/market_currents.xml"
}
RSS_FEEDS.update(get_symbol_feeds(TRACKED_SYMBOLS))

print('RSS_FEEDS', RSS_FEEDS)

# Utility functions
def extract_symbols(text: str) -> List[str]:
    symbols = re.findall(r"([A-Z]{4,5})", text)
    words = text.upper().split()
    for symbol in TRACKED_SYMBOLS:
        if symbol in words:
            symbols.append(symbol)
    return list(set(symbols))

def analyze_sentiment(text: str) -> tuple:
    global sentiment_analyzer
    if not sentiment_analyzer:
        return 0.0, "neutral", 0.5
    clean_text = re.sub(r'http\S+', '', text)
    clean_text = re.sub(r'@\w+', '', clean_text).strip()
    if not clean_text:
        print('no clean text in ', text)
        return 0.0, "neutral", 0.5
    
    # print('clean text', clean_text)
    results = sentiment_analyzer(clean_text[:512])
    scores = {item['label']: item['score'] for item in results[0]}
    # print('scores', scores)
    pos = scores.get('positive', 0)
    neg = scores.get('negative', 0)
    neu = scores.get('neutral', 0)
    sentiment = pos - neg
    if sentiment > 0.1:
        label = 'positive'
    elif sentiment < -0.1:
        label = 'negative'
    else:
        label = 'neutral'
    confidence = max(pos, neg, neu)
    return sentiment, label, confidence

def generate_trading_signal(sentiment_score: float, confidence: float) -> str:
    if confidence < 0.6:
        return "HOLD"
    if sentiment_score > 0.3:
        return "BUY"
    if sentiment_score < -0.3:
        return "SELL"
    return "HOLD"

# Fetch and process news
async def fetch_rss_news(session: aiohttp.ClientSession, name: str, url: str) -> List[dict]:
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/114.0.0.0 Safari/537.36"
            ),
            "Accept": "application/rss+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            content = await resp.text()

        feed = feedparser.parse(content)
        items = []
        for entry in feed.entries[:10]:
            title = entry.get('title', '')
            summary = entry.get('summary', entry.get('description', ''))
            published = entry.get('published', '')
            full = f"{title} {summary}"
            score, label, conf = analyze_sentiment(full)
            # print("- - - - - - - - - - - -")
            symbols = extract_symbols(full)
            # print(full, " extracted ", score, label, conf, symbols)
            items.append({
                'title': title,
                'summary': summary[:300] + '...' if len(summary) > 300 else summary,
                'published': published,
                'source': name,
                'sentiment_score': round(score, 3),
                'sentiment_label': label,
                'confidence': round(conf, 3),
                'symbols': symbols
            })
        return items
    except Exception as e:
        logger.error(f"Error fetching {name}: {e}")
        return []

async def collect_news():
    global all_news, news_cache, sentiment_history
    connector = aiohttp.TCPConnector(limit=10)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [fetch_rss_news(session, n, u) for n, u in RSS_FEEDS.items()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for res in results:
            if isinstance(res, list): all_news.extend(res)
        if not all_news:
            return
        news_cache = all_news[-50:]
        symbol_map: Dict[str, List[dict]] = {}
        for news in all_news:
            for sym in news['symbols']:
                symbol_map.setdefault(sym, []).append({
                    'sentiment': news['sentiment_score'],
                    'confidence': news['confidence']
                })
        now = datetime.now().isoformat()
        updates = []
        for sym in TRACKED_SYMBOLS:
            lst = symbol_map.get(sym, [])
            if lst:
                wsum = sum(x['sentiment'] * x['confidence'] for x in lst)
                total = sum(x['confidence'] for x in lst)
                avg = wsum / total if total else 0.0
                avg_conf = sum(x['confidence'] for x in lst) / len(lst)
            else:
                avg, avg_conf = 0.0, 0.5
            sig = generate_trading_signal(avg, avg_conf)
            data = {
                'symbol': sym,
                'sentiment': round(avg, 3),
                'timestamp': now,
                'signal': sig,
                'confidence': round(avg_conf, 3)
            }
            sentiment_history.setdefault(sym, []).append(data)
            sentiment_history[sym] = sentiment_history[sym][-100:]
            updates.append(data)
        await manager.broadcast({'type': 'sentiment_update', 'data': updates})
        await manager.broadcast({'type': 'news_update', 'data': all_news})
        logger.info(f"Processed {len(all_news)} news items, {len(updates)} sentiment updates")

async def news_collector_task():
    try:
        while True:
            await collect_news()
            await asyncio.sleep(300)
    except asyncio.CancelledError:
        logger.info("News collector task cancelled")
    except Exception as e:
        logger.error(f"News collector task error: {e}")
        await asyncio.sleep(60)

# HTTP Routes
@app.get("/")
async def root():
    return {"message": "Market Sentiment API", "status": "running"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "news_items": len(news_cache),
        "tracked_symbols": len(TRACKED_SYMBOLS),
        "model_loaded": sentiment_analyzer is not None
    }

@app.get("/news", response_model=List[NewsItem])
async def get_recent_news():
    return news_cache[-20:]

@app.get("/sentiment/{symbol}")
async def get_symbol_sentiment(symbol: str):
    sym = symbol.upper()
    if sym not in sentiment_history:
        raise HTTPException(status_code=404, detail="Symbol not found")
    return {"symbol": sym, "history": sentiment_history[sym][-50:], "current": sentiment_history[sym][-1]}

@app.get("/sentiment")
async def get_all_sentiment():
    return {s: sentiment_history[s][-1] for s in TRACKED_SYMBOLS if sentiment_history.get(s)}

# Heartbeat helper
async def heartbeat(ws: WebSocket):
    try:
        while True:
            await asyncio.sleep(PING_INTERVAL)
            await ws.send_text(json.dumps({"type": "ping"}))
    except Exception:
        return

# WebSocket endpoint with server-side heartbeat
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    hb_task = asyncio.create_task(heartbeat(ws))
    try:
        await ws.send_text(json.dumps({
            'type': 'initial_data',
            'news': all_news,
            'sentiment': {sym: sentiment_history.get(sym, [None])[-1] for sym in TRACKED_SYMBOLS}
        }))
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(ws)
    finally:
        hb_task.cancel()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        log_level="info"
    )
