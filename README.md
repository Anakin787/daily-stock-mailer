# Daily US Stock Email Agent

Claude가 매일 아침 미국 증시 시황을 분석해서 메일로 자동 발송하는 MCP 서버입니다.

**MCP(Model Context Protocol)** 란 Claude 같은 AI 모델에게 외부 도구(tool)를 연결해주는 표준 프로토콜입니다.  
쉽게 말해, AI가 직접 할 수 없는 작업(메일 발송, DB 조회 등)을 MCP 서버를 통해 대신 실행할 수 있게 해주는 중간 다리 역할입니다.

이 프로젝트는 Claude에게 `send_email` 도구를 제공하는 MCP 서버 역할만 합니다.  
주식 데이터 수집·분석·메일 본문 작성은 Claude(AI)가 담당합니다.

```
Claude (AI)                    이 프로젝트 (MCP 서버)
────────────────               ────────────────────────
웹에서 주식 정보 수집    →    send_email 도구 제공
시황 분석 및 본문 작성   →    SendGrid API로 실제 발송
send_email 도구 호출     →    수신자 메일함 도착
```

---

## 1. SendGrid 설정 (최초 1회)

1. [SendGrid](https://sendgrid.com) 가입 → **API Keys** 메뉴에서 API Key 생성 (`Mail Send` 권한)
2. **Sender Authentication** → 발송에 사용할 이메일 주소를 Verified Sender로 등록

---

## 2. 설치

```bash
git clone https://github.com/Anakin787/daily-stock-mailer.git
cd daily-stock-mailer

python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate # macOS/Linux

pip install -r requirements.txt
```

---

## 3. 환경 변수 설정

`.env` 파일을 직접 생성합니다 (git에 포함되지 않음):

```env
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxxxxx
FROM_ADDRESS=your_verified_sender@example.com
FROM_NAME=US Market Brief
MCP_HOST=0.0.0.0
MCP_PORT=3002
```

---

## 4. MCP 서버 실행

```bash
python mail_mcp_server.py
```

```
[mail-mcp] Starting on streamable-http (bind 0.0.0.0:3002, endpoint /mcp)
  SendGrid API → your_verified_sender@example.com
```

이 터미널은 켜둔 채로 유지합니다.

---

## 5. Claude에 등록 (최초 1회)

```bash
claude mcp add -s user mail --transport http http://localhost:3002/mcp
claude mcp list   # mail 확인
```

---

## 6. 동작 확인

Claude에게 직접 요청:

```
어제 미국 증시 마감 결과를 정리해서 {recipient}@example.com으로 send_email 도구를 써서 보내줘.
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
어제 미국 증시 마감 결과를 정리해서 {recipient}@example.com으로 send_email 도구를 써서 발송해줘.
포함 내용: 주요지수(다우/S&P500/나스닥), 섹터별 흐름, 주요 종목 이슈, 거시(금리/환율/유가).
제목: [시황] 미국증시 YYYY-MM-DD 마감 요약
본문: HTML
```

---

## 8. 자주 만나는 에러

| 에러 | 원인 | 해결 |
|------|------|------|
| `401 Unauthorized` | API Key 오류 | `.env`의 `SENDGRID_API_KEY` 확인 |
| `403 Forbidden` | Sender 미인증 | SendGrid에서 `FROM_ADDRESS` Verified Sender 등록 |
| `Connection refused` | MCP 서버 미실행 | `python mail_mcp_server.py` 먼저 실행 |

---

## 9. 보안 메모

- `.env`는 `.gitignore`에 포함되어 git에 올라가지 않습니다.
- MCP 서버는 기본 `0.0.0.0:3002`에 노출됩니다. 로컬 전용이면 `MCP_HOST=127.0.0.1`로 변경하세요.
- SendGrid API Key는 언제든지 SendGrid 대시보드에서 폐기 가능합니다.
