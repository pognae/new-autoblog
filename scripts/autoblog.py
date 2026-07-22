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

def get_google_trends_keywords():
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
            print(f"Extracted keywords from RSS: {keywords}")
            return keywords
        else:
            raise Exception("No keywords found in RSS feed.")
    except requests.exceptions.Timeout:
        print("TimeoutError: Google Trends RSS request timed out after 30 seconds.")
        return []
    except Exception as e:
        print(f"Failed to extract Google realtime keyword: {e}")
        return []

def select_ai_keyword(trends_keywords):
    print("Selecting or generating AI-related keyword...")
    trends_str = ", ".join(trends_keywords) if trends_keywords else "없음"
    
    prompt = f"""
당신은 IT 및 인공지능(AI) 기술 전문 파워 블로거입니다.
구글 트렌드 실시간 키워드 목록을 분석하여, 인공지능(AI), 딥러닝, 머신러닝, AI 반도체, AI 서비스(예: ChatGPT, Claude, Midjourney 등), AI 윤리/트렌드 등 **'인공지능 및 AI 기술' 분야와 직접적인 관련이 있는 키워드**를 선정해야 합니다.

[구글 트렌드 키워드 목록]: {trends_str}

[선정 규칙]:
1. 만약 목록에 AI, 딥러닝, 머신러닝, AI 칩(NVIDIA, NPU 등), AI 서비스나 관련 기업(OpenAI, Anthropic 등) 등 AI 기술/산업과 연관된 키워드가 존재한다면, 그 중 가장 검색 매력도가 높은 키워드를 선택하세요.
2. 만약 목록에 AI 관련 키워드가 전혀 없거나 목록이 비어 있다면, **현재 가장 뜨겁고 트렌디하면서 대중적인 관심이 높고 검색 최적화(SEO)에 유리한 인공지능, 딥러닝, AI 기술 분야의 키워드/주제**를 직접 1개 발굴하여 선정하세요. (예: "ChatGPT 실용적인 활용법", "Claude 3.5 Sonnet 특징", "Llama 3.1 로컬 실행 방법", "AI 반도체 NPU 시장 전망" 등)
3. 정치적인 키워드나 민감한 사회적 이슈, 스포츠, 단순 연예인 관련 내용은 절대로 선정하거나 다루지 마십시오.

[출력 형식]:
반드시 최종 선정된 단 하나의 키워드(혹은 구)만 답변하세요. 마크다운 기호, 따옴표, 설명 없이 텍스트로만 출력하세요. (예: ChatGPT 활용법)
"""
    
    # We will try to call NVIDIA NIM API, and fallback to Gemini API
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type": "application/json",
        "accept": "application/json"
    }
    payload = {
        "model": "meta/llama-3.1-70b-instruct",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.5,
        "max_tokens": 100
    }
    
    try:
        print("Sending keyword request to NVIDIA NIM API...")
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        keyword = data["choices"][0]["message"]["content"].strip()
        keyword = keyword.replace('"', '').replace("'", "")
        print(f"Selected AI keyword: {keyword}")
        return keyword
    except Exception as e:
        print(f"NVIDIA API failed to select keyword: {e}")
        print("Falling back to Gemini API for keyword selection...")
        try:
            res = generate_blog_post_gemini(prompt).strip()
            return res.replace('"', '').replace("'", "")
        except Exception as ge:
            print(f"Gemini API also failed: {ge}")
            return "AI 기술 트렌드" # Hard fallback


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
당신은 상위 0.1% 구글 SEO 전문가이자 수만 명의 구독자를 보유한 베테랑 전문 블로거입니다.
주어진 키워드를 주제로, 구글 검색 1위에 노출될 수 있는 압도적인 퀄리티의 블로그 포스팅을 작성해 주세요.
이 포스팅은 인공지능, 딥러닝, AI 기술에 대한 주제이어야 하며, 구글 애드센스의 '저품질 콘텐츠(Low-quality content)' 및 AI 글쓰기 감지 필터에 걸리지 않도록 **반드시 실제 사람이 직접 겪고 작성한 것처럼 자연스럽고 생생한 문체**로 작성해야 합니다.

[타겟 키워드]: {keyword}

[핵심 미션 1: 인간적인 문체 및 애드센스 저품질 회피]
1. **생생한 블로거 어조 (Conversational Korean Tone)**:
   - 딱딱하고 차가운 백과사전식 설명조는 피하세요. IT/AI 분야의 전문 블로거가 독자에게 친근하게 말을 건네는 듯한 어투를 구사하세요 (예: "~합니다", "~더라고요", "~인 것 같습니다", "~라는 생각이 듭니다").
   - 실제 블로거들이 자주 쓰는 친근하고 자연스러운 표현(예: "꿀팁", "직접 써보며 느낀 점", "솔직히 말씀드리면", "이 부분은 정말 유용했습니다", "처음엔 좀 헤맸지만")을 자연스럽게 섞으세요.
2. **AI 특유의 기계적 단어 및 반복 배제**:
   - 문단 연결 시 "첫째, 둘째, 셋째"와 같이 지나치게 정형화된 열거형 표현을 남발하지 마세요. 대신 "가장 먼저 눈에 띄는 부분은", "그 다음으로 주목할 점은", "마지막으로 살펴볼 특징은" 등으로 자연스럽게 전환하세요.
   - "요약하자면", "결론적으로", "따라서", "하지만"과 같이 AI가 습관적으로 쓰는 접속사를 한 문단에서 과도하게 반복하지 마세요.
   - 모든 문장의 길이가 비슷하거나 어미가 획일적으로 끝나는 단조로운 패턴을 피하고, 호흡이 긴 문장과 임팩트 있는 짧은 문장을 조화롭게 섞으세요.
3. **스토리텔링 도입부**:
   - "안녕하세요! 오늘은 ~에 대해 알아보겠습니다."라는 로봇 같은 상투적인 인사말로 시작하지 마세요.
   - 독자가 겪을 법한 문제 상황이나, 필자가 해당 AI 기술을 접하고 겪은 흥미로운 경험담(예: "며칠 전 새로 나온 AI 툴을 세팅하느라 밤새 삽질을 하다가...", "요즘 AI 뉴스 보면 눈이 핑핑 돌 정도로 빠르죠? 저도 매일 따라가기 벅찰 때가 많습니다.")으로 본론의 포문을 열어 강렬한 첫인상을 남기세요.
4. **리스트와 줄글의 조화**:
   - 모든 정보를 일률적으로 불릿 리스트(-, * )로 나열하는 것은 AI의 전형적인 서식입니다. 핵심 설명은 설득력 있는 긴 줄글 단락으로 충분히 풀어쓰고, 요약이나 주의사항 등 꼭 필요한 곳에만 리스트를 적절히 활용하세요.

[핵심 미션 2: Google E-E-A-T 준수]
1. **Experience (경험)**: 필자가 직접 이 AI 기술/서비스를 써보고 검토한 듯한 1인칭 관점의 생생한 어투를 유지하세요. (예: "제가 직접 테스트해본 결과...", "실제로 돌려봤을 때 체감되는 속도는...")
2. **Expertise (전문성)**: 단순한 단순 외신/뉴스 번역이나 짜깁기가 아닌, 해당 AI 기술의 원리, 한계점, 실무 활용 방안에 대한 깊이 있는 해설과 인사이트를 제공하세요.
3. **Authoritativeness (권위성)**: 구조적이고 가독성이 뛰어난 목차(H2, H3)로 체계적으로 서술하세요. 소제목도 뻔한 명사형(예: "개요", "특징") 대신 매력적인 문장형(예: "직접 써보며 깨달은 가장 놀라운 변화")으로 지으세요.
4. **Trustworthiness (신뢰성)**: 과장된 찬양 일색은 피하고, 기술적 한계점, 주의사항, 부작용을 솔직하게 털어놓으며 대안을 함께 제안하세요.

[필수 준수 규칙]
1. **분량**: 반드시 6,000자 이상의 매우 긴 장문으로 작성하세요. 내용이 빈약하면 안 됩니다. 서론, 본론(최소 5개 이상의 상세 목차), 결론, Q&A 형식까지 포함하여 최대한 자세하고 정성스럽게 적어주세요.
2. **언어**: **100% 한국어로만 작성하세요.** 부득이한 고유명사나 모델명(예: ChatGPT, Claude, NVIDIA)을 제외하고는 모든 전문 용어를 한국어로 풀어서 설명하거나 한글로만 표기하세요. 영어 단어가 문장 속에 섞여 들어가는 것을 엄격히 금지합니다.
3. **SEO 최적화**: '{keyword}' 키워드를 제목, 소제목(H2, H3), 본문 첫 문단, 본문 중간, 결론에 매우 자연스럽게 20회 이상 반복해서 배치하세요.
4. **마크다운 포맷**: H1, H2, H3, 리스트(-), 인용구(>) 등을 적극적으로 활용하여 가독성 높고 화려한 마크다운 문서를 만드세요.
5. **독자 가치 제공**: 단순한 겉핥기식 정보가 아닌, 실제 독자가 읽고 "정말 유용하다"라고 느낄 수 있는 실전 팁, 주의사항, FAQ를 꽉꽉 채워 넣으세요.
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

def validate_and_fix_post(keyword, content):
    print(f"Auditing post for E-E-A-T and Korean-only compliance...")
    
    audit_prompt = f"""
당신은 구글 검색 품질 평가자이자 전문 교정 작가입니다. 
다음 블로그 포스팅이 구글 E-E-A-T 가이드라인을 완벽히 준수하고, 100% 한국어(영어 혼용 없음)로 작성되었으며, AI가 작성한 티가 전혀 나지 않고 실제 전문가가 직접 작성한 것처럼 자연스러운지 정밀 점검하고 교정해 주세요.

[대상 포스팅]
키워드: {keyword}
본문 내용:
{content}

[점검 및 교정 가이드라인]
1. **사람이 직접 쓴 듯한 자연스러운 글체로 교정 (AI 패턴 및 구글 애드센스 저품질 회피)**:
   - 문맥이 매끄럽고 인간미가 느껴지는지 확인하여, 지나치게 정형화되거나 딱딱한 번역투 문장을 친근하고 매끄러운 한국어 구어체 블로그 톤으로 교정하세요.
   - "요약하자면", "결론적으로", "첫째/둘째/셋째"와 같은 대표적인 AI 지향적 접속어 및 로봇 같은 표현을 최소화하고 흐름에 맞게 부드러운 연결어(예: "정리해 보자면", "우선 먼저", "다음으로", "이어서")로 대체하세요.
   - 도입부에서 뻔한 로봇 인사("안녕하세요! 오늘은 ~에 대해...")를 제거하고, 흥미를 끄는 이야기나 독자 맞춤형 문제 제기 방식으로 시작되도록 가다듬으세요.
   - 정보 나열식 불릿 포인트가 과도하게 많다면, 이를 풍부한 세부 정보가 담긴 줄글로 풀어서 작성하여 기계적인 요약 문서 느낌을 완전히 제거하세요.
2. **100% 한국어 원칙**:
   - 문장 중간에 섞여 있는 영어 단어(예: "Review", "Key point", "NPU", "LLM" 등 고유명사나 널리 쓰는 영어 단어를 제외한 것)를 자연스러운 한글 표현으로 교정하세요.
   - 단, 모델명이나 브랜드명 등 고유명사(예: ChatGPT, Claude, NVIDIA)는 유지해도 되지만, 일반 명사는 한글로 변경하십시오.
3. **E-E-A-T 및 신뢰성 극대화**:
   - 필자가 직접 테스트하고 연구해본 듯한 생생한 1인칭 어투("제가 직접 확인해본 결과", "실제로 테스트해보니")로 다듬으세요.
   - 내용이 단순 정보의 복제가 아닌, 해당 AI 기술에 대한 분석과 통찰이 느껴지도록 깊이감을 부여하세요.
4. **마크다운 및 가독성 유지**:
   - 소제목(H2, H3)과 적절한 여백, 문장 흐름을 유지하며 글의 가치를 높이세요.
   - 반드시 교정이 완료된 최종 마크다운 본문만 출력하고, 교정 이유나 인사말 등 불필요한 메타 텍스트는 일절 포함하지 마십시오.
"""

    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type": "application/json",
        "accept": "application/json"
    }
    payload = {
        "model": "meta/llama-3.1-70b-instruct",
        "messages": [
            {"role": "user", "content": audit_prompt}
        ],
        "temperature": 0.5, # Lower temperature for precision
        "max_tokens": 6000
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=180)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Audit failed: {e}. Returning original content.")
        return content

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
                page.locator('.btn_login').click()
                
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
    trends_keywords = get_google_trends_keywords()
    keyword = select_ai_keyword(trends_keywords)

    # 2. Generate Content
    try:
        content = generate_blog_post(keyword)
        
        # 2-1. E-E-A-T and Korean-only Validation
        print(f"Applying E-E-A-T & Korean-only validation logic...")
        content = validate_and_fix_post(keyword, content)
            
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
