import os
import time
import json
import requests
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from playwright.sync_api import sync_playwright

NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY")
KAKAO_EMAIL = os.environ.get("KAKAO_EMAIL")
KAKAO_PASSWORD = os.environ.get("KAKAO_PASSWORD")
TISTORY_COOKIES = os.environ.get("TISTORY_COOKIES")

def get_google_trends_keyword():
    try:
        print("Fetching Google Trends data via RSS...")
        # Using google.co.kr or generic trends
        url = "https://trends.google.co.kr/trends/trendingsearches/daily/rss?geo=KR"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        root = ET.fromstring(response.content)
        keywords = []
        for item in root.findall('.//item'):
            title = item.find('title')
            if title is not None:
                keywords.append(title.text)
                
        if keywords:
            print(f"Extracted keyword: {keywords[0]}")
            return keywords[0]
        else:
            raise Exception("No keywords found in RSS feed.")
    except requests.exceptions.Timeout:
        print("TimeoutError: Google Trends RSS request timed out after 30 seconds.")
        return "자동 포스팅" # Fallback keyword
    except Exception as e:
        print(f"Failed to extract Google realtime keyword: {e}")
        return "자동 포스팅" # Fallback keyword

def generate_blog_post(keyword):
    print(f"Generating post for keyword: {keyword}")
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type": "application/json",
        "accept": "application/json"
    }

    # As per rules: 6000+ characters, Korean only, SEO optimized, heavily use keywords
    prompt = f"""
당신은 최고의 구글 SEO 전문가이자 전문 블로거입니다.
다음 키워드를 바탕으로 구글 검색에 최상단 노출될 수 있는 완벽한 블로그 포스팅을 작성해주세요.

[키워드]: {keyword}

[규칙]
1. 반드시 한글로만 작성하세요. (외국어 구절이나 영어가 섞이지 않도록 주의할 것, 필요한 명칭 외에는 절대적으로 한국어 사용)
2. 글의 길이는 6000자 이상으로 매우 길고 상세하게 작성해야 합니다.
3. '{keyword}' 키워드를 제목과 본문에 자연스럽게, 하지만 최대한 많이 사용하세요.
4. 마크다운 형식으로 작성하세요.
5. 중간중간 관련 정보, 팁, 분석 등을 포함하여 깊이 있는 정보를 제공하세요.
6. 글의 첫 부분에는 이 글의 요약을 제공하고, 마지막에는 결론을 내리세요.
"""

    payload = {
        "model": "meta/llama-3.1-70b-instruct",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 4000
    }

    try:
        print("Sending request to NVIDIA NIM API (timeout=180s)...")
        response = requests.post(url, headers=headers, json=payload, timeout=180)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except requests.exceptions.Timeout:
        print("TimeoutError: NVIDIA NIM API request timed out after 180 seconds.")
        raise
    except Exception as e:
        print(f"Error generating post: {e}")
        raise

def generate_image_url(keyword):
    # Using Pollinations AI for free text-to-image without API keys
    # Replacing spaces with URL-friendly characters
    encoded_keyword = requests.utils.quote(f"high quality realistic blog cover image for {keyword}")
    url = f"https://pollinations.ai/p/{encoded_keyword}?width=800&height=400&nologo=true"
    return url

def publish_to_tistory(title, content):
    if not TISTORY_COOKIES and (not KAKAO_EMAIL or not KAKAO_PASSWORD):
        print("Error: Either TISTORY_COOKIES or KAKAO credentials must be set.")
        sys.exit(1)
        
    print("Starting Playwright to publish on Tistory...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            locale="ko-KR"
        )
        
        # Inject cookies if provided (Bypasses Login and Captchas completely)
        if TISTORY_COOKIES:
            print("Injecting Tistory cookies for authentication...")
            try:
                raw_cookies = json.loads(TISTORY_COOKIES)
                valid_cookies = []
                # If user pasted a single dict instead of list
                if isinstance(raw_cookies, dict):
                    raw_cookies = [raw_cookies]
                    
                for c in raw_cookies:
                    # Playwright requires name, value, and either domain or url
                    # By forcing 'url' to the target blog, we bypass all domain validation issues.
                    new_c = {
                        'name': str(c.get('name', '')),
                        'value': str(c.get('value', '')),
                        'domain': '.tistory.com',
                        'path': '/'
                    }
                    valid_cookies.append(new_c)
                    
                print(f"DEBUG valid_cookies: {valid_cookies}")
                context.add_cookies(valid_cookies)
            except Exception as e:
                print(f"Failed to parse TISTORY_COOKIES JSON. Error: {e}")
                sys.exit(1)
                
        page = context.new_page()
        
        try:
            # 1. Login (Only if no cookies are provided)
            if not TISTORY_COOKIES:
                print("Navigating to Tistory login...")
                page.goto("https://www.tistory.com/auth/login")
                page.get_by_text("카카오계정 로그인").click()
                
                print("Entering Kakao credentials...")
                page.wait_for_selector('input[name="loginId"]', timeout=10000)
                page.fill('input[name="loginId"]', KAKAO_EMAIL)
                page.fill('input[name="password"]', KAKAO_PASSWORD)
                page.click('.btn_g.highlight.submit')
                
                print("Waiting for login completion...")
                page.wait_for_load_state('networkidle')
                time.sleep(3)
            
            # 2. Go to Write Page
            print("Navigating to the write page...")
            page.goto("https://gumdrop.tistory.com/manage/post")
            page.wait_for_load_state('networkidle')
            time.sleep(3) # Wait for editor to load
            
            # Check if login was successful
            if "login" in page.url:
                print("Error: Redirected to login page. Authentication failed! Check cookies or credentials.")
                sys.exit(1)
            
            # Handle possible popup alerts ("임시 저장된 글이 있습니다" 등)
            page.on("dialog", lambda dialog: dialog.dismiss())
            
            # 3. Enter Title
            print("Entering title...")
            page.get_by_placeholder("제목을 입력하세요").fill(title)
            
            # 4. Switch to Markdown mode
            print("Switching to Markdown mode...")
            try:
                mode_btn = page.locator('button:has-text("기본모드")').first
                if mode_btn.is_visible():
                    mode_btn.click(timeout=5000)
                    page.locator('button:has-text("마크다운")').first.click(timeout=5000)
                    page.on("dialog", lambda dialog: dialog.accept())
            except Exception as e:
                print(f"Could not switch to Markdown via menu: {e}")
            
            # 5. Enter Content
            print("Entering content...")
            editor_area = page.locator('.CodeMirror-scroll').first
            if editor_area.is_visible():
                editor_area.click()
            else:
                page.locator('#editor-root').first.click() # fallback
            
            page.keyboard.insert_text(content)
            
            # 6. Click Publish
            print("Clicking Publish buttons...")
            page.locator('button:has-text("완료")').last.click()
            time.sleep(2)
            
            # The final modal publish button
            page.locator('button:has-text("공개 발행")').first.click()
            
            # Wait for successful publish navigation
            page.wait_for_load_state('networkidle')
            time.sleep(3)
            print("Successfully published to Tistory via Headless Browser!")
            
        except Exception as e:
            print(f"Error during Playwright execution: {e}")
            page.screenshot(path="playwright_error.png")
            print("Saved screenshot to playwright_error.png for debugging.")
            sys.exit(1)
        finally:
            browser.close()

def main():
    if not NVIDIA_API_KEY:
        print("Error: NVIDIA_API_KEY environment variable is not set.")
        sys.exit(1)

    # 1. Get Keyword
    keyword = get_google_trends_keyword()

    # 2. Generate Content
    try:
        content = generate_blog_post(keyword)
    except Exception as e:
        print(f"Failed to generate content. Exiting. Error: {e}")
        sys.exit(1)

    # 3. Generate Image
    image_url = generate_image_url(keyword)
    
    # 4. Construct Final Post
    today = datetime.now().strftime("%Y-%m-%d")
    title_keyword = keyword.replace(" ", "-")
    filename = f"posts/{today}-{title_keyword}.md"
    
    # Create posts directory if it doesn't exist
    os.makedirs("posts", exist_ok=True)
    
    # Format the markdown with image
    final_markdown = f"# {keyword} 완벽 분석 및 총정리\n\n"
    final_markdown += f"![{keyword} SEO Image]({image_url})\n\n"
    final_markdown += content

    with open(filename, "w", encoding="utf-8") as f:
        f.write(final_markdown)
    
    print(f"Successfully generated post: {filename}")
    
    # 5. Publish to Tistory via Playwright
    title = f"{keyword} 완벽 분석 및 총정리"
    publish_to_tistory(title, final_markdown)

if __name__ == "__main__":
    main()
