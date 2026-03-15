import asyncio
import re
import threading
import os
from datetime import datetime
from pyrogram import Client
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from flask import Flask

# --- FLASK SETUP FOR UPTIMEROBOT ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Bot is alive and running!"

def run_server():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host="0.0.0.0", port=port)

# --- TELEGRAM BOT SETUP ---
# Pulling credentials securely from Render's Environment Variables
API_ID = int(os.environ.get("API_ID", 0)) 
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHANNEL_ID = os.environ.get("CHANNEL_ID", "")

app = Client("shein_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Store previous data to calculate the difference (+ / -)
previous_data = {"Men": None, "Women": None}

def scrape_shein_stock():
    """Automates the website process to extract stock counts."""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--incognito') # Clears cache/starts fresh session
    
    driver = webdriver.Chrome(options=options)
    url = "https://www.sheinindia.in/c/sverse-5939-37961"
    
    try:
        driver.get(url)
        wait = WebDriverWait(driver, 15)
        
        # 1. Click the "CATEGORY" button
        category_btn = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//div[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'category')]")
        ))
        driver.execute_script("arguments[0].click();", category_btn) # JS click is often more reliable in headless
        
        # 2. Wait for the popup and find the text for Women and Men
        women_element = wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Women (')]")))
        men_element = wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Men (')]")))
        
        # 3. Extract numbers using regex
        women_stock = int(re.search(r'\d+', women_element.text).group())
        men_stock = int(re.search(r'\d+', men_element.text).group())
        
        return {"Men": men_stock, "Women": women_stock}
        
    except Exception as e:
        print(f"Scraping error: {e}")
        return None
    finally:
        driver.quit()

async def update_loop():
    global previous_data
    
    while True:
        # Run the scraping script in a separate thread so it doesn't freeze Pyrogram
        data = await asyncio.to_thread(scrape_shein_stock)
        
        if data:
            men_current = data["Men"]
            women_current = data["Women"]
            
            # Handle the very first run so we don't crash doing math with 'None'
            if previous_data["Men"] is None:
                men_diff = 0
                women_diff = 0
            else:
                men_diff = men_current - previous_data["Men"]
                women_diff = women_current - previous_data["Women"]
            
            # Format arrows and + signs
            men_arrow = "⬆️" if men_diff >= 0 else "⬇️"
            women_arrow = "⬆️" if women_diff >= 0 else "⬇️"
            
            men_diff_str = f"+{men_diff}" if men_diff >= 0 else f"{men_diff}"
            women_diff_str = f"+{women_diff}" if women_diff >= 0 else f"{women_diff}"
            
            now = datetime.now().strftime("%d %b %Y, %I:%M %p")
            
            message = (
                f"🔔 Shein Stock Update\n\n"
                f"👨 Men → {men_current} {men_arrow} {men_diff_str}\n"
                f"👩 Women → {women_current} {women_arrow} {women_diff_str}\n\n"
                f"⏰ {now}\n\n"
                f"Direct Link: https://www.sheinindia.in/c/sverse-5939-37961"
            )
            
            try:
                await app.send_message(CHANNEL_ID, message)
                previous_data = data # Save current state for the next check
            except Exception as e:
                print(f"Telegram error: {e}")
                
        # Wait 10 seconds before checking again
        await asyncio.sleep(10)

async def main():
    await app.start()
    await update_loop()

if __name__ == "__main__":
    # Start the Flask web server in a background thread
    threading.Thread(target=run_server, daemon=True).start()
    
    # Start the main bot loop
    asyncio.run(main())
