"""
Answer generation over retrieved chunks.
Model: Qwen3.6-35B via OpenAI-compatible API at ai.scheidy.com:8082.
Uses /no_thinking prefix to suppress chain-of-thought in output.
"""
import os
from typing import List, Optional

# ChunkResult imported at call time to avoid circular path issues
_SYSTEM_PROMPT = (
    "You are a financial analyst assistant with expertise in SEC 10-K filings. "
    "Answer questions using ONLY the provided context. "
    "Attribute every claim to the specific company and section it came from. "
    "Do not speculate beyond what the context states."
)

_USER_TEMPLATE = """/no_thinking
Context chunks from SEC 10-K filings:

{context}

---
Question: {question}

Answer in 2-3 paragraphs. Cite the company name and section for each key claim.
"""


def format_context(chunks: list) -> str:
    parts = []
    for i, c in enumerate(chunks, 1):
        section = c.section_title or "Unknown Section"
        parts.append(
            f"[{i}] {c.company} ({c.year}) — {section}\n{c.content.strip()}"
        )
    return "\n\n".join(parts)


def generate_answer(
    query: str,
    chunks: list,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    max_tokens: int = 512,
    temperature: float = 0.1,
) -> str:
    from openai import OpenAI
    client = OpenAI(
        base_url=base_url or os.getenv("GEN_BASE_URL", "http://ai.scheidy.com:8082/v1"),
        api_key="not-needed",
    )
    model = model or os.getenv("GEN_MODEL", "Qwen3.6-35B-A3B-MXFP4_MOE.gguf")
    context = format_context(chunks)
    user_msg = _USER_TEMPLATE.format(context=context, question=query)

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return resp.choices[0].message.content.strip()
