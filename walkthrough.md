# Tistory Auto-Publishing (Cookie Injection)

GitHub Actions 서버에서 카카오 로그인 시 발생하는 캡차 및 해외 IP 차단을 완벽하게 회피하기 위해, **'쿠키 주입(Cookie Injection)'** 방식을 도입했습니다! 🎉

## 1. 어떻게 변경되었나요?
`autoblog.py` 코드가 업데이트되어, 이제 봇이 카카오 이메일과 비밀번호를 직접 타이핑하지 않습니다. 대신 회원님의 PC에서 이미 성공적으로 로그인된 **티스토리 세션 쿠키(TSSESSION 등)를 그대로 복사해서 봇에게 전달**합니다. 
봇은 이 쿠키를 브라우저에 덮어씌워서 곧바로 로그인된 상태로 글쓰기 페이지에 진입합니다!

이 방식은 캡차를 100% 우회할 수 있는 가장 확실하고 안전한 방법입니다.

## 2. 세팅 방법 (가장 중요 ⭐️)

이제 `KAKAO_EMAIL`이나 `KAKAO_PASSWORD` 대신, **쿠키값** 하나만 GitHub Secrets에 등록해주시면 됩니다.

### [1단계: 내 PC에서 티스토리 쿠키 추출하기]
1. 크롬 브라우저에서 **[EditThisCookie](https://chrome.google.com/webstore/detail/editthiscookie/fngmhnnpilhplaeedifhccceomclgfbg)** 같은 쿠키 관리 확장 프로그램을 설치합니다.
2. PC에서 본인 티스토리(gumdrop.tistory.com 또는 www.tistory.com)에 접속하여 로그인합니다.
3. 확장 프로그램(EditThisCookie) 아이콘을 클릭하고, 상단의 **'내보내기(Export)'** 버튼을 클릭합니다.
4. 클립보드에 `[{"domain": ".tistory.com", "name": "TSSESSION", ...}]` 형태의 긴 글자가 복사됩니다.

### [2단계: GitHub Secrets에 등록하기]
1. GitHub 저장소의 **Settings -> Secrets and variables -> Actions** 로 이동합니다.
2. **New repository secret**을 클릭합니다.
3. Name에 `TISTORY_COOKIES` 라고 적습니다.
4. Secret에 복사해둔 **쿠키 텍스트 전체를 그대로 붙여넣고** 저장(Add secret)합니다.

> [!NOTE]
> 만약 쿠키 설정을 원치 않고 기존 아이디/비밀번호 방식을 쓰고 싶다면, `TISTORY_COOKIES`를 등록하지 않고 기존처럼 `KAKAO_EMAIL`, `KAKAO_PASSWORD`만 유지하셔도 됩니다. (코드가 알아서 스위칭합니다.)

## 3. 확인 (Verification)
1. 변경된 코드들을 커밋 & 푸시합니다.
2. Actions 탭에서 다시 한번 **Run workflow**를 눌러 테스트해 보세요.
3. 봇이 로그인 페이지를 통과하고 티스토리에 성공적으로 글을 발행할 것입니다!
