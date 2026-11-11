import asyncio
import aiohttp
import time
import random
import string
import os

# ==========================================
# أداة فحص ديسكورد المتقدمة - 24/7 مع عزل التوكنات التالفة
# ==========================================

TOKEN = os.getenv("TOKEN", "")

CHANNEL_URL = "https://discord.com/channels/1569068084982059129/1569818461792772228"
WEBHOOK_URL = "https://discord.com/api/webhooks/1569827836041101323/LoLYfvNjEnarlvjEavVYL2-e7YQ30SlNTvfuFY502JQf4mUnwDiKYxip4SKvJ1GS501J"

BATCH_SIZE = 10000       # حجم الدفعة الواحدة
USERNAME_LENGTH = 4      # طول اليوزر (رباعي)
OUTPUT_FILE = "available_pro.txt"

CHARS = string.ascii_lowercase + string.digits + "_"

def generate_random_username(length):
    """توليد يوزر عشوائي مطابق لشروط ديسكورد"""
    while True:
        uname = "".join(random.choices(CHARS, k=length))
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
    """فحص اليوزر مع معالجة ذكية وسريعة للـ Rate Limit والتوكنات"""
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
                await send_webhook(session, username)
                return True
                
            elif resp.status == 429:
                stats["ratelimited"] += 1
                # في حال الحظر، نرجع مؤشر خطأ عشان السكربت يبدل التوكن فوراً
                return False
                
            elif resp.status in (401, 403):
                # توكن غير صالح أو محظور نهائياً، نرفضه
                stats["dead_tokens"] += 1
                return "DEAD"
            
            return True
    except Exception:
        stats["errors"] += 1
        return False

async def worker(worker_id, active_tokens, queue, stats):
  """عامل فحص ديناميكي يسحب التوكنات الحية ويفحص الطابور"""
  connector = aiohttp.TCPConnector(limit=30, force_close=True)
  async with aiohttp.ClientSession(connector=connector) as session:
    while not queue.empty():
      if not active_tokens:
        await asyncio.sleep(2.0)  # انتظار لو انتهت التوكنات مؤقتاً
        continue

      # اختيار توكن دوري
      token = active_tokens[worker_id % len(active_tokens)]

      try:
        username = queue.get_nowait()
      except asyncio.QueueEmpty:
        break

      result = await check_username(session, token, username, stats)

      if result == "DEAD":
        # إزالة التوكن التالف من القائمة فوراً عشان ما يبطئ الشغل
        if token in active_tokens:
          active_tokens.remove(token)
          print(
              f"\n⚠️ [تحذير] تم استبعاد توكن تالف/محظور. التوكنات المتبقية:"
              f" {len(active_tokens)}"
          )
      elif result is False:
        # لو جاء 429، نعيد اليوزر للطابور ونعطي التوكن راحة قصيرة
        await queue.put(username)
        await asyncio.sleep(0.5)

      queue.task_done()


async def main():
    if not TOKEN:
        print("❌ خطأ: لم يتم العثور على التوكن! تأكد من إضافة متغير `TOKEN` في إعدادات Railway.")
        return

    tokens_list = [t.strip() for t in TOKEN.split(",") if t.strip()]
    print(f"🚀 بدء التشغيل المستمر (24/7). عدد التوكنات الإجمالي: {len(tokens_list)}")

    batch_number = 1

    while True:
        # نسختة حية للتوكنات عشان نقدر نحذف منها وقت الحظر بدون ما نخرب القائمة الأصلية
        current_active_tokens = list(tokens_list)
        if not current_active_tokens:
            print("❌ لا توجد توكنات فعالة حالياً!")
            await asyncio.sleep(5)
            continue

        print(f"\n🎲 [الدفعة #{batch_number}] جاري توليد وتجهيز ({BATCH_SIZE}) يوزر عشوائي جديد...")
        
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
            "dead_tokens": 0
        }

        start_time = time.time()
        workers_count = len(current_active_tokens) * 8

        tasks = [asyncio.create_task(worker(i, current_active_tokens, usernames_queue, stats)) for i in range(workers_count)]

        while not usernames_queue.empty() and current_active_tokens:
            elapsed = time.time() - start_time
            speed = stats["checked"] / elapsed if elapsed > 0 else 0
            print(f"\r📊 [دفعة #{batch_number} | فحص: {stats['checked']}/{BATCH_SIZE}] | 🟢 [متاح: {stats['available']}] | ⏳ [السرعة: {speed:.1f} يوزر/ث] | ⚠️ [429: {stats['ratelimited']}]", end="")
            await asyncio.sleep(0.4)

        await asyncio.gather(*tasks, return_exceptions=True)
        
        elapsed_total = time.time() - start_time
        print(f"\n✅ انتهت الدفعة #{batch_number} في {elapsed_total:.2f} ثانية! الانتقال للدفعة التالية...")
        batch_number += 1

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n❌ تم إيقاف الأداة.")
