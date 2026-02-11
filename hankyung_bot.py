import os
import time
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# Configuration
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
TARGET_URL = "https://www.hankyung.com/mr"

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in background
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def get_article_summary(driver, url):
    """
    Visits the article URL and extracts the first 3 valid sentences.
    """
    try:
        driver.get(url)
        # Wait for body text to load
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#articletxt, .article-body, .article_body"))
        )
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # Common body selectors for Hankyung
        content_element = soup.select_one("#articletxt") or soup.select_one(".article-body") or soup.select_one(".article_body")
        
        if not content_element:
            return None
            
        text = content_element.get_text(separator="\n").strip()
        sentences = text.split('.')
        
        summary = []
        for s in sentences:
            s = s.strip()
            # Filter out short strings, ads, or metadata
            if len(s) > 30 and "기자" not in s and "이메일" not in s and "ⓒ" not in s:
                summary.append(s + '.')
                if len(summary) >= 3:
                    break
                    
        return summary
    except Exception as e:
        print(f"Error summarizing {url}: {e}")
        return None

def fetch_hankyung_mr():
    print(f"Fetching {TARGET_URL}...")
    driver = setup_driver()
    data = {
        "youtube_link": None,
        "articles": []
    }
    
    try:
        driver.get(TARGET_URL)
        # Wait for the main content
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
        )
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # 1. Find YouTube Link
        # Usually in a section '모닝루틴 생방송' or looking for youtube iframe/link
        # Based on screenshot, there is a "LIVE 2026년 2월 11일 모닝루틴" section with a link
        youtube_candidates = soup.find_all("a", href=True)
        for a in youtube_candidates:
            href = a['href']
            if "youtube.com/watch" in href or "youtu.be" in href:
                data["youtube_link"] = href
                break
        
        if not data["youtube_link"]:
             # Fallback: finding iframe if embedded
            iframe = soup.find("iframe", src=True)
            if iframe and "youtube" in iframe['src']:
                data["youtube_link"] = iframe['src']

        # 2. Find "모닝루틴 Pick! 오늘의 기사"
        # Since we don't know the exact class, we look for the header text and get following list
        # We can simulate clicking links or just grabbing Href
        
        print("Searching for articles...")
        # Inspecting page structure via Beautiful Soup logic since we can't see source directly
        # We look for the text "모닝루틴 Pick! 오늘의 기사" and find the list roughly
        
        # Broad search for article links in the right sidebar or main listing
        # Hankyung article links usually contain '/article/'
        
        # Let's try to be smart searching for the container.
        # Based on screenshot, it's a list on the right. 
        # We'll just pick all articles that look like news in the main container if specific selector fails.
        
        article_links = []
        
        # Try to find specific section by text
        headers = soup.find_all(string=lambda t: t and "오늘의 기사" in t)
        
        target_container = None
        if headers:
            # Go up to find the container
            header = headers[0]
            target_container = header.find_parent("div") or header.find_parent("section")
            # Maybe go up one more level if it's just a span
            if target_container and len(target_container.get_text()) < 50:
                target_container = target_container.parent
        
        if target_container:
            links = target_container.find_all("a", href=True)
        else:
            # Fallback: Get all links that look like articles
            links = soup.find_all("a", href=True)
            
        seen_urls = set()
        
        for link in links:
            url = link['href']
            title = link.get_text(strip=True)
            
            if "/article/" in url and title and len(title) > 10:
                if not url.startswith("http"):
                    url = "https://www.hankyung.com" + url
                    
                if url not in seen_urls:
                    article_links.append({"title": title, "url": url})
                    seen_urls.add(url)
                    
        # Limit to top 10 as requested
        # Usually the "Pick" section is at the top or sidebar.
        # If we got too many, maybe we want to be more selective.
        # For now, let's take the first 10 distinct articles found near the header or just first 10.
        
        target_articles = article_links[:10]
        
        print(f"Found {len(target_articles)} articles. Processing summaries...")
        
        for art in target_articles:
            print(f"Summarizing: {art['title']}...")
            summary = get_article_summary(driver, art['url'])
            art['summary'] = summary
            time.sleep(1) # Be polite
            
        data["articles"] = target_articles
        
    except Exception as e:
        print(f"Error scraping: {e}")
    finally:
        driver.quit()
        
    return data

def send_to_discord(data):
    if not WEBHOOK_URL:
        print("Error: DISCORD_WEBHOOK_URL not set.")
        return

    articles = data["articles"]
    youtube = data["youtube_link"]
    
    if not articles:
        print("No articles to send.")
        return
        
    print(f"Sending {len(articles)} items to Discord...")
    
    embeds = []
    
    # 1. Header & YouTube Embed
    description = f"{datetime.now().strftime('%Y-%m-%d')} 한국경제 모닝루틴 Pick"
    if youtube:
        description += f"\n📺 [라이브 방송 보러가기]({youtube})"
        
    embeds.append({
        "title": "☕ 굿모닝! 한경 모닝루틴 브리핑",
        "description": description,
        "color": 0x1E90FF, # Dodger Blue
        "url": TARGET_URL
    })
    
    # 2. Article Embeds
    # Discord limit: 10 embeds per message.
    # If we have 1 header + 10 articles = 11 embeds -> Split required.
    
    current_embeds = [embeds[0]] # Start with header
    
    for i, art in enumerate(articles):
        summ_text = ""
        if art.get("summary"):
            for point in art["summary"]:
                summ_text += f"- {point}\n"
        else:
            summ_text = "요약을 가져오지 못했습니다. 링크를 확인하세요."
            
        article_embed = {
            "title": f"{i+1}. {art['title']}",
            "url": art['url'],
            "description": summ_text,
            "color": 0xFFFFFF # White
        }
        
        current_embeds.append(article_embed)
        
        # If we reached 10 embeds, send and reset
        if len(current_embeds) == 10:
            requests.post(WEBHOOK_URL, json={"username": "한경모닝루틴봇", "embeds": current_embeds})
            current_embeds = []
            time.sleep(1)
            
    # Send remaining
    if current_embeds:
        requests.post(WEBHOOK_URL, json={"username": "한경모닝루틴봇", "embeds": current_embeds})
        
    print("Sent successfully.")

if __name__ == "__main__":
    data = fetch_hankyung_mr()
    send_to_discord(data)
