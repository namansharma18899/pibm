import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

CACHE_FILE = Path("news_cache.json")
CACHE_MAX_AGE = 24 * 60 * 60
ARTICLES_PER_SECTION = 6
FETCH_MULTIPLIER = 3

SECTIONS = [
    {"key": "business", "label": "Business & Market News", "has_regions": True},
    {"key": "ai_tech", "label": "AI & Emerging Technology", "has_regions": False},
    {"key": "marketing", "label": "Marketing & Consumer Trends", "has_regions": False},
    {"key": "finance", "label": "Finance, Economy & Entrepreneurship", "has_regions": True},
    {"key": "misc", "label": "Miscellaneous", "has_regions": False},
]


AD_KEYWORDS = [
    "sponsored", "advertorial", "promoted", "partner content",
    "buy now", "shop now", "order now", "sign up", "subscribe now",
    "discount", "coupon", "promo code", "deal of the day", "flash sale",
    "limited time offer", "exclusive offer", "special offer", "best deal",
    "free trial", "act now", "don't miss out", "hurry",
    "click here", "learn more at", "visit our", "check out our",
    "paid post", "brought to you by", "in partnership with",
    "affiliate", "earn money", "make money online", "work from home",
    "crypto trading", "forex signal", "investment opportunity",
]

AD_URL_PATTERNS = [
    "/sponsored/", "/advertorial/", "/partner/", "/promoted/",
    "/brand-content/", "/paid-post/", "/native-ad/",
    "utm_medium=paid", "utm_source=sponsored",
]

JUNK_TITLES = ["[removed]", "[deleted]", "null", "untitled", "no title"]


def _is_ad(title: str, description: str, url: str) -> bool:
    title_lower = title.lower().strip()
    desc_lower = description.lower().strip()

    if not title_lower or title_lower in JUNK_TITLES:
        return True

    if len(title_lower) < 10:
        return True

    combined = title_lower + " " + desc_lower

    for kw in AD_KEYWORDS:
        if kw in combined:
            return True

    url_lower = url.lower()
    for pattern in AD_URL_PATTERNS:
        if pattern in url_lower:
            return True

    if title_lower.count("!") >= 2 or title_lower.count("$") >= 1 or title_lower.count("%") >= 2:
        return True

    if sum(1 for c in title if c.isupper()) / max(len(title), 1) > 0.6 and len(title) > 15:
        return True

    return False


def _article(title: str, description: str, url: str, image_url: str | None, source: str, published: str | None = None) -> dict:
    return {
        "title": title,
        "description": description or "",
        "url": url,
        "image_url": image_url,
        "source": source,
        "published": published,
    }


def _fetch_newsdata(query: str | None = None, category: str | None = None, country: str | None = None) -> list[dict]:
    if not settings.newsdata_api_key:
        logger.warning("NEWSDATA_API_KEY not set — skipping NewsData.io fetch")
        return []
    params = {
        "apikey": settings.newsdata_api_key,
        "language": "en",
        "size": 10,
    }
    if query:
        params["q"] = query
    if category:
        params["category"] = category
    if country:
        params["country"] = country
    try:
        resp = httpx.get("https://newsdata.io/api/1/latest", params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        articles = []
        for item in data.get("results") or []:
            if len(articles) >= ARTICLES_PER_SECTION:
                break
            title = item.get("title", "")
            desc = item.get("description", "")
            url = item.get("link", "")
            if _is_ad(title, desc, url):
                continue
            articles.append(_article(
                title=item.get("title", ""),
                description=item.get("description", ""),
                url=item.get("link", ""),
                image_url=item.get("image_url"),
                source=item.get("source_name", item.get("source_id", "NewsData")),
                published=item.get("pubDate"),
            ))
        logger.info("NewsData.io fetched %d articles for q=%s", len(articles), query)
        return articles
    except Exception as e:
        logger.error("NewsData.io fetch failed: %s", e)
        return []


def _fetch_hackernews() -> list[dict]:
    try:
        resp = httpx.get("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=10)
        resp.raise_for_status()
        story_ids = resp.json()[:ARTICLES_PER_SECTION * FETCH_MULTIPLIER]

        articles = []
        for sid in story_ids:
            if len(articles) >= ARTICLES_PER_SECTION:
                break
            try:
                item = httpx.get(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json", timeout=5).json()
                if not item or item.get("type") != "story" or not item.get("url"):
                    continue
                hn_title = item.get("title", "")
                if _is_ad(hn_title, "", item["url"]):
                    continue
                articles.append(_article(
                    title=hn_title,
                    description=f"{item.get('score', 0)} points | {item.get('descendants', 0)} comments",
                    url=item["url"],
                    image_url=None,
                    source="Hacker News",
                    published=datetime.fromtimestamp(item.get("time", 0), tz=timezone.utc).isoformat() if item.get("time") else None,
                ))
            except Exception:
                continue
        logger.info("Hacker News fetched %d articles", len(articles))
        return articles
    except Exception as e:
        logger.error("Hacker News fetch failed: %s", e)
        return []


def _fetch_newsapi(query: str) -> list[dict]:
    if not settings.newsapi_key:
        logger.warning("NEWSAPI_KEY not set — skipping NewsAPI fetch")
        return []
    try:
        resp = httpx.get(
            "https://newsapi.org/v2/everything",
            params={"q": query, "language": "en", "sortBy": "publishedAt", "pageSize": ARTICLES_PER_SECTION * FETCH_MULTIPLIER},
            headers={"X-Api-Key": settings.newsapi_key},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        articles = []
        for item in data.get("articles") or []:
            if len(articles) >= ARTICLES_PER_SECTION:
                break
            title = item.get("title", "")
            desc = item.get("description", "")
            url = item.get("url", "")
            if _is_ad(title, desc, url):
                continue
            articles.append(_article(
                title=title,
                description=desc,
                url=url,
                image_url=item.get("urlToImage"),
                source=(item.get("source") or {}).get("name", "NewsAPI"),
                published=item.get("publishedAt"),
            ))
        logger.info("NewsAPI fetched %d articles for q=%s", len(articles), query)
        return articles
    except Exception as e:
        logger.error("NewsAPI fetch failed: %s", e)
        return []


def _fetch_finnhub() -> list[dict]:
    if not settings.finnhub_api_key:
        logger.warning("FINNHUB_API_KEY not set — skipping Finnhub fetch")
        return []
    try:
        resp = httpx.get(
            "https://finnhub.io/api/v1/news",
            params={"category": "general", "token": settings.finnhub_api_key},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        articles = []
        for item in data or []:
            if len(articles) >= ARTICLES_PER_SECTION:
                break
            title = item.get("headline", "")
            desc = item.get("summary", "")
            url = item.get("url", "")
            if _is_ad(title, desc, url):
                continue
            articles.append(_article(
                title=title,
                description=desc,
                url=url,
                image_url=item.get("image") or None,
                source=item.get("source", "Finnhub"),
                published=datetime.fromtimestamp(item.get("datetime", 0), tz=timezone.utc).isoformat() if item.get("datetime") else None,
            ))
        logger.info("Finnhub fetched %d articles", len(articles))
        return articles
    except Exception as e:
        logger.error("Finnhub fetch failed: %s", e)
        return []


def refresh_all_news() -> dict:
    logger.info("Refreshing news cache from all sources...")
    news = {
        "business": {
            "in": _fetch_newsdata(category="business", country="in"),
            "global": _fetch_newsdata(category="business"),
        },
        "ai_tech": _fetch_hackernews(),
        "marketing": _fetch_newsapi("marketing OR consumer trends"),
        "finance": {
            "in": _fetch_newsdata(query="economy OR market OR Sensex OR Nifty OR RBI", country="in"),
            "global": _fetch_finnhub(),
        },
        "misc": _fetch_newsdata(query="trending", country="in"),
        "fetched_at": time.time(),
    }
    try:
        CACHE_FILE.write_text(json.dumps(news, ensure_ascii=False))
        count = 0
        for v in news.values():
            if isinstance(v, list):
                count += len(v)
            elif isinstance(v, dict) and "in" in v:
                count += len(v.get("in", [])) + len(v.get("global", []))
        logger.info("News cache written — %d total articles", count)
    except Exception as e:
        logger.error("Failed to write news cache: %s", e)
    return news


def get_cached_news() -> dict:
    if not CACHE_FILE.exists():
        return {s["key"]: [] for s in SECTIONS}
    try:
        data = json.loads(CACHE_FILE.read_text())
        return data
    except Exception as e:
        logger.error("Failed to read news cache: %s", e)
        return {s["key"]: [] for s in SECTIONS}


def maybe_refresh_cache() -> None:
    if CACHE_FILE.exists():
        try:
            data = json.loads(CACHE_FILE.read_text())
            age = time.time() - data.get("fetched_at", 0)
            if age < CACHE_MAX_AGE:
                logger.info("News cache is fresh (%.1fh old) — skipping refresh", age / 3600)
                return
        except Exception:
            pass
    refresh_all_news()
