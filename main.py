import os
import discord
from discord.ext import commands
import yt_dlp

# إعداد البوت مع صلاحيات كاملة
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

ytdl_format_options = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'default_search': 'auto',
    'quiet': True,
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

# إعدادات تشغيل الصوت مع الـ FFmpeg وفلتر التضخيم
# ملاحظة: إذا كان الفلتر 10x نستخدم "volume=10.0"
ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"✅ تم مزامنة ({len(synced)}) من أوامر السلاش بنجاح!")
    except Exception as e:
        print(f"❌ خطأ في المزامنة: {e}")
    print(f"🤖 البوت الرسمي شغال باسم: {bot.user.name}")

@bot.tree.command(name="playaudio", description="تشغيل مقطع تيك توك أو يوتيوب بالفويس الفعلي مع التحكم بالتضخيم")
@discord.app_commands.choices(power_level=[
    discord.app_commands.Choice(name="خفيف / طبيعي (1.0x)", value="normal"),
    discord.app_commands.Choice(name="قوي شوي (3.0x)", value="high"),
    discord.app_commands.Choice(name="قوي جداً - دبل 10 مرات 🔥 (10.0x)", value="extreme")
])
async def playaudio(
    interaction: discord.Interaction, 
    user_token: str, 
    query: str, 
    voice_channel_id: str,
    power_level: str
):
    await interaction.response.send_message("⏳ جاري الاتصال بروم الفويس وسحب الصوت...", ephemeral=True)

    # تحديد مستوى التضخيم (Volume Filter)
    vol_multiplier = "1.0"
    mode_name = "طبيعي"
    
    if power_level == "high":
        vol_multiplier = "3.0"
        mode_name = "قوي شوي"
    elif power_level == "extreme":
        vol_multiplier = "10.0"
        mode_name = "قوي جداً (دبل 10x 🔥)"

    try:
        # البحث عن الروم الصوتي باستخدام الآيدي المدخل
        channel_id_int = int(voice_channel_id)
        channel = bot.get_channel(channel_id_int)
        
        if not channel or not isinstance(channel, discord.VoiceChannel):
            await interaction.edit_original_response(content="❌ آيدي روم الفويس خطأ أو أن الروم غير موجود! تأكد من آيدي الروم.")
            return

        # استخراج معلومات الصوت عبر yt-dlp
        data = ytdl.extract_info(query, download=False)
        if 'entries' in data:
            entries = data['entries']
            if not entries:
                await interaction.edit_original_response(content="❌ عذراً، لم يتم العثور على أي مقطع مطابق لبحثك.")
                return
            data = entries[0]
            
        audio_url = data.get('url')
        title = data.get('title', 'مقطع صوتي')

        if not audio_url:
            await interaction.edit_original_response(content="❌ لم يتمكن البوت من استخراج رابط الصوت المباشر.")
            return

        # الاتصال بروم الفويس إذا لم يكن متصلاً مسبقاً
        if interaction.guild.voice_client is not None:
            await interaction.guild.voice_client.move_to(channel)
            voice_client = interaction.guild.voice_client
        else:
            voice_client = await channel.connect()

        # تجهيز مصدر الصوت مع فلتر التضخيم المطلوب
        # ندمج فلتر الـ volume بناءً على القوة المختارة
        current_ffmpeg_options = ffmpeg_options.copy()
        current_ffmpeg_options['options'] += f' -filter:a "volume={vol_multiplier}"'

        source = discord.FFmpegPCMAudio(audio_url, **current_ffmpeg_options)

        # تشغيل الصوت داخل الفويس إذا ما كان يشتغل شي حالياً
        if voice_client.is_playing():
            voice_client.stop()

        voice_client.play(source, after=lambda e: print(f'انتهى التشغيل أو حدث خطأ: {e}' if e else 'تم تشغيل الصوت بنجاح'))

        await interaction.edit_original_response(
            content=f"✅ **جاري بث المقطع الآن في الفويس!**\n🎵 **العنوان:** `{title}`\n🎚️ **مستوى التضخيم:** `{mode_name}`\n🔊 **الروم:** `{channel.name}`"
        )

    except Exception as e:
        await interaction.edit_original_response(content=f"❌ حدث خطأ أثناء تشغيل الصوت: `{e}`")

# تشغيل البوت عبر التوكن الآمن
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    print("❌ خطأ: متغير البيئة TOKEN غير موجود!")
else:
    bot.run(TOKEN)
