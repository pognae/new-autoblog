import os
import time
import json
import requests
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from playwright.sync_api import sync_playwright
import markdown

NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY")
KAKAO_EMAIL = os.environ.get("KAKAO_EMAIL")
KAKAO_PASSWORD = os.environ.get("KAKAO_PASSWORD")
TISTORY_COOKIES = os.environ.get("TISTORY_COOKIES")

def get_google_trends_keyword():
    try:
        print("Fetching Google Trends data via RSS...")
        # Using google.com for trends
        url = "https://trends.google.com/trending/rss?geo=KR"
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

def generate_blog_post_gemini(prompt):
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        raise Exception("GEMINI_API_KEY environment variable is not set for fallback.")
    
    print("Sending request to Google Gemini API (fallback)...")
    
    models_to_try = ["gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-2.5-pro"]
    last_error = None
    
    for model in models_to_try:
        print(f"Trying Gemini model: {model}...")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.7}
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=180)
        
        if response.status_code == 200:
            data = response.json()
            try:
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError) as e:
                print(f"Failed to parse Gemini response for {model}: {data}")
                raise
        else:
            print(f"Model {model} failed with status {response.status_code}: {response.text}")
            last_error = f"{response.status_code} Error for {model}"
            
    raise Exception(f"All Gemini models failed. Last error: {last_error}")

def generate_blog_post(keyword):
    print(f"Generating post for keyword: {keyword}")
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type": "application/json",
        "accept": "application/json"
    }

    prompt = f"""
당신은 상위 1% 구글 SEO 전문가이자 프로 블로거입니다.
주어진 키워드를 주제로, 구글 검색 1위에 무조건 노출될 수 있는 압도적인 퀄리티의 블로그 포스팅을 작성해 주세요.

[타겟 키워드]: {keyword}

[필수 준수 규칙]
1. **분량**: 반드시 6,000자 이상의 매우 긴 장문으로 작성하세요. 내용이 빈약하면 안 됩니다. 서론, 본론(최소 5개 이상의 상세 목차), 결론, Q&A 형식까지 포함하여 최대한 자세하고 정성스럽게 적어주세요.
2. **언어**: 100% 한국어로만 작성하세요. (부득이한 전문 용어 외에는 영어 사용 엄격히 금지)
3. **SEO 최적화**: '{keyword}' 키워드를 제목, 소제목(H2, H3), 본문 첫 문단, 본문 중간, 결론에 매우 자연스럽게 20회 이상 반복해서 배치하세요.
4. **마크다운 포맷**: H1, H2, H3, 리스트(-), 인용구(>) 등을 적극적으로 활용하여 가독성 높고 화려한 마크다운 문서를 만드세요.
5. **독자 가치 제공**: 단순한 겉핥기식 정보가 아닌, 실제 독자가 읽고 "정말 유용하다"라고 느낄 수 있는 깊이 있는 전문 지식, 구체적인 사례, 실전 팁, 주의사항 등을 꽉꽉 채워 넣으세요.
6. **목차 구성**:
   - 도입부 (독자의 흥미 유발 및 핵심 요약)
   - 주제에 대한 상세한 설명 및 배경지식
   - 구체적인 장단점, 특징, 또는 활용법 (다양한 관점에서 분석)
   - 실생활 예시 및 꿀팁 방출
   - 자주 묻는 질문 (FAQ) 3가지 이상
   - 최종 결론 및 요약
"""

    payload = {
        "model": "meta/llama-3.1-70b-instruct",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 6000
    }

    try:
        print("Sending request to NVIDIA NIM API (timeout=180s)...")
        response = requests.post(url, headers=headers, json=payload, timeout=180)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"NVIDIA API failed or timed out: {e}")
        print("Falling back to Google Gemini API...")
        return generate_blog_post_gemini(prompt)

def generate_image_url(keyword):
    # Using Pollinations AI with path parameters to avoid query strings which Tistory's image proxy might block
    encoded_keyword = requests.utils.quote(f"high quality realistic blog cover image for {keyword}")
    # Using the direct image endpoint without any query parameters
    url = f"https://image.pollinations.ai/prompt/{encoded_keyword}"
    return url

def publish_to_tistory(title, content):
    cookies_data = TISTORY_COOKIES
    if not cookies_data and os.path.exists("tistory_cookies.json"):
        try:
            with open("tistory_cookies.json", "r", encoding="utf-8") as f:
                cookies_data = f.read()
        except Exception as e:
            print(f"Failed to load local tistory_cookies.json: {e}")
            
    if not cookies_data and (not KAKAO_EMAIL or not KAKAO_PASSWORD):
        print("Error: Either TISTORY_COOKIES or KAKAO credentials must be set.")
        sys.exit(1)
        
    print("Starting Playwright to publish on Tistory...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            locale="ko-KR",
            permissions=["clipboard-read", "clipboard-write"]
        )
        
        # Inject cookies if provided (Bypasses Login and Captchas completely)
        if cookies_data:
            print("Injecting Tistory cookies for authentication...")
            try:
                raw_cookies = json.loads(cookies_data)
                valid_cookies = []
                # If user pasted a single dict instead of list
                if isinstance(raw_cookies, dict):
                    raw_cookies = [raw_cookies]
                    
                for c in raw_cookies:
                    # Playwright requires name, value, and either domain or url
                    # By forcing domain and path, we bypass url validation issues as per rules.
                    domain = c.get('domain', '.tistory.com')
                    # Ensure domain starts with '.' for broad matching if it's tistory.com
                    if domain == 'tistory.com':
                        domain = '.tistory.com'
                        
                    new_c = {
                        'name': str(c.get('name', '')),
                        'value': str(c.get('value', '')),
                        'domain': domain,
                        'path': c.get('path', '/')
                    }
                    valid_cookies.append(new_c)
                    
                print(f"DEBUG valid_cookies: {valid_cookies}")
                context.add_cookies(valid_cookies)
            except Exception as e:
                print(f"Failed to parse cookies data JSON. Error: {e}")
                sys.exit(1)
                
        page = context.new_page()
        
        try:
            # 2. Go to Write Page
            print("Navigating to the write page...")
            page.goto("https://gumdrop.tistory.com/manage/post")
            page.wait_for_load_state('networkidle')
            time.sleep(3) # Wait for editor to load
            
            # Check if login was successful
            if "login" in page.url:
                print("Cookies expired, invalid, or missing. Falling back to ID/PW Kakao login with Stealth...")
                if not KAKAO_EMAIL or not KAKAO_PASSWORD:
                    print("Error: KAKAO_EMAIL and KAKAO_PASSWORD are required for fallback login.")
                    sys.exit(1)
                
                from playwright_stealth import Stealth
                Stealth().apply_stealth_sync(page)
                
                print("Navigating to Tistory login...")
                page.goto("https://www.tistory.com/auth/login")
                page.get_by_text("카카오계정으로 로그인").click()
                
                print("Entering Kakao credentials...")
                page.wait_for_selector('input[name="loginId"]', timeout=10000)
                page.fill('input[name="loginId"]', KAKAO_EMAIL)
                page.fill('input[name="password"]', KAKAO_PASSWORD)
                page.click('.btn_g.highlight.submit')
                
                print("Waiting for login completion...")
                page.wait_for_load_state('networkidle')
                time.sleep(3)
                
                # Go to write page again
                print("Navigating to the write page after fallback login...")
                page.goto("https://gumdrop.tistory.com/manage/post")
                page.wait_for_load_state('networkidle')
                time.sleep(3)
                
                if "login" in page.url:
                    print("Error: Fallback login also failed. Check Kakao credentials or Captcha.")
                    sys.exit(1)
                else:
                    print("Fallback login successful. Saving new cookies to tistory_cookies.json...")
                    new_cookies = context.cookies()
                    try:
                        with open("tistory_cookies.json", "w", encoding="utf-8") as f:
                            json.dump(new_cookies, f)
                    except Exception as e:
                        print(f"Failed to save new cookies: {e}")
            
            # Handle possible popup alerts smartly
            def handle_dialog(dialog):
                if "마크다운" in dialog.message or "초기화" in dialog.message or "변경" in dialog.message:
                    dialog.accept()
                else:
                    dialog.dismiss()
            
            page.on("dialog", handle_dialog)
            # 3. Enter Title
            print("Entering title...")
            title_input = page.get_by_role("textbox", name="제목을 입력하세요")
            title_input.fill(title)
            
            # 4. Convert Markdown to HTML
            print("Converting Markdown to HTML...")
            html_content = markdown.markdown(content, extensions=['fenced_code', 'tables', 'extra', 'nl2br'])
            
            # 5. Enter Content using TinyMCE API
            print("Entering content via TinyMCE...")
            try:
                # Wait for TinyMCE to be ready
                page.wait_for_function('window.tinymce !== undefined && (window.tinymce.activeEditor || window.tinymce.editors.length > 0)', timeout=15000)
                
                success = page.evaluate('''([html]) => {
                    const editor = window.tinymce && (window.tinymce.activeEditor || window.tinymce.editors[0]);
                    if (!editor) return false;
                    
                    editor.setContent(html);
                    editor.undoManager.add();
                    editor.setDirty(true);
                    editor.save();
                    editor.fire("change");
                    editor.fire("input");
                    return true;
                }''', [html_content])
                
                if success:
                    print("Successfully injected HTML via TinyMCE.")
                else:
                    print("Warning: TinyMCE injection returned false.")
            except Exception as e:
                print(f"Content insertion failed: {e}")
            
            time.sleep(2)
            
            # 5-1. Enter Tags
            print("Entering tags...")
            try:
                # Use a very broad locator for Tistory tags
                tag_input = page.locator('input[placeholder*="태그"], #tagText').first
                if tag_input.is_visible():
                    tag_input.scroll_into_view_if_needed()
                    tag_input.click(timeout=3000)
                    
                    tags = [keyword.replace(" ", ""), "이슈", "트렌드", "정보", "분석"]
                    for tag in tags:
                        tag_input.press_sequentially(tag, delay=100)
                        time.sleep(0.5)
                        page.keyboard.press("Enter")
                        time.sleep(0.5)
                    print("Successfully entered tags.")
                else:
                    print("Tag input field not found using role.")
            except Exception as e:
                print(f"Failed to enter tags: {e}")
            
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
    if not NVIDIA_API_KEY and not os.environ.get("GEMINI_API_KEY"):
        print("Error: Neither NVIDIA_API_KEY nor GEMINI_API_KEY environment variables are set.")
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
    
    # Format the markdown with image using markdown format
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
