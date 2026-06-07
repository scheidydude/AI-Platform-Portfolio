# ADR-001 — P05 Import Strategy: sys.path Injection

**Status:** Accepted  
**Date:** 2026-06-06  
**Deciders:** David Scheiderman

---

## Context

P06 needs to import two modules from P05:
- `src/content_isolation.py`
- `src/pii_scanner.py`

P03 has a `pyproject.toml` with `[build-system]` and `packages = ["src"]`, making it installable as a path dep:

```toml
"project-03-agentic-mcp @ file://../project-03-agentic-mcp"
```

**P05 does not have a `pyproject.toml`.** It uses a `requirements.txt` and a flat `src/` directory with no build backend. The path dep syntax requires a PEP 517/518 build backend (`[build-system]` table). Without it, `pip install -e ../project-05-security-compliance` fails.

Additionally, both P03 and P05 use `packages = ["src"]` in their packaging configs (P03 explicitly; P05 would if it had one). This means installing both would create conflicting `src.*` namespace entries in the Python environment.

---

## Options Considered

### Option A — Add `pyproject.toml` to P05 with renamed package namespace

Add `pyproject.toml` to P05 with `packages = [{"include": "src", "from": ".", "name": "project_05_security"}]` and install as a path dep.

**Pros:** Proper pip-managed dependency; IDE completion works.  
**Cons:** Modifies P05 (a parent project that should be independently owned); changes the import path P05's own tests use (`from src.content_isolation import...` → `from project_05_security.content_isolation import...`); would require updating P05's 55 tests.

**Rejected:** Violates NFR-3 (zero modification to P05 source files) and creates churn in a complete project.

### Option B — sys.path injection in `tests/conftest.py`

Insert `../project-05-security-compliance/src` into `sys.path` before imports. This is a pytest-standard pattern for projects without packaging:

```python
# tests/conftest.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "project-05-security-compliance" / "src"))
```

**Pros:** Zero modification to P05; no namespace collision; P06 conftest.py is the explicit, auditable point of ownership for the import wiring.  
**Cons:** sys.path manipulation is fragile in complex environments (ordering, CI path assumptions); IDE may not resolve imports without manual config; runtime code in `src/secure_researcher.py` also needs the path injection (not just tests).

### Option C — Copy P05 source into P06

Copy `content_isolation.py` and `pii_scanner.py` into P06 directly.

**Pros:** No import complexity.  
**Cons:** Two copies diverge; P05 is a complete project whose ownership should remain in P05; this defeats the integration premise of the portfolio artifact.

**Rejected.**

---

## Decision

**Option B — sys.path injection.**

Rationale:
1. Zero P05 modification is the primary constraint (see ADR-003).
2. sys.path injection is the standard pattern for monorepo path wiring without packaging infrastructure. The fragility concern is managed by co-locating the injection in a single place (`tests/conftest.py` and `src/__init__.py`) and documenting it explicitly.
3. For `src/secure_researcher.py`, the same sys.path injection is applied in a `_bootstrap_p05_path()` call at module load time. This is documented explicitly so a future engineer knows why it is there.

**Implementation:**
- `tests/conftest.py`: sys.path injection for test imports
- `src/__init__.py`: sys.path injection for runtime imports from `secure_researcher.py`
- `docs/integration-surface.md`: documents the path assumption (P05 must be at `../project-05-security-compliance` relative to P06)

---

## Consequences

- P05 stays unchanged and independently runnable.
- P06 has an explicit, documented dependency on the monorepo directory layout.
- If P05 is moved or renamed, the path in `tests/conftest.py` must be updated — a one-line change.
- IDE import resolution for `from content_isolation import ...` may require a `.pth` file or `pyrightconfig.json` pointing to P05's `src/`. This is a DX concern, not a runtime concern.

## Implementation Note — src→p06 rename

During Phase 1 implementation, an additional collision was discovered: both P03 and P06 used `packages = ["src"]` in their build configs. When both are editable-installed via uv, both add their project roots to `sys.path` via `.pth` files. Python's `''` (current directory) entry then finds whichever `src/__init__.py` is in the CWD first — which was P06's, breaking P03's `from src.models import...`.

**Resolution:** Renamed P06's source directory from `src/` to `p06/`. This is correct namespace hygiene: P06 owns the `p06` namespace; P03 owns `src`. All imports in tests use `from p06.secure_researcher import ...` and `from src.models import ...` respectively.

Logged in `task_plan.md` error table as "src namespace collision."
