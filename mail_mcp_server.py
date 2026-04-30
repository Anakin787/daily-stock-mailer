"""
Mail MCP Server (SendGrid + PDF)
---------------------------------
send_email 도구로 SendGrid HTTP API를 통해 메일 발송.
attach_pdf=True 시 HTML 본문을 파싱해 PDF 첨부파일 자동 생성.

Required env vars (.env):
    SENDGRID_API_KEY   SendGrid API Key (starts with SG.)
    FROM_ADDRESS       Verified sender email address
    FROM_NAME          (optional) Display name in recipients' inbox
"""

from __future__ import annotations

import base64
import os
import re
import sys
import threading
import urllib.request
from typing import Literal, Optional

import requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "").strip()
FROM_ADDRESS     = os.environ.get("FROM_ADDRESS", "").strip()
FROM_NAME        = os.environ.get("FROM_NAME", "US Market Brief").strip()
MCP_HOST         = os.environ.get("MCP_HOST", "0.0.0.0")
MCP_PORT         = int(os.environ.get("MCP_PORT", "3002"))
SENDGRID_URL     = "https://api.sendgrid.com/v3/mail/send"

# ---------------------------------------------------------------------------
# Font paths (resolved once at startup)
# ---------------------------------------------------------------------------

_FONT_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
_FONT_REG  = os.path.join(_FONT_DIR, "NanumGothic-Regular.ttf")
_FONT_BOLD = os.path.join(_FONT_DIR, "NanumGothic-Bold.ttf")
_fonts_ready = False


def _ensure_fonts() -> bool:
    """Download NanumGothic TTF fonts if not present. Returns True on success."""
    global _fonts_ready
    if _fonts_ready:
        return True
    os.makedirs(_FONT_DIR, exist_ok=True)
    urls = {
        _FONT_REG:  "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf",
        _FONT_BOLD: "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Bold.ttf",
    }
    for path, url in urls.items():
        if not os.path.exists(path):
            print(f"[mail-mcp] Downloading font: {os.path.basename(path)}", file=sys.stderr)
            try:
                urllib.request.urlretrieve(url, path)
            except Exception as e:
                print(f"[mail-mcp] Font download failed: {e}", file=sys.stderr)
                return False
    _fonts_ready = True
    return True


def _warmup_fonts():
    """Pre-load fonts in background at startup so first PDF is fast."""
    try:
        if _ensure_fonts():
            from fpdf import FPDF
            pdf = FPDF()
            pdf.add_page()
            pdf.add_font("Nanum", "",  _FONT_REG)
            pdf.add_font("Nanum", "B", _FONT_BOLD)
            pdf.set_font("Nanum", "", 10)
            pdf.cell(0, 5, "warmup")
            pdf.output()
            print("[mail-mcp] Font warmup complete.", file=sys.stderr, flush=True)
    except Exception as e:
        print(f"[mail-mcp] Font warmup error (non-fatal): {e}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _split_recipients(value: Optional[str | list[str]]) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        items = [p.strip() for p in value.replace(";", ",").split(",")]
    else:
        items = [str(p).strip() for p in value]
    return [a for a in items if a]


def _check_config() -> None:
    missing = [n for n, v in [("SENDGRID_API_KEY", SENDGRID_API_KEY), ("FROM_ADDRESS", FROM_ADDRESS)] if not v]
    if missing:
        raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")


def _strip_emoji(text: str) -> str:
    return re.sub(r'[^\x20-\x7E가-힣㄰-㆏]+', '', text).strip()


def _col_widths(n: int) -> list[float]:
    total = 183.0
    if n == 5: return [50, 30, 30, 30, 43]
    if n == 4: return [50, 35, 32, 66]
    if n == 3: return [62, 30, 91]
    if n == 2: return [65, 118]
    return [total / n] * n


def _html_to_pdf(html_body: str, subject: str) -> bytes:
    from fpdf import FPDF
    from bs4 import BeautifulSoup

    if not _ensure_fonts():
        raise RuntimeError("Font files unavailable")

    soup = BeautifulSoup(html_body, "html.parser")

    NAVY    = (30,  58,  95)
    DARK    = (34,  34,  34)
    GRAY    = (130, 130, 130)
    GREEN   = (22,  163,  74)
    RED     = (220,  38,  38)
    BG      = (240, 244, 248)
    ROW_ALT = (248, 250, 252)
    WHITE   = (255, 255, 255)

    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_margins(13, 13, 13)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.add_font("Nanum", "",  _FONT_REG)
    pdf.add_font("Nanum", "B", _FONT_BOLD)

    # ── 제목 헤더 (단색 배경 셀로 구현 - rect 없이) ──
    pdf.set_fill_color(*NAVY)
    pdf.set_text_color(*WHITE)
    pdf.set_font("Nanum", "B", 14)
    title = _strip_emoji(subject.replace("[시황] ", ""))
    pdf.cell(0, 12, "  " + title, ln=True, fill=True)
    pdf.set_font("Nanum", "", 8)
    pdf.set_fill_color(*NAVY)
    pdf.cell(0, 6, "  US Market Daily Brief", ln=True, fill=True)
    pdf.ln(5)

    # ── 날짜 ──
    date_text = ""
    for el in soup.find_all(["div", "p", "small"]):
        t = el.get_text(strip=True)
        if ("거래일" in t or "마감" in t) and len(t) < 80:
            date_text = t
            break
    if date_text:
        pdf.set_font("Nanum", "", 9)
        pdf.set_text_color(*GRAY)
        pdf.cell(0, 5, _strip_emoji(date_text), ln=True)
        pdf.ln(3)

    ROW_H = 7

    # ── 섹션별 테이블 ──
    for h2 in soup.find_all("h2"):
        sec_raw = _strip_emoji(h2.get_text(strip=True))

        # 섹션 헤더: 네이비 왼쪽 셀 + BG 오른쪽 셀
        pdf.set_font("Nanum", "B", 11)
        pdf.set_fill_color(*NAVY)
        pdf.set_text_color(*WHITE)
        pdf.cell(3, 8, "", fill=True)
        pdf.set_fill_color(*BG)
        pdf.set_text_color(*NAVY)
        pdf.cell(180, 8, "  " + sec_raw, ln=True, fill=True)
        pdf.ln(1)

        tbl = h2.find_next_sibling("table")
        if not tbl:
            pdf.ln(2)
            continue

        headers = [th.get_text(strip=True) for th in tbl.find_all("th")]
        rows_raw = []
        for tr in tbl.find_all("tr"):
            tds = tr.find_all("td")
            if tds:
                row = []
                for td in tds:
                    s = td.get("style", "")
                    color = GREEN if "#16a34a" in s else (RED if "#dc2626" in s else None)
                    bold  = "font-weight" in s
                    row.append((td.get_text(strip=True), color, bold))
                rows_raw.append(row)

        if not headers:
            pdf.ln(3)
            continue

        widths = _col_widths(len(headers))

        # 헤더 행
        pdf.set_font("Nanum", "B", 8.5)
        pdf.set_fill_color(*NAVY)
        pdf.set_text_color(*WHITE)
        pdf.set_draw_color(200, 210, 225)
        pdf.set_line_width(0.2)
        for i, h in enumerate(headers):
            pdf.cell(widths[i], ROW_H, h, border=1, fill=True, align='C')
        pdf.ln()

        # 데이터 행 (마지막 컬럼 줄 수에 따라 전체 행 높이 통일)
        for r_idx, row in enumerate(rows_raw):
            fill = ROW_ALT if r_idx % 2 == 0 else WHITE
            y_row = pdf.get_y()

            # 마지막 컬럼 줄 수 계산 (4컬럼 이상 테이블만)
            num_lines = 1
            lw = widths[len(row)-1] if len(row)-1 < len(widths) else widths[-1]
            if len(row) >= 4:
                pdf.set_font("Nanum", "", 8.5)
                sw = pdf.get_string_width(row[-1][0])
                usable = max(1.0, lw - 4)
                num_lines = max(1, int(sw / usable) + (1 if sw % usable > 0 else 0))

            actual_h = ROW_H * num_lines  # 모든 셀이 이 높이를 공유

            # 마지막 컬럼 제외한 나머지 셀 렌더링
            needs_wrap = num_lines > 1
            cols_to_render = row[:-1] if needs_wrap else row
            for i, (txt, col, is_bold) in enumerate(cols_to_render):
                pdf.set_fill_color(*fill)
                pdf.set_text_color(*(col if col else DARK))
                pdf.set_font("Nanum", "B" if (is_bold or col) else "", 8.5)
                w = widths[i] if i < len(widths) else widths[-1]
                is_last = (i == len(row) - 1)
                align = 'L' if is_last and len(row) >= 4 else 'C'
                pdf.cell(w, actual_h, txt, border=1, fill=True, align=align)

            # 마지막 컬럼: 줄바꿈 필요 시 multi_cell, 아니면 일반 cell
            if needs_wrap:
                last_txt, col, is_bold = row[-1]
                pdf.set_fill_color(*fill)
                pdf.set_text_color(*(col if col else DARK))
                pdf.set_font("Nanum", "B" if (is_bold or col) else "", 8.5)
                pdf.multi_cell(lw, ROW_H, last_txt, border=1, fill=True, align='L')
                # multi_cell 후 커서를 다음 행 시작 위치로 강제 이동
                pdf.set_xy(13, y_row + actual_h)
            else:
                pdf.ln()

        pdf.set_text_color(*DARK)
        pdf.ln(4)

    # ── 헤드라인 ──
    headline_p = soup.find("p", style=lambda s: s and "font-size" in s if s else False)
    if headline_p:
        pdf.set_font("Nanum", "B", 11)
        pdf.set_fill_color(*NAVY)
        pdf.set_text_color(*WHITE)
        pdf.cell(3, 8, "", fill=True)
        pdf.set_fill_color(*BG)
        pdf.set_text_color(*NAVY)
        pdf.cell(180, 8, "  주요 헤드라인", ln=True, fill=True)
        pdf.ln(1)
        pdf.set_font("Nanum", "", 9)
        pdf.set_text_color(*DARK)
        for line in headline_p.get_text(separator="\n", strip=True).split("\n"):
            line = _strip_emoji(line.strip())
            if line and "헤드라인" not in line and len(line) > 2:
                pdf.multi_cell(0, 6, line)
                pdf.ln(1)
        pdf.ln(2)

    # ── 코멘트 ──
    comment = soup.find("div", style=lambda s: (
        s and "border-left" in s and ("1e3a5f" in s or "f0f4f8" in s)
    ) if s else False)
    if comment:
        pdf.set_font("Nanum", "B", 11)
        pdf.set_fill_color(*NAVY)
        pdf.set_text_color(*WHITE)
        pdf.cell(3, 8, "", fill=True)
        pdf.set_fill_color(*BG)
        pdf.set_text_color(*NAVY)
        pdf.cell(180, 8, "  한 줄 코멘트", ln=True, fill=True)
        pdf.ln(1)
        text = _strip_emoji(comment.get_text(separator=" ", strip=True))
        text = text.replace("한 줄 코멘트", "").strip()
        pdf.set_fill_color(*BG)
        pdf.set_font("Nanum", "", 9)
        pdf.set_text_color(*DARK)
        pdf.multi_cell(0, 6.5, text, fill=True)
        pdf.ln(2)

    # ── 푸터 ──
    pdf.set_draw_color(*GRAY)
    pdf.set_line_width(0.3)
    pdf.line(13, pdf.get_y(), 197, pdf.get_y())
    pdf.ln(3)
    pdf.set_font("Nanum", "", 7.5)
    pdf.set_text_color(*GRAY)
    pdf.multi_cell(0, 5,
        "본 브리핑은 공개된 금융 미디어 데이터를 기반으로 자동 작성되었습니다. "
        "투자 판단의 근거로 단독 사용하지 마세요.")

    return bytes(pdf.output())


# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------

mcp = FastMCP("mail-mcp", host=MCP_HOST, port=MCP_PORT)


@mcp.tool()
def send_email(
    to: str | list[str],
    subject: str,
    body: str,
    body_type: Literal["Text", "HTML"] = "HTML",
    cc: Optional[str | list[str]] = None,
    bcc: Optional[str | list[str]] = None,
    attach_pdf: bool = False,
) -> str:
    """Send an email via SendGrid HTTP API.

    Args:
        to: Recipient address(es). List or comma-separated string.
        subject: Email subject.
        body: Email body (text or HTML).
        body_type: "Text" or "HTML" (default: "HTML").
        cc: Optional CC recipient(s).
        bcc: Optional BCC recipient(s).
        attach_pdf: If True, generate a PDF from the HTML body and attach it.

    Returns:
        Confirmation string.
    """
    _check_config()

    to_list  = _split_recipients(to)
    cc_list  = _split_recipients(cc)
    bcc_list = _split_recipients(bcc)

    if not to_list:
        raise ValueError("'to' must contain at least one address.")

    content_type = "text/html" if body_type.lower() == "html" else "text/plain"

    payload: dict = {
        "personalizations": [{
            "to": [{"email": a} for a in to_list],
            **({"cc":  [{"email": a} for a in cc_list]}  if cc_list  else {}),
            **({"bcc": [{"email": a} for a in bcc_list]} if bcc_list else {}),
        }],
        "from": {"email": FROM_ADDRESS, **({"name": FROM_NAME} if FROM_NAME else {})},
        "subject": subject,
        "content": [{"type": content_type, "value": body}],
    }

    # ── PDF 첨부 ──
    if attach_pdf and body_type.lower() == "html":
        try:
            pdf_bytes = _html_to_pdf(body, subject)
            fname = subject.replace("[시황] 미국증시 ", "").replace(" 마감 요약", "") + ".pdf"
            fname = fname.replace(" ", "_")
            payload["attachments"] = [{
                "content":     base64.b64encode(pdf_bytes).decode(),
                "type":        "application/pdf",
                "filename":    fname,
                "disposition": "attachment",
            }]
        except Exception as e:
            print(f"[mail-mcp] PDF 생성 실패 (메일은 발송): {e}", file=sys.stderr)

    headers = {
        "Authorization": f"Bearer {SENDGRID_API_KEY}",
        "Content-Type":  "application/json",
    }

    resp = requests.post(SENDGRID_URL, json=payload, headers=headers, timeout=30)

    if resp.status_code not in (200, 202):
        raise RuntimeError(f"SendGrid API error {resp.status_code}: {resp.text}")

    preview = ", ".join(to_list)
    pdf_note = " (PDF 첨부)" if attach_pdf else ""
    return f"Sent email to {preview} (subject: {subject!r}){pdf_note}."


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    transport = os.environ.get("MCP_TRANSPORT", "streamable-http")
    print(
        f"[mail-mcp] Starting on {transport} "
        f"(bind {MCP_HOST}:{MCP_PORT})\n"
        f"  SendGrid -> {FROM_ADDRESS or '(unset)'}",
        file=sys.stderr, flush=True,
    )
    # 폰트 사전 로드 (백그라운드) — 첫 PDF 요청 시 지연 방지
    threading.Thread(target=_warmup_fonts, daemon=True).start()
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
