import json
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    try:
        # test 1: empty
        # context.add_cookies([]) 
        
        # test 2: missing url and domain
        context.add_cookies([{'name': 'test', 'value': '123', 'path': '/'}])
    except Exception as e:
        print(f"Test 2 Error: {e}")

    try:
        # test 3: url only
        context.add_cookies([{'name': 'test', 'value': '123', 'url': 'https://gumdrop.tistory.com', 'path': '/'}])
        print("Test 3 passed!")
    except Exception as e:
        print(f"Test 3 Error: {e}")
        
    browser.close()
