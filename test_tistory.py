import json
import time
from playwright.sync_api import sync_playwright

def main():
    try:
        with open('tistory_cookies.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()
            cookies_str = lines[-1].strip()
        raw_cookies = json.loads(cookies_str)
    except Exception as e:
        print("Failed to load cookies:", e)
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            locale="ko-KR",
            permissions=["clipboard-read", "clipboard-write"]
        )
        
        valid_cookies = []
        for c in raw_cookies:
            domain = c.get('domain', '.tistory.com')
            if domain == 'tistory.com':
                domain = '.tistory.com'
            valid_cookies.append({
                'name': str(c.get('name', '')),
                'value': str(c.get('value', '')),
                'domain': domain,
                'path': c.get('path', '/')
            })
            
        context.add_cookies(valid_cookies)
        page = context.new_page()
        page.goto("https://gumdrop.tistory.com/manage/post")
        page.wait_for_load_state('networkidle')
        time.sleep(5)
        
        if "login" in page.url:
            print("Login failed")
            browser.close()
            return
            
        print("Successfully logged in. Saving screenshot and HTML...")
        page.screenshot(path="tistory_editor.png", full_page=True)
        
        with open("tistory_editor.html", "w", encoding="utf-8") as f:
            f.write(page.content())
            
        print("Done.")
        browser.close()

if __name__ == "__main__":
    main()
