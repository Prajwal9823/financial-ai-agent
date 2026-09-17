# Financial AI Agent — Market Insights

An agentic financial research platform that allows users to ask financial questions in natural language and receive structured, source-grounded market insights.

Instead of simply sending a question to an LLM, the system first determines what kind of financial information is required, retrieves the relevant real-world data, performs numerical calculations using Python, and then uses an LLM only for the final explanation.

### Example queries

- `Analyze AAPL`
- `Why did NVDA move recently?`
- `Compare NVDA vs AMD`
- `What are the risks in Apple's latest 10-K?`
- `Show me the technical indicators for MSFT`
- `What is the current price of Apple?`
- `What is the recent news sentiment for NVIDIA?`

The system is designed as a **research and informational tool**, not as a trading or investment-advisory system.

---

## Features

### 📈 Market Data

- Current stock price
- Daily price change
- Daily percentage change
- Historical OHLCV data
- Company profile
- Market information

Market data is retrieved using free data sources and normalized before being returned to the frontend.

---

### 📊 Technical Analysis

Technical indicators are calculated directly using Python, pandas, and NumPy.

Currently implemented:

- SMA 50
- SMA 200
- EMA 20
- MACD
- MACD Signal
- MACD Trend
- RSI 14
- Stochastic Oscillator
- Bollinger Bands
- Historical Volatility
- Maximum Drawdown
- 1-Day Return
- 1-Week Return
- 1-Month Return
- 3-Month Return
- 1-Year Return

All calculations are performed by Python rather than the LLM.

For example:

```text
SMA 50       → Python/pandas
RSI 14       → Python/pandas
MACD         → Python/pandas
Volatility   → Python/NumPy
Returns      → Python arithmetic