"""
Financial Research Agent — the orchestration core described in the spec's
"Agent Decision-Making" section:

    User Query -> Intent Detection -> Tool Selection -> Data Retrieval ->
    Data Validation -> Financial Analysis -> RAG Retrieval -> LLM Reasoning
    -> Structured Response

Design choice: intent -> fixed tool plan (see intent.py) rather than
letting the LLM freely pick tools. This keeps the agent auditable and
debuggable (every response lists exactly which tools ran and whether
each succeeded — the `tools_used` trace) while still using the LLM for
what it's actually good at: turning retrieved numbers/news/filing text
into a readable, well-organized answer.
"""
from __future__ import annotations

import json
import time
from google.genai import errors
from google import genai

from app.agents.intent import Intent, detect_intent, extract_tickers
from app.core.config import get_settings
from app.core.logging_config import get_logger
from app.models.schemas import ResearchResponse, ToolTrace
from app.tools import fundamentals as fundamentals_tool
from app.tools import news_sentiment as news_tool
from app.tools import sec_filings as sec_tool
from app.tools import stock_data as stock_tool
from app.tools import technical_analysis as ta_tool

log = get_logger("agents.agent")
settings = get_settings()

_client: genai.Client | None = None


def _llm_client() -> genai.Client:
    global _client

    if _client is None:
        if not settings.gemini_api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Add it to backend/.env."
            )

        _client = genai.Client(
            api_key=settings.gemini_api_key
        )

    return _client


_SYSTEM_PROMPT = """You are a financial research analyst assistant.

You are given ONLY pre-retrieved, real data (prices, technical indicators,
fundamentals, news, sentiment, SEC filing excerpts). Rules you must follow:

1. Use ONLY the data provided to you below. Never invent numbers, news, or
   filing content that is not present in the data.
2. If a field says it is unavailable, say so plainly — do not guess a value.
3. Clearly separate: retrieved facts, calculated metrics, your own
   interpretation, and remaining uncertainty/risk.
4. This is a research/informational tool, NOT investment advice. Never say
   "buy", "sell", or claim to know future price direction with certainty.
5. Be concise, structured (use headers/bullets), and cite which data source
   backs each major claim (e.g. "per the latest 10-K", "per recent news").
"""


def _run_tool(trace: list[ToolTrace], name: str, fn, *args, **kwargs):
    """Runs a tool, appends a trace entry, and never lets one failing tool
    take down the whole request — a missing/failed data source degrades
    the answer instead of crashing it (rule: graceful missing-data handling)."""
    try:
        log.info(f"[TOOL] {name}{args}")
        result = fn(*args, **kwargs)
        trace.append(ToolTrace(tool=name, status="success"))
        return result
    except Exception as exc:  # noqa: BLE001 - intentionally broad: any tool may fail on bad/rate-limited data
        log.warning(f"[TOOL] {name} failed: {exc}")
        trace.append(ToolTrace(tool=name, status="error"))
        return None


def _gather_data_for_ticker(ticker: str, intent: Intent, query: str, trace: list[ToolTrace]) -> dict:
    """Runs only the tools relevant to the detected intent — this is the
    'do not blindly call every tool' rule from the spec."""
    data: dict = {}

    data["profile"] = _run_tool(trace, "get_company_profile", stock_tool.get_company_profile, ticker)
    data["price"] = _run_tool(trace, "get_stock_price", stock_tool.get_stock_price, ticker)

    if intent in (Intent.STOCK_ANALYSIS, Intent.TECHNICAL_ANALYSIS, Intent.MARKET_OVERVIEW):
        data["technicals"] = _run_tool(trace, "calculate_technical_indicators", ta_tool.calculate_technical_indicators, ticker)

    if intent in (Intent.STOCK_ANALYSIS, Intent.FUNDAMENTAL_ANALYSIS, Intent.MARKET_OVERVIEW):
        data["fundamentals"] = _run_tool(trace, "get_company_fundamentals", fundamentals_tool.get_company_fundamentals, ticker)

    if intent in (Intent.STOCK_ANALYSIS, Intent.NEWS_ANALYSIS, Intent.SENTIMENT_ANALYSIS, Intent.MARKET_OVERVIEW):
        data["news_sentiment"] = _run_tool(trace, "analyze_news_sentiment", news_tool.analyze_news_sentiment, ticker)

    if intent in (Intent.SEC_ANALYSIS, Intent.STOCK_ANALYSIS, Intent.MARKET_OVERVIEW):
        focus = query if intent == Intent.SEC_ANALYSIS else "key risks and financial highlights"
        chunks = _run_tool(trace, "search_sec_filings", sec_tool.search_sec_filings, ticker, focus)
        data["sec_chunks"] = chunks

    return data


def _serialize_for_llm(data: dict) -> str:
    """Pydantic models -> plain JSON the LLM can read. `default=str` keeps
    this robust to any field type without a bespoke encoder."""
    plain = {}
    for k, v in data.items():
        if v is None:
            plain[k] = "unavailable"
        elif isinstance(v, list):
            plain[k] = [item.model_dump() if hasattr(item, "model_dump") else item for item in v]
        elif hasattr(v, "model_dump"):
            plain[k] = v.model_dump()
        else:
            plain[k] = v
    return json.dumps(plain, indent=2, default=str)


def _collect_sources(data: dict) -> list[str]:
    sources: list[str] = []
    if data.get("news_sentiment"):
        sources += [a.url for a in data["news_sentiment"].articles if a.url]
    if data.get("sec_chunks"):
        sources += list({c.source.url for c in data["sec_chunks"]})
    return sources


async def run_research_agent(query: str) -> ResearchResponse:
    trace: list[ToolTrace] = []
    intent = detect_intent(query)
    tickers = extract_tickers(query)
    log.info(f"[AGENT] Intent: {intent.value} | Tickers: {tickers}")

    # detect_intent() already guarantees GENERAL_FINANCIAL_QUESTION whenever
    # no ticker was found, so no duplicate check is needed here.
    all_data: dict[str, dict] = {}
    if intent == Intent.GENERAL_FINANCIAL_QUESTION:
        context = "No specific ticker was identified in the query. Answer generally and, if helpful, ask the user which company they mean."
    else:
        for ticker in tickers[:2]:  # cap to 2 tickers per query to bound latency/cost
            all_data[ticker] = _gather_data_for_ticker(ticker, intent, query, trace)
        context = _serialize_for_llm(all_data)

    log.info("[LLM] Generating final response")
    client = _llm_client()
    prompt = f"""
    {_SYSTEM_PROMPT}
    
    User question: {query}
    
    Detected intent: {intent.value}
    
    Retrieved data:
    {context}
    """
    
    response = _generate_llm_response(
        client=client,
        model=settings.llm_model,
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=(
            f"User question: {query}\n\n"
            f"Detected intent: {intent.value}\n\n"
            f"Retrieved data:\n{context}"
        ),
    )
    
    answer_text = response.text

    sources: list[str] = []
    for ticker_data in all_data.values():
        sources += _collect_sources(ticker_data)

    return ResearchResponse(
        query=query,
        intent=intent.value,
        tools_used=trace,
        answer=answer_text,
        sources=list(dict.fromkeys(sources)),  # de-dupe, preserve order
        raw_data={t: _json_safe(d) for t, d in all_data.items()},
    )


def _json_safe(data: dict) -> dict:
    return json.loads(_serialize_for_llm(data))

def _generate_llm_response(
    client,
    model: str,
    system_prompt: str,
    user_prompt: str,
):
    """
    Generate an LLM response with a small retry for temporary
    Gemini server/load errors.
    """

    last_error = None

    for attempt in range(3):
        try:
            log.info(
                f"[LLM] Calling {model} "
                f"(attempt {attempt + 1}/3)"
            )

            response = client.models.generate_content(
                model=model,
                contents=user_prompt,
                config={
                    "system_instruction": system_prompt,
                    "temperature": 0.2,
                    "max_output_tokens": 1500,
                },
            )

            return response

        except errors.ServerError as exc:
            last_error = exc

            log.warning(
                f"[LLM] Gemini server error "
                f"(attempt {attempt + 1}/3): {exc}"
            )

            if attempt < 2:
                time.sleep(2 ** attempt)

        except Exception as exc:
            log.exception(
                f"[LLM] Unexpected Gemini error: {exc}"
            )
            raise

    raise RuntimeError(
        f"Gemini temporarily unavailable after 3 attempts: "
        f"{last_error}"
    )