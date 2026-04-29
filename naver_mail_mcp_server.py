"""
Naver Mail MCP Server
---------------------
A Model Context Protocol server exposing a single tool, `send_email`, that
sends mail via SMTP (defaults to Naver smtp.naver.com).

No Azure / OAuth / admin consent needed. Just an SMTP-enabled mail account.

Required env vars (see .env.example):
    SMTP_HOST       SMTP server hostname    (default: smtp.naver.com)
    SMTP_PORT       SMTP server port        (default: 465  - SSL)
    SMTP_USER       Login username          (e.g. yourid@naver.com)
    SMTP_PASSWORD   Login password / app password
    FROM_ADDRESS    From: header address    (default: same as SMTP_USER)
    FROM_NAME       (optional) Display name shown in recipients' inbox
    SMTP_USE_SSL    "true" for SMTPS (port 465), "false" for STARTTLS (port 587)
                    Default: "true"
"""

from __future__ import annotations

import os
import smtplib
import ssl
import sys
from email.message import EmailMessage
from email.utils import formataddr
from typing import Literal, Optional

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

load_dotenv()
if not os.environ.get("SMTP_USER") or not os.environ.get("SMTP_PASSWORD"):
    load_dotenv(".env.example")

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.naver.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
SMTP_USER = os.environ.get("SMTP_USER", "").strip()
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
FROM_ADDRESS = os.environ.get("FROM_ADDRESS", "").strip() or SMTP_USER
FROM_NAME = os.environ.get("FROM_NAME", "").strip()
SMTP_USE_SSL = os.environ.get("SMTP_USE_SSL", "true").lower() in ("1", "true", "yes")

MCP_HOST = os.environ.get("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.environ.get("MCP_PORT", "3002"))


def _split_recipients(value: Optional[str | list[str]]) -> list[str]:
    """Accept either a list or comma/semicolon-delimited string."""
    if not value:
        return []
    if isinstance(value, str):
        items = [p.strip() for p in value.replace(";", ",").split(",")]
    else:
        items = [str(p).strip() for p in value]
    return [a for a in items if a]


def _check_config() -> None:
    missing = [
        name
        for name, val in (
            ("SMTP_USER", SMTP_USER),
            ("SMTP_PASSWORD", SMTP_PASSWORD),
        )
        if not val
    ]
    if missing:
        raise RuntimeError(
            f"Missing required env vars: {', '.join(missing)}. "
            "Copy .env.example to .env and fill in your Naver credentials."
        )


# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------

mcp = FastMCP("naver-mail-mcp", host=MCP_HOST, port=MCP_PORT)


@mcp.tool()
def send_email(
    to: str | list[str],
    subject: str,
    body: str,
    body_type: Literal["Text", "HTML"] = "HTML",
    cc: Optional[str | list[str]] = None,
    bcc: Optional[str | list[str]] = None,
) -> str:
    """Send an email via SMTP (Naver by default).

    Args:
        to: Recipient address(es). List or comma-separated string.
        subject: Email subject.
        body: Email body (text or HTML).
        body_type: "Text" or "HTML" (default: "HTML").
        cc: Optional CC recipient(s).
        bcc: Optional BCC recipient(s).

    Returns:
        Confirmation string.
    """
    _check_config()

    to_list = _split_recipients(to)
    cc_list = _split_recipients(cc)
    bcc_list = _split_recipients(bcc)
    if not to_list:
        raise ValueError("'to' must contain at least one address.")

    msg = EmailMessage()
    if FROM_NAME:
        msg["From"] = formataddr((FROM_NAME, FROM_ADDRESS))
    else:
        msg["From"] = FROM_ADDRESS
    msg["To"] = ", ".join(to_list)
    if cc_list:
        msg["Cc"] = ", ".join(cc_list)
    msg["Subject"] = subject

    subtype = "html" if body_type.lower() == "html" else "plain"
    msg.set_content(body, subtype=subtype, charset="utf-8")

    all_recipients = to_list + cc_list + bcc_list

    context = ssl.create_default_context()

    try:
        if SMTP_USE_SSL:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context, timeout=30) as s:
                s.login(SMTP_USER, SMTP_PASSWORD)
                s.send_message(msg, from_addr=FROM_ADDRESS, to_addrs=all_recipients)
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as s:
                s.ehlo()
                s.starttls(context=context)
                s.ehlo()
                s.login(SMTP_USER, SMTP_PASSWORD)
                s.send_message(msg, from_addr=FROM_ADDRESS, to_addrs=all_recipients)
    except smtplib.SMTPAuthenticationError as e:
        raise RuntimeError(
            "SMTP authentication failed. For Naver: enable IMAP/SMTP in "
            "메일 환경설정 > POP3/IMAP 설정 > IMAP/SMTP 사용 '사용함'. "
            f"Server response: {e.smtp_code} {e.smtp_error}"
        ) from e

    preview = ", ".join(to_list)
    return f"Sent email to {preview} (subject: {subject!r})."


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    transport = os.environ.get("MCP_TRANSPORT", "streamable-http")
    print(
        f"[naver-mail-mcp] Starting on {transport} "
        f"(bind {MCP_HOST}:{MCP_PORT}, endpoint /mcp)\n"
        f"  SMTP: {SMTP_HOST}:{SMTP_PORT} "
        f"({'SSL' if SMTP_USE_SSL else 'STARTTLS'}) as {SMTP_USER or '(unset)'}",
        file=sys.stderr,
        flush=True,
    )
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
