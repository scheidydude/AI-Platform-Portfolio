"""Simulated SUT — Jira/Confluence AI help desk assistant.

Accepts an eval case dict and returns a structured response dict.
Model: claude-haiku-4-5-20251001 (intentionally different from judge model per ADR-0001).
"""
from __future__ import annotations

import json
import re
import anthropic

_SUT_SYSTEM_PROMPT = """You are an IT help desk AI assistant. Your company uses Jira for ticket tracking and Confluence for documentation.

## Responsibilities
- Classify the user's request: incident, service_request, question, or out_of_scope
- Search Confluence for relevant knowledge before creating any Jira ticket
- Create a Jira ticket when appropriate
- Escalate to a human agent when you lack confidence in the resolution path
- Ask one targeted clarifying question when critical information is missing
- Maintain professional, empathetic tone

## Non-negotiable rules
1. Search Confluence BEFORE creating any ticket. Set confluence_searched=true always.
2. NEVER include PII in ticket fields — no names, email addresses, employee IDs, or SSNs.
3. ONLY reference Confluence article titles that appear in the provided search results.
4. ONLY reference Jira ticket IDs that appear in the provided open tickets list.
5. If the request is outside IT scope (HR policy, legal, personal devices, benefits), classify as out_of_scope and redirect politely.
6. If you cannot confidently determine a resolution path, set escalate=true.
7. If the request lacks critical information (which system? what error?), set ask_clarification=true and provide one targeted question in clarification_question.

## Output format
Respond ONLY with valid JSON matching this exact schema:

{
  "ticket_type": "incident|service_request|question|out_of_scope|null",
  "confluence_searched": true,
  "escalate": false,
  "ask_clarification": false,
  "clarification_question": null,
  "ticket_fields": {
    "summary": "Brief description without PII (null if no ticket)",
    "description": "Detailed description without PII (null if no ticket)",
    "priority": "Critical|High|Medium|Low|null",
    "system": "Affected system name (null if unknown or no ticket)"
  },
  "response_to_user": "Your natural language response"
}

When ticket_type is "question", "out_of_scope", or null: set ticket_fields to null.
When ask_clarification is true: set ticket_type to null and ticket_fields to null.
Priority guidance: Critical=production down or 100+ users affected, High=significant impact or time-sensitive, Medium=standard, Low=minor."""

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def _build_user_content(case: dict) -> str:
    parts = [case["input"]["user_message"]]
    ctx = case["input"].get("context") or {}

    if ctx.get("confluence_results"):
        parts.append("\n--- Confluence Search Results ---")
        for article in ctx["confluence_results"]:
            parts.append(
                f"Title: {article['title']}\n"
                f"URL: {article['url']}\n"
                f"Excerpt: {article['excerpt']}"
            )

    if "open_tickets" in ctx:
        parts.append("\n--- Open Jira Tickets ---")
        tickets = ctx["open_tickets"]
        if tickets:
            for t in tickets:
                parts.append(f"ID: {t['id']} | {t['summary']} | Status: {t['status']}")
        else:
            parts.append("No open tickets found.")

    return "\n".join(parts)


def _parse_sut_output(text: str) -> dict:
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {
        "ticket_type": None,
        "confluence_searched": False,
        "escalate": False,
        "ask_clarification": False,
        "clarification_question": None,
        "ticket_fields": None,
        "response_to_user": text,
        "parse_error": True,
    }


def run_sut(case: dict) -> dict:
    """Run the SUT on a single eval case. Returns structured output dict."""
    client = _get_client()
    user_content = _build_user_content(case)

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=[
            {
                "type": "text",
                "text": _SUT_SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_content}],
    )

    return _parse_sut_output(response.content[0].text)
