import asyncio
import aiohttp
import time
import random
import string
import os

# ==========================================
# أداة فحص وتوليد اليوزرات العشوائية (Railway Ready)
# ==========================================

# في Railway: سيقوم السكربت بسحب التوكنات مباشرة من إعدادات المتغيرات (Variables) هناك.
# محلياً: يمكنك وضعها في المتغير النصي الاحتياطي أسفل لو احتجت.
TOKEN = os.getenv("TOKEN", "ضع_التوكن_هنا_لو_بتشغله_محلياً")

# إعدادات الفحص
TOTAL_TO_CHECK = 10000   # عدد اليوزرات العشوائية المراد فحصها
USERNAME_LENGTH = 4      # طول اليوزر (4 للرباعي)
OUTPUT_FILE = "available_pro.txt"

# الرموز المسموحة رسمياً في ديسكورد
CHARS = string.ascii_lowercase + string.digits + "_"

def generate_random_username(length):
    """توليد يوزر عشوائي واستبعاد الشروط المرفوضة من ديسكورد تلقائياً"""
    while True:
        uname = "".join(random.choices(CHARS, k=length))
        if not uname.startswith("_") and not uname.endswith("_") and "__" not in uname:
            return uname

async def check_username(session, token, username, stats):
    """فحص اليوزر باستخدام هيدرز المتصفح المتقدمة"""
    headers = {
        "Authorization": token.strip(),
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "X-Super-Properties": "eyJvcyI6I3dpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIn0=",
        "X-Discord-Locale": "en-US"
    }
    
    url = "https://discord.com/api/v10/users/@me"

    try:
        async with session.get(url, headers=headers) as resp:
            stats["checked"] += 1
            if resp.status == 200:
                stats["available"] += 1
                with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
                    f.write(f"{username}\n")
                print(f"\n[🎯 صيد متاح!] -> {username}")
            elif resp.status == 429:
                stats["ratelimited"] += 1
                await asyncio.sleep(2.0)
    except Exception:
        stats["errors"] += 1

async def worker(worker_id, tokens, queue, stats):
    if not tokens:
        return
    token = tokens[worker_id % len(tokens)]
    connector = aiohttp.TCPConnector(limit=30, force_close=True)
    async with aiohttp.ClientSession(connector=connector) as session:
        while not queue.empty():
            username = await queue.get()
            await check_username(session, token, username, stats)
            queue.task_done()

async def main():
    if not TOKEN or TOKEN == "ضع_التوكن_هنا_لو_بتشغله_محلياً":
        print("❌ خطأ: لم يتم العثور على التوكن! تأكد من إضافة متغير `TOKEN` في إعدادات Railway.")
        return

    # دعم وضع توكن واحد أو عدة توكنات مفصولة بفاصلة في نفس المتغير
    tokens_list = [t.strip() for t in TOKEN.split(",") if t.strip()]

    print(f"🎲 جاري توليد وتجهيز ({TOTAL_TO_CHECK}) يوزر عشوائي بطول ({USERNAME_LENGTH} خانات)...")
    
    usernames_queue = asyncio.Queue()
    generated_set = set()

    while len(generated_set) < TOTAL_TO_CHECK:
        uname = generate_random_username(USERNAME_LENGTH)
        if uname not in generated_set:
            generated_set.add(uname)
            await usernames_queue.put(uname)

    print(f"📦 تم تحميل الطابور بنجاح. عدد التوكنات الفعالة: {len(tokens_list)}")
    print("🔥 بدء محرك الفحص فائق السرعة...\n")

    stats = {
        "checked": 0,
        "available": 0,
        "ratelimited": 0,
        "errors": 0
    }

    start_time = time.time()

    workers_count = len(tokens_list) * 5
    tasks = []
    for i in range(workers_count):
        task = asyncio.create_task(worker(i, tokens_list, usernames_queue, stats))
        tasks.append(task)

    while not usernames_queue.empty():
        elapsed = time.time() - start_time
        speed = stats["checked"] / elapsed if elapsed > 0 else 0
        print(f"\r📊 [فحص: {stats['checked']}/{TOTAL_TO_CHECK}] | 🟢 [متاح: {stats['available']}] | ⏳ [السرعة: {speed:.1f} يوزر/ثانية] | ⚠️ [429: {stats['ratelimited']}]", end="")
        await asyncio.sleep(0.3)

    await asyncio.gather(*tasks)
    
    elapsed_total = time.time() - start_time
    print(f"\n\n✅ انتهى الفحص بالكامل في {elapsed_total:.2f} ثانية!")
    print(f"📁 النتائج محفوظة في ملف: {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(main())
