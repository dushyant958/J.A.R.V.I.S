"""
Web tools — search, fetch pages, and global news briefings.
"""

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


async def _fetch_and_parse_feed(client: httpx.AsyncClient, url: str) -> list[dict]:
    """Fetch a single RSS feed and return a list of article dicts."""
    try:
        r = await client.get(url, headers={"User-Agent": "JARVIS-AI/2.0"}, timeout=5.0)
        if r.status_code != 200:
            return []
        root = ET.fromstring(r.content)
        source = url.split(".")[1].upper()
        items = []
        for item in root.findall(".//item")[:5]:
            title = item.findtext("title") or ""
            desc = item.findtext("description") or ""
            link = item.findtext("link") or ""
            desc = re.sub(r"<[^>]+>", "", desc).strip()
            items.append({
                "source": source,
                "title": title,
                "summary": desc[:250] + "..." if len(desc) > 250 else desc,
                "link": link,
            })
        return items
    except Exception:
        return []


def register(mcp):

    @mcp.tool()
    async def get_world_news() -> str:
        """
        Fetch the latest global headlines from BBC, CNBC, NYT, and Al Jazeera simultaneously.
        Use when the user asks 'What's going on?', 'Brief me', 'Any news?', 'What did I miss?'.
        """
        async with httpx.AsyncClient(follow_redirects=True) as client:
            results = await asyncio.gather(
                *[_fetch_and_parse_feed(client, url) for url in SEED_FEEDS]
            )

        articles = [a for feed in results for a in feed]
        if not articles:
            return "Global news grid is unresponsive right now."

        lines = [f"### GLOBAL NEWS BRIEFING — {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n"]
        for a in articles[:12]:
            lines.append(f"[{a['source']}] {a['title']}")
            if a["summary"]:
                lines.append(f"  {a['summary']}")
            lines.append(f"  {a['link']}\n")
        return "\n".join(lines)

    @mcp.tool()
    async def search_web(query: str, max_results: int = 5) -> str:
        """
        Search the web using DuckDuckGo and return a summary of the top results.
        Use for any question that needs current information, facts, or general lookups.
        """
        try:
            from ddgs import DDGS
            results = await asyncio.to_thread(
                lambda: list(DDGS().text(query, max_results=max_results))
            )
            if not results:
                return f"No results found for: {query}"

            lines = [f"### Web Search: {query}\n"]
            for i, r in enumerate(results, 1):
                lines.append(f"{i}. **{r.get('title', 'No title')}**")
                lines.append(f"   {r.get('body', '')[:300]}")
                lines.append(f"   {r.get('href', '')}\n")
            return "\n".join(lines)
        except ImportError:
            return "Search unavailable — run: uv add duckduckgo-search"
        except Exception as e:
            return f"Search failed: {e}"

    @mcp.tool()
    async def fetch_url(url: str) -> str:
        """
        Fetch the raw text content of any URL.
        Use to read an article, webpage, or API response.
        """
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
                r = await client.get(url, headers={"User-Agent": "JARVIS-AI/2.0"})
                r.raise_for_status()
                # Strip HTML tags for cleaner content
                text = re.sub(r"<[^>]+>", " ", r.text)
                text = re.sub(r"\s+", " ", text).strip()
                return text[:5000]
        except Exception as e:
            return f"Could not fetch URL: {e}"

    @mcp.tool()
    async def get_weather(city: str) -> str:
        """
        Get current weather conditions for any city.
        Use when user asks about the weather, temperature, or forecast.
        """
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
                # wttr.in is a free weather service — no API key needed
                r = await client.get(
                    f"https://wttr.in/{city}?format=j1",
                    headers={"User-Agent": "JARVIS-AI/2.0"},
                )
                r.raise_for_status()
                data = r.json()
                current = data["current_condition"][0]
                area = data["nearest_area"][0]
                area_name = area["areaName"][0]["value"]
                country = area["country"][0]["value"]
                desc = current["weatherDesc"][0]["value"]
                temp_c = current["temp_C"]
                feels_c = current["FeelsLikeC"]
                humidity = current["humidity"]
                wind_kmph = current["windspeedKmph"]
                return (
                    f"Weather in {area_name}, {country}: {desc}. "
                    f"Temperature: {temp_c}°C (feels like {feels_c}°C). "
                    f"Humidity: {humidity}%. Wind: {wind_kmph} km/h."
                )
        except Exception as e:
            return f"Could not fetch weather for {city}: {e}"

    @mcp.tool()
    async def open_world_monitor() -> str:
        """
        Opens the World Monitor dashboard in the default browser for a live global map view.
        Always call this after delivering a world news brief.
        """
        try:
            webbrowser.open("https://worldmonitor.app/")
            return "World Monitor is now live on your screen."
        except Exception as e:
            return f"Could not open World Monitor: {e}"

    @mcp.tool()
    async def open_url(url: str) -> str:
        """
        Open any URL in the default web browser.
        Use when the user wants to visit a website or open a link.
        """
        try:
            webbrowser.open(url)
            return f"Opened {url} in your browser."
        except Exception as e:
            return f"Could not open URL: {e}"
