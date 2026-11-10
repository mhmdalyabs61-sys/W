import asyncio
import aiohttp
import time
import random
import string
import os

# ==========================================
# أداة فحص وتوليد اليوزرات العشوائية + Loop 24/7 + Webhook
# ==========================================

# 1. التوكنات: تُسحب تلقائياً من متغير البيئة TOKEN في Railway (مفصولة بفواصل)
TOKEN = os.getenv("TOKEN", "")

# 2. معلومات روم الويب هوك
CHANNEL_URL = "https://discord.com/channels/1569068084982059129/1569818461792772228"
WEBHOOK_URL = "https://discord.com/api/webhooks/1569827836041101323/LoLYfvNjEnarlvjEavVYL2-e7YQ30SlNTvfuFY502JQf4mUnwDiKYxip4SKvJ1GS501J"

# إعدادات الفحص لكل دفعة
BATCH_SIZE = 10000       # عدد اليوزرات في كل دفعة
USERNAME_LENGTH = 4      # طول اليوزر (4 للرباعي)
OUTPUT_FILE = "available_pro.txt"

CHARS = string.ascii_lowercase + string.digits + "_"

def generate_random_username(length):
    """توليد يوزر عشوائي واستبعاد الشروط المرفوضة من ديسكورد"""
    while True:
        uname = "".join(random.choices(CHARS, k=length))
        if not uname.startswith("_") and not uname.endswith("_") and "__" not in uname:
            return uname

async def send_webhook(session, username):
    """إرسال تنبيه فوري إلى روم ديسكورد عبر الويب هوك عند صيد يوزر متاح"""
    payload = {
        "content": f"🎉 **تم صيد يوزر ديسكورد متاح بنجاح!**\n> اليوزر: `{username}`\n📍 الروم: {CHANNEL_URL}\n⚡ مبروك الصيد يا وحش!"
    }
    try:
        async with session.post(WEBHOOK_URL, json=payload) as resp:
            pass
    except Exception:
        pass

async def check_username(session, token, username, stats):
    """فحص اليوزر باستخدام هيدرز المتصفح مع معالجة ذكية للـ Rate Limit"""
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

    max_retries = 3
    for _ in range(max_retries):
        try:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    stats["checked"] += 1
                    stats["available"] += 1
                    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
                        f.write(f"{username}\n")
                    print(f"\n[🎯 صيد متاح!] -> {username}")
                    await send_webhook(session, username)
                    return
                
                elif resp.status == 429:
                    stats["ratelimited"] += 1
                    # قراءة وقت الانتظار من ديسكورد إذا توفر، أو الالتزام بتهدئة قصيرة وآمنة
                    retry_after = 1.5
                    try:
                        data = await resp.json()
                        retry_after = float(data.get("retry_after", 1.5))
                    except Exception:
                        pass
                    await asyncio.sleep(retry_after + random.uniform(0.1, 0.4))
                    continue
                
                elif resp.status in (401, 403):
                    # مشكلة في التوكن نفسه، ننتظر قليلاً لتجنب الحظر الكامل
                    await asyncio.sleep(2.0)
                    stats["checked"] += 1
                    return
                
                else:
                    stats["checked"] += 1
                    return
        except Exception:
            stats["errors"] += 1
            await asyncio.sleep(1.0)
            return

async def worker(worker_id, tokens_list, queue, stats):
    """عامل متزامن يسحب من الطابور ويفحص باستخدام توكن مخصص له للتوزيع العادل"""
    token = tokens_list[worker_id % len(tokens_list)]
    connector = aiohttp.TCPConnector(limit=50, force_close=True)
    async with aiohttp.ClientSession(connector=connector) as session:
        while not queue.empty():
            try:
                username = queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            
            await check_username(session, token, username, stats)
            queue.task_done()

async def main():
    if not TOKEN:
        print("❌ خطأ: لم يتم العثور على التوكن! تأكد من إضافة متغير `TOKEN` في إعدادات Railway.")
        return

    tokens_list = [t.strip() for t in TOKEN.split(",") if t.strip()]
    print(f"🚀 بدء التشغيل المستمر (24/7). عدد التوكنات الفعالة: {len(tokens_list)}")

    batch_number = 1

    # حلقة تكرار أبدية تفحص دفعة وتنتقل للدفعة التالية تلقائياً بلا توقف
    while True:
        print(f"\n🎲 [الدفعة #{batch_number}] جاري توليد وتجهيز ({BATCH_SIZE}) يوزر عشوائي جديد...")
        
        usernames_queue = asyncio.Queue()
        generated_set = set()

        # توليد أسماء جديدة كلياً لكل دفعة
        while len(generated_set) < BATCH_SIZE:
            uname = generate_random_username(USERNAME_LENGTH)
            if uname not in generated_set:
                generated_set.add(uname)
                usernames_queue.put_nowait(uname)

        stats = {
            "checked": 0,
            "available": 0,
            "ratelimited": 0,
            "errors": 0
        }

        start_time = time.time()
        workers_count = len(tokens_list) * 10  # توزيع عالي للسرعة القصوى

        tasks = [asyncio.create_task(worker(i, tokens_list, usernames_queue, stats)) for i in range(workers_count)]

        # حلقة عرض التقدم للدفعة الحالية
        while not usernames_queue.empty():
            elapsed = time.time() - start_time
            speed = stats["checked"] / elapsed if elapsed > 0 else 0
            print(f"\r📊 [دفعة #{batch_number} | فحص: {stats['checked']}/{BATCH_SIZE}] | 🟢 [متاح: {stats['available']}] | ⏳ [السرعة: {speed:.1f} يوزر/ث] | ⚠️ [429: {stats['ratelimited']}]", end="")
            await asyncio.sleep(0.4)

        await asyncio.gather(*tasks)
        
        elapsed_total = time.time() - start_time
        print(f"\n✅ انتهت الدفعة #{batch_number} بالكامل في {elapsed_total:.2f} ثانية! الانتقال للدفعة التالية فوراً...")
        batch_number += 1

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n❌ تم إيقاف الأداة.")
