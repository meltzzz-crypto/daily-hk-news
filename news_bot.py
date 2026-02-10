import feedparser
import requests
import os
import time
from datetime import datetime
from bs4 import BeautifulSoup

# 설정
RSS_URL = "https://www.mk.co.kr/rss/50300009/"
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

def get_summary_from_url(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, "html.parser")
        
        # 본문 찾기 (매일경제 사이트 구조 분석)
        content = ""
        for selector in ["div.art_txt", "div.news_cnt_detail_wrap", ".txt_area"]:
            element = soup.select_one(selector)
            if element:
                content = element.get_text(separator=" ").strip()
                break
        
        if not content: return None

        # 3문장 요약 (간단한 로직)
        sentences = content.split('다.')
        summary = []
        for s in sentences:
            s = s.strip()
            if len(s) > 30 and "기자" not in s: # 너무 짧거나 기자 이름 등 제외
                summary.append(s + '다.')
                if len(summary) >= 3: break
        
        return summary
    except:
        return None

def fetch_rss_news():
    print("뉴스 가져오는 중...")
    feed = feedparser.parse(RSS_URL)
    news_items = []
    
    # 13개 가져오기
    for entry in feed.entries[:13]:
        link = entry.link
        print(f"처리 중: {entry.title}")
        
        # 본문 요약 시도
        summary_points = get_summary_from_url(link)
        
        if summary_points:
            desc = "\n".join([f"- {p}" for p in summary_points])
        else:
            desc = entry.description[:100] + "..." # 실패하면 기본 요약
            
        news_items.append({
            "title": entry.title,
            "link": link,
            "summary": desc,
            "published": entry.published
        })
        time.sleep(0.5)
    
    return news_items

def send_to_discord(items):
    if not items: return
    
    # 10개씩 나눠서 보내기 (디스코드 제한)
    chunks = [items[i:i + 10] for i in range(0, len(items), 10)]
    
    for i, chunk in enumerate(chunks):
        embeds = []
        if i == 0:
            embeds.append({
                "title": "📰 매일경제 부동산 주요 뉴스 (13선)",
                "description": f"{datetime.now().strftime('%Y-%m-%d')} 아침 뉴스 요약입니다.",
                "color": 0x00ff00
            })
            
        for item in chunk:
            embeds.append({
                "title": item['title'],
                "url": item['link'],
                "description": item['summary'],
                "footer": {"text": "MK News"}
            })
            
        requests.post(WEBHOOK_URL, json={"username": "MK부동산뉴스봇", "embeds": embeds})
        time.sleep(1)

if __name__ == "__main__":
    news = fetch_rss_news()
    send_to_discord(news)
