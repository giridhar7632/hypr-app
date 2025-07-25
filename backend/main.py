from fastapi import FastAPI,Request, status, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import re
import aiohttp, asyncio
import logging
import requests
import finnhub
import pandas as pd
import yfinance as yf
from transformers import pipeline
from contextlib import asynccontextmanager
from curl_cffi import requests as curl_requests
from datetime import datetime, timedelta, timezone

from helpers import *
from config import settings
from database import supabase

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Heartbeat interval (seconds)
PING_INTERVAL = 20

# Global variables for model and data
engine = None
popular_quotes_task = None
sentiment_analyzer = None
finnhub_client = finnhub.Client(settings.FINNHUB_API_KEY)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: load model
    global sentiment_analyzer, popular_quotes_task
    logger.info("Loading sentiment analysis model...")
    sentiment_analyzer = pipeline(
        "sentiment-analysis",
        model="ProsusAI/finbert",
        top_k=None
    )
    logger.info("Model loaded successfully!")
 
    popular_quotes_task = asyncio.create_task(broadcast_popular_quotes())
    logger.info("Popular quotes task started successfully!")

    try:
        yield
    finally:
        popular_quotes_task.cancel()
        try:
            await popular_quotes_task
        except asyncio.CancelledError:
            logger.info("popular_quotes_task cancelled successfully")


app = FastAPI(title="Hypr API", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_company_info(ticker_symbol: str):
    """
    Get basic company info from the ticker symbol using Finnhub
    """
    profile = None
    result = supabase.table("company_info").select("*").eq("ticker", ticker_symbol).execute()

    if result.data:
        profile = result.data[0]
    else:
        profile = finnhub_client.company_profile2(symbol=ticker_symbol)

        if not profile or not profile.get("name"):
            logger.error(f"No profile data found for {ticker_symbol}")
            return {
                "error": f"Invalid ticker symbol: {ticker_symbol}",
                "name": ticker_symbol,
                "ticker": ticker_symbol
            }

        supabase.table("company_info").insert(profile).execute()
    
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

def get_financial_data(ticker_symbol, period="2mo", interval="1d"):
    """
    Fetching financial data of a company
    """
    try:
        # Create a session with Chrome impersonation using curl_requests
        session = curl_requests.Session(
            impersonate="chrome110",
            timeout=30,
            verify=True
        )
        
        # Configure headers to mimic a real browser
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        })

        print("DEBUG: Creating Ticker with session")
        company = yf.Ticker(ticker_symbol, session=session)
        
        # Get company description
        stock = yf.Ticker(ticker_symbol, session=session)
        description = stock.info.get('longBusinessSummary', 'No description available')
        
        print("DEBUG: Fetching historical data")
        # Use a longer period to ensure we have enough data
        hist = company.history(period=period, interval=interval)
        print("DEBUG: Historical data shape:", hist.shape)
        # print("DEBUG: Historical data columns:", hist.columns)
        # print("DEBUG: Historical data index:", hist.index)
        # print("DEBUG: Historical data sample:", hist.head())
        # print("DEBUG: Last 5 dates:", hist.index[-5:])

        if hist.empty:
            logger.error(f"No historical data found for {ticker_symbol}")
            return {
                "ticker": ticker_symbol,
                "error": f"No historical data found for {ticker_symbol}"
            }

        # daily metrics
        latest = hist.iloc[-1]
        prev_day = hist.iloc[-2]

        # calculating volatility (20-day std dev of return)
        returns = hist['Close'].pct_change()
        volatility = returns.std() * (256 ** 0.5) # annualized

        historical_data = {}
        for date, row in hist.iterrows():
            if date.tzinfo is not None:
                est_date = date.tz_convert('US/Eastern')
            else:
                est_date = date.tz_localize('UTC').tz_convert('US/Eastern')
            
            date_str = est_date.strftime('%Y-%m-%d')
            historical_data[date_str] = {
                'Open': float(row['Open']),
                'High': float(row['High']),
                'Low': float(row['Low']),
                'Close': float(row['Close']),
                'Volume': float(row['Volume'])
            }

        # print("DEBUG: Processed historical data keys:", list(historical_data.keys())[-5:])  # Show last 5 dates

        data = {
            "ticker": ticker_symbol,
            "current_price": float(latest['Close']),
            "opening_price": float(latest['Open']),
            "daily_high": float(latest['High']),
            "daily_low": float(latest['Low']),
            "price_change": float(((latest["Close"] - prev_day['Close']) / prev_day['Close']) * 100),
            "trading_volume": float(latest["Volume"]),
            "volatility": float(volatility),
            "historical_data": historical_data,
            "description": description
        }

        # print("DEBUG: Financial data structure:", json.dumps(data, indent=2))
        return data
    except Exception as e:
        import traceback
        print(f"Error retrieving financial data: {e}")
        print(f"Error type: {type(e)}")
        print(f"Error details: {str(e)}")
        print("Full traceback:")
        print(traceback.format_exc())
        return {
            "ticker": ticker_symbol,
            "error": f"Error retrieving financial data: {str(e)}"
        }

def analyze_sentiment(text: str) -> tuple:
    global sentiment_analyzer
    if not sentiment_analyzer:
        return (0.0, "neutral", 0.5)
    clean_text = re.sub(r'http\S+', '', text)
    clean_text = re.sub(r'@\w+', '', clean_text).strip()
    if not clean_text:
        print('no clean text in ', text)
        return (0.0, "neutral", 0.5)
    
    results = sentiment_analyzer(clean_text[:512])
    scores = {item['label']: item['score'] for item in results[0]}
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

    return (sentiment, label, confidence)

def get_news_and_analyze(company_name,ticker_symbol=None, days=2, max_articles=20):
    """
    Scrape news articles from multiple sources and extract keywords

    Parameters:
        ticker_symbol (str): Stock ticker for Finnhub API, defaults to None
        days (int): Number of days to look back
        max_articles (int): Maximum number of articles to process
    """

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    from_date = start_date.strftime('%Y-%m-%d')
    to_date = end_date.strftime('%Y-%m-%d')

    articles_data = []

    def process_article(article, articles_data):
        """Helper function to process individual articles"""
        try:
            text_to_analyze = article.get("headline", "") + " " + article.get("summary", "")
            sentiment, label, confidence = analyze_sentiment(text_to_analyze)
            article_data = {
                        "title":article.get("headline", ""),
                        "description":article.get("summary", ""),
                        "company_name":company_name,
                        "ticker":ticker_symbol,
                        "url":article.get("url", ""),
                        "published_at": datetime.fromtimestamp(article.get("datetime", 0)).isoformat(),
                        "source":article.get("source", "Finnhub"),
                        "sentiment":sentiment,
                        "label":label,
                        "confidence":confidence,
                    }

            articles_data.append(article_data)

        except Exception as e:
            print(f"Error processing article {article.get('url')}: {e}")

    if ticker_symbol:
        try:
            finnhub_news = finnhub_client.company_news(ticker_symbol, _from=from_date, to=to_date)
            for article in finnhub_news[:max_articles]:
                process_article(article, articles_data)

        except Exception as e:
            print(f"Error fetching news from Finnhub: {e}")

    return { "articles": articles_data }

def scrape_social_media(company_name: str, search_queries: List[str], max_results: int = 30):
    all_posts = []
    
    # Get Reddit posts
    reddit_posts = fetch_reddit_posts(company_name=company_name, search_queries=search_queries, analyze_sentiment=analyze_sentiment)
    all_posts.extend(reddit_posts)
    
    # Get Bluesky posts
    logger.info("Fetching Bluesky posts")
    bluesky_posts = fetch_bluesky_posts(company_name=company_name, search_queries=search_queries, analyze_sentiment=analyze_sentiment, max_results=max_results)
    all_posts.extend(bluesky_posts)
    logger.info(f"Total Bluesky posts collected: {len(all_posts)}")
    
    if not all_posts:
        return []
    
    # Calculate metrics
    sentiments = [post["sentiment"] for post in all_posts]
    avg_sentiment = sum(sentiments) / len(sentiments)
    
    # Get top posts by engagement
    top_posts = sorted(all_posts, key=lambda x: x["engagement"], reverse=True)[:10]
    
    return {
        "posts":all_posts,
        "top_posts":top_posts,
        "total_posts":len(all_posts),
        "avg_sentiment":avg_sentiment
    }

def get_alpha_vantage_trending():

    try:
        result = supabase.table("trending_stocks").select("*").execute()
        if result.data and result.data[0]:
            last_updated = datetime.fromisoformat(result.data[0]["last_updated"])
            now_utc = datetime.now(timezone.utc)

            if last_updated < now_utc - timedelta(days=1):
                data = fetch_alpha_vantage_trending()
                supabase.table("trending_stocks").insert(data).execute()
                return data
            else:
                return result.data[0]

        else:
            data = fetch_alpha_vantage_trending()
            supabase.table("trending_stocks").insert(data).execute()
            return data
        
    except Exception as e:
        print(f"Error with Alpha Vantage: {e}")
        return []

clients = set()
POPULAR_TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META"]
async def fetch_quote(session, symbol):
    url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={settings.FINNHUB_API_KEY}"
    async with session.get(url) as resp:
        data = await resp.json()
        return {
            "ticker": symbol,
            "price": data.get("c"),
            "change_amount": data.get("d"),
            "change_percentage": data.get("dp"),
        }

async def fetch_popular_quotes(symbols):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_quote(session, symbol) for symbol in symbols]
        quotes = await asyncio.gather(*tasks)
        return quotes
        
def save_quotes_to_db(quotes):
    now = datetime.utcnow().isoformat()
    for q in quotes:
        q["updated_at"] = now
    supabase.table("live_quotes").upsert(quotes).execute()

def fetch_cached_quotes_from_db():
    result = supabase.table("live_quotes").select("*").order("updated_at", desc=True).limit(10).execute()
    return result.data if result.data else []

async def broadcast_popular_quotes():
    while True:
        try:
            if is_market_open():
                quotes = await fetch_popular_quotes(POPULAR_TICKERS)
                save_quotes_to_db(quotes)
                logger.info("Broadcasting live quotes.")
            else:
                quotes = fetch_cached_quotes_from_db()
                logger.info("Broadcasting cached quotes (market closed).")

            disconnected = set()
            for client in clients:
                try:
                    await client.send_json({"type": "quotes", "data": quotes})
                except Exception:
                    disconnected.add(client)

            for client in disconnected:
                clients.remove(client)

        except Exception as e:
            logger.error(f"Error in quote broadcaster: {e}")

        await asyncio.sleep(15)


@app.websocket("/ws/popular")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.add(websocket)
    logger.info(f"WebSocket connection accepted: {len(clients)}")

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        clients.remove(websocket)

@app.get('/popular')
async def get_popular_quotes():
    if is_market_open():
        quotes = await fetch_popular_quotes(POPULAR_TICKERS)
        save_quotes_to_db(quotes)
        logger.info("Broadcasting live quotes.")
    else:
        quotes = fetch_cached_quotes_from_db()
        logger.info("Broadcasting cached quotes (market closed).")
    return quotes

@app.post('/analyze')
def analyze(data: AnalyzeItem):
    """Analyze stock endpoint with SSE support"""
    if not data:
        logger.error("No JSON data received in request")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No JSON data received"
        )
    print(data)
    ticker = data.symbol.upper()
    if not ticker:
        logger.error("No symbol provided in request")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No symbol provided"
        )

    force_refresh = data.force_refresh
    logger.info(f"Starting analysis for {ticker} (force_refresh={force_refresh})")

    def generate():
        try:
            # Check cache first
            now_utc = datetime.now(timezone.utc)
            logger.info(f"Current UTC time: {now_utc.isoformat()}")
            
            # Debug: Print the SQL query            
            result = supabase.table("data").select("last_run").contains("company_info", {"ticker": ticker}).order("last_run", desc=True).limit(1).execute()
            logger.info(f"Cache check result: {result}")

            # If force refresh is requested, skip cache check and run pipeline
            if force_refresh:
                logger.info("Force refresh requested, running pipeline")
                yield send_sse_message({"step": "cache", "status": "info", "message": "Force refresh requested, running pipeline"})
            elif result and result.data and result.data[0]:
                logger.info(f"Found cache entry with last_run: {result.data[0]}")
                
                # Check if cache is still valid (less than 1 hour old)
                cache_age = now_utc - datetime.fromisoformat(result.data[0]["last_run"])
                cache_age_hours = cache_age.total_seconds() / 3600
                logger.info(f"Current time (UTC): {now_utc.isoformat()}")
                logger.info(f"Last run time (UTC): {result.data[0]["last_run"]}")
                logger.info(f"Cache age: {cache_age_hours:.2f} hours")
                
                if cache_age < timedelta(hours=1):
                    logger.info(f"Using cached data (age: {cache_age_hours:.2f} hours)")
                    yield send_sse_message({"step": "cache", "status": "success", "message": f"Using cached data (age: {cache_age_hours:.2f} hours)"})
                        
                    # Debug: Print the data query
                    recent_data = supabase.table("data").select("*").eq("ticker", ticker).order("last_run", desc=True).limit(1).execute()
                    logger.info(f"Found cached data: {bool(recent_data)}")

                    if recent_data.data and recent_data.data[0]:
                        logger.info("Successfully reconstructed cached data")
                        yield send_sse_message({"step": "complete", "status": "success", "data": recent_data.data[0]})
                        return
                    else:
                        logger.info("No cached data found in database")
                        yield send_sse_message({"step": "cache", "status": "error", "message": "No cached data found"})
                else:
                    logger.info(f"Cache expired (age: {cache_age_hours:.2f} hours), running pipeline")
                    yield send_sse_message({"step": "cache", "status": "info", "message": f"Cache expired (age: {cache_age_hours:.2f} hours), running pipeline"})
            else:
                logger.info("No cache found, running pipeline")
                yield send_sse_message({"step": "cache", "status": "info", "message": "No cache found, running pipeline"})

            # Only run pipeline if cache is expired or no cache exists
            if force_refresh or not result or not result[0] or cache_age >= timedelta(hours=1):
                # Step 1: Financial data
                logger.info("Starting company info fetch")
                yield send_sse_message({"step": "company_info", "status": "started", "message": "Fetching company info"})
                company_info = get_company_info(ticker)
                
                if "error" in company_info:
                    logger.error(f"Error in company info: {company_info['error']}")
                    yield send_sse_message({"step": "company_info", "status": "error", "message": company_info["error"]})
                    return

                logger.info(f"Got company info for {company_info['name']}")
                yield send_sse_message({"step": "company_info", "status": "success", "message": f"Got data for {company_info['name']}"})

                # Step 2: Get financial data
                logger.info("Starting financial data fetch")
                yield send_sse_message({"step": "financial_data", "status": "started", "message": "Fetching financial data"})
                financial_data = get_financial_data(ticker, period="1mo")
                
                if "error" in financial_data:
                    logger.error(f"Error in financial data: {financial_data['error']}")
                    yield send_sse_message({"step": "financial_data", "status": "error", "message": financial_data["error"]})
                    return
                    
                logger.info("Got financial data")
                yield send_sse_message({"step": "financial_data", "status": "success", "message": "Got financial data"})

                # Step 3: News data
                logger.info("Starting news analysis")
                yield send_sse_message({"step": "news", "status": "started", "message": "Analyzing news"})
                news_data = get_news_and_analyze(company_name=company_info['name'], ticker_symbol=ticker, days=2)
                logger.info(f"Found {len(news_data['articles'])} articles")
                yield send_sse_message({"step": "news", "status": "success", "message": f"Found {len(news_data['articles'])} articles"})

                # Step 4: Expand keywords with AI
                logger.info("Starting keyword expansion")
                yield send_sse_message({"step": "keywords", "status": "started", "message": "Expanding keywords"})
                expanded_data = expand_keywords_and_generate_queries(company_info['name'], company_info.get('industry', 'N/A'))
                logger.info("Generated search queries")
                yield send_sse_message({"step": "keywords", "status": "success", "message": "Generated search queries"})

                # Step 5: Scraping social media
                logger.info("Starting social media analysis")
                yield send_sse_message({"step": "social", "status": "started", "message": "Analyzing social media"})
                social_data = scrape_social_media(company_name=company_info['name'], search_queries=expanded_data['search_queries'])
                logger.info(f"Analyzed {social_data['total_posts']} posts")
                yield send_sse_message({"step": "social", "status": "success", "message": f"Analyzed {social_data['total_posts']} posts"})

                # Step 6: Calculate metrics
                logger.info("Starting metrics calculation")
                yield send_sse_message({"step": "metrics", "status": "started", "message": "Calculating metrics"})
                scores = calculate_metrics(financial_data, news_data, social_data)
                logger.info("Calculated all scores")
                yield send_sse_message({"step": "metrics", "status": "success", "message": "Calculated all scores"})

                # Prepare the response structure
                res = {
                    "ticker": ticker,
                    "company_info": company_info,
                    "financial_data": financial_data,
                    "news_data": news_data,
                    "expanded_data": expanded_data,
                    "social_data": social_data,
                    "scores": scores,
                    "last_run": now_utc.isoformat()
                }

                try:
                    supabase.table("data").insert(res).execute()
                    yield send_sse_message({"step": "complete", "status": "success", "data": res})
                except Exception as e:
                    error_msg = f"Error in data processing: {str(e)}"
                    logger.error(error_msg)
                    yield send_sse_message({"step": "complete", "status": "error", "message": error_msg})
                    raise

        except Exception as e:
            error_msg = f"Error in pipeline: {str(e)}"
            logger.error(error_msg)
            yield send_sse_message({"step": "complete", "status": "error", "message": error_msg})
            raise

    return StreamingResponse(
        generate(),
        media_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )

@app.get("/company/{ticker}")
def get_company(ticker: str):
    return get_company_info(ticker)

@app.get("/financial/{ticker_symbol}")
def get_financial_data_route(ticker_symbol: str):
    return get_financial_data(ticker_symbol)

@app.get("/news/{ticker}")
def get_news_and_analyze_route(ticker: str):
    return get_news_and_analyze(company_name=ticker, ticker_symbol=ticker)

@app.get("/trending")
def get_alpha_vantage_trending_route():
    return get_alpha_vantage_trending()

# WebSocket manager
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
