# Ruh_Eye.py

from flask import Flask
import threading
import time

app = Flask(__name__)

@app.route("/health")
def health_check():
    return "OK", 200

# Bot বা Cron job function
def run_bot():
    while True:
        print("Bot running...")
        time.sleep(60)  # Demo purpose

# Bot আলাদা thread এ চালান
bot_thread = threading.Thread(target=run_bot)
bot_thread.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
