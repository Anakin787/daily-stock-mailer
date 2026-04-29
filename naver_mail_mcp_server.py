"""
Mail MCP Server (SendGrid)
--------------------------
A Model Context Protocol server exposing a single tool, `send_email`,
that sends mail via SendGrid HTTP API (HTTPS port 443 — firewall friendly).

Required env vars (.env):
    SENDGRID_API_KEY   SendGrid API Key (starts with SG.)
    FROM_ADDRESS       Verified sender email address
    FROM_NAME          (optional) Display name in recipients' inbox
"""

from __future__ import annotations

import os
import sys
from typing import Literal, Optional

import requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

load_dotenv()

SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "").strip()
FROM_ADDRESS     = os.environ.get("FROM_ADDRESS", "").strip()
FROM_NAME        = os.environ.get("FROM_NAME", "US Market Brief").strip()

MCP_HOST = os.environ.get("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.environ.get("MCP_PORT", "3002"))

SENDGRID_URL = "https://api.sendgrid.com/v3/mail/send"


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
            ("SENDGRID_API_KEY", SENDGRID_API_KEY),
            ("FROM_ADDRESS", FROM_ADDRESS),
        )
        if not val
    ]
    if missing:
        raise RuntimeError(
            f"Missing required env vars: {', '.join(missing)}. "
            "Please set them in your .env file."
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
    """Send an email via SendGrid HTTP API.

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

    to_list  = _split_recipients(to)
    cc_list  = _split_recipients(cc)
    bcc_list = _split_recipients(bcc)

    if not to_list:
        raise ValueError("'to' must contain at least one address.")

    content_type = "text/html" if body_type.lower() == "html" else "text/plain"

    payload: dict = {
        "personalizations": [
            {
                "to": [{"email": addr} for addr in to_list],
                **({"cc":  [{"email": a} for a in cc_list]}  if cc_list  else {}),
                **({"bcc": [{"email": a} for a in bcc_list]} if bcc_list else {}),
            }
        ],
        "from": {
            "email": FROM_ADDRESS,
            **({"name": FROM_NAME} if FROM_NAME else {}),
        },
        "subject": subject,
        "content": [{"type": content_type, "value": body}],
    }

    headers = {
        "Authorization": f"Bearer {SENDGRID_API_KEY}",
        "Content-Type": "application/json",
    }

    resp = requests.post(SENDGRID_URL, json=payload, headers=headers, timeout=15)

    if resp.status_code not in (200, 202):
        raise RuntimeError(
            f"SendGrid API error {resp.status_code}: {resp.text}"
        )

    preview = ", ".join(to_list)
    return f"Sent email to {preview} (subject: {subject!r})."


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    transport = os.environ.get("MCP_TRANSPORT", "streamable-http")
    print(
        f"[mail-mcp] Starting on {transport} "
        f"(bind {MCP_HOST}:{MCP_PORT}, endpoint /mcp)\n"
        f"  SendGrid API → {FROM_ADDRESS or '(FROM_ADDRESS unset)'}",
        file=sys.stderr,
        flush=True,
    )
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
