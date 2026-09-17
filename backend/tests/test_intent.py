from app.agents.intent import Intent, detect_intent, extract_tickers


def test_extract_single_ticker():
    assert extract_tickers("Analyze NVDA.") == ["NVDA"]


def test_extract_multiple_tickers_ignores_stopwords():
    tickers = extract_tickers("Compare NVIDIA vs AMD and also check AAPL")
    assert "AMD" in tickers
    assert "AAPL" in tickers
    assert "VS" not in tickers
    assert "AND" not in tickers


def test_intent_technical_analysis():
    assert detect_intent("Analyze the technical indicators for AAPL") == Intent.TECHNICAL_ANALYSIS


def test_intent_sec_analysis():
    assert detect_intent("What are the risks in NVDA's latest 10-K?") == Intent.SEC_ANALYSIS


def test_intent_comparison():
    assert detect_intent("Compare NVDA vs AMD") == Intent.COMPANY_COMPARISON


def test_intent_general_question_with_no_ticker():
    assert detect_intent("What is a P/E ratio?") == Intent.GENERAL_FINANCIAL_QUESTION


def test_intent_defaults_to_stock_analysis_with_bare_ticker():
    assert detect_intent("Give me a detailed analysis of NVDA") == Intent.STOCK_ANALYSIS
