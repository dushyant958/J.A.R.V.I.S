"""Web tools — search, news, weather, fetch."""

import httpx
import xml.etree.ElementTree as ET
import asyncio
import re
import webbrowser
from datetime import datetime

SEED_FEEDS = [
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://www.cnbc.com/id/100727362/device/rss/rss.html",
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "https://www.aljazeera.com/xml/rss/all.xml",
]

TOPIC_FEEDS = {
    "sports":   ["https://feeds.bbci.co.uk/sport/rss.xml",
                 "https://www.skysports.com/rss/12040"],
    "football": ["https://feeds.bbci.co.uk/sport/football/rss.xml",
                 "https://www.skysports.com/rss/12040"],
    "cricket":  ["https://feeds.bbci.co.uk/sport/cricket/rss.xml"],
    "tech":     ["https://feeds.bbci.co.uk/news/technology/rss.xml",
                 "https://www.theverge.com/rss/index.xml"],
    "india":    ["https://feeds.bbci.co.uk/news/world/asia/india/rss.xml"],
    "business": ["https://feeds.bbci.co.uk/news/business/rss.xml",
                 "https://www.cnbc.com/id/100727362/device/rss/rss.html"],
    "world":    SEED_FEEDS,
}


async def _fetch_feed(client: httpx.AsyncClient, url: str) -> list[dict]:
    try:
        r = await client.get(url, headers={"User-Agent": "JARVIS/2.0"}, timeout=5.0)
        if r.status_code != 200:
            return []
        root = ET.fromstring(r.content)
        items = []
        for item in root.findall(".//item")[:5]:
            title = item.findtext("title") or ""
            items.append({"title": title.strip()})
        return items
    except Exception:
        return []


def register(mcp):

    @mcp.tool()
    async def get_news(topic: str = "world") -> str:
        """Fetch latest headlines. topic: 'world','football','sports','cricket','tech','india','business'."""
        feeds = TOPIC_FEEDS.get(topic.lower().strip(), SEED_FEEDS)
        async with httpx.AsyncClient(follow_redirects=True) as client:
            results = await asyncio.gather(*[_fetch_feed(client, url) for url in feeds])
        articles = [a for feed in results for a in feed]
        if not articles:
            return f"No {topic} news available right now."
        headlines = [a['title'] for a in articles[:5]]
        return f"Top {topic} headlines: " + " | ".join(headlines)

    @mcp.tool()
    async def search_web(query: str, max_results: int = 5) -> str:
        """Search the web using DuckDuckGo. Use for current facts, news, or any lookup."""
        try:
            from ddgs import DDGS
            results = await asyncio.to_thread(
                lambda: list(DDGS().text(query, max_results=max_results))
            )
            if not results:
                return f"No results found for: {query}"
            parts = []
            for r in results[:3]:
                title = r.get('title', '')
                body = r.get('body', '')[:150].rstrip()
                parts.append(f"{title} — {body}")
            return " | ".join(parts)
        except ImportError:
            return "Search unavailable — run: uv add duckduckgo-search"
        except Exception as e:
            return f"Search failed: {e}"

    @mcp.tool()
    async def fetch_url(url: str) -> str:
        """Fetch the text content of a URL."""
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
                r = await client.get(url, headers={"User-Agent": "JARVIS/2.0"})
                r.raise_for_status()
                text = re.sub(r"<[^>]+>", " ", r.text)
                return re.sub(r"\s+", " ", text).strip()[:3000]
        except Exception as e:
            return f"Could not fetch URL: {e}"

    @mcp.tool()
    async def get_weather(city: str) -> str:
        """Get current weather for any city."""
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
                r = await client.get(
                    f"https://wttr.in/{city}?format=j1",
                    headers={"User-Agent": "JARVIS/2.0"},
                )
                r.raise_for_status()
                data = r.json()
                c = data["current_condition"][0]
                area = data["nearest_area"][0]["areaName"][0]["value"]
                return (
                    f"{area}: {c['weatherDesc'][0]['value']}, {c['temp_C']}C "
                    f"(feels {c['FeelsLikeC']}C), humidity {c['humidity']}%."
                )
        except Exception as e:
            return f"Could not fetch weather for {city}: {e}"

    @mcp.tool()
    async def open_url(url: str) -> str:
        """Open a URL in the default browser."""
        try:
            webbrowser.open(url)
            return f"Opened {url}."
        except Exception as e:
            return f"Could not open URL: {e}"
