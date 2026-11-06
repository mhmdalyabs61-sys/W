import os
import threading
import time
from flask import Flask
import requests

# 1. إعداد سيرفر الويب الوهمي عشان الاستضافة تحسب السكربت شغال
app = Flask("")


@app.route("/")
def home():
  return "Script Pinger is active and running 24/7!"


def run_web():
  # تشغيل السيرفر على بورت 8080
  app.run(host="0.0.0.0", port=8080)


def keep_alive():
  t = threading.Thread(target=run_web)
  t.start()


# 2. سكربت الـ Ping اللي يزور الرابط كل 5 دقائق
def pinger_loop():
  # حط الرابط اللي تبيه يدخله هنا
  target_url = "https://your-target-link.com"

  # 300 ثانية = 5 دقائق
  interval = 300

  print(
      f"-> بدأ تشغيل نظام الـ Ping! سيتم زيارة الرابط: {target_url} كل 5 دقائق."
  )

  while True:
    time.sleep(interval)
    try:
      response = requests.get(target_url)
      print(
          f"[تم بنجاح] الرمز المستلم: {response.status_code} - الوقت: {time.strftime('%H:%M:%S')}"
      )
    except Exception as e:
      print(f"[خطأ] فشل الاتصال بالرابط: {e}")


if __name__ == "__main__":
  # تشغيل سيرفر الويب الوهمي أولاً في الخلفية
  keep_alive()

  # تشغيل حلقة الـ Ping في الخلفية
  ping_thread = threading.Thread(target=pinger_loop)
  ping_thread.start()

  print("تم تشغيل النظام بالكامل بنجاح!")

