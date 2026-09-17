"""
TOOL: get_company_fundamentals

Free fundamentals using SEC EDGAR XBRL Company Facts.

No Yahoo Finance quoteSummary calls are used here.

Rule #11:
Financial metrics are calculated deterministically from SEC-reported
financial data. The LLM is never asked to calculate financial numbers.
"""

from __future__ import annotations

import requests

from app.core.cache import cache, cache_key
from app.core.logging_config import get_logger
from app.models.schemas import Fundamentals

log = get_logger("tools.fundamentals")


SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

SEC_HEADERS = {
    "User-Agent": (
        "FinancialAIAgent research-project "
        "contact@example.com"
    ),
    "Accept-Encoding": "gzip, deflate",
}


# ---------------------------------------------------------------------------
# SEC helpers
# ---------------------------------------------------------------------------

def _get_cik(ticker: str) -> str:
    """Convert ticker -> zero-padded SEC CIK."""

    response = requests.get(
        SEC_TICKERS_URL,
        headers=SEC_HEADERS,
        timeout=20,
    )

    response.raise_for_status()

    data = response.json()

    ticker = ticker.upper().strip()

    for company in data.values():
        if company.get("ticker", "").upper() == ticker:
            return str(company["cik_str"]).zfill(10)

    raise ValueError(
        f"Ticker '{ticker}' was not found in the SEC ticker database."
    )


def _get_company_facts(ticker: str) -> dict:
    """Download SEC XBRL Company Facts for a ticker."""

    cik = _get_cik(ticker)

    url = SEC_FACTS_URL.format(cik=cik)

    log.info(
        f"[SEC] Downloading company facts for {ticker} "
        f"(CIK={cik})"
    )

    response = requests.get(
        url,
        headers=SEC_HEADERS,
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


def _get_fact(
    facts: dict,
    concept_names: list[str],
    unit: str | None = None,
    form: str | None = None,
) -> float | None:
    """
    Return the most recent SEC-reported value.

    If unit is provided, prefer that unit. Otherwise inspect all
    available units for the requested concept.
    """

    us_gaap = facts.get("facts", {}).get("us-gaap", {})

    candidates = []

    for concept_name in concept_names:
        concept = us_gaap.get(concept_name)

        if not concept:
            continue

        units = concept.get("units", {})

        if unit and unit in units:
            entries = units[unit]
        else:
            entries = [
                entry
                for unit_entries in units.values()
                for entry in unit_entries
            ]

        for entry in entries:
            if form and entry.get("form") != form:
                continue

            value = entry.get("val")

            if value is None:
                continue

            candidates.append(entry)

    if not candidates:
        return None

    candidates.sort(
        key=lambda x: (
            x.get("filed", ""),
            x.get("end", ""),
        ),
        reverse=True,
    )

    return float(candidates[0]["val"])


def _get_latest_company_name(facts: dict, ticker: str) -> str:
    return facts.get(
        "entityName",
        ticker.upper(),
    )


# ---------------------------------------------------------------------------
# Fundamentals
# ---------------------------------------------------------------------------

def get_company_fundamentals(ticker: str) -> Fundamentals:

    ticker = ticker.upper().strip()

    key = cache_key(
        "fundamentals",
        ticker,
    )

    if cached := cache.get(key):
        return cached

    log.info(
        f"[TOOL] get_company_fundamentals({ticker})"
    )

    try:
        facts = _get_company_facts(ticker)

    except Exception as exc:
        log.warning(
            f"[SEC] Fundamentals failed for {ticker}: {exc}"
        )

        raise RuntimeError(
            f"Could not retrieve SEC fundamentals for '{ticker}'."
        ) from exc

    unavailable: list[str] = []

    # ---------------------------------------------------------------
    # Revenue
    # ---------------------------------------------------------------

    revenue = _get_fact(
        facts,
        [
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "Revenues",
            "SalesRevenueNet",
        ],
        "USD",
        form="10-K",
    )

    if revenue is None:
        unavailable.append("revenue_ttm")

    # ---------------------------------------------------------------
    # Net income
    # ---------------------------------------------------------------

    net_income = _get_fact(
        facts,
        [
            "NetIncomeLoss",
            "ProfitLoss",
        ],
        "USD",
        form="10-K",
    )

    if net_income is None:
        unavailable.append("net_income_ttm")

    # ---------------------------------------------------------------
    # EPS
    # ---------------------------------------------------------------

    eps = _get_fact(
        facts,
        [
            "EarningsPerShareDiluted",
            "EarningsPerShareBasic",
        ],
        None,
        form="10-K",
    )

    if eps is None:
        unavailable.append("eps_ttm")

    # ---------------------------------------------------------------
    # Assets
    # ---------------------------------------------------------------

    assets = _get_fact(
        facts,
        [
            "Assets",
        ],
        "USD",
        form="10-K",
    )

    # ---------------------------------------------------------------
    # Liabilities
    # ---------------------------------------------------------------

    liabilities = _get_fact(
        facts,
        [
            "Liabilities",
        ],
        "USD",
        form="10-K",
    )

    # ---------------------------------------------------------------
    # Equity
    # ---------------------------------------------------------------

    equity = _get_fact(
        facts,
        [
            "StockholdersEquity",
            "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        ],
        "USD",
        form="10-K",
    )

    # ---------------------------------------------------------------
    # Debt
    # ---------------------------------------------------------------

    debt = _get_fact(
        facts,
        [
            "LongTermDebtNoncurrent",
            "LongTermDebtCurrent",
            "LongTermDebt",
        ],
        "USD",
        form="10-K",
    )

    # ---------------------------------------------------------------
    # Free cash flow
    #
    # FCF = Operating Cash Flow - Capital Expenditure
    # ---------------------------------------------------------------

    operating_cash_flow = _get_fact(
        facts,
        [
            "NetCashProvidedByUsedInOperatingActivities",
        ],
        "USD",
        form="10-K",
    )

    capital_expenditure = _get_fact(
        facts,
        [
            "PaymentsToAcquirePropertyPlantAndEquipment",
            "PaymentsToAcquireProductiveAssets",
        ],
        "USD",
        form="10-K",
    )

    free_cash_flow = None

    if (
        operating_cash_flow is not None
        and capital_expenditure is not None
    ):
        free_cash_flow = (
            operating_cash_flow
            - abs(capital_expenditure)
        )
    else:
        unavailable.append("free_cash_flow")

    # ---------------------------------------------------------------
    # Derived metrics
    # ---------------------------------------------------------------

    profit_margin = None

    if (
        net_income is not None
        and revenue is not None
        and revenue != 0
    ):
        profit_margin = (
            net_income / revenue
        )

    roe = None

    if (
        net_income is not None
        and equity is not None
        and equity != 0
    ):
        roe = (
            net_income / equity
        )

    debt_to_equity = None

    if (
        debt is not None
        and equity is not None
        and equity != 0
    ):
        debt_to_equity = (
            debt / equity
        )

    # ---------------------------------------------------------------
    # Yahoo-specific metrics unavailable from this endpoint
    # ---------------------------------------------------------------

    unavailable.extend(
        [
            "revenue_growth",
            "operating_margin",
            "pe_ratio",
            "market_cap",
            "earnings_growth",
        ]
    )

    values = {
        "revenue_ttm": revenue,
        "revenue_growth": None,
        "net_income_ttm": net_income,
        "eps_ttm": eps,
        "profit_margin": profit_margin,
        "operating_margin": None,
        "roe": roe,
        "debt_to_equity": debt_to_equity,
        "pe_ratio": None,
        "market_cap": None,
        "free_cash_flow": free_cash_flow,
        "earnings_growth": None,
    }

    result = Fundamentals(
        ticker=ticker,
        unavailable_fields=list(
            dict.fromkeys(unavailable)
        ),
        **values,
    )

    cache.set(
        key,
        result,
        ttl_seconds=3600,
    )

    return result