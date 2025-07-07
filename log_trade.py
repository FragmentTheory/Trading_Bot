import csv
from datetime import datetime

def log_trade(symbol, side, strategy, price, amount, outcome="pending"):
    with open("trade_log.csv", mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([
            datetime.utcnow().isoformat(),
            symbol,
            side,
            strategy,
            price,
            amount,
            outcome
        ])
