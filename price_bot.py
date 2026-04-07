import os
import json
import requests
from datetime import datetime
import pytz

MAKE_WEBHOOK_URL = os.environ.get("MAKE_WEBHOOK_URL")
PRICE_FILE = "last_price.json"

def get_current_singapore_pegged_price():
    # โค้ดสมมติสำหรับการดึง API ราคาน้ำมันของคุณ 
    # (คุณต้องใส่ URL API ที่คุณใช้ดึงราคา ณ ปัจจุบันตรงนี้)
    # api_url = "https://your-realtime-price-api.com/latest"
    # response = requests.get(api_url).json()
    # return response['prices']
    pass

def post_to_make(text):
    if not MAKE_WEBHOOK_URL:
        return
    requests.post(MAKE_WEBHOOK_URL, json={'message': text})

def main():
    # 1. ดึงราคาแบบเรียลไทม์
    current_prices = get_current_singapore_pegged_price()
    if not current_prices:
        return

    # 2. โหลดราคาเก่าที่เคยเซฟไว้มาเทียบ
    old_prices = {}
    if os.path.exists(PRICE_FILE):
        with open(PRICE_FILE, "r", encoding="utf-8") as f:
            try: old_prices = json.load(f)
            except: old_prices = {}

    # 3. เทียบราคาว่ามีการเปลี่ยนแปลงหรือไม่
    if current_prices != old_prices:
        # ถ้าราคาไม่ตรงกัน แสดงว่ามีการอัปเดต!
        tz = pytz.timezone('Asia/Bangkok')
        now_str = datetime.now(tz).strftime('%d/%m/%Y %H:%M:%S')
        
        # จัดรูปแบบข้อความ
        msg = f"🚨 [ด่วน] อัปเดตราคาน้ำมันล่าสุด!\n\n"
        for fuel, price in current_prices.items():
            msg += f"⛽ {fuel}: {price} บาท\n"
        msg += f"\n🕒 อัปเดตเวลา: {now_str}\n#ราคาน้ำมันเรียลไทม์"

        # ส่งไป Make.com เพื่อโพสต์ Facebook
        post_to_make(msg)
        print("ส่งแจ้งเตือนราคาใหม่เรียบร้อย!")

        # เซฟราคาใหม่ทับลงไป
        with open(PRICE_FILE, "w", encoding="utf-8") as f:
            json.dump(current_prices, f, ensure_ascii=False, indent=2)
    else:
        print("ราคายังคงที่ ไม่มีการแจ้งเตือน")

if __name__ == "__main__":
    main()
