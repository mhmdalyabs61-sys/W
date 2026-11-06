import threading
import time
from flask import Flask
import requests

# 1. سيرفر ويب وهمي عشان استضافة Render تعتبر الأداة شغالة 24 ساعة وما تنزلها
app = Flask("")


@app.route("/")
def home():
  return "Pinger Tool is active and running 24/7!"


def run_web():
  app.run(host="0.0.0.0", port=8080)


def keep_alive():
  t = threading.Thread(target=run_web)
  t.start()


# 2. الأداة الأساسية: تدخل على الرابط حقك كل 5 دقائق
def pinger_loop():
  # حط رابط مشروعك أو الرابط اللي تبيه بين القوسين هنا
  target_url = "https://your-project-link.com"

  # 300 ثانية = 5 دقائق بالضبط
  interval = 300

  print(
      f"-> بدأت الأداة العمل! سيتم زيارة الرابط: {target_url} كل 5 دقائق بشكل"
      " مستمر."
  )

  while True:
    time.sleep(interval)
    try:
      response = requests.get(target_url)
      print(
          f"[تم بنجاح] الرمز المستلم: {response.status_code} - الوقت:"
          f" {time.strftime('%H:%M:%S')}"
      )
    except Exception as e:
      print(f"[خطأ] ما قدر يفتح الرابط: {e}")


if __name__ == "__main__":
  # تشغيل السيرفر الوهمي في الخلفية
  keep_alive()

  # تشغيل الأداة في الخلفية
  ping_thread = threading.Thread(target=pinger_loop)
  ping_thread.start()

  print("تم تشغيل الأداة بالكامل بنجاح!")
