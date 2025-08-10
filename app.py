from fastapi import FastAPI
from playwright.async_api import async_playwright
import json
import os
import asyncio

app = FastAPI()

AUTH_STATE_FILE = "auth_state.json"

async def get_session_data():
    if not os.path.exists(AUTH_STATE_FILE):
        raise FileNotFoundError(f"auth_state.json tidak ditemukan di {os.getcwd()}")

    async with async_playwright() as p:
        print("🚀 Meluncurkan Chromium...")
        
        # Launch browser dengan extra arguments untuk compatibility
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--disable-gpu',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--disable-blink-features=AutomationControlled'
            ]
        )
        
        # Setup context dengan storage state dan user agent
        context = await browser.new_context(
            storage_state=AUTH_STATE_FILE,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        page = await context.new_page()

        try:
            print("🌐 Meminta session data dari ImageFX...")
            
            # Request ke auth session endpoint
            resp = await page.request.get("https://labs.google/fx/api/auth/session")
            print(f"📡 Status code: {resp.status}")

            if resp.status != 200:
                print("❌ Gagal ambil session")
                error_text = await resp.text()
                print(error_text)
                raise Exception(f"Session request gagal: {resp.status} - {error_text}")

            # Parse response JSON
            session_data = await resp.json()
            bearer_token = session_data.get("access_token")
            
            if not bearer_token:
                raise Exception("Access token tidak ditemukan di response")

            print("🍪 Mengambil cookies...")
            
            # Ambil semua cookies dari context
            cookies = await context.cookies()
            print(f"🍪 Total cookies ditemukan: {len(cookies)}")
            
            # Filter cookies yang relevan untuk ImageFX
            relevant_domains = ['labs.google', '.google.com', 'google.com']
            filtered_cookies = []
            
            for cookie in cookies:
                if any(domain in cookie['domain'] for domain in relevant_domains):
                    filtered_cookies.append(cookie)
            
            print(f"🎯 Cookies relevan ditemukan: {len(filtered_cookies)}")
            
            # Buat cookie string dalam format name=value; name2=value2
            cookie_pairs = []
            for cookie in filtered_cookies:
                cookie_pairs.append(f"{cookie['name']}={cookie['value']}")
            
            cookie_string = "; ".join(cookie_pairs)
            
            print(f"✅ Data berhasil diambil!")
            print(f"👤 User: {session_data.get('user', {}).get('name', 'Unknown')}")
            print(f"📧 Email: {session_data.get('user', {}).get('email', 'Unknown')}")
            print(f"📏 Panjang cookie string: {len(cookie_string)} karakter")
            
            return {
                "bearer_token": bearer_token,
                "cookies": cookie_string,
                "session_info": {
                    "user_name": session_data.get('user', {}).get('name', 'Unknown'),
                    "user_email": session_data.get('user', {}).get('email', 'Unknown'),
                    "expires": session_data.get('expires', 'Unknown'),
                    "total_cookies": len(filtered_cookies),
                    "cookie_length": len(cookie_string)
                }
            }
            
        finally:
            await browser.close()

@app.get("/session")
async def get_session():
    """Endpoint untuk mendapatkan bearer token dan cookies"""
    try:
        data = await get_session_data()
        return data
    except Exception as e:
        print(f"Error: {str(e)}")
        return {"error": str(e)}

@app.get("/token")
async def token():
    """Endpoint khusus bearer token saja (backward compatibility)"""
    try:
        data = await get_session_data()
        return {"bearer_token": data["bearer_token"]}
    except Exception as e:
        print(f"Error: {str(e)}")
        return {"error": str(e)}

@app.get("/cookies")
async def cookies():
    """Endpoint khusus cookies saja"""
    try:
        data = await get_session_data()
        return {"cookies": data["cookies"]}
    except Exception as e:
        print(f"Error: {str(e)}")
        return {"error": str(e)}

@app.get("/health")
async def health():
    """Health check endpoint"""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True, 
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            await browser.close()
            return {"status": "ok", "playwright": "working"}
    except Exception as e:
        return {"status": "error", "playwright": str(e)}