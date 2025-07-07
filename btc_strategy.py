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

# === FETCH ACCOUNT INFO ===
account = api.get_account()
buying_power = float(account.cash)
percent_to_use = 0.10  # 10%
amount_to_spend = round(buying_power * percent_to_use, 2)

print(f"\n💰 Available cash: ${buying_power:.2f}")
print(f"📌 Planning to use 10% → ${amount_to_spend:.2f} for trade")

if amount_to_spend < 1:
    print("⚠️ Not enough cash to place a meaningful trade. Skipping.")
    exit()

# === FETCH 15-MINUTE BTC DATA ===
print("\n📊 Fetching 15-minute historical data for BTC/USD...")
bars = api.get_crypto_bars("BTC/USD", TimeFrame.Minute, limit=1000).df
btc = bars.copy()

# Resample to 15-minute candles
btc = btc.resample("15min").agg({
    "open": "first",
    "high": "max",
    "low": "min",
    "close": "last",
    "volume": "sum"
}).dropna()

# === CALCULATE INDICATORS ===
btc["EMA9"] = ta.trend.ema_indicator(btc["close"], window=9)
btc["EMA21"] = ta.trend.ema_indicator(btc["close"], window=21)
btc["RSI"] = ta.momentum.RSIIndicator(btc["close"], window=14).rsi()

# Pull latest data point
latest = btc.iloc[-1]

print("\n📌 Latest BTC Summary:")
print(f"• Close Price: ${latest['close']:.2f}")
print(f"• EMA9:        ${latest['EMA9']:.2f}")
print(f"• EMA21:       ${latest['EMA21']:.2f}")
print(f"• RSI:         {latest['RSI']:.2f}")

# === BUY LOGIC ===
if latest["EMA9"] > latest["EMA21"] and latest["RSI"] < 40:
    print("\n🚀 BUY SIGNAL TRIGGERED!")
    print("Reason: EMA9 crossed above EMA21 and RSI is under 40 (potential bullish reversal).")
    print(f"→ Preparing to place a market buy order for ${amount_to_spend:.2f} of BTC...")

    try:
        positions = api.list_positions()
        already_holding = any(p.symbol == "BTC/USD" for p in positions)

        if already_holding:
            print("⛔ BTC already held. Skipping duplicate buy.")
        else:
            api.submit_order(
                symbol="BTC/USD",
                notional=amount_to_spend,
                side="buy",
                type="market",
                time_in_force="gtc"
            )
            print(f"✅ Buy order submitted: ${amount_to_spend:.2f} of BTC purchased.")
            log_trade("BTC/USD", "buy", "btc_high_risk", latest["close"], amount_to_spend)
    except Exception as e:
        print("❌ Failed to submit buy order:", e)

# === SELL LOGIC ===
elif latest["EMA9"] < latest["EMA21"] and latest["RSI"] > 70:
    print("\n📉 SELL SIGNAL TRIGGERED!")
    print("Reason: EMA9 crossed below EMA21 and RSI is above 70 (overbought/reversal risk).")
    print("→ Checking BTC position before selling...")

    try:
        positions = api.list_positions()
        btc_position = next((p for p in positions if p.symbol == "BTC/USD"), None)

        if btc_position:
            qty = btc_position.qty
            print(f"→ Selling full BTC position: {qty} BTC at market price.")

            api.submit_order(
                symbol="BTC/USD",
                qty=qty,
                side="sell",
                type="market",
                time_in_force="gtc"
            )
            print(f"✅ Sell order submitted: Sold {qty} BTC.")
            log_trade("BTC/USD", "sell", "btc_high_risk", latest["close"], qty)
        else:
            print("ℹ️ No BTC position to sell.")
    except Exception as e:
        print("❌ Failed to submit sell order:", e)

# === NO SIGNAL ===
else:
    print("\n🕵️ No trading signal at this time.")
    print("Conditions not met for high-risk entry or exit.")

print("\n✅ BTC strategy check complete.\n")
