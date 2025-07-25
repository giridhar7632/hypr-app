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

async def fetch_alpha_vantage_trending():
    url = f"https://www.alphavantage.co/query?function=TOP_GAINERS_LOSERS&apikey={settings.ALPHA_VANTAGE_API_KEY}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    print(f"Alpha Vantage API returned status {response.status}")
                    return {"top_gainers": [], "top_losers": [], "most_actively_traded": []}
                data = await response.json()

                for k in ("top_gainers", "top_losers", "most_actively_traded"):
                    data[k] = data.get(k, [])[:5]

                data.pop("metadata", None)
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

def calculate_metrics(financial_data: Dict, news_data: Dict, social_data: Dict):
    scores = {}
    try:
        hist_df = pd.DataFrame.from_dict(financial_data["historical_data"], orient="index")
        hist_df.index = pd.to_datetime(hist_df.index)
        hist_df = hist_df.sort_index()
        price_change_5d = hist_df['Close'].pct_change(5).iloc[-1] * 100
        price_change_20d = hist_df['Close'].pct_change(20).iloc[-1] * 100
        volume_ratio = hist_df['Volume'].iloc[-1] / max(hist_df['Volume'].iloc[-20:].mean(), 1)
        volatility = financial_data.get("volatility", 0.01)
        volatility_score = min(50, (1/max(volatility, 0.001)) * 10)
        fm = min(100, max(0, price_change_5d*3 + price_change_20d*2 + volume_ratio*10 + volatility_score))
        scores["financial_momentum"] = fm
    except Exception as e:
        print(f"Financial momentum error: {e}"); scores["financial_momentum"] = 50
    try:
        arts = news_data.get("articles", [])
        if arts:
            avg_sent = sum(a["sentiment"] for a in arts) / len(arts)
            news_sentiment = (avg_sent + 1) * 50
            count_factor = min(1.5, max(0.5, len(arts)/10))
            scores["news_sentiment"] = min(100, max(0, news_sentiment*count_factor))
        else:
            scores["news_sentiment"] = 50
    except Exception as e:
        print(f"News sentiment error: {e}"); scores["news_sentiment"] = 50
    try:
        posts = social_data.get("posts", [])
        if posts:
            soc_sent = (social_data["avg_sentiment"] + 1) * 50
            post_vol = min(2.0, max(0.5, social_data["total_posts"]/50))
            now = datetime.now(timezone.utc)
            recents = [p for p in posts if isinstance(p.get("created_at"), (datetime, np.datetime64))
                and parse_timestamp(p["created_at"]) > now - timedelta(hours=24)]
            recency = min(1.5, max(0.5, len(recents)/max(1,len(posts))*3))
            avg_eng = sum(p.get("engagement",0) for p in posts) / max(1,len(posts))
            eng_factor = min(2.0, max(0.5, avg_eng/10))
            social_buzz = min(100, max(0, soc_sent*post_vol*recency*eng_factor))
            scores["social_buzz"] = social_buzz
        else: scores["social_buzz"] = 0
    except Exception as e:
        print(f"Social buzz error: {e}"); scores["social_buzz"] = 0
    try:
        scores["hype_index"] = (
            scores["financial_momentum"] * 0.6 +
            scores["news_sentiment"] * 0.2 +
            scores["social_buzz"] * 0.2
        )
    except Exception as e:
        print(f"Hype index error: {e}"); scores["hype_index"] = 50
    try:
        price_change_3d = hist_df['Close'].pct_change(3).iloc[-1] * 100
        combined_sentiment = (scores["news_sentiment"] + scores["social_buzz"])/2
        norm_price = min(100, max(0, (price_change_3d+10)*5))
        scores["sentiment_price_divergence"] = norm_price - combined_sentiment
    except Exception as e:
        print(f"Sentiment-price divergence error: {e}"); scores["sentiment_price_divergence"] = 0
    return scores

def generate_trading_signal(sentiment_score: float, confidence: float) -> str:
    if confidence < 0.6: return "HOLD"
    if sentiment_score >= 0.4: return "BUY"
    if sentiment_score <= -0.4: return "SELL"
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
