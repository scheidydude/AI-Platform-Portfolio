from __future__ import annotations
import tiktoken

_ENCODING = tiktoken.get_encoding("cl100k_base")


def estimate_tokens(messages: list[dict]) -> int:
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            total += len(_ENCODING.encode(content))
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and isinstance(part.get("text"), str):
                    total += len(_ENCODING.encode(part["text"]))
        total += 4  # per-message overhead: role + delimiters
    total += 2  # reply priming
    return total
