"""Phase 1 smoke test: verify all cross-project imports resolve via conftest.py.

This test is deleted after Phase 1 is confirmed complete — it is a wiring
verification, not a functional test. Functional tests are in test_injection_defense.py,
test_pii_scan_on_findings.py, and test_pipeline_regression.py.
"""


def test_p03_imports():
    from src.models import ResearchFinding, ResearchTask, AgentConstraints
    from src.agents.researcher import ResearcherAgent
    from src.orchestrator import Orchestrator
    assert ResearchFinding.model_fields  # non-empty


def test_p05_imports():
    from content_isolation import RetrievedChunk, prepare_retrieved_context, isolate_chunk, preprocess_content
    from pii_scanner import scan_output_for_pii, PIIScanResult
    assert RetrievedChunk.__dataclass_fields__  # non-empty


def test_p06_imports():
    from p06 import __file__ as p06_init
    assert "project-06" in p06_init


def test_retrueved_chunk_shape():
    from content_isolation import RetrievedChunk
    chunk = RetrievedChunk(source="mcp/web_search", chunk_id="tc_001", content="test content")
    assert chunk.source == "mcp/web_search"
    assert chunk.chunk_id == "tc_001"
    assert chunk.content == "test content"


def test_prepare_retrieved_context_wraps():
    from content_isolation import RetrievedChunk, prepare_retrieved_context
    chunk = RetrievedChunk(source="mcp/fetch_page", chunk_id="tc_001", content="hello world")
    result = prepare_retrieved_context([chunk])
    assert "[RETRIEVED FROM:" in result
    assert "[END RETRIEVED CONTENT]" in result
    assert "hello world" in result
