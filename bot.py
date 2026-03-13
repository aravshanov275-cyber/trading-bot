import requests
import time

TOKEN = "8309912114:AAGITQHtT41b30khIr0iHYB4D6jaZRex6MQ"
CHAT_ID = "-1003745385954"

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": text
    }
    requests.post(url, data=data)

send_message("✅ Bot ishga tushdi")

while True:
    time.sleep(3600)
