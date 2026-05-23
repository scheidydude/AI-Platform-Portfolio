"""
Document extraction — handles both PDF (pdfplumber) and HTML (EDGAR .htm) files.
Extracts text while preserving section structure.
"""

import re
import json
import pdfplumber
from html.parser import HTMLParser
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional


@dataclass
class ExtractedPage:
    page_number: int
    text: str
    tables: List[dict]
    section_hint: str


@dataclass
class ExtractedDocument:
    filename: str
    company: str
    year: int
    pages: List[ExtractedPage]
    total_pages: int
    raw_text: str


SECTION_PATTERN = re.compile(
    r"(ITEM\s+\d+[A-Z]?\.?\s+[A-Z][^\n]{2,80})",
    re.MULTILINE,
)


# ─────────────────────────────────────────────
# HTML extraction (EDGAR .htm filings)
# ─────────────────────────────────────────────

class _TextExtractor(HTMLParser):
    # Tags whose content is entirely skipped (including children)
    SKIP_TAGS = {"script", "style", "head", "meta", "link", "ix:header", "ix:resources"}
    # iXBRL inline tags — skip the tag but keep readable child text
    IXBRL_PASS_TAGS = {"ix:nonfraction", "ix:nonnumeric", "ix:fraction", "ix:continuation"}
    # Block-level tags that get a newline separator
    BLOCK_TAGS = {"p", "div", "tr", "br", "h1", "h2", "h3", "h4", "h5", "li", "td", "th"}

    def __init__(self):
        super().__init__()
        self.parts = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        tag_lower = tag.lower()
        if tag_lower in self.SKIP_TAGS:
            self._skip += 1
        if tag_lower in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        tag_lower = tag.lower()
        if tag_lower in self.SKIP_TAGS:
            self._skip = max(0, self._skip - 1)

    def handle_data(self, data):
        if self._skip == 0:
            # Skip XBRL code-like data (long strings with no spaces that are mostly URLs/IDs)
            stripped = data.strip()
            if stripped and not _is_xbrl_noise(stripped):
                self.parts.append(data)

    def get_text(self) -> str:
        raw = "".join(self.parts)
        lines = [l.strip() for l in raw.splitlines()]
        collapsed = "\n".join(l for l in lines if l)
        return re.sub(r"\n{3,}", "\n\n", collapsed)


def _is_xbrl_noise(text: str) -> bool:
    """Detect XBRL/iXBRL encoded data — not human-readable filing text."""
    if len(text) > 200 and " " not in text:
        return True
    # URL-heavy content (XBRL namespace strings)
    if text.count("http://") + text.count("https://") > 2:
        return True
    # XBRL ID patterns: long token strings with colons and no spaces
    if re.match(r"^[\w\-\.:/]{50,}$", text):
        return True
    return False


def extract_html(html_path: Path, company: str, year: int) -> ExtractedDocument:
    with open(html_path, "r", encoding="utf-8", errors="replace") as f:
        html = f.read()

    parser = _TextExtractor()
    parser.feed(html)
    raw_text = parser.get_text()

    # Split into synthetic "pages" of ~3000 chars for consistent metadata
    page_size = 3000
    text_chunks = [raw_text[i:i+page_size] for i in range(0, len(raw_text), page_size)]

    current_section = "PREAMBLE"
    pages = []
    for i, text in enumerate(text_chunks):
        matches = SECTION_PATTERN.findall(text)
        if matches:
            current_section = matches[-1].strip()
        pages.append(
            ExtractedPage(
                page_number=i + 1,
                text=text,
                tables=[],
                section_hint=current_section,
            )
        )

    return ExtractedDocument(
        filename=html_path.name,
        company=company,
        year=year,
        pages=pages,
        total_pages=len(pages),
        raw_text=raw_text,
    )


# ─────────────────────────────────────────────
# PDF extraction
# ─────────────────────────────────────────────

def extract_pdf(pdf_path: Path, company: str, year: int) -> ExtractedDocument:
    pages = []
    current_section = "PREAMBLE"
    all_text_parts = []

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        for page in pdf.pages:
            text = page.extract_text() or ""
            tables = [{"rows": tbl} for tbl in page.extract_tables() if tbl]

            matches = SECTION_PATTERN.findall(text)
            if matches:
                current_section = matches[-1].strip()

            pages.append(
                ExtractedPage(
                    page_number=page.page_number,
                    text=text,
                    tables=tables,
                    section_hint=current_section,
                )
            )
            all_text_parts.append(text)

    return ExtractedDocument(
        filename=pdf_path.name,
        company=company,
        year=year,
        pages=pages,
        total_pages=total_pages,
        raw_text="\n\n".join(all_text_parts),
    )


# ─────────────────────────────────────────────
# Dispatch + persistence
# ─────────────────────────────────────────────

def extract_document(path: Path, company: str, year: int) -> ExtractedDocument:
    if path.suffix.lower() in (".htm", ".html"):
        return extract_html(path, company, year)
    return extract_pdf(path, company, year)


def save_extracted(doc: ExtractedDocument, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = re.sub(r"\.(pdf|htm|html)$", "", doc.filename, flags=re.IGNORECASE)
    out_path = out_dir / f"{stem}_extracted.json"

    with open(out_path, "w") as f:
        json.dump(
            {
                "filename": doc.filename,
                "company": doc.company,
                "year": doc.year,
                "total_pages": doc.total_pages,
                "raw_text": doc.raw_text,
                "pages": [asdict(p) for p in doc.pages],
            },
            f,
            indent=2,
        )
    return out_path


def batch_extract(raw_dir: Path, processed_dir: Path, manifest_path: Path) -> List[Path]:
    with open(manifest_path) as f:
        manifest = json.load(f)

    extracted_paths = []
    for entry in manifest:
        if not entry.get("path"):
            continue
        file_path = Path(entry["path"])
        if not file_path.exists():
            print(f"  [skip] {file_path.name} — file missing")
            continue

        # Infer year from filename or entry
        year = entry.get("year")
        if not year:
            m = re.search(r"_(\d{4})_", file_path.name)
            year = int(m.group(1)) if m else 2023

        print(f"  Extracting {file_path.name}...")
        try:
            doc = extract_document(file_path, entry["company"], year)
            out_path = save_extracted(doc, processed_dir)
            extracted_paths.append(out_path)
            size_kb = len(doc.raw_text) // 1024
            print(f"  [OK] {out_path.name} ({doc.total_pages} pages, ~{size_kb}KB text)")
        except Exception as e:
            print(f"  [ERROR] {file_path.name}: {e}")

    return extracted_paths


if __name__ == "__main__":
    base = Path(__file__).parents[2]
    paths = batch_extract(
        raw_dir=base / "data" / "raw",
        processed_dir=base / "data" / "processed",
        manifest_path=base / "data" / "raw" / "manifest.json",
    )
    print(f"\nExtracted {len(paths)} documents")
