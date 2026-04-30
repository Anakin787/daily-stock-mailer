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
import sys
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


def _ensure_fonts() -> tuple[str, str]:
    """Download NanumGothic TTF fonts if not present. Returns (regular, bold) paths."""
    font_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
    os.makedirs(font_dir, exist_ok=True)
    fonts = {
        "NanumGothic-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf",
        "NanumGothic-Bold.ttf":    "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Bold.ttf",
    }
    for fname, url in fonts.items():
        path = os.path.join(font_dir, fname)
        if not os.path.exists(path):
            print(f"[mail-mcp] Downloading font: {fname}", file=sys.stderr)
            urllib.request.urlretrieve(url, path)
    return (
        os.path.join(font_dir, "NanumGothic-Regular.ttf"),
        os.path.join(font_dir, "NanumGothic-Bold.ttf"),
    )


def _col_widths(n: int) -> list[float]:
    total = 190.0
    if n == 2: return [60, 130]
    if n == 3: return [55, 30, 105]
    if n == 4: return [55, 35, 30, 70]
    w = total / n
    return [w] * n


def _html_to_pdf(html_body: str, subject: str) -> bytes:
    from fpdf import FPDF
    from bs4 import BeautifulSoup

    regular, bold = _ensure_fonts()

    soup = BeautifulSoup(html_body, "html.parser")

    NAVY  = (30, 58, 95)
    DARK  = (34, 34, 34)
    GRAY  = (136, 136, 136)
    GREEN = (22, 163, 74)
    RED   = (220, 38, 38)
    BG    = (240, 244, 248)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.add_font("Nanum",  "",  regular)
    pdf.add_font("Nanum",  "B", bold)

    # ── 제목 ──
    title = subject.replace("[시황] ", "")
    pdf.set_font("Nanum", "B", 16)
    pdf.set_text_color(*NAVY)
    pdf.multi_cell(0, 10, title)
    pdf.set_draw_color(*NAVY)
    pdf.set_line_width(0.5)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)

    # ── 날짜 부제 ──
    date_tag = soup.find("p", style=lambda s: s and "color:#888" in s if s else False)
    if date_tag:
        pdf.set_font("Nanum", "", 9)
        pdf.set_text_color(*GRAY)
        pdf.cell(0, 6, date_tag.get_text(strip=True), ln=True)
        pdf.ln(3)

    # ── 섹션별 테이블 ──
    for h2 in soup.find_all("h2"):
        sec = h2.get_text(strip=True)
        pdf.set_font("Nanum", "B", 12)
        pdf.set_text_color(*NAVY)
        pdf.set_fill_color(*BG)
        pdf.cell(0, 8, sec, ln=True, fill=True)
        pdf.ln(1)

        tbl = h2.find_next_sibling("table")
        if not tbl:
            pdf.ln(3)
            continue

        headers = [th.get_text(strip=True) for th in tbl.find_all("th")]
        rows_raw = []
        for tr in tbl.find_all("tr"):
            tds = tr.find_all("td")
            if tds:
                row = []
                for td in tds:
                    style = td.get("style", "")
                    color = GREEN if "#16a34a" in style else (RED if "#dc2626" in style else None)
                    row.append((td.get_text(strip=True), color))
                rows_raw.append(row)

        if headers:
            widths = _col_widths(len(headers))
            pdf.set_font("Nanum", "B", 9)
            pdf.set_fill_color(*BG)
            pdf.set_text_color(68, 68, 68)
            for i, h in enumerate(headers):
                pdf.cell(widths[i], 7, h, border=1, fill=True)
            pdf.ln()

            for row in rows_raw:
                pdf.set_font("Nanum", "", 9)
                for i, (txt, col) in enumerate(row):
                    pdf.set_text_color(*(col if col else DARK))
                    w = widths[i] if i < len(widths) else widths[-1]
                    pdf.cell(w, 7, txt, border=1)
                pdf.ln()
            pdf.set_text_color(*DARK)

        pdf.ln(4)

    # ── 주요 헤드라인 ──
    headline_p = soup.find("p", style=lambda s: s and "font-size:14px" in s if s else False)
    if headline_p:
        pdf.set_font("Nanum", "B", 11)
        pdf.set_text_color(*NAVY)
        pdf.cell(0, 7, "주요 헤드라인", ln=True)
        pdf.set_font("Nanum", "", 9)
        pdf.set_text_color(*DARK)
        for line in headline_p.get_text(separator="\n", strip=True).split("\n"):
            line = line.strip()
            if line and "헤드라인" not in line:
                pdf.multi_cell(0, 6, line)
        pdf.ln(3)

    # ── 한 줄 코멘트 ──
    comment = soup.find("div", style=lambda s: s and "border-left:4px solid #1e3a5f" in s if s else False)
    if comment:
        text = comment.get_text(separator=" ", strip=True)
        text = text.replace("💬", "").replace("한 줄 코멘트", "").strip()
        pdf.set_font("Nanum", "B", 10)
        pdf.set_text_color(*NAVY)
        pdf.set_fill_color(*BG)
        pdf.cell(0, 7, "💬 한 줄 코멘트", ln=True, fill=True)
        pdf.set_font("Nanum", "", 9)
        pdf.set_text_color(*DARK)
        pdf.multi_cell(0, 6, text, fill=True)

    # ── 푸터 ──
    pdf.ln(6)
    pdf.set_font("Nanum", "", 8)
    pdf.set_text_color(*GRAY)
    pdf.multi_cell(0, 5, "본 브리핑은 공개된 금융 미디어 데이터를 기반으로 자동 작성되었습니다. 투자 판단의 근거로 단독 사용하지 마세요.")

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

    resp = requests.post(SENDGRID_URL, json=payload, headers=headers, timeout=15)

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
        f"  SendGrid → {FROM_ADDRESS or '(unset)'}",
        file=sys.stderr, flush=True,
    )
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
