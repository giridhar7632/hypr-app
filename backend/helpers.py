import pytz
import praw
import json
from openai import AsyncOpenAI
import numpy as np
import pandas as pd
from typing import List, Optional, Dict, Any
from config import settings
from pydantic import BaseModel
from datetime import datetime, time, timedelta, timezone, date

class AnalyzeItem(BaseModel):
    symbol: str
    force_refresh: Optional[bool] = False

def is_market_open():
    eastern = pytz.timezone("US/Eastern")
    now_eastern = datetime.now(eastern)
    market_open = time(9, 30)
    market_close = time(16, 0)
    return now_eastern.weekday() < 5 and market_open <= now_eastern.time() <= market_close

def json_serial(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def send_sse_message(message, event_type="message"):
    return f"event: {event_type}\ndata: {json.dumps(message, default=json_serial)}\n\n"

async def fetch_alpha_vantage_trending(session):
    url = f"https://www.alphavantage.co/query?function=TOP_GAINERS_LOSERS&apikey={settings.ALPHA_VANTAGE_API_KEY}"
    try:
        async with session.get(url) as response:
            if response.status != 200:
                print(f"Alpha Vantage API returned status {response.status}")
                return {"top_gainers": [], "top_losers": [], "most_actively_traded": []}
            data = await response.json()

            for k in ("top_gainers", "top_losers", "most_actively_traded"):
                data[k] = data.get(k, [])[:5]

            del data["metadata"]
            return data
    except Exception as e:
        print(f"Error fetching Alpha Vantage trending: {e}")
        return {"top_gainers": [], "top_losers": [], "most_actively_traded": []}

async def expand_keywords_and_generate_queries(company_name: str, industry: str):
    keywords = ["stock", "earnings", "price target", "news", "forecast"]
    default_queries = [f"{company_name} {kw}" for kw in keywords]
    prompt = (
        f'Given the company "{company_name}" in the {industry} industry, '
        "provide 5 semantic search queries for social media news and updates. Output:\n"
        '{ "search_queries": [...] }'
    )

    try:
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You will generate queries for social media news and updates about the company."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=800
        )

        content = response.choices[0].message.content
        qs = json.loads(content)
        return {"search_queries": qs.get("search_queries", default_queries)}

    except Exception as e:
        print(f"OpenAI expansion failed: {e}")
        return {"search_queries": default_queries}

def fetch_reddit_posts(company_name: str, search_queries: List[str], analyze_sentiment, limit=30):
    try:
        reddit = praw.Reddit(
            client_id=settings.REDDIT_CLIENT_ID, client_secret=settings.REDDIT_CLIENT_SECRET,
            user_agent=settings.REDDIT_USER_AGENT
        )
        posts, min_posts_target = [], 20
        subreddits = ["stocks", "investing", "wallstreetbets", "StockMarket", "finance", "economy", "business"]
        try:
            company_subreddit = reddit.subreddit(company_name.lower())
            _ = company_subreddit.created_utc
            subreddits.insert(0, company_name.lower())
        except Exception:
            pass
        one_week_ago = (datetime.now() - timedelta(days=7)).timestamp()
        for subreddit_name in subreddits:
            if len(posts) >= min_posts_target:
                break
            try:
                subreddit = reddit.subreddit(subreddit_name)
                for query in search_queries:
                    for submission in subreddit.search(query, sort="new", time_filter="week", limit=limit):
                        if submission.created_utc < one_week_ago:
                            continue
                        post = {
                            "platform": "Reddit",
                            "title": submission.title,
                            "description": (submission.selftext or "")[:512],
                            "text": submission.title + " " + (submission.selftext or ""),
                            "created_at": datetime.fromtimestamp(submission.created_utc, tz=timezone.utc).isoformat(),
                            "username": getattr(submission.author, 'name', '[deleted]'),
                            "likes": submission.score,
                            "comments": submission.num_comments,
                            "engagement": submission.score + submission.num_comments,
                            "url": f"https://www.reddit.com{submission.permalink}",
                            "subreddit": subreddit.display_name
                        }
                        sentiment, label, confidence = analyze_sentiment(post["text"])
                        post.update({"sentiment": sentiment, "label": label, "confidence": confidence})
                        post.pop("text")
                        posts.append(post)
                        if len(posts) >= min_posts_target:
                            break
            except Exception as e:
                print(f"Subreddit {subreddit_name} error: {e}")
        return posts
    except Exception as e:
        print(f"Reddit API/init error: {e}")
        return []

def fetch_bluesky_posts(company_name: str, search_queries: List[str], analyze_sentiment, max_results: int = 30):
    import requests
    BLUESKY_API = "https://bsky.social/xrpc"
    try:
        auth = requests.post(
            f"{BLUESKY_API}/com.atproto.server.createSession",
            json={"identifier": settings.BSKY_IDENTIFIER, "password": settings.BSKY_PASSWORD}
        )
        auth.raise_for_status()
        access_token = auth.json()["accessJwt"]
        headers = {"Authorization": f"Bearer {access_token}"}
        posts = []
        for query in search_queries:
            try:
                res = requests.get(
                    f"{BLUESKY_API}/app.bsky.feed.searchPosts",
                    headers=headers, params={"q": query, "limit": max_results}
                )
                res.raise_for_status()
                for post_data in res.json().get("posts", []):
                    text = post_data.get("record", {}).get("text", "")
                    if not text:
                        continue
                    sentiment, label, confidence = analyze_sentiment(text)
                    posts.append({
                        "platform":"Bluesky",
                        "text": text,
                        "created_at": datetime.fromisoformat(post_data.get("indexedAt").replace('Z', '+00:00')),
                        "username": post_data.get("author", {}).get("handle", "unknown"),
                        "likes":0, "comments":0, "engagement":0,
                        "url": f"https://bsky.app/profile/{post_data['author']['handle']}",
                        "sentiment": sentiment, "label": label, "confidence": confidence
                    })
            except Exception as e:
                print(f"Bluesky search '{query}': {e}")
        return posts
    except Exception as e:
        print(f"Bluesky auth failed: {e}")
        return []

def calculate_metrics(
    financial_data: Dict[str, Any],
    news_data: Dict[str, Any],
    social_data: Dict[str, Any]
) -> Dict[str, Any]:
    scores = {}

    # Financial Momentum (price, volume, volatility)
    try:
        hist_df = pd.DataFrame.from_dict(financial_data["historical_data"], orient="index")
        hist_df.index = pd.to_datetime(hist_df.index)
        hist_df = hist_df.sort_index()

        price_change_5d = hist_df['Close'].pct_change(5).iloc[-1] * 100
        price_change_20d = hist_df['Close'].pct_change(20).iloc[-1] * 100
        volume_ratio = hist_df['Volume'].iloc[-1] / max(hist_df['Volume'].iloc[-20:].mean(), 1)

        # Real-world volatility (annualized std dev of daily returns)
        returns = hist_df['Close'].pct_change().dropna()
        volatility = returns.std() * np.sqrt(252)
        volatility_score = min(50, (1/max(volatility, 1e-4)) * 10)

        fm = min(100, max(0, price_change_5d * 3 + price_change_20d * 2 + volume_ratio * 10 + volatility_score))
        scores["financial_momentum"] = fm
    except Exception as e:
        print(f"Financial momentum error: {e}")
        scores["financial_momentum"] = 50

    # News Sentiment and Confidence (weighted by article confidence)
    try:
        articles = news_data.get("articles", [])
        if articles:
            sentiments = [a.get("sentiment", 0) for a in articles]
            confidences = [a.get("confidence", 0.5) for a in articles]
            if confidences and sum(confidences) > 0:
                avg_sent = float(np.average(sentiments, weights=confidences))
                avg_confidence = float(np.mean(confidences))
            else:
                avg_sent = float(np.mean(sentiments)) if sentiments else 0.0
                avg_confidence = 0.5
            news_sentiment = (avg_sent + 1) * 50  # normalize -1~1 → 0~100
            article_count_factor = min(1.5, max(0.5, len(articles) / 10))
            news_sentiment = min(100, max(0, news_sentiment * article_count_factor))
            scores["news_sentiment"] = news_sentiment
            scores["news_confidence"] = avg_confidence
        else:
            scores["news_sentiment"] = 50
            scores["news_confidence"] = 0.5
    except Exception as e:
        print(f"News sentiment error: {e}")
        scores["news_sentiment"] = 50
        scores["news_confidence"] = 0.5

    # Social Buzz, Sentiment, and Confidence
    try:
        posts = social_data.get("posts", [])
        if posts:
            social_sentiments = [p.get("sentiment", 0) for p in posts]
            social_confidences = [p.get("confidence", 0.5) for p in posts]
            avg_social_sentiment = float(np.average(social_sentiments, weights=social_confidences)) if social_confidences and sum(social_confidences) > 0 else float(np.mean(social_sentiments)) if social_sentiments else 0.0
            avg_social_confidence = float(np.mean(social_confidences)) if social_confidences else 0.5
            post_vol = min(2.0, max(0.5, social_data.get("total_posts", 0) / 50))
            now = datetime.now(timezone.utc)
            recent_posts = [
                p for p in posts
                if isinstance(p.get("created_at"), (datetime, pd.Timestamp, np.datetime64))
                and pd.to_datetime(p["created_at"]).replace(tzinfo=timezone.utc) > (now - timedelta(hours=24))
            ]
            recency_factor = min(1.5, max(0.5, len(recent_posts) / max(1, len(posts)) * 3))
            avg_engagement = np.mean([p.get("engagement", 0) for p in posts]) if posts else 0
            eng_factor = min(2.0, max(0.5, avg_engagement / 10))

            social_buzz_raw = avg_social_sentiment * post_vol * recency_factor * eng_factor
            social_buzz = min(100, max(0, (social_buzz_raw + 1) * 50))  # normalize
            scores["social_buzz"] = social_buzz
            scores["social_confidence"] = avg_social_confidence
        else:
            scores["social_buzz"] = 0
            scores["social_confidence"] = 0.5
    except Exception as e:
        print(f"Social buzz error: {e}")
        scores["social_buzz"] = 0
        scores["social_confidence"] = 0.5

    # Hype Index (weighted composite)
    try:
        scores["hype_index"] = (
            scores["financial_momentum"] * 0.6 +
            scores["news_sentiment"] * 0.2 +
            scores["social_buzz"] * 0.2
        )
    except Exception as e:
        print(f"Hype index error: {e}")
        scores["hype_index"] = 50

    # Sentiment-Price Divergence
    try:
        price_change_3d = hist_df['Close'].pct_change(3).iloc[-1] * 100
        combined_sentiment = (scores["news_sentiment"] + scores["social_buzz"]) / 2
        norm_price = min(100, max(0, (price_change_3d + 10) * 5))
        scores["sentiment_price_divergence"] = norm_price - combined_sentiment
    except Exception as e:
        print(f"Sentiment-price divergence error: {e}")
        scores["sentiment_price_divergence"] = 0

    scores["trading_signal"] = generate_trading_signal(financial_momentum=scores.get("financial_momentum", 50),news_sentiment=scores.get("news_sentiment", 50),news_confidence=scores.get("news_confidence", 0.5),social_buzz=scores.get("social_buzz", 0),social_confidence=scores.get("social_confidence", 0.5),sentiment_price_divergence=scores.get("sentiment_price_divergence", 0),threshold_confidence=0.6,positive_threshold=60,negative_threshold=40)

    return scores

def generate_trading_signal(financial_momentum: float,news_sentiment: float,news_confidence: float,social_buzz: float,social_confidence: float,sentiment_price_divergence: float,threshold_confidence: float = 0.6,positive_threshold: float = 60,negative_threshold: float = 40) -> str:
    # Weighted composite sentiment/score
    composite_sentiment = (
        financial_momentum * 0.6 +
        news_sentiment * 0.2 * news_confidence +
        social_buzz * 0.2 * social_confidence
    )
    combined_confidence = (news_confidence + social_confidence + 1.0) / 3.0

    if combined_confidence < threshold_confidence:
        return "HOLD"
    if composite_sentiment >= positive_threshold and sentiment_price_divergence < 0:
        return "BUY"
    elif composite_sentiment <= negative_threshold and sentiment_price_divergence > 0:
        return "SELL"
    else:
        return "HOLD"


def flatten_nested_dict(d, parent_key='', sep='.'):
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            if k == 'historical_data':
                items.append((new_key, json.dumps(v, default=json_serial)))
            else:
                items.extend(flatten_nested_dict(v, new_key, sep=sep).items())
        elif isinstance(v, (list, tuple)):
            items.append((new_key, json.dumps(v, default=json_serial)))
        elif isinstance(v, (datetime, date)):
            items.append((new_key, v.isoformat()))
        else:
            items.append((new_key, v))
    return dict(items)

def parse_timestamp(timestamp_str):
    if not timestamp_str: return None
    try:
        if isinstance(timestamp_str, (datetime, date)):
            if timestamp_str.tzinfo is None:
                return timestamp_str.replace(tzinfo=timezone.utc)
            return timestamp_str
        if not isinstance(timestamp_str, str):
            timestamp_str = str(timestamp_str)
        parsed_time = datetime.fromisoformat(timestamp_str)
        if parsed_time.tzinfo is None:
            parsed_time = parsed_time.replace(tzinfo=timezone.utc)
        return parsed_time
    except ValueError:
        for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f'):
            try:
                parsed_time = datetime.strptime(timestamp_str, fmt)
                return parsed_time.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        print(f"Could not parse timestamp: {timestamp_str}")
        return None
