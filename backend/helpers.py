import pytz
import praw
import json
import openai
import requests
import numpy as np
import pandas as pd
from typing import List
from typing import Optional
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


def send_sse_message(message, event_type="message"):
    """Helper function to format SSE messages"""
    return f"event: {event_type}\ndata: {json.dumps(message, default=json_serial)}\n\n"

def fetch_alpha_vantage_trending():
    url = f"https://www.alphavantage.co/query?function=TOP_GAINERS_LOSERS&apikey={settings.ALPHA_VANTAGE_API_KEY}"
    result = requests.get(url)
    data = result.json()
    data["top_gainers"] = data["top_gainers"][:5]
    data["top_losers"] = data["top_losers"][:5]
    data["most_actively_traded"] = data["most_actively_traded"][:5]
    del data["metadata"]

    return data
    
def expand_keywords_and_generate_queries(company_name, industry):
    keywords = ["stock", "earnings", "price target", "news", "forecast"]
    default_queries = [f"{company_name} {kw}" for kw in keywords]
    prompt = f"""
    Given the company "{company_name}" in the {industry} industry,
    please provide: 5 semantic search queries that could be used to find relevant social media discussions about latest news and updates about the company.

    Only output a JSON object with the following format:

    {{
      "search_queries": ["query1", "query2", "query3", "query4", "query5"]
    }}
    """

    try:
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that expands keywords and generates search queries."},
                {"role": "user", "content": prompt.strip()}
            ],
            temperature=0.7,
            max_tokens=800
        )

        content = response.choices[0].message.content
        result = json.loads(content)

        return {
            "search_queries": result.get("search_queries", default_queries)
        }

    except Exception as e:
        print(f"Error with OpenAI keyword expansion: {e}")
        return {
            "search_queries": default_queries
        }

def fetch_reddit_posts(company_name: str, search_queries: List[str], analyze_sentiment, limit=30):
    try:
        reddit = praw.Reddit(
            client_id=settings.REDDIT_CLIENT_ID,
            client_secret=settings.REDDIT_CLIENT_SECRET,
            user_agent=settings.REDDIT_USER_AGENT
        )

        posts = []
        subreddits = ["stocks", "investing", "wallstreetbets"]

        # Try to add company-specific subreddit if available
        try:
            company_subreddit = reddit.subreddit(company_name.lower())
            _ = company_subreddit.created_utc  # triggers exception if invalid
            subreddits.append(company_name.lower())
        except Exception as e:
            print(f"Company subreddit not accessible: {e}")

        industry_subreddits = ["StockMarket", "finance", "economy", "business"]
        subreddits.extend(industry_subreddits)

        one_week_ago = (datetime.now() - timedelta(days=7)).timestamp()
        seen_urls = set()
        min_posts_target = 20

        def filter_and_score_post(post):
            # Calculate sentiment on the combined text
            sentiment, label, confidence = analyze_sentiment(post["text"])
            del post["text"]
            post["sentiment"] = sentiment
            post["label"] = label
            post["confidence"] = confidence
            return post

        def get_recent_posts(subreddit_obj, query, limit=30):
            recent_posts = []
            try:
                # First try with search
                for submission in subreddit_obj.search(query, sort="new", time_filter="week", limit=limit):
                    # Skip if post is too old
                    if submission.created_utc < one_week_ago:
                        continue

                    post = {
                        "platform": "Reddit",
                        "title": submission.title,
                        "description": submission.selftext[:512] if submission.selftext else "",
                        "text": submission.title + " " + (submission.selftext if submission.selftext else ""),
                        "created_at": pd.to_datetime(submission.created_utc, unit='s').isoformat(),
                        "username": submission.author.name if submission.author and hasattr(submission.author, 'name') else "[deleted]",
                        "likes": submission.score,
                        "comments": submission.num_comments,
                        "engagement": submission.score + submission.num_comments,
                        "url": f"https://www.reddit.com{submission.permalink}",
                        "subreddit": subreddit_obj.display_name
                    }

                    recent_posts.append(post)

                # If we didn't get enough posts, browsing hot/new as well
                if len(recent_posts) < 20:
                    browse_methods = [
                        (subreddit_obj.hot, min(20, limit)),
                        (subreddit_obj.new, min(20, limit))
                    ]

                    for method, method_limit in browse_methods:
                        for submission in method(limit=method_limit):
                            # Skip if post is too old
                            if submission.created_utc < one_week_ago:
                                continue

                            # Skip if post doesn't contain any relevant keywords
                            if not any(query.lower() in submission.title.lower() or
                                    (submission.selftext and query.lower() in submission.selftext.lower())
                                    for query in search_queries):
                                continue

                            post = {
                                "platform": "Reddit",
                                "title": submission.title,
                                "description": submission.selftext if submission.selftext else "",
                                "text": submission.title + " " + (submission.selftext if submission.selftext else ""),
                                "created_at": pd.to_datetime(submission.created_utc, unit='s').isoformat(),
                                "username": submission.author.name if submission.author and hasattr(submission.author, 'name') else "[deleted]",
                                "likes": submission.score,
                                "comments": submission.num_comments,
                                "engagement": submission.score + submission.num_comments,
                                "url": f"https://www.reddit.com{submission.permalink}",
                                "subreddit": subreddit_obj.display_name
                            }

                            # to avoid duplicates
                            if not any(existing["url"] == post["url"] for existing in recent_posts):
                                recent_posts.append(post)
            except Exception as e:
                print(f"Error getting posts from subreddit {subreddit_obj.display_name}: {e}")

            return recent_posts

        for subreddit_name in subreddits:
            if len(posts) >= min_posts_target:
                break

            try:
                subreddit = reddit.subreddit(subreddit_name)
                posts_needed = min_posts_target - len(posts)

                if posts_needed <= 0:
                    break

                # Try each search query until we have enough posts
                for query in search_queries:
                    new_posts = get_recent_posts(subreddit, query, limit=30)
                    posts.extend([filter_and_score_post(post) for post in new_posts])

                    print(f"Found {len(new_posts)} posts for query '{query}' in r/{subreddit_name}")

                    if len(posts) >= min_posts_target:
                        break
            except Exception as e:
                print(f"Error accessing subreddit {subreddit_name}: {e}")
                continue


        return posts

    except Exception as e:
        print(f"Error initializing Reddit API or fetching posts: {e}")
        return []


def fetch_bluesky_posts(company_name: str, search_queries: List[str], analyze_sentiment, max_results: int = 30):
    BLUESKY_API = "https://bsky.social/xrpc"
    
    try:
        # Auth
        auth_response = requests.post(
            f"{BLUESKY_API}/com.atproto.server.createSession",
            json={"identifier": settings.BSKY_IDENTIFIER, "password": settings.BSKY_PASSWORD},
        )
        auth_response.raise_for_status()
        access_token = auth_response.json()["accessJwt"]
        
        headers = {"Authorization": f"Bearer {access_token}"}
        posts = []
        
        for query in search_queries:
            try:
                response = requests.get(
                    f"{BLUESKY_API}/app.bsky.feed.searchPosts",
                    headers=headers,
                    params={"q": query, "limit": max_results},
                )
                response.raise_for_status()
                
                for post_data in response.json().get("posts", []):
                    text = post_data.get("record", {}).get("text", "")
                    if not text:
                        continue
                    
                    sentiment, label, confidence = analyze_sentiment(text)
                    
                    post = {
                        "platform":"Bluesky",
                        "text":text,
                        "created_at":datetime.fromisoformat(post_data.get("indexedAt").replace('Z', '+00:00')),
                        "username":post_data.get("author", {}).get("handle", "unknown"),
                        "likes":0,
                        "comments":0,
                        "engagement":0,
                        "url":f"https://bsky.app/profile/{post_data['author']['handle']}",
                        "sentiment":sentiment,
                        "label":label,
                        "confidence":confidence
                    }
                    
                    posts.append(post)
                    
            except Exception as e:
                print(f"Error searching Bluesky for '{query}': {e}")
                continue
        
        return posts
        
    except Exception as e:
        print(f"Bluesky auth failed: {e}")
        return []


def calculate_metrics(financial_data, news_data, social_data):
    """Calculate metrics based on financial, news, and social data"""
    scores = {}

    # 1. Financial momentum score (0-100)
    try:
        # Convert historical data to DataFrame for calculations
        hist_df = pd.DataFrame.from_dict(financial_data["historical_data"], orient='index')
        hist_df.index = pd.to_datetime(hist_df.index)
        hist_df = hist_df.sort_index()

        # Price momentum (recent performance vs historical)
        price_change_5d = hist_df['Close'].pct_change(5).iloc[-1] * 100
        price_change_20d = hist_df['Close'].pct_change(20).iloc[-1] * 100

        # Volume momentum (recent volume vs average)
        volume_ratio = hist_df['Volume'].iloc[-1] / hist_df['Volume'].iloc[-20:].mean()

        # Volatility adjustment
        volatility = financial_data.get("volatility", 0.01)
        volatility = max(0.001, volatility)
        volatility_score = min(50, (1/volatility) * 10)

        # Combine into financial momentum (0-100)
        financial_momentum = min(100, max(0, (
            (price_change_5d * 3) +
            (price_change_20d * 2) +
            (volume_ratio * 10) +
            volatility_score
        )))

        scores["financial_momentum"] = financial_momentum
    except Exception as e:
        print(f"Error calculating financial momentum: {e}")
        print(f"Error type: {type(e)}")
        print(f"Error details: {str(e)}")
        print(f"Financial data structure: {json.dumps(financial_data, indent=2, default=json_serial)}")
        if 'historical_data' in financial_data:
            print(f"Historical data type: {type(financial_data['historical_data'])}")
            print(f"Historical data sample: {json.dumps(dict(list(financial_data['historical_data'].items())[:2]), indent=2, default=json_serial)}")
        scores["financial_momentum"] = 50

    # 2. News sentiment score (0-100)
    try:
        if news_data.get("articles"):
            # Average sentiment across all articles
            sentiment_values = [article["sentiment"] for article in news_data["articles"]]
            avg_sentiment = sum(sentiment_values) / len(sentiment_values)

            # Scale from -1,1 to 0,100
            news_sentiment = (avg_sentiment + 1) * 50

            # Adjust by article count
            article_count_factor = min(1.5, max(0.5, len(news_data["articles"]) / 10))
            news_sentiment = min(100, max(0, news_sentiment * article_count_factor))

            scores["news_sentiment"] = news_sentiment
        else:
            scores["news_sentiment"] = 50
    except Exception as e:
        print(f"Error calculating news sentiment: {e}")
        scores["news_sentiment"] = 50

    # 3. Social media buzz score (0-100)
    try:
        if social_data.get("posts"):
            # Basic social sentiment
            social_sentiment = (social_data["avg_sentiment"] + 1) * 50

            # Volume factor
            post_volume = min(2.0, max(0.5, social_data["total_posts"] / 50))

            # Recent post ratio
            now = datetime.now(timezone.utc)


            recent_posts = [p for p in social_data["posts"]
                if isinstance(p.get("created_at"), (datetime, np.datetime64)) and
                  p["created_at"].replace(tzinfo=timezone.utc) > (now - timedelta(hours=24))
            ]
            recency_factor = min(1.5, max(0.5, len(recent_posts) / max(1, len(social_data["posts"])) * 3))

            # Engagement factor
            engagements = [p.get("engagement", 0) for p in social_data["posts"]]
            avg_engagement = sum(engagements) / max(1, len(engagements))
            engagement_factor = min(2.0, max(0.5, avg_engagement / 10))

            # Combined social buzz score
            social_buzz = min(100, max(0, social_sentiment * post_volume * recency_factor * engagement_factor))

            scores["social_buzz"] = social_buzz
        else:
            scores["social_buzz"] = 0
    except Exception as e:
        print(f"Error calculating social buzz: {e}")
        scores["social_buzz"] = 0

    # 4. Combined "Hype Index"
    try:
        # Adjusted weights to give more importance to financial momentum
        hype_index = (
            (scores["financial_momentum"] * 0.6) +  
            (scores["news_sentiment"] * 0.2) +     
            (scores["social_buzz"] * 0.2)           
        )

        scores["hype_index"] = hype_index
    except Exception as e:
        print(f"Error calculating hype index: {e}")
        scores["hype_index"] = 50

    # 5. Sentiment-Price Divergence
    try:
        # Use the same DataFrame we created for financial momentum
        price_change_3d = hist_df['Close'].pct_change(3).iloc[-1] * 100
        combined_sentiment = (scores["news_sentiment"] + scores["social_buzz"]) / 2

        # Normalize price change to 0-100 scale
        norm_price = min(100, max(0, (price_change_3d + 10) * 5))

        # Calculate divergence (price - sentiment)
        # Positive means price is higher than sentiment (bearish divergence)
        # Negative means price is lower than sentiment (bullish divergence)
        sentiment_price_divergence = norm_price - combined_sentiment
        scores["sentiment_price_divergence"] = sentiment_price_divergence
    except Exception as e:
        print(f"Error calculating sentiment-price divergence: {e}")
        print(f"Error type: {type(e)}")
        print(f"Error details: {str(e)}")
        scores["sentiment_price_divergence"] = 0

    return scores


def generate_trading_signal(sentiment_score: float, confidence: float) -> str:
    if confidence < 0.6:
        return "HOLD"
    if sentiment_score >= 0.4:
        return "BUY"
    elif sentiment_score <= -0.4:
        return "SELL"
    else:
        return "HOLD"

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError("Type %s not serializable" % type(obj))

def flatten_nested_dict(d, parent_key='', sep='.'):
    """
    Flatten a nested dictionary with custom separator and handle complex data types
    """
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
    """Helper function to parse timestamps from database"""
    if not timestamp_str:
        return None
        
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
        try:
            parsed_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
            return parsed_time.replace(tzinfo=timezone.utc)
        except ValueError:
            try:
                parsed_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
                return parsed_time.replace(tzinfo=timezone.utc)
            except ValueError:
                logger.error(f"Could not parse timestamp: {timestamp_str}")
                return None

