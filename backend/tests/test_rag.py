"""
retrieve() must rank by actual relevance, not just return the top-N table
rows -- a query about "water safety plans" should surface the excerpt that
mentions water safety plans, not whichever chunk happens to be first in the
index. Also must degrade to an empty result when no PDFs are indexed
(a fresh checkout has none -- they're gitignored), never crash.
"""
from unittest.mock import patch

from ai.rag import build_index_from_chunks, retrieve


def _fake_index():
    chunks = [
        {"text": "The water safety plan must be reviewed annually by the WSA.", "source": "blue_drop.pdf", "page": 12},
        {"text": "Non-revenue water increased by 3 percent in the reporting period.", "source": "no_drop.pdf", "page": 40},
        {"text": "Maintenance expenditure should meet the 8 percent benchmark of asset value.", "source": "benchmarking.pdf", "page": 5},
    ]
    return build_index_from_chunks(chunks)


def test_retrieve_ranks_the_most_relevant_chunk_first():
    results = retrieve("water safety plan requirements", top_k=3, index=_fake_index())
    assert results[0]["source"] == "blue_drop.pdf"
    assert results[0]["page"] == 12


def test_retrieve_respects_top_k():
    results = retrieve("water", top_k=1, index=_fake_index())
    assert len(results) == 1


def test_retrieve_returns_empty_list_for_empty_index():
    empty_index = build_index_from_chunks([])
    assert retrieve("anything", index=empty_index) == []


def test_retrieve_excludes_zero_score_matches():
    # a query with no vocabulary overlap should not return irrelevant chunks
    results = retrieve("xyzxyzxyz nonsense query unrelated", top_k=3, index=_fake_index())
    assert results == []


def test_build_index_from_chunks_handles_empty_list():
    index = build_index_from_chunks([])
    assert index["chunks"] == []
    assert index["vectorizer"] is None


def test_get_index_returns_empty_when_no_pdfs_present():
    from ai import rag
    with patch.object(rag, "RAW_DIR") as mock_dir:
        mock_dir.glob.return_value = []
        # bypass the module cache for this check
        rag._index_cache.clear()
        index = rag.get_index()
    assert index["chunks"] == []
    rag._index_cache.clear()


def test_regulatory_context_endpoint_requires_admin(client):
    resp = client.get("/ai/regulatory-context", params={"query": "water safety plan"})
    assert resp.status_code == 401


def test_regulatory_context_endpoint_404_when_nothing_indexed(client, auth_headers):
    with patch("app.routes.ai.retrieve", return_value=[]):
        resp = client.get("/ai/regulatory-context", params={"query": "anything"}, headers=auth_headers)
    assert resp.status_code == 404


def test_regulatory_context_endpoint_returns_cited_answer(client, auth_headers):
    fake_excerpts = [{"text": "Water safety plans must be reviewed annually.", "source": "blue_drop.pdf", "page": 12, "score": 0.8}]
    with patch("app.routes.ai.retrieve", return_value=fake_excerpts), \
         patch("app.routes.ai.call_openai", return_value="Water safety plans must be reviewed annually (blue_drop.pdf, p.12)."):
        resp = client.get("/ai/regulatory-context", params={"query": "water safety plan review frequency"}, headers=auth_headers)

    assert resp.status_code == 200
    body = resp.json()
    assert "annually" in body["answer"]
    assert body["sources"][0]["source"] == "blue_drop.pdf"
    assert body["sources"][0]["page"] == 12
