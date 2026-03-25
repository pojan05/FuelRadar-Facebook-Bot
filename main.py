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

# รับ URL ของ Make.com จาก GitHub Secrets
MAKE_WEBHOOK_URL = os.environ.get("MAKE_WEBHOOK_URL")
DATA_URL = "https://script.google.com/macros/s/AKfycbxflVoeKNYwHDhMFqoZkeKUR0AG5GI4jwfqefySHxXa6MnDdBn7NbTkT4NjN-WbgYQrMQ/exec"

def post_to_make(text):
    """ส่งข้อความไปให้ Make.com เพื่อนำไปโพสต์ลง Facebook"""
    if not MAKE_WEBHOOK_URL:
        print("❌ ไม่พบ MAKE_WEBHOOK_URL")
        return
        
    payload = {'message': text}
    try:
        res = requests.post(MAKE_WEBHOOK_URL, json=payload)
        res.raise_for_status()
        print("✅ ส่งข้อมูลให้ Make.com สำเร็จ!")
    except Exception as e:
        print(f"❌ ส่งข้อมูลไป Make.com ไม่สำเร็จ: {e}")

def get_fuel_data():
    print("🔍 [FB Bot] เริ่มต้นดึงข้อมูล...")
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    
    stations = {}
    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(DATA_URL)
        
        iframe1 = WebDriverWait(driver, 40).until(EC.presence_of_element_located((By.ID, "sandboxFrame")))
        driver.switch_to.frame(iframe1)
        
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
        driver.switch_to.frame(driver.find_element(By.TAG_NAME, "iframe"))
        
        WebDriverWait(driver, 40).until(EC.presence_of_element_located((By.ID, "tbody-dash")))
        time.sleep(5)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        rows = soup.find('tbody', id='tbody-dash').find_all('tr')
        
        for tr in rows:
            tds = tr.find_all('td')
            if len(tds) >= 9:
                district = tds[8].text.strip()
                if "อินทร์บุรี" in district:
                    name = tds[0].text.strip()
                    stations[name] = {
                        "ดีเซล": tds[1].text.strip(),
                        "G95": tds[2].text.strip(),
                        "G91": tds[3].text.strip(),
                        "E20": tds[4].text.strip(),
                        "รถขนส่ง": tds[5].text.strip().replace('\n', ' '),
                        "อัปเดตล่าสุด": tds[6].text.strip()
                    }
        print(f"📊 ดึงข้อมูลสำเร็จ! พบ {len(stations)} สถานี")
    except Exception as e:
        print(f"🧨 เกิดข้อผิดพลาดในการดึงข้อมูล: {e}")
    finally:
        if driver: driver.quit()
    return stations

def main():
    tz = pytz.timezone('Asia/Bangkok')
    now = datetime.now(tz)
    thai_now_str = now.strftime('%d/%m/%Y %H:%M:%S')
    
    is_morning_report = (now.hour == 6 and 0 <= now.minute <= 15)

    current_data = get_fuel_data()
    if not current_data:
        return
        
    old_data = {}
    if os.path.exists("data_fb.json"):
        with open("data_fb.json", "r", encoding="utf-8") as f:
            try: old_data = json.load(f)
            except: old_data = {}
            
    updates = []
    for station, d in current_data.items():
        if is_morning_report or station not in old_data or current_data[station] != old_data[station]:
            def icon(s): return "✅" if "มี" in s else "❌" if "หมด" in s else "⚪"
            msg = f"📍 {station}\n⛽ ดีเซล:{icon(d['ดีเซล'])} | G95:{icon(d['G95'])}\n⛽ G91:{icon(d['G91'])} | E20:{icon(d['E20'])}\n🚚 รถขนส่ง: {d['รถขนส่ง']}\n🕒 อัปเดต: {d['อัปเดตล่าสุด']}"
            updates.append(msg)
            
    if updates:
        print(f"🔔 มีข้อมูลอัปเดต {len(updates)} แห่ง ส่งให้ Make.com...")
        header = "📢 [รายงานสรุปประจำวัน] น้ำมันอินทร์บุรี" if is_morning_report else "🔔 [อัปเดตสถานะน้ำมัน] อินทร์บุรี"
        footer = f"\n\n📊 ตรวจสอบอัตโนมัติเมื่อ: {thai_now_str}\n#น้ำมันอินทร์บุรี #อินทร์บุรีรอดมั้ย"
        
        # จุดที่แก้: รวมข้อมูลทั้งหมดเป็น 1 โพสต์ยาวๆ
        full_post = f"{header}\n\n" + "\n\n---\n\n".join(updates) + footer
        post_to_make(full_post)
            
        with open("data_fb.json", "w", encoding="utf-8") as f:
            json.dump(current_data, f, ensure_ascii=False, indent=2)
    else:
        print("✅ ข้อมูลยังเป็นปัจจุบัน")

if __name__ == "__main__":
    main()
