# Naver Mail MCP (send_email via SMTP)

Naver SMTP를 통해 메일을 발송하는 MCP 서버. **Azure 등록도, 회사 IT 승인도 필요 없습니다.**

동료분 Teams MCP와 같은 방식으로 띄우고 `claude mcp add`로 등록.

---

## 1. Naver 메일 SMTP 활성화 (1회만)

1. Naver 메일 접속 → **환경설정** → **POP3/IMAP 설정** 탭
2. **IMAP/SMTP 사용** → **사용함** 선택 → 저장

> 그러면 SMTP 서버 정보가 화면에 뜹니다 (smtp.naver.com:465). 비밀번호는 본인 Naver 로그인 비밀번호.

**2단계 인증 켜놓으셨다면:**
- Naver 로그인 비밀번호로는 SMTP 인증 불가
- Naver → 보안설정 → **애플리케이션 비밀번호** 발급 → 그 값을 `SMTP_PASSWORD`에 넣기

---

## 2. 설치

```bash
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# .env 편집 - SMTP_USER, SMTP_PASSWORD만 채우면 됨
```

---

## 3. 메일 발송 테스트

```bash
set -a; source .env; set +a   # Windows PowerShell이면 환경변수 주입 방식 별도

python -c "
from naver_mail_mcp_server import send_email
print(send_email(
    to='yourid@naver.com',
    subject='Naver MCP test',
    body='Hello from MCP!',
    body_type='Text'
))
"
```

본인 Naver 메일함에 도착하면 성공.

**자주 만나는 에러:**
- `SMTP authentication failed` → Naver SMTP 사용함 체크 안 됨, 또는 2단계 인증 켜놓고 일반 비밀번호 쓰는 경우 (애플리케이션 비밀번호로 교체)
- `relay access denied` → `FROM_ADDRESS`가 `SMTP_USER`와 다르면 Naver가 거부. 둘을 같게 두세요.

---

## 4. HTTP MCP 서버 실행

```bash
python naver_mail_mcp_server.py
```

```
[naver-mail-mcp] Starting on streamable-http (bind 0.0.0.0:3002, endpoint /mcp)
  SMTP: smtp.naver.com:465 (SSL) as yourid@naver.com
```

이 터미널은 켜둔 채로 두기.

---

## 5. Claude에 등록

새 터미널에서 (동료분 Teams MCP와 동일한 방식):

```bash
claude mcp add -s user naver-mail --transport http http://localhost:3002/mcp
claude mcp list
```

목록에 `naver-mail`이 보이면 끝. Claude/Cowork에서 `send_email` 도구가 사용 가능해집니다.

---

## 6. 사용 예

```json
{
  "name": "send_email",
  "arguments": {
    "to": "yourid@naver.com",
    "subject": "[시황] 미국증시 2026-04-22 마감 요약",
    "body": "<h2>주요지수</h2><ul><li>S&P500 ...</li></ul>",
    "body_type": "HTML"
  }
}
```

---

## 7. 다음 단계 — 매일 09시 시황 자동 발송

이 MCP가 등록되면, Cowork의 scheduled task로 다음을 매일 09:00 (KST)에 실행:

> 어제 미국 증시 마감 결과를 정리해서 본인 Naver 메일로 send_email 도구를 써서 발송해줘.
> 포함 내용: 주요지수(다우/S&P500/나스닥), 섹터별 흐름, 주요 종목 이슈, 거시(금리/환율/유가).
> 제목: `[시황] 미국증시 YYYY-MM-DD 마감 요약`
> 본문: HTML

등록 끝나면 채팅에 "등록 완료" 한 마디만 알려주세요. 스케줄 태스크는 제가 만들어드릴게요.

---

## 8. 보안 메모

- `.env`에 SMTP 비밀번호가 들어가니 git에 커밋하지 말 것 (`.gitignore`에 `.env` 추가)
- MCP 서버는 기본적으로 `0.0.0.0:3002`에 노출됩니다. 외부 노출 안 하려면 `MCP_HOST=127.0.0.1`로 변경
- Naver 애플리케이션 비밀번호는 언제든 폐기 가능 (보안설정에서)

---

## 9. 다른 메일 서비스로 바꾸려면

`.env`만 수정. SMTP만 지원하면 다 됩니다:

| 서비스 | SMTP_HOST | SMTP_PORT | SMTP_USE_SSL |
|--------|-----------|-----------|--------------|
| Naver  | smtp.naver.com | 465 | true |
| Gmail  | smtp.gmail.com | 465 | true |
| Daum   | smtp.daum.net  | 465 | true |
| Outlook (개인) | smtp-mail.outlook.com | 587 | false (STARTTLS) |
