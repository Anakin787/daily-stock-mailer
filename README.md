# Daily US Stock Email Agent

Claude가 매일 아침 미국 증시 시황을 분석해서 네이버 메일로 자동 발송하는 MCP 서버입니다.

이 프로젝트는 Claude에게 `send_email` 도구를 제공하는 역할만 합니다.  
주식 데이터 수집·분석·메일 본문 작성은 Claude(AI)가 담당합니다.

```
Claude (AI)                    이 프로젝트 (MCP 서버)
────────────────               ────────────────────────
웹에서 주식 정보 수집    →    send_email 도구 제공
시황 분석 및 본문 작성   →    Naver SMTP로 실제 발송
send_email 도구 호출     →    수신자 메일함 도착
```

---

## 1. Naver 메일 SMTP 활성화 (최초 1회)

1. Naver 메일 접속 → **환경설정** → **POP3/IMAP 설정** 탭
2. **IMAP/SMTP 사용** → **사용함** 선택 → 저장

> SMTP 서버 정보: `smtp.naver.com:465`  
> 비밀번호: Naver 로그인 비밀번호

**2단계 인증을 사용 중이라면:**  
Naver → 보안설정 → **애플리케이션 비밀번호** 발급 후 `SMTP_PASSWORD`에 입력

---

## 2. 설치

```bash
git clone https://github.com/Anakin787/Stock-Email_Agent.git
cd Stock-Email_Agent

python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate # macOS/Linux

pip install -r requirements.txt
```

---

## 3. 환경 변수 설정

`.env` 파일을 직접 생성합니다 (git에 포함되지 않음):

```env
SMTP_USER=yourid@naver.com
SMTP_PASSWORD=your_password_or_app_password
SMTP_HOST=smtp.naver.com
SMTP_PORT=465
SMTP_USE_SSL=true
MCP_HOST=0.0.0.0
MCP_PORT=3002
```

---

## 4. MCP 서버 실행

```bash
python naver_mail_mcp_server.py
```

```
[naver-mail-mcp] Starting on streamable-http (bind 0.0.0.0:3002, endpoint /mcp)
  SMTP: smtp.naver.com:465 (SSL) as yourid@naver.com
```

이 터미널은 켜둔 채로 유지합니다.

---

## 5. Claude에 등록 (최초 1회)

```bash
claude mcp add -s user naver-mail --transport http http://localhost:3002/mcp
claude mcp list   # naver-mail 확인
```

---

## 6. 동작 확인

Claude에게 직접 요청:

```
어제 미국 증시 마감 결과를 정리해서 {yourid}@naver.com으로 send_email 도구를 써서 보내줘.
포함 내용: 주요지수(다우/S&P500/나스닥), 섹터별 흐름, 주요 종목 이슈, 금리/환율/유가.
제목: [시황] 미국증시 YYYY-MM-DD 마감 요약
본문: HTML
```

---

## 7. 매일 자동 발송 설정

Claude Code scheduled task로 매일 09:00(KST)에 자동 실행:

```
/schedule
```

스케줄 프롬프트 예시:
```
어제 미국 증시 마감 결과를 정리해서 {yourid}@naver.com으로 send_email 도구를 써서 발송해줘.
포함 내용: 주요지수(다우/S&P500/나스닥), 섹터별 흐름, 주요 종목 이슈, 거시(금리/환율/유가).
제목: [시황] 미국증시 YYYY-MM-DD 마감 요약
본문: HTML
```

---

## 8. 자주 만나는 에러

| 에러 | 원인 | 해결 |
|------|------|------|
| `SMTP authentication failed` | SMTP 미활성화 또는 2단계 인증 | SMTP 사용함 체크 / 애플리케이션 비밀번호 사용 |
| `relay access denied` | `FROM_ADDRESS`와 `SMTP_USER` 불일치 | 둘을 동일하게 설정 |
| `Connection refused` | MCP 서버 미실행 | `python naver_mail_mcp_server.py` 먼저 실행 |

---

## 9. 보안 메모

- `.env`는 `.gitignore`에 포함되어 git에 올라가지 않습니다.
- MCP 서버는 기본 `0.0.0.0:3002`에 노출됩니다. 로컬 전용이면 `MCP_HOST=127.0.0.1`로 변경하세요.
- Naver 애플리케이션 비밀번호는 보안설정에서 언제든지 폐기 가능합니다.

---

## 10. 다른 메일 서비스로 전환

`.env`만 수정하면 됩니다:

| 서비스 | SMTP_HOST | SMTP_PORT | SMTP_USE_SSL |
|--------|-----------|-----------|--------------|
| Naver  | smtp.naver.com | 465 | true |
| Gmail  | smtp.gmail.com | 465 | true |
| Daum   | smtp.daum.net  | 465 | true |
| Outlook (개인) | smtp-mail.outlook.com | 587 | false |
