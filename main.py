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

# ดึงค่าจาก GitHub Secrets
FB_PAGE_ID = os.environ.get("FB_PAGE_ID")
FB_ACCESS_TOKEN = os.environ.get("FB_ACCESS_TOKEN")
DATA_URL = "https://script.google.com/macros/s/AKfycbxflVoeKNYwHDhMFqoZkeKUR0AG5GI4jwfqefySHxXa6MnDdBn7NbTkT4NjN-WbgYQrMQ/exec"

def post_to_facebook(text):
    """ฟังก์ชันสำหรับโพสต์ลง Facebook Page"""
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
        if hasattr(res, 'text'): print(f"📝 รายละเอียดจาก Facebook: {res.text}")

def get_fuel_data():
    """ฟังก์ชันดึงข้อมูลน้ำมัน (เน้นความแม่นยำด้วยการมุด 2 ชั้น)"""
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
        
        # มุดเข้า Sandbox ชั้นที่ 1
        iframe1 = WebDriverWait(driver, 40).until(EC.presence_of_element_located((By.ID, "sandboxFrame")))
        driver.switch_to.frame(iframe1)
        
        # มุดเข้า Content ชั้นที่ 2
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
        driver.switch_to.frame(driver.find_element(By.TAG_NAME, "iframe"))
        
        # รอโหลดตารางข้อมูล
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
        print(f"📊 ดึงข้อมูลสำเร็จ! พบ {len(stations)} สถานีในอินทร์บุรี")
    except Exception as e:
        print(f"🧨 เกิดข้อผิดพลาดในการดึงข้อมูล: {e}")
    finally:
        if driver: driver.quit()
    return stations

def main():
    tz = pytz.timezone('Asia/Bangkok')
    now = datetime.now(tz)
    thai_now_str = now.strftime('%d/%m/%Y %H:%M:%S')
    
    # เงื่อนไขรายงานสรุป 6 โมงเช้า (06:00 - 06:15 น.)
    is_morning_report = (now.hour == 6 and 0 <= now.minute <= 15)

    current_data = get_fuel_data()
    if not current_data:
        print("⚠️ ดึงข้อมูลล้มเหลว ข้ามการโพสต์")
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
            msg = f"📍 {station}\n⛽ ดีเซล:{icon(d['ดีเซล'])} | G95:{icon(d['G95'])}\n⛽ G91:{icon(d['G91'])} | E20:{icon(d['E20'])}\n🚚 รถขนส่ง: {d['รถขนส่ง']}\n🕒 อัปเดตล่าสุด: {d['อัปเดตล่าสุด']}"
            updates.append(msg)
            
    if updates:
        print(f"🔔 มีข้อมูลที่ต้องอัปเดต {len(updates)} แห่ง...")
        header = "📢 [รายงานสรุปประจำวัน] น้ำมันอินทร์บุรี" if is_morning_report else "🔔 [อัปเดตสถานะน้ำมัน] อินทร์บุรี"
        footer = f"\n\n📊 ตรวจสอบอัตโนมัติเมื่อ: {thai_now_str}\n#น้ำมันอินทร์บุรี #อินทร์บุรีรอดมั้ย"
        
        # หั่นโพสต์ละ 4 ปั๊มเพื่อความสวยงาม
        for i in range(0, len(updates), 4):
            chunk = updates[i:i+4]
            full_post = f"{header}\n\n" + "\n\n---\n\n".join(chunk) + footer
            post_to_facebook(full_post)
            time.sleep(5)
            
        with open("data_fb.json", "w", encoding="utf-8") as f:
            json.dump(current_data, f, ensure_ascii=False, indent=2)
    else:
        print("✅ ข้อมูลยังเป็นปัจจุบัน ไม่ต้องโพสต์ใหม่")

if __name__ == "__main__":
    main()
