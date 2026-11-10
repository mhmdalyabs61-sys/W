import discord
from discord.ext import commands
import asyncio
import os

# ==========================================
# إعدادات البوت الأساسي (الذي يستقبل الأمر !join)
# ==========================================
# ملاحظة: يفضل دائماً قراءة التوكن من Environment Variables لسلامة حسابك على GitHub
BOT_TOKEN = os.getenv("DISCORD_TOKEN", "حط_توكن_البوت_الأساسي_هنا")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"==================================================")
    print(f"[+] البوت الأساسي اشتغل بنجاح كـ: {bot.user.name}")
    print(f"[+] جاهز لاستقبال أمر !join من أي مكان في ديسكورد.")
    print(f"==================================================")

# ==========================================
# استقبال أمر التشغيل والتحكم بالفويس
# ==========================================
@bot.command(name="join", description="تشغيل الحساب الشخصي ودخوله الفويس بالتوكن المستخرج")
async def join_voice_cmd(ctx, user_token: str, channel_id: str, audio_url: str, volume_level: str = "normal"):
    # حذف رسالة الأمر فوراً لحماية التوكن والخصوصية من المتواجدين بالسيرفر
    try:
        await ctx.message.delete()
    except Exception:
        pass

    await ctx.send("⏳ جاري تنفيذ الطلب، ومعالجة توكن الحساب الشخصي للدخول إلى الفويس...", delete_after=5)
    
    # تشغيل الحساب الشخصي (Self-bot) في مهمة خلفية لكي لا يجمد البوت الأساسي
    asyncio.create_task(run_selfbot_voice(ctx, user_token, int(channel_id), audio_url, volume_level))

# ==========================================
# دالة تشغيل الحساب الشخصي والاتصال بالصوت
# ==========================================
async def run_selfbot_voice(ctx, token: str, channel_id: int, url: str, level: str):
    try:
        # إعدادات الـ Client الخاص بالحساب الشخصي
        client_intents = discord.Intents.default()
        client_intents.message_content = True
        user_client = discord.Client(intents=client_intents)

        @user_client.event
        async def on_ready():
            print(f"[+] تم تسجيل الدخول بالحساب الشخصي بنجاح: {user_client.user}")
            try:
                print(f"[*] جاري البحث عن الروم الصوتي برقم ID: {channel_id}...")
                # جلب الروم الصوتي مباشرة من سيرفرات ديسكورد بالـ API لضمان عدم رجوع قيمة فارغة
                channel = await user_client.fetch_channel(channel_id)
                
                if channel:
                    print(f"[+] تم العثور على الروم: {channel.name}. جاري الاتصال...")
                    vc = await channel.connect()
                    print("[+] تم الاتصال بالقناة الصوتية بنجاح!")
                    
                    # خريطة مستويات الصوت المتاحة
                    volume_mapping = {
                        "low": 0.3,
                        "normal": 1.0,
                        "high": 1.5,
                        "max": 2.0
                    }
                    selected_volume = volume_mapping.get(level, 1.0)

                    # إعدادات FFmpeg لمعالجة الصوت ودرجة العلو
                    ffmpeg_options = {
                        'options': f'-vn -filter:a "volume={selected_volume}"'
                    }
                    
                    audio_source = discord.FFmpegPCMAudio(url, **ffmpeg_options)
                    
                    if not vc.is_playing():
                        vc.play(audio_source, after=lambda e: print(f'[-] انتهى التشغيل أو حدث خطأ صوتي: {e}'))
                        print(f"✅ جاري تشغيل المقطع الآن بمستوى صوت: {level}")
                        await ctx.send(f"✅ تم دخول حسابك الشخصي للفويس بنجاح وتشغيل المقطع بمستوى صوت: **{level}**!")
                else:
                    print("[-] لم يتم العثور على الروم الصوتي المحدد.")
                    await ctx.send("❌ لم يتم العثور على الروم الصوتي، تأكد من صحة الـ ID.")
                    
            except Exception as inner_e:
                print(f"[-] خطأ أثناء جلب الروم أو الاتصال بالصوت: {inner_e}")
                await ctx.send(f"❌ فشل الاتصال بالفويس: `{inner_e}`")

        # بدء تشغيل الحساب الشخصي بالتوكن المرسل
        await user_client.start(token)

    except Exception as e:
        print(f"[-] خطأ خطير في تشغيل السيلف بوت: {e}")
        await ctx.send(f"❌ خطأ تقني في تشغيل الحساب الشخصي: `{e}`")

# ==========================================
# تشغيل السكربت بالكامل
# ==========================================
if __name__ == "__main__":
    if BOT_TOKEN and BOT_TOKEN != "حط_توكن_البوت_الأساسي_هنا":
        bot.run(BOT_TOKEN)
    else:
        print("❌ خطأ: يرجى وضع توكن البوت الأساسي الصحيح في متغير BOT_TOKEN أو عبر Environment Variables.")
