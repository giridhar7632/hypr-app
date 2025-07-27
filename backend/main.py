import asyncio
import aiohttp
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
import logging
import re
from transformers import pipeline
from typing import List, AsyncGenerator, Optional
import torch
from database import _select, _insert, _upsert
from config import settings
from helpers import *

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PING_INTERVAL = 20
POPULAR_TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META"]

sentiment_analyzer = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: load model
    import os
    os.environ["TOKENIZERS_PARALLELISM"] = "false"

    global sentiment_analyzer, popular_quotes_task
    logger.info("Loading sentiment analysis model...")
    sentiment_analyzer = pipeline(
        "sentiment-analysis",
        model="mrm8488/distilroberta-finetuned-financial-news-sentiment-analysis",
        device="cuda" if torch.cuda.is_available() else "cpu",
        top_k=None
    )
    logger.info("Model loaded successfully!")

    app.state.aiohttp_session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
    logger.info("HTTP session initialized.")
 
    popular_quotes_task = asyncio.create_task(broadcast_popular_quotes())
    logger.info("Popular quotes task started successfully!")

    try:
        yield
    finally:
        if app.state.aiohttp_session:
            await app.state.aiohttp_session.close()
        popular_quotes_task.cancel()
        try:
            await popular_quotes_task
        except asyncio.CancelledError:
            logger.info("popular_quotes_task cancelled successfully")


app = FastAPI(title="Hypr API", lifespan=lifespan)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def async_company_profile(ticker_symbol: str, session: aiohttp.ClientSession):
    url = f"https://finnhub.io/api/v1/stock/profile2?symbol={ticker_symbol}&token={settings.FINNHUB_API_KEY}"
    async with session.get(url) as response:
        if response.status == 200:
            return await response.json()
        else:
            return None

async def get_company_info(ticker_symbol: str):
    # Check cache
    cached_profile_res = await _select("company_info", filters=[("ticker", ticker_symbol)], limit=1)
    if cached_profile_res.data:
        profile = cached_profile_res.data[0]
        return {
            "name": profile.get("name", ticker_symbol),
            "ticker": profile.get("ticker", ticker_symbol),
            "country": profile.get("country", "Unknown"),
            "industry": profile.get("finnhubIndustry", "Unknown"),
            "exchange": profile.get("exchange", "Unknown"),
            "ipo": profile.get("ipo", "Unknown"),
            "marketCap": float(profile.get("marketCapitalization", 0)),
            "url": profile.get("weburl", "")
        }
    # Not found in cache, call external API
    profile = await async_company_profile(ticker_symbol, app.state.aiohttp_session)
    if not profile or not profile.get("name"):
        logger.error(f"No profile data found for {ticker_symbol}")
        return {
            "error": f"Invalid ticker symbol: {ticker_symbol}",
            "name": ticker_symbol,
            "ticker": ticker_symbol
        }
    # Save to DB
    await _upsert("company_info", profile)
    return {
        "name": profile.get("name", ticker_symbol),
        "ticker": profile.get("ticker", ticker_symbol),
        "country": profile.get("country", "Unknown"),
        "industry": profile.get("finnhubIndustry", "Unknown"),
        "exchange": profile.get("exchange", "Unknown"),
        "ipo": profile.get("ipo", "Unknown"),
        "marketCap": float(profile.get("marketCapitalization", 0)),
        "url": profile.get("weburl", "")
    }


async def get_financial_data(ticker_symbol: str, period="2mo", interval="1d"):
    session: aiohttp.ClientSession = app.state.aiohttp_session
    if session is None:
        raise RuntimeError("HTTP session is not initialized")
    import yfinance as yf
    from functools import partial

    try:

        def yf_fetch():
            company = yf.Ticker(ticker_symbol)
            hist = company.history(period=period, interval=interval)
            description = company.info.get("longBusinessSummary", "No description available")
            return hist, description

        hist, description = await asyncio.to_thread(yf_fetch)
        if hist.empty:
            logger.error(f"No historical data found for {ticker_symbol}")
            return {"ticker": ticker_symbol, "error": "No historical data found"}

        latest = hist.iloc[-1]
        prev_day = hist.iloc[-2]

        returns = hist["Close"].pct_change()
        volatility = returns.std() * (256 ** 0.5)  # annualized

        historical_data = {}
        for date, row in hist.iterrows():
            if date.tzinfo is not None:
                est_date = date.tz_convert("US/Eastern")
            else:
                est_date = date.tz_localize("UTC").tz_convert("US/Eastern")
            date_str = est_date.strftime("%Y-%m-%d")
            historical_data[date_str] = {
                "Open": float(row["Open"]),
                "High": float(row["High"]),
                "Low": float(row["Low"]),
                "Close": float(row["Close"]),
                "Volume": float(row["Volume"]),
            }

        return {
            "ticker": ticker_symbol,
            "current_price": float(latest["Close"]),
            "opening_price": float(latest["Open"]),
            "daily_high": float(latest["High"]),
            "daily_low": float(latest["Low"]),
            "price_change": float(((latest["Close"] - prev_day["Close"]) / prev_day["Close"]) * 100),
            "trading_volume": float(latest["Volume"]),
            "volatility": float(volatility),
            "historical_data": historical_data,
            "description": description,
        }
    except Exception as e:
        logger.error(f"Error retrieving financial data for {ticker_symbol}: {e}")
        return {"ticker": ticker_symbol, "error": str(e)}


def analyze_sentiment(text: str) -> tuple:
    global sentiment_analyzer
    if sentiment_analyzer is None:
        return 0.0, "neutral", 0.5

    clean_text = re.sub(r"http\S+", "", text)
    clean_text = re.sub(r"@\w+", "", clean_text).strip()
    if not clean_text:
        return 0.0, "neutral", 0.5

    results = sentiment_analyzer(clean_text[:512])
    scores = {item["label"]: item["score"] for item in results[0]}
    pos = scores.get("positive", 0)
    neg = scores.get("negative", 0)
    neu = scores.get("neutral", 0)
    sentiment = pos - neg
    if sentiment > 0.1:
        label = "positive"
    elif sentiment < -0.1:
        label = "negative"
    else:
        label = "neutral"
    confidence = max(pos, neg, neu)

    return sentiment, label, confidence


async def get_news_and_analyze(ticker_symbol: str, company_name: Optional[str] = None, days: int = 2, max_articles: int = 20):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    from_date = start_date.strftime("%Y-%m-%d")
    to_date = end_date.strftime("%Y-%m-%d")
    articles_data = []

    def process_article(article):
        try:
            text_to_analyze = article.get("headline", "") + " " + article.get("summary", "")
            sentiment, label, confidence = analyze_sentiment(text_to_analyze)
            return {
                "title": article.get("headline", ""),
                "description": article.get("summary", ""),
                "company_name": company_name,
                "ticker": ticker_symbol,
                "url": article.get("url", ""),
                "published_at": datetime.fromtimestamp(article.get("datetime", 0)).isoformat(),
                "source": article.get("source", "Finnhub"),
                "sentiment": sentiment,
                "label": label,
                "confidence": confidence,
            }
        except Exception as e:
            logger.error(f"Error processing article: {e}")
            return None

    try:
        if ticker_symbol:
            async def get_news(session):
                url = f"https://finnhub.io/api/v1/company-news?symbol={ticker_symbol}&from={from_date}&to={to_date}&token={settings.FINNHUB_API_KEY}"
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return None

            finnhub_news = await get_news(app.state.aiohttp_session)

            for article in finnhub_news[:max_articles]:
                article_data = process_article(article)
                if article_data:
                    articles_data.append(article_data)

        total_weight = sum(a["confidence"] for a in articles_data if a["confidence"] > 0)
        if total_weight == 0:
            return {"articles": articles_data, "avg_sentiment": 0}

        weighted_sentiment = sum(a["sentiment"] * a["confidence"] for a in articles_data) / total_weight
        return {"articles": articles_data, "avg_sentiment": weighted_sentiment}
    except Exception as e:
        logger.error(f"Error fetching news: {e}")
        return {"articles": [], "avg_sentiment": 0}

async def scrape_social_media(company_name: str, search_queries: List[str], max_results=30):
    loop = asyncio.get_event_loop()
    reddit_posts = await loop.run_in_executor(
      None,
      lambda: fetch_reddit_posts(company_name, search_queries, analyze_sentiment, limit=max_results)
    )
    bluesky_posts = await loop.run_in_executor(
      None,
      lambda: fetch_bluesky_posts(company_name, search_queries, analyze_sentiment, max_results=max_results)
    )
    all_posts = reddit_posts + bluesky_posts

    if not all_posts:
        return []

    sentiments = [post["sentiment"] for post in all_posts]
    avg_sentiment = sum(sentiments) / len(sentiments)

    top_posts = sorted(all_posts, key=lambda x: x.get("engagement", 0), reverse=True)[:10]

    return {
        "posts": all_posts,
        "top_posts": top_posts,
        "total_posts": len(all_posts),
        "avg_sentiment": avg_sentiment,
    }

async def get_alpha_vantage_trending():
    try:
        result = await _select("trending_stocks", order="last_updated", desc=True, limit=1)

        if result.data and result.data[0]:
            last_updated = datetime.fromisoformat(result.data[0]["last_updated"])
            now_utc = datetime.now(timezone.utc)

            if last_updated < now_utc - timedelta(days=1):
                data = await fetch_alpha_vantage_trending(app.state.aiohttp_session)
                await _upsert("trending_stocks", data)
                return data
            else:
                return result.data[0]
        else:
            data = await fetch_alpha_vantage_trending()
            await _upsert("trending_stocks", data)
            return data

    except Exception as e:
        print(f"Error with Alpha Vantage: {e}")
        return {"top_gainers": [], "top_losers": [], "most_actively_traded": []}

async def fetch_quote(session: aiohttp.ClientSession, symbol: str):
    url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={settings.FINNHUB_API_KEY}"
    async with session.get(url) as resp:
        if resp.status != 200:
            logger.warning(f"Failed to fetch quote for {symbol}: status {resp.status}")
            return {"ticker": symbol, "price": None, "change_amount": None, "change_percentage": None}
        data = await resp.json()
        return {
            "ticker": symbol,
            "price": data.get("c"),
            "change_amount": data.get("d"),
            "change_percentage": data.get("dp"),
        }

async def fetch_popular_quotes(symbols: List[str]):
    session = app.state.aiohttp_session
    if session is None:
        raise RuntimeError("HTTP session not initialized")
    tasks = [fetch_quote(session, symbol) for symbol in symbols]
    quotes = await asyncio.gather(*tasks, return_exceptions=True)
    result = []
    for res in quotes:
        if isinstance(res, Exception):
            logger.error(f"Error fetching quote: {res}")
        else:
            result.append(res)
    return result

async def save_quotes_to_db(quotes: List[dict]):
    now = datetime.utcnow().isoformat()
    for q in quotes:
        q["updated_at"] = now
    await _upsert("live_quotes", quotes)


async def fetch_cached_quotes_from_db():
    result = await _select("live_quotes", order="updated_at", desc=True, limit=10)
    return result.data if result.data else []


clients = set()

async def broadcast_popular_quotes():
    while True:
        try:
            if len(clients) > 0:
                if is_market_open():
                    quotes = await fetch_popular_quotes(POPULAR_TICKERS)
                    await save_quotes_to_db(quotes)
                    logger.info("Broadcasting live quotes.")
                else:
                    quotes = await fetch_cached_quotes_from_db()
                    logger.info("Broadcasting cached quotes (market closed).")

                disconnected = set()
                for client in clients:
                    try:
                        await client.send_json({"type": "quotes", "data": quotes})
                    except Exception as e:
                        logger.warning(f"WebSocket client disconnected: {e}")
                        disconnected.add(client)

                clients.difference_update(disconnected)
            else:
                logger.info("No WebSocket clients connected.")
        except Exception as e:
            logger.error(f"Error in quote broadcaster: {e}")

        await asyncio.sleep(15)

@app.websocket("/ws/popular")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.add(websocket)
    logger.info(f"WebSocket connection accepted. Total clients: {len(clients)}")

    try:
        while True:
            await websocket.receive_text()  # Keep connection alive, ignoring messages
    except WebSocketDisconnect:
        clients.remove(websocket)
        logger.info(f"WebSocket disconnected. Total clients: {len(clients)}")


@app.get("/popular")
async def get_popular_quotes():
    if is_market_open():
        quotes = await fetch_popular_quotes(POPULAR_TICKERS)
        await save_quotes_to_db(quotes)
        logger.info("Providing live quotes.")
    else:
        quotes = await fetch_cached_quotes_from_db()
        logger.info("Providing cached quotes (market closed).")
    return quotes


@app.post("/analyze")
async def analyze(data: AnalyzeItem):
    if not data or not data.symbol:
        raise HTTPException(status_code=400, detail="No symbol provided")
    ticker = data.symbol.upper()
    force_refresh = data.force_refresh
    logger.info(f"Starting analysis for {ticker} (force_refresh={force_refresh})")

    async def generate() -> AsyncGenerator[str, None]:
        try:
            now_utc = datetime.now(timezone.utc)
            # Check cache asynchronously
            cache_result = await _select(
                "data", filters=[("company_info->>ticker", ticker)], order="last_run", desc=True, limit=1
            )

            # Cache valid?
            if not force_refresh and cache_result.data and len(cache_result.data) > 0:
                last_run_str = cache_result.data[0]["last_run"]
                last_run_time = datetime.fromisoformat(last_run_str)
                if now_utc - last_run_time < timedelta(hours=1):
                    yield send_sse_message(
                        {"step": "cache", "status": "success", "message": "Using cached data."}
                    )
                    yield send_sse_message({"step": "complete", "status": "success", "data": cache_result.data[0]})
                    return
                else:
                    yield send_sse_message(
                        {"step": "cache", "status": "warning", "message": "Cache expired. Re-running analysis.", "data": cache_result.data[0]}
                    )

            # step 1: company info
            yield send_sse_message({"step": "company_info", "status": "started", "message": "Fetching company info"})
            company_info = await get_company_info(ticker)
            if "error" in company_info:
                yield send_sse_message({"step": "company_info", "status": "error", "message": company_info["error"]})
                return

            yield send_sse_message({"step": "company_info", "status": "success", "message": f"Got company info for {company_info['name']}"})

            # step 2: financial data
            yield send_sse_message({"step": "financial_data", "status": "started", "message": "Fetching financial data"})
            financial_data = await get_financial_data(ticker, period="2mo")
            if "error" in financial_data:
                yield send_sse_message({"step": "financial_data", "status": "error", "message": financial_data["error"]})
                return

            yield send_sse_message({"step": "financial_data", "status": "success", "message": "Got financial data"})

            # step 3: news and analyze
            yield send_sse_message({"step": "news", "status": "started", "message": "Analyzing news"})
            news_data = await get_news_and_analyze(company_info["name"], ticker_symbol=ticker)
            yield send_sse_message({"step": "news", "status": "success", "message": f"Found {len(news_data['articles'])} articles"})

            # step 4: expand keywords and generate queries
            yield send_sse_message({"step": "keywords", "status": "started", "message": "Expanding keywords"})
            expanded_data = await expand_keywords_and_generate_queries(company_info['name'], company_info.get('industry', 'N/A'))
            yield send_sse_message({"step": "keywords", "status": "success", "message": "Generated search queries"})

            # step 5: scrape social media
            yield send_sse_message({"step": "social", "status": "started", "message": "Analyzing social media"})
            social_data = await scrape_social_media(company_name=company_info['name'], search_queries=expanded_data['search_queries'])
            yield send_sse_message({"step": "social", "status": "success", "message": f"Analyzed {social_data['total_posts']} posts"})

            # step 6: calculate metrics
            yield send_sse_message({"step": "calculate", "status": "started", "message": "Calculating metrics"})
            scores = calculate_metrics(financial_data, news_data, social_data)
            yield send_sse_message({"step": "calculate", "status": "success", "message": "Calculated metrics"})

            # step 7: save to db
            result = {
                "ticker": ticker,
                "company_info": company_info,
                "financial_data": financial_data,
                "news_data": news_data,
                "expanded_data": expanded_data,
                "social_data": social_data,
                "scores": scores,
                "last_run": now_utc.isoformat(),
            }
            
            await _upsert("data", result)
            yield send_sse_message({"step": "complete", "status": "success", "data": result})

        except Exception as e:
            logger.error(f"Error in /analyze pipeline: {e}", exc_info=True)
            yield send_sse_message({"step": "complete", "status": "error", "message": str(e), "data": None})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/company/{ticker}")
async def get_company(ticker: str):
    return await get_company_info(ticker)

@app.get("/financial/{ticker_symbol}")
async def get_financial_data_route(ticker_symbol: str):
    return await get_financial_data(ticker_symbol=ticker_symbol)

@app.get("/news/{ticker}")
async def get_news_and_analyze_route(ticker: str):
    return await get_news_and_analyze(ticker_symbol=ticker)

@app.get("/trending")
async def get_alpha_vantage_trending_route():
    return await get_alpha_vantage_trending()

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
