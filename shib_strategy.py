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

# === FETCH 15-MINUTE SHIB DATA ===
print("\n\U0001F4CA Fetching 15-minute historical data for SHIB/USD...")
bars = api.get_crypto_bars("SHIB/USD", TimeFrame.Minute, limit=1000).df
shib = bars.copy()

# Resample to 15-minute candles
shib = shib.resample("15min").agg({
    "open": "first",
    "high": "max",
    "low": "min",
    "close": "last",
    "volume": "sum"
}).dropna()

# === CALCULATE INDICATORS ===
shib["EMA5"] = ta.trend.ema_indicator(shib["close"], window=5)
shib["EMA20"] = ta.trend.ema_indicator(shib["close"], window=20)
shib["RSI"] = ta.momentum.RSIIndicator(shib["close"], window=14).rsi()

# Pull latest data point
latest = shib.iloc[-1]

print("\n\U0001F4CC Latest SHIB Summary:")
print(f"• Close Price: {latest['close']}")
print(f"• EMA5:        {latest['EMA5']}")
print(f"• EMA20:       {latest['EMA20']}")
print(f"• RSI:         {latest['RSI']:.2f}")

# === CALCULATE AVAILABLE FUNDS ===
account = api.get_account()
balance = float(account.cash)
allocation_pct = 0.05  # 5%
notional = round(balance * allocation_pct, 2)

print(f"\n\U0001F4B3 Account Cash: ${balance:.2f}")
print(f"✅ Allocating 5% (${notional}) for trade")

MIN_ORDER = 1.00

# === BUY LOGIC ===
buy_condition = latest["EMA5"] > latest["EMA20"] and latest["RSI"] < 35

if buy_condition:
    if notional >= MIN_ORDER:
        print("\n\U0001F7E2 BUY SIGNAL for SHIB/USD!")
        print("Reason: EMA5 > EMA20 and RSI < 35 (oversold with bullish crossover)")

        try:
            positions = api.list_positions()
            shib_position = next((p for p in positions if p.symbol == "SHIB/USD"), None)

            if shib_position:
                print("ℹ️ SHIB already held. Skipping duplicate buy.")
            else:
                print(f"\u2192 Placing market buy order for ${notional} of SHIB...")
                api.submit_order(
                    symbol="SHIB/USD",
                    notional=notional,
                    side="buy",
                    type="market",
                    time_in_force="gtc"
                )
                print(f"✅ Buy order submitted: ${notional} worth of SHIB purchased.")
                log_trade("SHIB/USD", "buy", "shib_daytrade", latest["close"], notional)
        except Exception as e:
            print("❌ Failed to submit buy order:", e)
    else:
        print(f"\n🚫 Trade skipped: ${notional} is below minimum trade amount of ${MIN_ORDER}.")

# === SELL LOGIC ===
elif latest["EMA5"] < latest["EMA20"] or latest["RSI"] > 70:
    print("\n\U0001F534 SELL SIGNAL for SHIB/USD!")
    print("Reason: EMA5 < EMA20 or RSI > 70 (overbought or bearish crossover).")
    print("→ Checking SHIB position before selling...")

    try:
        positions = api.list_positions()
        shib_position = next((p for p in positions if p.symbol == "SHIB/USD"), None)

        if shib_position:
            qty = shib_position.qty
            print(f"\u2192 Selling SHIB position: {qty} SHIB at market price.")

            api.submit_order(
                symbol="SHIB/USD",
                qty=qty,
                side="sell",
                type="market",
                time_in_force="gtc"
            )
            print(f"✅ Sell order submitted: Sold {qty} SHIB.")
            log_trade("SHIB/USD", "sell", "shib_daytrade", latest["close"], qty)
        else:
            print("ℹ️ No SHIB currently held.")
    except Exception as e:
        print("❌ Failed to submit sell order:", e)

# === NO SIGNAL ===
else:
    print("\n\U0001F575️ No SHIB trading signal at this time.")
    print("Waiting for EMA crossover and volume confirmation or reversal.")

print("\n✅ SHIB strategy check complete.")
