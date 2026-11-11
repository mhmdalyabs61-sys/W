import asyncio
import aiohttp
import time
import random
import string
import os

# ==========================================
# فاحص يوزرات ديسكورد - سرعة ثابتة وآمنة تماماً (10 طلب/ث)
# ==========================================

TOKEN = os.getenv("TOKEN", "")

CHANNEL_URL = "https://discord.com/channels/1569068084982059129/1569818461792772228"
WEBHOOK_URL = "https://discord.com/api/webhooks/1569827836041101323/LoLYfvNjEnarlvjEavVYL2-e7YQ30SlNTvfuFY502JQf4mUnwDiKYxip4SKvJ1GS501J"

BATCH_SIZE = 10000       # حجم الدفعة
USERNAME_LENGTH = 4      # طول اليوزر (رباعي)
OUTPUT_FILE = "available_pro.txt"

# السرعة مقفولة تماماً على 10 طلبات بالثانية بناءً على طلبك
TARGET_REQUESTS_PER_SECOND = 10

CHARS = string.ascii_lowercase + string.digits + "_"

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
    """فحص توفر اليوزر الحقيقي عبر نقطة نهاية ديسكورد"""
    headers = {
        "Authorization": token.strip(),
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
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
                return "OK"
                
            elif resp.status == 429:
                stats["ratelimited"] += 1
                return "RATELIMIT"
                
            elif resp.status in (401, 403):
                stats["dead_tokens"] += 1
                return "DEAD"
            
            return "OK"
    except Exception:
        stats["errors"] += 1
        return "ERROR"

async def worker(worker_id, active_tokens, queue, stats, rate_limiter):
    """عامل فحص يلتزم بالسرعة الثابتة (10 طلب/ث) بدقة"""
    connector = aiohttp.TCPConnector(limit=5, force_close=True)
    async with aiohttp.ClientSession(connector=connector) as session:
        while not queue.empty():
            if not active_tokens:
                await asyncio.sleep(3.0)
                continue

            token = active_tokens[worker_id % len(active_tokens)]

            try:
                username = queue.get_nowait()
            except asyncio.QueueEmpty:
                break

            stats["current_user"] = username

            # استخدام Semaphore لتقييد السرعة بـ 10 طلبات بالثانية بدقة
            async with rate_limiter:
                result = await check_username(session, token, username, stats)
                # مهلة زمنية دقيقة لضبط إيقاع الطلبات
                await asyncio.sleep(1.0 / TARGET_REQUESTS_PER_SECOND)

            if result == "DEAD":
                if token in active_tokens:
                    active_tokens.remove(token)
                    print(f"\n⚠️ [تحذير] استبعاد توكن تالف. المتبقي: {len(active_tokens)}")
            elif result == "RATELIMIT":
                # إذا جاء لمتد، نريح التوكن شوي عشان ما يعلق بـ 429
                await queue.put(username)
                await asyncio.sleep(3.0)

            queue.task_done()

async def main():
    if not TOKEN:
        print("❌ خطأ: لم يتم العثور على التوكن! تأكد من إضافة متغير `TOKEN` في إعدادات Railway.")
        return

    tokens_list = [t.strip() for t in TOKEN.split(",") if t.strip()]
    print(f"🚀 بدء التشغيل برتم آمن وثابت تماماً ({TARGET_REQUESTS_PER_SECOND} طلب/ث). التوكنات: {len(tokens_list)}")

    rate_limiter = asyncio.Semaphore(TARGET_REQUESTS_PER_SECOND)
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
        # تقليل عدد العمال ليتناسب مع السرعة الهادئة والمحددة بـ 10
        workers_count = min(len(current_active_tokens) * 2, 5)

        tasks = [asyncio.create_task(worker(i, current_active_tokens, usernames_queue, stats, rate_limiter)) for i in range(workers_count)]

        while not usernames_queue.empty() and current_active_tokens:
            elapsed = time.time() - start_time
            speed = stats["checked"] / elapsed if elapsed > 0 else 0
            print(f"\r🔍 [فحص: {stats['checked']}/{BATCH_SIZE}] | 👤 [{stats['current_user']:<6}] | 🟢 [متاح: {stats['available']}] | ⏳ [{speed:.1f} يوزر/ث] | ⚠️ [429: {stats['ratelimited']}]", end="")
            await asyncio.sleep(0.4)

        await asyncio.gather(*tasks, return_exceptions=True)
        
        elapsed_total = time.time() - start_time
        print(f"\n✅ انتهت الدفعة #{batch_number} في {elapsed_total:.2f} ثانية!")
        batch_number += 1

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n❌ تم إيقاف الأداة.")
