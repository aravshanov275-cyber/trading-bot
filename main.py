import requests
import time

TOKEN = "BOT_TOKEN"
CHAT_ID = "-1003745385954"

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": text
    }
    requests.post(url, data=data)

while True:
    send_message("Bot ishlayapti ✅")
    time.sleep(3600)
