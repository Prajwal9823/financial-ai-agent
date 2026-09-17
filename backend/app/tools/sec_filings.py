"""
TOOL: retrieve_sec_filings / search_sec_filings / summarize_sec_filing

Data source: SEC EDGAR's free JSON APIs — data.sec.gov (company submissions
index) and www.sec.gov (raw filing documents). No API key required; SEC
only asks that every request carries a descriptive User-Agent header
(see SEC_USER_AGENT in .env.example) — undeclared or generic User-Agents
get rate-limited/blocked.

RAG pipeline (Document Loader -> Cleaner -> Chunker -> Embeddings ->
Vector Search -> LLM), implemented here with a TF-IDF vector space
(scikit-learn) instead of a neural embedding model. This keeps the whole
pipeline dependency-light and fast to run with zero model downloads —
the retrieval quality is lower than a real embedding model (e.g.
sentence-transformers + FAISS), which is the natural Phase-7 upgrade:
swap `_build_vector_index` / `_search_index` below for FAISS + an
embedding model and nothing else in the RAG flow has to change, since the
rest of the codebase only depends on `RetrievedChunk` objects.
"""
from __future__ import annotations

import re

import httpx
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.core.cache import cache, cache_key
from app.core.config import get_settings
from app.core.logging_config import get_logger
from app.models.schemas import FilingReference, RetrievedChunk

log = get_logger("tools.sec_filings")
settings = get_settings()

_HEADERS = {"User-Agent": settings.sec_user_agent}
_TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"

_CHUNK_SIZE_CHARS = 1500
_CHUNK_OVERLAP_CHARS = 200


class FilingNotFoundError(Exception):
    pass


# ---------------------------------------------------------------------------
# Step 1: ticker -> CIK lookup
# ---------------------------------------------------------------------------

def _get_cik_for_ticker(ticker: str) -> int:
    key = cache_key("cik_map")
    cik_map = cache.get(key)
    if cik_map is None:
        log.info("[TOOL] Loading SEC ticker->CIK map")
        resp = httpx.get(_TICKER_MAP_URL, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
        raw = resp.json()
        cik_map = {row["ticker"].upper(): row["cik_str"] for row in raw.values()}
        cache.set(key, cik_map, ttl_seconds=24 * 3600)

    cik = cik_map.get(ticker.upper())
    if cik is None:
        raise FilingNotFoundError(f"No SEC CIK found for ticker '{ticker}'.")
    return cik


# ---------------------------------------------------------------------------
# Step 2: list recent filings for a company
# ---------------------------------------------------------------------------

def retrieve_sec_filings(ticker: str, form_type: str = "10-K", limit: int = 1) -> list[FilingReference]:
    """List the most recent filings of a given form type (10-K, 10-Q, 8-K)."""
    key = cache_key("filings_list", ticker, form_type, str(limit))
    if cached := cache.get(key):
        return cached

    log.info(f"[TOOL] retrieve_sec_filings({ticker}, {form_type})")
    cik = _get_cik_for_ticker(ticker)
    resp = httpx.get(_SUBMISSIONS_URL.format(cik=cik), headers=_HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    recent = data["filings"]["recent"]
    results: list[FilingReference] = []
    for form, acc_no, filed, primary_doc in zip(
        recent["form"], recent["accessionNumber"], recent["filingDate"], recent["primaryDocument"]
    ):
        if form != form_type:
            continue
        acc_no_nodash = acc_no.replace("-", "")
        doc_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_no_nodash}/{primary_doc}"
        results.append(
            FilingReference(
                ticker=ticker.upper(), form_type=form, filing_date=filed,
                accession_number=acc_no, url=doc_url,
            )
        )
        if len(results) >= limit:
            break

    if not results:
        raise FilingNotFoundError(f"No '{form_type}' filings found for '{ticker}'.")

    cache.set(key, results, ttl_seconds=24 * 3600)
    return results


# ---------------------------------------------------------------------------
# Step 3-5: fetch document, clean, chunk
# ---------------------------------------------------------------------------

def _clean_html_to_text(html: str) -> str:
    # Deliberately dependency-light: strip tags/scripts/styles with regex
    # rather than pulling in a full HTML parser, since filings are large.
    text = re.sub(r"(?is)<(script|style).*?>.*?(</\1>)", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;|&#160;", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _chunk_text(text: str) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + _CHUNK_SIZE_CHARS
        chunks.append(text[start:end])
        start = end - _CHUNK_OVERLAP_CHARS
    return [c for c in chunks if len(c.strip()) > 100]


def _load_and_chunk_filing(filing: FilingReference) -> list[str]:
    key = cache_key("filing_chunks", filing.accession_number)
    if cached := cache.get(key):
        return cached

    log.info(f"[TOOL] Downloading + chunking filing {filing.accession_number}")
    resp = httpx.get(filing.url, headers=_HEADERS, timeout=30, follow_redirects=True)
    resp.raise_for_status()
    text = _clean_html_to_text(resp.text)
    chunks = _chunk_text(text)

    cache.set(key, chunks, ttl_seconds=24 * 3600)
    return chunks


# ---------------------------------------------------------------------------
# Step 6-8: embed (TF-IDF) + similarity search
# ---------------------------------------------------------------------------

def search_sec_filings(ticker: str, question: str, form_type: str = "10-K", top_k: int = 5) -> list[RetrievedChunk]:
    """Full RAG retrieval step: find the chunks of the latest filing most
    relevant to `question`, ranked by cosine similarity over TF-IDF vectors."""
    log.info(f"[RAG] search_sec_filings({ticker}, form={form_type}) :: '{question}'")
    filing = retrieve_sec_filings(ticker, form_type=form_type, limit=1)[0]
    chunks = _load_and_chunk_filing(filing)

    if not chunks:
        return []

    vectorizer = TfidfVectorizer(stop_words="english", max_features=20000)
    chunk_vectors = vectorizer.fit_transform(chunks)
    query_vector = vectorizer.transform([question])

    similarities = cosine_similarity(query_vector, chunk_vectors).flatten()
    top_indices = similarities.argsort()[::-1][:top_k]

    log.info(f"[RAG] Retrieved {len(top_indices)} relevant chunks")
    return [
        RetrievedChunk(text=chunks[i], source=filing, relevance_score=round(float(similarities[i]), 4))
        for i in top_indices
        if similarities[i] > 0
    ]


def summarize_sec_filing(ticker: str, form_type: str = "10-K", focus: str = "key risks and financial highlights") -> list[RetrievedChunk]:
    """Convenience wrapper: retrieves the chunks most relevant to a general
    'give me the highlights' style question, for the agent to summarize."""
    return search_sec_filings(ticker, question=focus, form_type=form_type, top_k=6)
