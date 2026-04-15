import requests
import os
import time

class TelegramNotifier:
    """Module quản lý thông báo qua Telegram Bot"""
    def __init__(self):
        # Thông tin cấu hình của bạn
        self.token = "8271641359:AAGTeHF6brf-xWhvZ_bsaY4HwYrM0ogq0xo"
        
        # BẠN CẦN ĐIỀN CHAT ID VÀO ĐÂY (Lấy từ @userinfobot)
        self.chat_id = "8578951342" 
        
        self.last_alert_time = 0
        self.cooldown = 0 # Đã có timer 10s riêng cho từng loại trong Run.py
        
    def can_send(self):
        """Kiểm tra xem đã hết thời gian chờ (cooldown) chưa"""
        return (time.time() - self.last_alert_time) > self.cooldown

    def send_text(self, message):
        """Gửi tin nhắn văn bản"""
        if not self.can_send(): return
        
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        try:
            requests.post(url, data=payload)
            self.last_alert_time = time.time()
        except Exception as e:
            print(f"Lỗi gửi Telegram: {e}")

    def send_photo(self, photo_path, caption):
        """Gửi ảnh chụp từ camera kèm nội dung cảnh báo"""
        if not self.can_send(): return
        
        url = f"https://api.telegram.org/bot{self.token}/sendPhoto"
        try:
            with open(photo_path, "rb") as photo:
                payload = {
                    "chat_id": self.chat_id,
                    "caption": caption,
                    "parse_mode": "HTML"
                }
                files = {"photo": photo}
                requests.post(url, data=payload, files=files)
                self.last_alert_time = time.time()
                print("--- ĐÃ GỬI CẢNH BÁO TELEGRAM THÀNH CÔNG ---")
        except Exception as e:
            print(f"Lỗi gửi ảnh Telegram: {e}")
