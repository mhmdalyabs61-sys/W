import asyncio
import aiohttp
import time
import random
import string
import os

# ==========================================
# فاحص ديسكورد المطور - تجاوز حظر الـ IP والبصمات
# ==========================================

TOKEN = os.getenv("TOKEN", "")

CHANNEL_URL = "https://discord.com/channels/1569068084982059129/1569818461792772228"
WEBHOOK_URL = "https://discord.com/api/webhooks/1569827836041101323/LoLYfvNjEnarlvjEavVYL2-e7YQ30SlNTvfuFY502JQf4mUnwDiKYxip4SKvJ1GS501J"

BATCH_SIZE = 10000       # حجم الدفعة
USERNAME_LENGTH = 4      # طول اليوزر (رباعي)
OUTPUT_FILE = "available_pro.txt"

TARGET_DELAY = 1.0       # طلب كل ثانية بالتمام

CHARS = string.ascii_lowercase + string.digits + "_"

# قائمة متنوعة من بصمات المتصفحات الحقيقية (User-Agents) لتغيير الهوية وتجنب حظر البصمة
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
]

def generate_random_username(length):
    """توليد يوزر عشوائي مطابق لشروط ديسكورد"""
    while True:
        uname = "".join(random.choices(CHARS, k=length))
        if not uname.startswith(".") and not uname.endswith(".") and ".." not in uname:
            if not uname.startswith("_") and not uname.endswith("_") and "__" not in uname:
                return uname

async def send_webhook(session, username):
    """إرسال التنبيه الفوري للروم عند صيد يوزر متاح"""
    payload = {
        "content": f"🎉 **تم صيد يوزر ديسكورد متاح بنجاح!**\n> اليوزر: `{username}`\n📍 الروم: {CHANNEL_URL}\n⚡ مبروك الصيد يا وحش!"
    }
    try:
        async with session.post(WEBHOOK_URL, json=payload) as resp:
            pass
    except Exception:
        pass

async def check_username(session, token, username, stats):
    """فحص توفر اليوزر مع هيدرز وبصمات متغيرة لتفادي حظر الـ IP"""
    
    # اختيار بصمة متصفح عشوائية مع كل طلب لإعطاء طابع تفاعل بشري متفرّد
    chosen_ua = random.choice(USER_AGENTS)
    
    headers = {
        "Authorization": token.strip(),
        "Content-Type": "application/json",
        "User-Agent": chosen_ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Sec-Ch-Ua": '"Chromium";v="122", "Not(A:Brand";v="8", "Google Chrome";v="122"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "Connection": "keep-alive"
    }
    
    url = f"https://discord.com/api/v10/users/@me/pomelo-attempt?username={username}"

    try:
        async with session.get(url, headers=headers) as resp:
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
                retry_after = 10.0  # وقت افتراضي أطول للتبريد
                try:
                    err_data = await resp.json()
                    retry_after = float(err_data.get("retry_after", 10.0))
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
        print("❌ خطأ: لم يتم العثور على التوكن! تأكد من إضافة متغير `TOKEN` في إعدادات Railway.")
        return

    tokens_list = [t.strip() for t in TOKEN.split(",") if t.strip()]
    print(f"🚀 بدء التشغيل بالبصمات المطورة (طلب كل ثانية + تجاوز الحظر). التوكنات: {len(tokens_list)}")

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
            while not usernames_queue.empty():
                try:
                    username = usernames_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

                stats["current_user"] = username

                # فحص اليوزر بالهيدرز الجديدة
                result, wait_time = await check_username(session, token, username, stats)

                if result == "DEAD":
                    print(f"\n⚠️ [تحذير] التوكن تالف أو غير صالح!")
                    break
                elif result == "RATELIMIT":
                    print(f"\n⏳ [رصد 429 / حظر IP مؤقت] ديسكورد طالب انتظار: {wait_time:.1f} ثانية.. جاري التبريد.")
                    await asyncio.sleep(wait_time + 2.0) # زيادة أمان

                # تحديث اللوق
                elapsed = time.time() - start_time
                speed = stats["checked"] / elapsed if elapsed > 0 else 0
                print(f"\r🔍 [فحص: {stats['checked']}/{BATCH_SIZE}] | 👤 [{stats['current_user']:<6}] | 🟢 [متاح: {stats['available']}] | ⏳ [{speed:.1f} يوزر/ث] | ⚠️ [429: {stats['ratelimited']}]", end="")

                # الفاصل الزمني بين الطلبات
                await asyncio.sleep(TARGET_DELAY)
                usernames_queue.task_done()

        print(f"\n✅ انتهت الدفعة #{batch_number} بنجاح!")
        batch_number += 1

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n❌ تم إيقاف الأداة.")
