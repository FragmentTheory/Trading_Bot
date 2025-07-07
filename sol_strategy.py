import os
import pandas as pd
from dotenv import load_dotenv
from alpaca_trade_api.rest import REST, TimeFrame
from log_trade import log_trade
import ta

load_dotenv()

api = REST(
    os.getenv("APCA_API_KEY_ID"),
    os.getenv("APCA_API_SECRET_KEY"),
    os.getenv("APCA_API_BASE_URL")
)

# === FETCH 15-MINUTE SOL DATA ===
print("\n📊 Fetching 15-minute historical data for SOL/USD...")
bars = api.get_crypto_bars("SOL/USD", TimeFrame.Minute, limit=1000).df
sol = bars.copy()

# Resample to 15-minute candles
sol = sol.resample("15min").agg({
    "open": "first",
    "high": "max",
    "low": "min",
    "close": "last",
    "volume": "sum"
}).dropna()

# === CALCULATE EMA ===
sol["EMA9"] = ta.trend.ema_indicator(sol["close"], window=9)

# Get the latest 4 candles
latest = sol.iloc[-1]
prev1 = sol.iloc[-2]
prev2 = sol.iloc[-3]
prev3 = sol.iloc[-4]

# EMA slope check
ema_now = latest["EMA9"]
ema_prev = sol["EMA9"].iloc[-2]

print("\n📌 Latest SOL Summary:")
print(f"• Close Price: {latest['close']}")
print(f"• EMA9:        {ema_now:.2f} (was {ema_prev:.2f})")

# === BUY LOGIC ===
if (
    latest["close"] > latest["open"] and
    prev1["close"] > prev1["open"] and
    prev2["close"] > prev2["open"] and
    ema_now > ema_prev
):
    print("\n🟢 BUY SIGNAL for SOL/USD!")
    print("Reason: 3 green candles + EMA9 rising (momentum confirmed).")
    print("→ Placing market buy order for $10 of SOL...")

    try:
        api.submit_order(
            symbol="SOL/USD",
            notional=10,
            side="buy",
            type="market",
            time_in_force="gtc"
        )
        print("✅ Buy order submitted: $10 worth of SOL purchased.")
        log_trade("SOL/USD", "buy", "sol_momentum_trend", latest["close"], 10)
    except Exception as e:
        print("❌ Failed to buy SOL:", e)

# === SELL LOGIC ===
elif latest["close"] < latest["open"] or ema_now < ema_prev:
    print("\n🔴 SELL SIGNAL for SOL/USD!")
    print("Reason: Red candle or EMA9 turning downward (momentum fading).")
    print("→ Checking SOL position before selling...")

    try:
        positions = api.list_positions()
        sol_position = next((p for p in positions if p.symbol == "SOL/USD"), None)

        if sol_position:
            qty = sol_position.qty
            print(f"→ Selling entire SOL position: {qty} SOL.")
            api.submit_order(
                symbol="SOL/USD",
                qty=qty,
                side="sell",
                type="market",
                time_in_force="gtc"
            )
            print(f"✅ Sell order submitted: Sold {qty} SOL.")
            log_trade("SOL/USD", "sell", "sol_momentum_trend", latest["close"], qty)
        else:
            print("ℹ️ No SOL currently held.")
    except Exception as e:
        print("❌ Failed to sell SOL:", e)

# === NO SIGNAL ===
else:
    print("\n🕵️ No SOL trading signal at this time.")
    print("Waiting for momentum or trend confirmation.")

print("\n✅ SOL strategy check complete.\n")
