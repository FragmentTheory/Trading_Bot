import os
import pandas as pd
from dotenv import load_dotenv
from alpaca_trade_api.rest import REST, TimeFrame
from ta.trend import EMAIndicator
from log_trade import log_trade

load_dotenv()

api = REST(
    os.getenv("APCA_API_KEY_ID"),
    os.getenv("APCA_API_SECRET_KEY"),
    os.getenv("APCA_API_BASE_URL")
)

symbol = "SOL/USD"
allocation_pct = 0.05  # 5% of buying power

print(f"\n📊 Fetching 15-minute historical data for {symbol}...\n")
bars = api.get_crypto_bars(symbol, TimeFrame.Minute, limit=1000).df
sol = bars.copy()

# Resample to 15-minute candles
sol = sol.resample("15min").agg({
    "open": "first",
    "high": "max",
    "low": "min",
    "close": "last",
    "volume": "sum"
}).dropna()

# Calculate EMA9 and green/red candles
sol["EMA9"] = EMAIndicator(sol["close"], window=9).ema_indicator()
sol["Candle"] = sol["close"] > sol["open"]

# Get last three candles
latest = sol.iloc[-1]
prev = sol.iloc[-2]
prev2 = sol.iloc[-3]

print(f"📌 Latest SOL Summary:")
print(f"• Close Price: {latest['close']:.2f}")
print(f"• EMA9:        {latest['EMA9']:.2f} (was {prev['EMA9']:.2f})")

account = api.get_account()
buying_power = float(account.buying_power)
trade_amount = buying_power * allocation_pct

# === SELL LOGIC ===
if not latest["Candle"] or latest["EMA9"] < prev["EMA9"]:
    print("\n🔴 SELL SIGNAL for SOL/USD!")
    print("Reason: Red candle or EMA9 turning downward (momentum fading).")
    print("→ Checking SOL position before selling...")

    try:
        positions = api.list_positions()
        sol_position = next((p for p in positions if p.symbol == symbol), None)

        if sol_position:
            qty = sol_position.qty
            print(f"→ Selling full SOL position: {qty} at market price.")

            api.submit_order(
                symbol=symbol,
                qty=qty,
                side="sell",
                type="market",
                time_in_force="gtc"
            )
            print(f"✅ Sell order submitted: Sold {qty} SOL.")
            log_trade(symbol, "sell", "sol_daytrade", latest["close"], qty)
        else:
            print("ℹ️ No SOL currently held.")
    except Exception as e:
        print("❌ Failed to submit sell order:", e)

# === BUY LOGIC ===
elif latest["Candle"] and prev["Candle"] and prev2["Candle"] and latest["EMA9"] > prev["EMA9"]:
    print("\n🟢 BUY SIGNAL for SOL/USD!")
    print("Reason: 3 green candles + EMA9 rising (momentum confirmed).")
    print(f"→ Available buying power: ${buying_power:.2f}")
    print(f"→ Allocating 5% (${trade_amount:.2f}) to SOL...")

    try:
        positions = api.list_positions()
        sol_position = next((p for p in positions if p.symbol == symbol), None)
        if sol_position:
            print("⚠️ Already holding SOL. Skipping duplicate buy.")
        elif trade_amount >= 1.00:
            api.submit_order(
                symbol=symbol,
                notional=trade_amount,
                side="buy",
                type="market",
                time_in_force="gtc"
            )
            print(f"✅ Buy order submitted: ${trade_amount:.2f} worth of SOL purchased.")
            log_trade(symbol, "buy", "sol_daytrade", latest["close"], trade_amount)
        else:
            print("⚠️ Trade amount too small to execute. Skipping buy.")
    except Exception as e:
        print("❌ Failed to submit buy order:", e)

# === NO SIGNAL ===
else:
    print("\n🕵️ No SOL trading signal at this time.")
    print("Waiting for better conditions.")

print("\n✅ SOL strategy check complete.\n")
