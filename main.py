import asyncio
import aiohttp
import time
import random
import string
import os

# ==========================================
# فاحص ديسكورد مع دعم البروكسيات لتجاوز حظر الـ IP النهائي
# ==========================================

TOKEN = os.getenv("TOKEN", "")
# حط البروكسيات هنا مفصولة بفواصل، مثال: "http://ip:port" أو اتركها فاضية لو بتجرب محلي
PROXIES_ENV = os.getenv("PROXIES", "") 

CHANNEL_URL = "https://discord.com/channels/1569068084982059129/1569818461792772228"
WEBHOOK_URL = "https://discord.com/api/webhooks/1569827836041101323/LoLYfvNjEnarlvjEavVYL2-e7YQ30SlNTvfuFY502JQf4mUnwDiKYxip4SKvJ1GS501J"

BATCH_SIZE = 10000       
USERNAME_LENGTH = 4      
OUTPUT_FILE = "available_pro.txt"

TARGET_DELAY = 1.0       # طلب كل ثانية

CHARS = string.ascii_lowercase + string.digits + "_"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]

def generate_random_username(length):
    while True:
        uname = "".join(random.choices(CHARS, k=length))
        if not uname.startswith(".") and not uname.endswith(".") and ".." not in uname:
            if not uname.startswith("_") and not uname.endswith("_") and "__" not in uname:
                return uname

async def send_webhook(session, username):
    payload = {
        "content": f"🎉 **تم صيد يوزر ديسكورد متاح بنجاح!**\n> اليوزر: `{username}`\n📍 الروم: {CHANNEL_URL}\n⚡ مبروك الصيد يا وحش!"
    }
    try:
        async with session.post(WEBHOOK_URL, json=payload) as resp:
            pass
    except Exception:
        pass

async def check_username(session, token, username, stats, proxy=None):
    chosen_ua = random.choice(USER_AGENTS)
    headers = {
        "Authorization": token.strip(),
        "Content-Type": "application/json",
        "User-Agent": chosen_ua,
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
    }
    
    url = f"https://discord.com/api/v10/users/@me/pomelo-attempt?username={username}"

    try:
        # استخدام البروكسي لو متوفر
        async with session.get(url, headers=headers, proxy=proxy) as resp:
            stats["checked"] += 1
            
            if resp.status == 200:
                data = await resp.json()
                if data.get("taken") is False:
                    stats["available"] += 1
                    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
                        f.write(f"{username}\n")
                    print(f"\n[🎯 صيد متاح!] -> {username}")
                    await send_webhook(session, username)
                return "OK", 0
                
            elif resp.status == 429:
                stats["ratelimited"] += 1
                retry_after = 15.0
                try:
                    err_data = await resp.json()
                    retry_after = float(err_data.get("retry_after", 15.0))
                except Exception:
                    pass
                return "RATELIMIT", retry_after
                
            elif resp.status in (401, 403):
                stats["dead_tokens"] += 1
                return "DEAD", 0
            
            return "OK", 0
    except Exception:
        stats["errors"] += 1
        return "ERROR", 0

async def main():
    if not TOKEN:
        print("❌ خطأ: لم يتم العثور على التوكن!")
        return

    tokens_list = [t.strip() for t in TOKEN.split(",") if t.strip()]
    proxies_list = [p.strip() for p in PROXIES_ENV.split(",") if p.strip()] if PROXIES_ENV else [None]
    
    print(f"🚀 بدء التشغيل مع دعم البروكسيات. التوكنات: {len(tokens_list)} | البروكسيات المتاحة: {len(proxies_list)}")

    batch_number = 1

    while True:
        current_active_tokens = list(tokens_list)
        if not current_active_tokens:
            print("❌ لا توجد توكنات فعالة!")
            await asyncio.sleep(5)
            continue

        print(f"\n🎲 [الدفعة #{batch_number}] جاري توليد ({BATCH_SIZE}) يوزر...")
        
        usernames_queue = asyncio.Queue()
        generated_set = set()

        while len(generated_set) < BATCH_SIZE:
            uname = generate_random_username(USERNAME_LENGTH)
            if uname not in generated_set:
                generated_set.add(uname)
                usernames_queue.put_nowait(uname)

        stats = {
            "checked": 0,
            "available": 0,
            "ratelimited": 0,
            "errors": 0,
            "dead_tokens": 0,
            "current_user": "---"
        }

        start_time = time.time()
        token = current_active_tokens[0]

        connector = aiohttp.TCPConnector(limit=2, force_close=True)
        async with aiohttp.ClientSession(connector=connector) as session:
            proxy_index = 0
            while not usernames_queue.empty():
                try:
                    username = usernames_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

                stats["current_user"] = username
                
                # اختيار بروكسي مختلف مع كل طلب لو فيه لستة بروكسيات
                current_proxy = proxies_list[proxy_index % len(proxies_list)]
                proxy_index += 1

                result, wait_time = await check_username(session, token, username, stats, proxy=current_proxy)

                if result == "DEAD":
                    print(f"\n⚠️ [تحذير] التوكن تالف!")
                    break
                elif result == "RATELIMIT":
                    print(f"\n⏳ [رصد 429] السيرفر صاد حظر IP، انتظار: {wait_time:.1f} ثانية..")
                    await asyncio.sleep(wait_time + 3.0)

                elapsed = time.time() - start_time
                speed = stats["checked"] / elapsed if elapsed > 0 else 0
                print(f"\r🔍 [فحص: {stats['checked']}/{BATCH_SIZE}] | 👤 [{stats['current_user']:<6}] | 🟢 [متاح: {stats['available']}] | ⏳ [{speed:.1f} يوزر/ث] | ⚠️ [429: {stats['ratelimited']}]", end="")

                await asyncio.sleep(TARGET_DELAY)
                usernames_queue.task_done()

        print(f"\n✅ انتهت الدفعة #{batch_number}!")
        batch_number += 1

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n❌ تم إيقاف الأداة.")
