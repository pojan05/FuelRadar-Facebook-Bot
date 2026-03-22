import os
import json
import time
import requests
from datetime import datetime
import pytz
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ตั้งค่า Facebook API (ดึงจาก GitHub Secrets)
FB_PAGE_ID = os.environ.get("FB_PAGE_ID")
FB_ACCESS_TOKEN = os.environ.get("FB_ACCESS_TOKEN")
DATA_URL = "https://script.google.com/macros/s/AKfycbxflVoeKNYwHDhMFqoZkeKUR0AG5GI4jwfqefySHxXa6MnDdBn7NbTkT4NjN-WbgYQrMQ/exec"

def post_to_facebook(text):
    """ฟังก์ชันสำหรับโพสต์ข้อความลง Facebook Page Feed"""
    url = f"https://graph.facebook.com/{FB_PAGE_ID}/feed"
    payload = {
        'message': text,
        'access_token': FB_ACCESS_TOKEN
    }
    try:
        res = requests.post(url, data=payload)
        res.raise_for_status()
        print("✅ โพสต์ลง Facebook Page สำเร็จ")
    except Exception as e:
        print(f"❌ โพสต์ Facebook ไม่สำเร็จ: {e}")

def get_fuel_data():
    """ฟังก์ชันดึงข้อมูลจากหน้าเว็บ (รักษาโครงสร้างมุด Iframe 2 ชั้นเดิม)"""
    print("🔍 [FB Bot] เริ่มต้นดึงข้อมูล...")
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36')
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    stations = {}
    
    try:
        driver.get(DATA_URL)
        # มุดเข้า Sandbox Frame
        iframe1 = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, "sandboxFrame")))
        driver.switch_to.frame(iframe1)
        # มุดเข้า Content Iframe
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
        driver.switch_to.frame(driver.find_element(By.TAG_NAME, "iframe"))
        # รอข้อมูลตาราง
        WebDriverWait(driver, 40).until(EC.presence_of_element_located((By.ID, "tbody-dash")))
        time.sleep(3)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        rows = soup.find('tbody', id='tbody-dash').find_all('tr')
        
        for tr in rows:
            tds = tr.find_all('td')
            if len(tds) >= 9:
                district = tds[8].text.strip()
                if "อินทร์บุรี" in district:
                    name = tds[0].text.strip()
                    stations[name] = {
                        "ดีเซล": tds[1].text.strip(), "G95": tds[2].text.strip(),
                        "G91": tds[3].text.strip(), "E20": tds[4].text.strip(),
                        "รถขนส่ง": tds[5].text.strip().replace('\n', ' '),
                        "อัปเดตล่าสุด": tds[6].text.strip()
                    }
    finally:
        driver.quit()
    return stations

def main():
    tz = pytz.timezone('Asia/Bangkok')
    now = datetime.now(tz)
    thai_now_str = now.strftime('%d/%m/%Y %H:%M:%S')
    
    # เงื่อนไขรายงานสรุป 6 โมงเช้า (06:00 - 06:15 น.)
    is_morning_report = (now.hour == 6 and 0 <= now.minute <= 15)

    current_data = get_fuel_data()
    if not current_data: return
        
    old_data = {}
    if os.path.exists("data_fb.json"):
        with open("data_fb.json", "r", encoding="utf-8") as f:
            try: old_data = json.load(f)
            except: old_data = {}
            
    updates = []
    for station, d in current_data.items():
        if is_morning_report or station not in old_data or current_data[station] != old_data[station]:
            def icon(s): return "✅ มี" if "มี" in s else "❌ หมด" if "หมด" in s else "⚪ N/A"
            
            msg = f"📍 {station}\n"
            msg += f"⛽ ดีเซล: {icon(d['ดีเซล'])} | G95: {icon(d['G95'])}\n"
            msg += f"⛽ G91: {icon(d['G91'])} | E20: {icon(d['E20'])}\n"
            msg += f"🚚 รถขนส่ง: {d['รถขนส่ง']}\n"
            msg += f"🕒 ข้อมูลหน้าเว็บอัปเดตเมื่อ: {d['อัปเดตล่าสุด']}"
            updates.append(msg)
            
    if updates:
        header = "📢 [สรุปประจำวัน] รายงานสถานะน้ำมันอินทร์บุรี" if is_morning_report else "🔔 [อัปเดต] พบการเปลี่ยนแปลงสถานะน้ำมัน"
        footer = f"\n\n📊 ตรวจสอบอัตโนมัติเมื่อ: {thai_now_str}\n#น้ำมันอินทร์บุรี #FuelRadar"
        
        # แยกโพสต์ 1 ปั๊มต่อ 1 โพสต์ หรือจะรวมกันก็ได้ (ในที่นี้แนะนำให้รวมเป็นชุดเพื่อไม่ให้โพสต์ถี่เกินไป)
        for i in range(0, len(updates), 4): # รวม 4 ปั๊มต่อ 1 โพสต์
            chunk = updates[i:i+4]
            full_post = f"{header}\n\n" + "\n\n------------------\n\n".join(chunk) + footer
            post_to_facebook(full_post)
            time.sleep(5) # เว้นระยะการโพสต์ป้องกัน Spam
            
        with open("data_fb.json", "w", encoding="utf-8") as f:
            json.dump(current_data, f, ensure_ascii=False, indent=2)
    else:
        print("✅ ข้อมูลบน Facebook ยังเป็นปัจจุบัน")

if __name__ == "__main__":
    main()
