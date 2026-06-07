"""Pytest configuration for P06 integration tests.

Path wiring strategy (see ADR-001):

P03 (src.*):
    Installed as editable package via: uv pip install -e ../project-03-agentic-mcp
    The .pth file in site-packages adds /project-03-agentic-mcp to sys.path.
    `from src.models import ResearchFinding` resolves through that path entry.
    P06 uses p06/ (not src/) to avoid shadowing this namespace.

P05 (content_isolation, pii_scanner):
    No pyproject.toml — src/ injected here via sys.path.insert(0, ...).
    Top-level import: `from content_isolation import ...`

P06 p06/ (secure_researcher):
    P06's project root injected so `from p06.secure_researcher import ...` works.
"""
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_P06_ROOT = Path(__file__).resolve().parent.parent
_P05_SRC = _REPO_ROOT / "project-05-security-compliance" / "src"

# P05: top-level modules (content_isolation, pii_scanner) — insert first
if str(_P05_SRC) not in sys.path:
    sys.path.insert(0, str(_P05_SRC))

# P06: project root so `from p06.secure_researcher import ...` works
if str(_P06_ROOT) not in sys.path:
    sys.path.insert(0, str(_P06_ROOT))
