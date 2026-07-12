import os
import sys
import time
import json
import subprocess
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

def renew_tistory_cookies():
    # 1. Load .env
    load_dotenv()
    kakao_email = os.environ.get("KAKAO_EMAIL")
    kakao_password = os.environ.get("KAKAO_PASSWORD")

    if not kakao_email or not kakao_password:
        print("Error: KAKAO_EMAIL or KAKAO_PASSWORD not found in .env file.")
        print("Please create a .env file and add your credentials.")
        sys.exit(1)

    print("Starting Playwright to renew Tistory cookies...")
    with sync_playwright() as p:
        # Headless=False to allow user to solve Captcha if it appears
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            locale="ko-KR"
        )
        page = context.new_page()

        # Apply stealth to bypass basic bot detections
        Stealth().apply_stealth_sync(page)

        try:
            print("Navigating to Tistory login...")
            page.goto("https://www.tistory.com/auth/login")
            
            print("Clicking Kakao login button...")
            page.locator('.btn_login').click()
            
            print("Entering Kakao credentials...")
            page.wait_for_selector('input[name="loginId"]', timeout=10000)
            page.fill('input[name="loginId"]', kakao_email)
            page.fill('input[name="password"]', kakao_password)
            page.click('.btn_g.highlight.submit')
            
            print("Waiting for login to complete... (If Captcha appears, please solve it in the browser!)")
            
            from urllib.parse import urlparse
            page.wait_for_url(lambda url: urlparse(url).netloc.endswith("tistory.com") and "auth/login" not in url, timeout=60000)
            time.sleep(3) # Give it a moment to set all cookies
            
            # Check if login was successful by navigating to write page
            page.goto("https://gumdrop.tistory.com/manage/post")
            page.wait_for_load_state('networkidle')
            time.sleep(3)
            
            if "login" in page.url:
                print("Error: Login failed. Please check credentials or solve captcha.")
                sys.exit(1)
                
            print("Login successful! Extracting cookies...")
            new_cookies = context.cookies()
            cookies_json = json.dumps(new_cookies)
            
            # Save locally just in case
            with open("tistory_cookies.json", "w", encoding="utf-8") as f:
                f.write(cookies_json)
            print("Saved cookies to tistory_cookies.json locally.")
            
            # Update GitHub Secrets using gh cli
            print("Updating GitHub Secret (TISTORY_COOKIES) using gh cli...")
            try:
                # Assuming gh cli is installed and authenticated
                process = subprocess.run(
                    ['gh', 'secret', 'set', 'TISTORY_COOKIES'],
                    input=cookies_json.encode('utf-8'),
                    capture_output=True,
                    check=True
                )
                print("Successfully updated GitHub Secret 'TISTORY_COOKIES'!")
            except subprocess.CalledProcessError as e:
                print(f"Failed to update GitHub Secret. Is 'gh' CLI installed and authenticated?")
                print(f"Error output: {e.stderr.decode('utf-8')}")
                print("\nYou can manually copy the contents of tistory_cookies.json to your GitHub Secrets.")
            except FileNotFoundError:
                print("GitHub CLI ('gh') not found. Please install it to update secrets automatically.")
                print("You can manually copy the contents of tistory_cookies.json to your GitHub Secrets.")

        except Exception as e:
            print(f"Error during login process: {e}")
            sys.exit(1)
        finally:
            browser.close()

if __name__ == "__main__":
    renew_tistory_cookies()
