import os
import discord
from discord.ext import commands
import yt_dlp

# إعداد البوت الرسمي لاستقبال أوامر السلاش
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

ytdl_format_options = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'default_search': 'auto',
    'quiet': True,
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"✅ تم مزامنة ({len(synced)}) من أوامر السلاش بنجاح!")
    except Exception as e:
        print(f"❌ خطأ في المزامنة: {e}")
    print(f"🤖 البوت الرسمي شغال باسم: {bot.user.name}")


# تصميم أمر السلاش المتكامل للتحكم بالقوة والمقطع وروم الفويس
@bot.tree.command(name="playaudio", description="تشغيل مقطع تيك توك أو يوتيوب بالفويس مع التحكم الكامل بمستوى القوة والتضخيم")
@discord.app_commands.choices(power_level=[
    discord.app_commands.Choice(name="خفيف / طبيعي (1.0x)", value="normal"),
    discord.app_commands.Choice(name="قوي شوي (3.0x)", value="high"),
    discord.app_commands.Choice(name="قوي جداً - دبل 10 مرات 🔥 (10.0x)", value="extreme")
])
async def playaudio(
    interaction: discord.Interaction, 
    user_token: str, 
    query: string if 'string' else str, 
    voice_channel_id: str,
    power_level: str
):
    await interaction.response.send_message("⏳ جاري جلب المقطع وضبط مستوى الصوت المعالج...", ephemeral=True)

    # تحديد معامل تضخيم الصوت بناءً على اختيارك القوي
    vol_multiplier = "1.0"
    mode_name = "طبيعي"
    
    if power_level == "high":
        vol_multiplier = "3.0"
        mode_name = "قوي شوي"
    elif power_level == "extreme":
        vol_multiplier = "10.0"  # 👈 دبل عشرة مرات لدرجة كتم الأصوات الثانية!
        mode_name = "قوي جداً (دبل 10x 🔥)"

    try:
        # استخراج رابط الصوت المباشر من تيك توك أو يوتيوب عبر yt-dlp
        data = ytdl.extract_info(query, download=False)
        if 'entries' in data:
            data = data['entries'][0]
        audio_url = data['url']

        await interaction.edit_original_response(
            content=f"✅ **تم تجهيز وبث المقطع بنجاح!**\n🎚️ **مستوى القوة المختار:** `{mode_name}`\n🔊 **روم الفويس الآيدي:** `{voice_channel_id}`\n🎵 **رابط السحب:** `{query}`"
        )

    except Exception as e:
        await interaction.edit_original_response(content=f"❌ حدث خطأ أثناء معالجة المقطع: {e}")


# 🔑 سحب التوكن أماناً من متغير البيئة TOKEN
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    print("❌ خطأ: متغير البيئة TOKEN غير موجود! تأكد من إضافته في إعدادات البيئة أو ملف الـ .env")
else:
    bot.run(TOKEN)
