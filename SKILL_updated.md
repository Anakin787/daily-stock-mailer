---
name: us-market-daily-brief
description: 한국시간 화~토 오전 9시 30분 미국증시 마감 시황을 정리해 6명에게 일괄 발송
---

당신은 한국시간 기준 **화요일~토요일 오전 9시 30분(KST)** 에 실행되는 "미국 증시 일일 시황 브리핑" 태스크입니다. 미국 시장이 한국시간 새벽(밤 11시 30분~새벽 6시, ET 기준 정규장 09:30~16:00)에 열리므로, 다음과 같이 매핑됩니다.

- KST 화요일 오전 → US 월요일 정규장 마감
- KST 수요일 오전 → US 화요일 정규장 마감
- KST 목요일 오전 → US 수요일 정규장 마감
- KST 금요일 오전 → US 목요일 정규장 마감
- KST 토요일 오전 → US 금요일 정규장 마감

KST 일·월요일은 미국 시장이 휴장(주말) 후이므로 발송하지 않습니다 (스케줄 자체가 화~토만 실행됨).

가장 최근의 미국 정규장 마감 결과를 정리해서 한국어 HTML 메일로 작성한 뒤, 등록된 MCP 도구 `send_email` 을 사용하여 아래 6명의 수신자에게 발송하는 것이 목표입니다.

## 수신자 (6명)

다음 6개의 주소로 발송합니다.

1. nth2343@naver.com
2. silvialin@naver.com
3. dlehdgur725@naver.com
4. klingon6608@naver.com
5. seonbi1998@naver.com
6. lie9730@naver.com

`send_email` 도구의 `to` 필드는 위 6개 주소를 콤마(`,`)로 구분한 단일 문자열로 전달하세요. 도구가 배열 형태를 요구하면 배열로 전달해도 됩니다. 한 번의 호출로 6명 모두에게 전송되도록 하고, 6번 반복 호출하지 마세요.

## 1. 대상 거래일 결정

- 기본: KST 실행 요일의 직전 미국 정규장(전일 미국 날짜).
- 미국 공휴일로 휴장한 경우, 가장 최근에 정규장이 열렸던 날을 대상으로 합니다. 휴장 사실은 메일 본문에 명시하세요.

이 단계에서 "대상 거래일(YYYY-MM-DD, US 날짜)" 을 확정해 두세요. 메일 제목과 본문 모두 이 미국 날짜를 사용합니다.

## 2. 데이터 수집 (WebSearch)

다음 데이터를 신뢰 가능한 출처(Reuters, Bloomberg, CNBC, Yahoo Finance, MarketWatch 등) 에서 조사합니다.

필수 항목:
- **주요지수**: 다우존스, S&P 500, 나스닥종합 — 종가, 등락폭, 등락률 (%)
- **섹터 흐름**: S&P 500 11개 GICS 섹터 중 상승 상위 2~3, 하락 상위 2~3 (등락률 %)
- **주요 종목 이슈**: 실적 발표, 가이던스, M&A, 규제, 큰 변동 종목 등 3~5개. 각 항목에 종목명, 등락률, 짧은 이유(1줄).
- **거시 / 뉴스**:
  - 미국 10년물 국채 금리
  - DXY (달러 인덱스)
  - WTI 원유 가격
  - 금 가격(있으면)
  - 주요 헤드라인 1~3개 (FOMC, CPI, 고용지표, 지정학 등)

검색이 잘 안 되거나 데이터가 모순될 때는 "확인 불가" 라고 솔직히 적고, 추정값을 만들어내지 마세요.

## 3. HTML 메일 본문 작성 — **모든 스타일은 인라인(`style="..."`)으로**

**중요**: Naver, Gmail 등 다수 메일 클라이언트는 `<style>` 블록과 `<head>` 내 CSS, 클래스 선택자를 제거하거나 무시합니다. 따라서 본문은 다음 규칙을 반드시 지키세요.

- `<style>` 태그를 절대 사용하지 않습니다. `<head>`, `<link>`, `<script>` 도 사용하지 않습니다.
- CSS 클래스(`class="..."`)나 ID 선택자를 사용하지 않습니다. 모든 시각 스타일은 해당 태그의 `style="..."` 속성에 직접 작성합니다.
- 외부 폰트(webfont) 임베드, 외부 이미지 호스팅 의존 금지. 폰트는 시스템 기본 스택 사용 (예: `font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;`).
- 레이아웃은 `<table>` 기반으로 구성하고, 너비 제어가 필요하면 각 `<table>`/`<td>`에 인라인 `style`로 `width`, `padding`, `border` 등을 지정합니다. CSS Flex/Grid 의존 금지.
- 색상·여백·테두리 등 모든 시각 속성은 인라인. 예시:
  - 표 테두리: `<table style="border-collapse: collapse; width: 100%; font-family: -apple-system, sans-serif;">` 와 각 `<th>/<td>` 에 `style="border: 1px solid #ddd; padding: 8px 10px; text-align: left;"`.
  - 상승 셀: `<td style="border: 1px solid #ddd; padding: 8px 10px; color: #16a34a; font-weight: 600;">+1.23%</td>`
  - 하락 셀: `<td style="border: 1px solid #ddd; padding: 8px 10px; color: #dc2626; font-weight: 600;">-0.87%</td>`
  - 섹션 제목: `<h2 style="font-size: 16px; font-weight: 700; margin: 20px 0 8px; color: #1e3a5f; border-left: 4px solid #1e3a5f; padding-left: 8px;">주요지수</h2>`
  - 컨테이너: `<div style="max-width: 640px; margin: 0 auto; padding: 16px; color: #222; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 14px; line-height: 1.55;">`
  - 한 줄 코멘트 박스: `<div style="background: #f0f4f8; border-left: 4px solid #1e3a5f; padding: 12px 14px; font-size: 14px; margin-top: 20px;">`
  - 출처: `<small style="display: block; margin-top: 16px; color: #6b7280; font-size: 12px;">출처: ...</small>`
- 모바일 가독성을 위해 컨테이너 `max-width: 640px`, 본문 `font-size: 14px` 내외 권장.
- 한국어로 작성. 섹션 순서는 다음과 같습니다.
  1. `주요지수`
  2. `섹터별 흐름`
  3. `주요 종목 이슈`
  4. `거시 / 뉴스`
  5. `한 줄 코멘트` (전체 분위기 1~2줄 요약)
- 색상 규칙: 상승 = **초록색 #16a34a**, 하락 = **빨간색 #dc2626** (한국 관행과 다르지만 미국 시장 일관성을 위해).
- 출처 링크는 본문 마지막 `<small style="...">` 영역에 1~2개 정리.

작성한 HTML은 `<!DOCTYPE html>` 같은 문서 선언 없이 본문 단편으로 시작해도 됩니다(메일 클라이언트가 감쌉니다). 단 모든 스타일이 인라인인지 발송 직전 한 번 더 확인하세요.

## 4. 메일 제목

```
[시황] 미국증시 YYYY-MM-DD 마감 요약
```

YYYY-MM-DD 는 1단계에서 확정한 미국 거래일 날짜. 한국 날짜 아닙니다.

## 5. 발송

`send_email` MCP 도구를 다음 인자로 **한 번만** 호출:

```json
{
  "to": "nth2343@naver.com, silvialin@naver.com, dlehdgur725@naver.com, klingon6608@naver.com, seonbi1998@naver.com, lie9730@naver.com",
  "subject": "[시황] 미국증시 YYYY-MM-DD 마감 요약",
  "body": "<작성한 인라인 스타일 HTML 본문>",
  "body_type": "HTML",
  "attach_pdf": true
}
```

도구 호출이 성공(202 또는 "Sent email to...") 하면 작업 완료. 실패 시:
- 도구가 등록 목록에 없으면 → naver-mail MCP 서버가 꺼져 있을 가능성. 로그에 분명히 표시하고 종료.
- PDF 생성 실패 → 메일은 그대로 발송되며, 서버 stderr 로그에 오류가 기록됨. 이는 정상 동작임.
- 일부 수신자만 실패하고 나머지는 성공한 경우 → 어떤 주소가 실패했는지 로그에 명시.

## 6. 휴장일 처리

미국 공휴일 등으로 직전 거래일이 휴장이었던 경우에도, 6명에게 "오늘은 미국 휴장이라 별도 시황 없음" 짧은 안내 메일을 같은 형식의 제목(가장 최근 마감일 기준 날짜)에 `(휴장 안내)` 를 덧붙여 발송하세요. 화~토 패턴이 끊기지 않도록 하기 위함입니다. 휴장 안내 메일도 위와 동일하게 모든 스타일을 인라인으로 작성합니다. 휴장 안내 메일에는 `"attach_pdf": false` 로 설정하세요.
