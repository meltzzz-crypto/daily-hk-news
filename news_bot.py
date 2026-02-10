import feedparser
import requests
import json
import os
from datetime import datetime
from bs4 import BeautifulSoup

# Configuration
# MK Real Estate News RSS Feed
RSS_URL = "https://www.mk.co.kr/rss/50300009/"
# Fallback Webhook URL (Ideally, this should be an environment variable)
# But for local testing convenience for the user, we can default it or ask them to set it.
# In GitHub Actions, we will use secrets.
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/1470648109892636705/VnxSywBvxtK9sOYHxQtxdImQM5US7ghGtyzk7NFLYKoAgLpdaI0a-Yea-36RO-ihphiS")

def fetch_rss_news():
    """Fetches news from the RSS feed."""
    print(f"Fetching news from {RSS_URL}...")
    feed = feedparser.parse(RSS_URL)
    
    news_items = []
    # Get top 5 news items
    for entry in feed.entries[:5]:
        title = entry.title
        link = entry.link
        # RSS 'description' often contains HTML, so we clean it up or just use it as summary
        summary = entry.description
        
        # Simple cleanup if summary contains HTML tags (optional, feedparser usually handles entities)
        soup = BeautifulSoup(summary, "html.parser")
        clean_summary = soup.get_text()[:200] + "..." if len(soup.get_text()) > 200 else soup.get_text()
        
        news_items.append({
            "title": title,
            "link": link,
            "summary": clean_summary,
            "published": entry.published
        })
    
    return news_items

def send_to_discord(news_items):
    """Sends formatted news to Discord."""
    if not news_items:
        print("No news items to send.")
        return

    print(f"Sending {len(news_items)} news items to Discord...")

    # Create the embed structure
    embeds = []
    
    # Header Embed
    embeds.append({
        "title": "📰 매일경제 부동산 주요 뉴스",
        "description": f"{datetime.now().strftime('%Y-%m-%d %H:%M')} 기준 최신 뉴스입니다.",
        "color": 0x00ff00  # Green color
    })

    # News Item Embeds
    for item in news_items:
        embeds.append({
            "title": item['title'],
            "url": item['link'],
            "description": item['summary'],
            "footer": {"text": item['published']}
        })
        
        # Discord has a limit of 10 embeds per message, and also character limits.
        # Ensure we don't exceed limits.
        if len(embeds) >= 10:
            break
            
    payload = {
        "username": "MK부동산뉴스봇",
        "embeds": embeds
    }

    try:
        response = requests.post(WEBHOOK_URL, json=payload)
        response.raise_for_status()
        print("Successfully sent to Discord.")
    except requests.exceptions.RequestException as e:
        print(f"Error sending to Discord: {e}")

if __name__ == "__main__":
    if "123456789" in WEBHOOK_URL:
        print("Error: Please set a valid WEBHOOK_URL in the script or environment variables.")
    else:
        news = fetch_rss_news()
        send_to_discord(news)
