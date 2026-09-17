from app.tools.stock_data import (
    get_stock_price,
    get_historical_prices,
    get_company_profile,
)

ticker = "AAPL"

print("\n--- PRICE ---")
print(get_stock_price(ticker))

print("\n--- HISTORY ---")
history = get_historical_prices(ticker, "1y", "1d")
print("Points:", len(history.points))
print("First:", history.points[0])
print("Last:", history.points[-1])

print("\n--- PROFILE ---")
print(get_company_profile(ticker))