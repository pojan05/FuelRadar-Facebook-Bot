import os
import json
import time
import requests
import base64
from io import BytesIO
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

# นำเข้าไลบรารีสำหรับวาดรูปและ AI
from PIL import Image, ImageDraw, ImageFont
import google.generativeai as genai

# รับตัวแปรจาก GitHub Secrets
MAKE_WEBHOOK_URL = os.environ.get("MAKE_WEBHOOK_URL")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
DATA_URL = "https://script.google.com/macros/s/AKfycbxflVoeKNYwHDhMFqoZkeKUR0AG5GI4jwfqefySHxXa6MnDdBn7NbTkT4NjN-WbgYQrMQ/exec"

def post_to_make(caption, image_b64):
    """ส่งแคปชั่นและรูปภาพ (Base64) ไปให้ Make.com"""
    if not MAKE_WEBHOOK_URL:
        print("❌ ไม่พบ MAKE_WEBHOOK_URL")
        return
        
    payload = {
        'caption': caption,
        'image_base64': image_b64
    }
    try:
        res = requests.post(MAKE_WEBHOOK_URL, json=payload)
        res.raise_for_status()
        print("✅ ส่งข้อมูลแคปชั่นและรูปภาพให้ Make.com สำเร็จ!")
    except Exception as e:
        print(f"❌ ส่งข้อมูลไป Make.com ไม่สำเร็จ: {e}")

def generate_ai_caption(fuel_data_text):
    """ใช้ Gemini สร้างแคปชั่น Facebook สไตล์ Alieninburi"""
    if not GEMINI_API_KEY:
        print("⚠️ ไม่พบ GEMINI_API_KEY จะใช้ข้อความมาตรฐานแทน")
        return f"📢 สรุปสถานะน้ำมันอินทร์บุรีล่าสุด\n\n{fuel_data_text}\n\n#น้ำมันอินทร์บุรี #Alieninburi"
    
    try:
        print("🤖 กำลังให้ AI ช่วยคิดแคปชั่น...")
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
        ในฐานะกระบอกเสียงของโปรเจกต์ 'Alieninburi' ช่วยเขียนแคปชั่น Facebook สั้นๆ น่ารัก เป็นกันเอง 
        สรุปสถานการณ์น้ำมันในอินทร์บุรีจากข้อมูลดิบนี้:
        {fuel_data_text}
        
        ข้อกำหนด:
        - โทนเป็นมิตร ให้กำลังใจชาวบ้าน
        - บอกให้ชัดเจนว่าปั๊มไหนมี ปั๊มไหนหมด
        - ใส่ Emoji ให้ดูน่าอ่าน
        - ปิดท้ายด้วยแฮชแท็ก #น้ำมันอินทร์บุรี #Alieninburi
        - ความยาวไม่เกิน 15 บรรทัด
        """
        response = model.generate_content(prompt)
        print("✅ AI สร้างแคปชั่นสำเร็จ!")
        return response.text.strip()
    except Exception as e:
        print(f"🧨 เกิดข้อผิดพลาดในการเรียกใช้ AI: {e}")
        return f"📢 สรุปสถานะน้ำมันอินทร์บุรีล่าสุด\n\n{fuel_data_text}\n\n#น้ำมันอินทร์บุรี #Alieninburi"

def generate_image_base64(stations, thai_now_str):
    """วาดข้อมูลน้ำมันลงบน Template และแปลงเป็น Base64"""
    print("🎨 กำลังสร้างรูปภาพสถานะน้ำมัน...")
    template_path = "template.png"
    font_path = "Sarabun-Regular.ttf"
    
    try:
        img = Image.open(template_path)
        draw = ImageDraw.Draw(img)
        
        # ตั้งค่าขนาดฟอนต์ (ปรับแก้ได้ถ้าตัวเล็ก/ใหญ่ไป)
        font_title = ImageFont.truetype(font_path, 50)
        font_text = ImageFont.truetype(font_path, 32)
        font_small = ImageFont.truetype(font_path, 22)
        
        # ฟังก์ชันช่วยวาดข้อความพร้อมเงา (ให้อ่านออกไม่ว่าพื้นหลังสีอะไร)
        def draw_text_with_shadow(xy, text, font, text_color=(255, 255, 255), shadow_color=(0, 0, 0)):
            x, y = xy
            draw.text((x+2, y+2), text, font=font, fill=shadow_color)
            draw.text((x, y), text, font=font, fill=text_color)

        # วาดหัวข้อ
        draw_text_with_shadow((50, 50), "รายงานสถานะน้ำมันอินทร์บุรี", font_title)
        draw_text_with_shadow((50, 110), f"ข้อมูลอัปเดตเมื่อ: {thai_now_str}", font_text, text_color=(230, 230, 230))
        
        y_offset = 180
        for name, data in stations.items():
            # ชื่อสถานี
            draw_text_with_shadow((50, y_offset), f"📍 {name}", font_text, text_color=(255, 200, 50))
            
            # สถานะน้ำมัน
            def get_icon(status): return "✅ มี" if "มี" in status else "❌ หมด" if "หมด" in status else "⚪"
            status_text = f"ดีเซล: {get_icon(data['ดีเซล'])} | G95: {get_icon(data['G95'])} | G91: {get_icon(data['G91'])} | E20: {get_icon(data['E20'])}"
            draw_text_with_shadow((80, y_offset + 45), status_text, font_text)
            
            # ข้อมูลรถขนส่ง
            draw_text_with_shadow((80, y_offset + 95), f"🚚 รถขนส่ง: {data['รถขนส่ง']}", font_small, text_color=(200, 255, 200))
            
            y_offset += 150 # เลื่อนบรรทัดสำหรับปั๊มถัดไป
            
        # แปลงรูปภาพเป็น Base64
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        print("✅ สร้างรูปภาพและแปลงเป็น Base64 สำเร็จ!")
        return img_str
        
    except Exception as e:
        print(f"🧨 เกิดข้อผิดพลาดในการสร้างรูปภาพ: {e}")
        return None

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
    has_changes = False
    
    # เช็คการเปลี่ยนแปลงและเตรียมข้อความดิบ
    for station, d in current_data.items():
        if is_morning_report or station not in old_data or current_data[station] != old_data[station]:
            has_changes = True
            
        def icon(s): return "✅" if "มี" in s else "❌" if "หมด" in s else "⚪"
        msg = f"📍 {station} | ดีเซล:{icon(d['ดีเซล'])} G95:{icon(d['G95'])} G91:{icon(d['G91'])} E20:{icon(d['E20'])} | รถขนส่ง: {d['รถขนส่ง']}"
        updates.append(msg)
            
    if has_changes:
        print(f"🔔 มีข้อมูลอัปเดต ส่งให้ AI และวาดรูป...")
        raw_text_for_ai = "\n".join(updates)
        
        # 1. ให้ AI คิดแคปชั่น
        final_caption = generate_ai_caption(raw_text_for_ai)
        
        # 2. วาดรูปภาพและแปลงเป็น Base64
        image_b64 = generate_image_base64(current_data, thai_now_str)
        
        # 3. ส่งทั้งคู่ไป Make.com
        if image_b64:
            post_to_make(final_caption, image_b64)
            
        # บันทึก state
        with open("data_fb.json", "w", encoding="utf-8") as f:
            json.dump(current_data, f, ensure_ascii=False, indent=2)
    else:
        print("✅ ข้อมูลยังเป็นปัจจุบัน ไม่มีอะไรอัปเดต")

if __name__ == "__main__":
    main()
