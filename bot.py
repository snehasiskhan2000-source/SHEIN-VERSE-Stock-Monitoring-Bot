import asyncio
import re
import threading
from datetime import datetime
from pyrogram import Client
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from flask import Flask
import os

# --- FLASK SETUP FOR UPTIMEROBOT ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Bot is alive and running!"

def run_server():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host="0.0.0.0", port=port)

# --- TELEGRAM BOT SETUP ---
# Replace with your actual credentials
API_ID = "YOUR_API_ID"
API_HASH = "YOUR_API_HASH"
BOT_TOKEN = "YOUR_BOT_TOKEN"
CHANNEL_ID = "@YourChannelUsername" # Or channel ID like -100xxxxxxx

app = Client("shein_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Store previous data to calculate difference
previous_data = {"Men": 0, "Women": 0}

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
        
        # 1. Click the "CATEGORY" button in the bottom nav
        # We look for an element containing the word CATEGORY
        category_btn = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//*[translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='category']")
        ))
        category_btn.click()
        
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
        driver.quit() # Always close the browser to free memory

async def update_loop():
    global previous_data
    await app.start()
    
    while True:
        data = scrape_shein_stock()
        
        if data:
            men_current = data["Men"]
            women_current = data["Women"]
            
            # Calculate changes
            men_diff = men_current - previous_data["Men"]
            women_diff = women_current - previous_data["Women"]
            
            # Format arrows
            men_arrow = "⬆️ +" if men_diff >= 0 else "⬇️ "
            women_arrow = "⬆️ +" if women_diff >= 0 else "⬇️ "
            
            now = datetime.now().strftime("%d %b %Y, %I:%M %p")
            
            message = (
                f"🔔 Shein Stock Update\n\n"
                f"👨 Men → {men_current} {men_arrow}{abs(men_diff)}\n"
                f"👩 Women → {women_current} {women_arrow}{abs(women_diff)}\n\n"
                f"⏰ {now}\n\n"
                f"Direct Link: https://www.sheinindia.in/c/sverse-5939-37961"
            )
            
            try:
                await app.send_message(CHANNEL_ID, message)
                # Update previous data for the next loop
                previous_data = data
            except Exception as e:
                print(f"Telegram error: {e}")
                
        # Wait 10 seconds before checking again (change to 300 for 5 mins later)
        await asyncio.sleep(10)

if __name__ == "__main__":
    # Start the Flask web server in a separate thread for UptimeRobot
    threading.Thread(target=run_server, daemon=True).start()
    
    # Start the Pyrogram async loop
    loop = asyncio.get_event_loop()
    loop.run_until_complete(update_loop())
