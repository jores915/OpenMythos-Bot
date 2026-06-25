import requests
import time

class TelegramNotifier:
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id

    def send(self, message):
        for attempt in range(3):
            try:
                requests.post(
                    f"https://api.telegram.org/bot{self.token}/sendMessage",
                    json={"chat_id": self.chat_id, "text": message},
                    timeout=10
                )
                return
            except Exception as e:
                if attempt == 2:
                    print(f"Telegram error (chat {self.chat_id}): {e}")
                time.sleep(2)
