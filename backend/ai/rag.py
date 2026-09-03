from pathlib import Path

import pdfplumber
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

RAW_DIR = Path("data/raw")

# page text shorter than this is almost always a cover/blank/figure-only
# page — not useful as a retrievable excerpt
_MIN_CHUNK_CHARS = 200

# lazy, in-process cache — the source PDFs run into the hundreds of pages
# combined, so this is built once on first request and reused, not on
# every call or at app startup (most requests never need it)
_index_cache: dict = {}


def build_index_from_chunks(chunks: list[dict]) -> dict:
    if not chunks:
        return {"chunks": [], "vectorizer": None, "matrix": None}
    vectorizer = TfidfVectorizer(stop_words="english", max_features=20000)
    matrix = vectorizer.fit_transform([c["text"] for c in chunks])
    return {"chunks": chunks, "vectorizer": vectorizer, "matrix": matrix}


def _extract_chunks() -> list[dict]:
    chunks: list[dict] = []
    for pdf_path in sorted(RAW_DIR.glob("*.pdf")):
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_number, page in enumerate(pdf.pages, start=1):
                    text = (page.extract_text() or "").strip()
                    if len(text) < _MIN_CHUNK_CHARS:
                        continue
                    chunks.append({"text": text, "source": pdf_path.name, "page": page_number})
        except Exception:  # noqa: BLE001 — a corrupt/unreadable PDF shouldn't block the rest of the index
            continue
    return chunks


def _directory_fingerprint() -> frozenset:
    # cheap: just filenames + mtimes, not file contents — lets get_index()
    # detect a dropped-in or edited PDF without re-parsing anything to check
    if not RAW_DIR.exists():
        return frozenset()
    return frozenset((p.name, p.stat().st_mtime) for p in RAW_DIR.glob("*.pdf"))


def get_index() -> dict:
    fingerprint = _directory_fingerprint()
    if not _index_cache or _index_cache.get("_fingerprint") != fingerprint:
        _index_cache.clear()
        _index_cache.update(build_index_from_chunks(_extract_chunks()))
        _index_cache["_fingerprint"] = fingerprint
    return _index_cache


def retrieve(query: str, top_k: int = 5, index: dict | None = None) -> list[dict]:
    """
    Retrieves the top_k most relevant page-level excerpts from the DWS
    regulatory PDFs already sitting in data/raw/, so AI answers can cite an
    actual source page instead of paraphrasing from a prompt with no
    citation trail.
    """
    index = index if index is not None else get_index()
    if not index["chunks"]:
        return []

    query_vector = index["vectorizer"].transform([query])
    scores = cosine_similarity(query_vector, index["matrix"])[0]
    ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

    return [
        {**index["chunks"][i], "score": float(scores[i])}
        for i in ranked
        if scores[i] > 0
    ]
