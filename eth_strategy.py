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

# === FETCH 15-MINUTE ETH DATA ===
print("\n📊 Fetching 15-minute historical data for ETH/USD...")
bars = api.get_crypto_bars("ETH/USD", TimeFrame.Minute, limit=1000).df
eth = bars.copy()

# Resample to 15-minute candles
eth = eth.resample("15min").agg({
    "open": "first",
    "high": "max",
    "low": "min",
    "close": "last",
    "volume": "sum"
}).dropna()

# === CALCULATE INDICATORS ===
eth["EMA9"] = ta.trend.ema_indicator(eth["close"], window=9)
eth["EMA21"] = ta.trend.ema_indicator(eth["close"], window=21)
eth["EMA50"] = ta.trend.ema_indicator(eth["close"], window=50)

# Pull latest data point
latest = eth.iloc[-1]

print("\n📌 Latest ETH Summary:")
print(f"• Close Price: ${latest['close']:.2f}")
print(f"• EMA9:        ${latest['EMA9']:.2f}")
print(f"• EMA21:       ${latest['EMA21']:.2f}")
print(f"• EMA50:       ${latest['EMA50']:.2f}")

# === BUY LOGIC ===
if latest["EMA9"] > latest["EMA21"] > latest["EMA50"]:
    print("\n🟢 BUY SIGNAL TRIGGERED!")
    print("Reason: EMA9 > EMA21 > EMA50 — indicating a strong uptrend.")
    print(f"→ Preparing to place a market buy order for ${amount_to_spend:.2f} of ETH...")

    try:
        positions = api.list_positions()
        already_holding = any(p.symbol == "ETH/USD" for p in positions)

        if already_holding:
            print("⛔ ETH already held. Skipping duplicate buy.")
        else:
            api.submit_order(
                symbol="ETH/USD",
                notional=amount_to_spend,
                side="buy",
                type="market",
                time_in_force="gtc"
            )
            print(f"✅ Buy order submitted: ${amount_to_spend:.2f} of ETH purchased.")
            log_trade("ETH/USD", "buy", "eth_semi_risky", latest["close"], amount_to_spend)
    except Exception as e:
        print("❌ Failed to submit buy order:", e)

# === SELL LOGIC ===
elif latest["EMA9"] < latest["EMA21"]:
    print("\n🔴 SELL SIGNAL TRIGGERED!")
    print("Reason: EMA9 has dropped below EMA21 — trend may be reversing.")
    print("→ Checking ETH position before placing sell order...")

    try:
        positions = api.list_positions()
        eth_position = next((p for p in positions if p.symbol == "ETH/USD"), None)

        if eth_position:
            qty = eth_position.qty
            print(f"→ Selling entire ETH position: {qty} ETH at market price.")

            api.submit_order(
                symbol="ETH/USD",
                qty=qty,
                side="sell",
                type="market",
                time_in_force="gtc"
            )
            print(f"✅ Sell order submitted: Sold {qty} ETH.")
            log_trade("ETH/USD", "sell", "eth_semi_risky", latest["close"], qty)
        else:
            print("ℹ️ No ETH currently held. Nothing to sell.")
    except Exception as e:
        print("❌ Failed to submit sell order:", e)

# === NO SIGNAL ===
else:
    print("\n🕵️ No ETH signal at this time.")
    print("EMA alignment not strong enough to buy or reverse enough to sell.")

print("\n✅ ETH strategy check complete.\n")
