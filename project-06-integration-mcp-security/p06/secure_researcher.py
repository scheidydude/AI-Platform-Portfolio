"""Secure integration wrapper for P03 ResearcherAgent and Orchestrator.

Wires P05 security controls into P03's execution path without modifying P03 source.
See DESIGN-001 for wiring points and sequence diagrams; ADR-002 for why this pattern
was chosen over a full method override or proxy client.

Wiring Point 1 (content isolation):
    Demonstrated via _to_retrieved_chunk() + prepare_retrieved_context() in tests.
    Not wired live into ResearcherAgent.run() — P03's agentic loop has no overridable
    hook for tool result content. See ADR-002 and docs/lessons-learned.md.

Wiring Point 2 (PII scan):
    SecureResearcherAgent.run() scans every ResearchFinding before returning it.
    PIIInFindingError is raised on action="block"; the Orchestrator exception handler
    transitions the pipeline to "failed" without persisting the finding.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

# Bootstrap P05 src/ for runtime imports (tests use conftest.py instead). ADR-001.
_P05_SRC = Path(__file__).resolve().parent.parent.parent / "project-05-security-compliance" / "src"
if str(_P05_SRC) not in sys.path:
    sys.path.insert(0, str(_P05_SRC))

from src.agents.researcher import ResearcherAgent
from src.models import ResearchFinding, ResearchTask
from src.orchestrator import Orchestrator
from content_isolation import RetrievedChunk, isolate_chunk, prepare_retrieved_context  # noqa: F401
from pii_scanner import scan_output_for_pii

logger = logging.getLogger(__name__)

_STATE_DIR = Path("state")


class PIIInFindingError(Exception):
    """Raised when scan_output_for_pii returns action='block' on a ResearchFinding.

    Propagates up through SecureOrchestrator.run() where the existing Orchestrator
    exception handler catches it, transitions the pipeline to 'failed', and persists
    the failed state — without persisting the PII-containing finding.
    """

    def __init__(self, task_id: str, pii_findings: list) -> None:
        self.task_id = task_id
        self.pii_findings = pii_findings
        entity_types = [f.entity_type for f in pii_findings]
        super().__init__(f"PII detected in finding {task_id!r}: {entity_types}")


class SecureResearcherAgent(ResearcherAgent):
    """ResearcherAgent subclass — scans each finding for PII before returning.

    Wiring Point 2 (DESIGN-001 §3): scan_output_for_pii() runs on every finding
    produced by the base agent. Because the Orchestrator persists findings only after
    receiving them from self.researcher.run(), raising here prevents persistence.
    """

    async def run(self, task: ResearchTask) -> ResearchFinding:
        finding = await super().run(task)
        result = scan_output_for_pii(finding.content)
        if result.action == "block":
            raise PIIInFindingError(task.task_id, result.findings)
        if result.action == "warn":
            logger.warning(
                "PII detected in finding %r — proceeding with warning (entities: %s)",
                task.task_id,
                [f.entity_type for f in result.findings],
            )
        return finding


class SecureOrchestrator(Orchestrator):
    """Drop-in replacement for Orchestrator using SecureResearcherAgent.

    All pipeline logic (planning, synthesis, state persistence, resume) is inherited
    unchanged. Only self.researcher is swapped. See DESIGN-001 §2.
    """

    def __init__(self, state_dir: Path = _STATE_DIR) -> None:
        super().__init__(state_dir)
        self.researcher = SecureResearcherAgent()


def _to_retrieved_chunk(tool_name: str, tool_call_id: str, content: str) -> RetrievedChunk:
    """Adapt a P03 MCP tool result to P05's RetrievedChunk type.

    Used in test_injection_defense.py to demonstrate prepare_retrieved_context()
    behavior on inputs shaped like real P03 tool results. The source field uses
    'mcp/{tool_name}' to make the origin explicit in the trust marker.
    See DESIGN-001 §3 Wiring Point 1 type adapter.
    """
    return RetrievedChunk(
        source=f"mcp/{tool_name}",
        chunk_id=tool_call_id,
        content=content,
    )
