"""
Content Isolation Layer
Controls: CTRL-01 (isolation markers), CTRL-07 (content preprocessing)
Threats mitigated: T-01, T-03, S-03, E-01, E-03
SRS reference: FR-1
ADR reference: ADR-002

Every chunk retrieved from Confluence or Jira passes through this module
before entering the model context. Two defenses are layered:

  1. preprocess_content() strips injection vectors: zero-width Unicode,
     hidden HTML, null bytes (CTRL-07).
  2. isolate_chunk() wraps the preprocessed content in explicit trust
     boundary markers so the system prompt can instruct the model to treat
     it as lowest-trust data, not instructions (CTRL-01).

No external dependencies. Standard library only.
"""

from __future__ import annotations

import html
import re
import unicodedata
from dataclasses import dataclass

# Matches our own trust markers — used to detect if content is trying to
# inject marker-like text to confuse the model about boundaries.
_MARKER_RE = re.compile(
    r"\[RETRIEVED FROM:[^\]]*\]|\[END RETRIEVED CONTENT\]",
    re.IGNORECASE,
)

# Strips characters that would break the marker format if they appeared
# in attacker-controlled source/id fields.
_UNSAFE_IN_MARKER = re.compile(r"[\[\]\|\n\r\t]")


@dataclass(frozen=True)
class RetrievedChunk:
    """A single chunk of content retrieved from Confluence or Jira."""
    source: str    # e.g. "confluence/page-42" or "jira/PROJ-123"
    chunk_id: str  # stable, server-assigned identifier
    content: str   # raw text as returned by the connector


@dataclass(frozen=True)
class IsolatedChunk:
    """A chunk after preprocessing and isolation wrapping."""
    source: str
    chunk_id: str
    raw_content: str
    preprocessed_content: str
    wrapped: str


def preprocess_content(text: str) -> str:
    """
    CTRL-07: Remove injection vectors from retrieved text before it enters
    the model context.

    Steps applied in order:
      1. Null byte removal — terminates strings in some parsers
      2. Unicode NFC normalization — collapses zero-width and invisible chars
         that attackers use to hide instruction text from human reviewers
      3. HTML entity decoding — reveals hidden text in &lt;script&gt; etc.
      4. HTML tag stripping — removes <tags> entirely after decoding

    Returns cleaned plain text.
    """
    # 1. Null bytes
    text = text.replace("\x00", "")

    # 2. Unicode NFC — normalises composed forms; zero-width joiners,
    #    soft hyphens, etc. survive NFC but are then visible for review.
    #    Strip category Cf (format chars) and Cc (control chars) except
    #    common whitespace (\n, \r, \t).
    text = unicodedata.normalize("NFC", text)
    text = "".join(
        ch for ch in text
        if unicodedata.category(ch) not in ("Cf", "Cc")
        or ch in "\n\r\t"
    )

    # 3. HTML entity decode (&amp; → &, &#x3C; → <, etc.)
    text = html.unescape(text)

    # 4. Strip HTML tags
    text = re.sub(r"<[^>]*>", "", text)

    return text


def _sanitize_field(value: str) -> str:
    """
    Prevent marker injection via attacker-influenced source or chunk_id fields.
    Strips bracket, pipe, and newline characters that would break the marker
    format or allow a crafted source field to close/open a fake marker.
    """
    return _UNSAFE_IN_MARKER.sub("", value)


def isolate_chunk(chunk: RetrievedChunk) -> IsolatedChunk:
    """
    CTRL-01: Preprocess a chunk and wrap it in trust boundary markers.

    The marker format is:
        [RETRIEVED FROM: {source} | TRUST: external-internal | ID: {chunk_id}]
        {preprocessed content}
        [END RETRIEVED CONTENT]

    The system prompt instructs the model to treat everything between these
    markers as external data — never as instructions.
    """
    preprocessed = preprocess_content(chunk.content)
    safe_source = _sanitize_field(chunk.source)
    safe_id = _sanitize_field(chunk.chunk_id)

    wrapped = (
        f"[RETRIEVED FROM: {safe_source}"
        f" | TRUST: external-internal"
        f" | ID: {safe_id}]\n"
        f"{preprocessed}\n"
        f"[END RETRIEVED CONTENT]"
    )

    return IsolatedChunk(
        source=safe_source,
        chunk_id=safe_id,
        raw_content=chunk.content,
        preprocessed_content=preprocessed,
        wrapped=wrapped,
    )


def prepare_retrieved_context(chunks: list[RetrievedChunk]) -> str:
    """
    Isolate a list of chunks and join them into a single context block
    ready for injection into the model prompt.

    Returns an empty string if chunks is empty.
    """
    if not chunks:
        return ""
    return "\n\n".join(isolate_chunk(c).wrapped for c in chunks)
