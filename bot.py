import os
from dotenv import load_dotenv
from alpaca_trade_api.rest import REST

load_dotenv(dotenv_path=".env")  # force it to read the file

print("Loaded key:", os.getenv("APCA_API_KEY_ID"))  # debug print


# Load your API keys from the .env file
load_dotenv()

# Connect to Alpaca
api = REST(
    os.getenv("APCA_API_KEY_ID"),
    os.getenv("APCA_API_SECRET_KEY"),
    os.getenv("APCA_API_BASE_URL")
)

# Check your account status
account = api.get_account()
print("Account status:", account.status)

# Optional: Submit a paper trade
clock = api.get_clock()
if clock.is_open:
    api.submit_order(
        symbol="AAPL",
        qty=1,
        side="buy",
        type="market",
        time_in_force="gtc"
    )
    print("Submitted market order to buy 1 share of AAPL")
else:
    print("Market is currently closed")
