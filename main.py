
import time
import subprocess

# Strategy scripts to run in sequence
strategies = [
    "btc_strategy.py",
    "eth_strategy.py",
    "shib_strategy.py",
    "pepe_strategy.py",
    "sol_strategy.py"
]

def run_strategy(script_name):
    print(f"\n🌀 Running: {script_name}")
    try:
        result = subprocess.run(["python", script_name], capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(f"⚠️ Error in {script_name}:\n{result.stderr}")
    except Exception as e:
        print(f"❌ Failed to run {script_name}: {e}")

print("🚀 Starting automated crypto bot loop...")

while True:
    for script in strategies:
        run_strategy(script)
    print("\n⏳ Sleeping for 15 minutes before next run...")
    time.sleep(900)  # Sleep for 15 minutes
