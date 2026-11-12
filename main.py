import os
import discord
from discord.ext import commands
import yt_dlp

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# إعدادات متطورة لتجاوز حماية تيك توك ومنصات الصوت
ytdl_format_options = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'default_search': 'ytsearch',  # نغيرها لبحث موجه يمنع أخطاء تيك توك النصية
    'quiet': True,
    # خداع تيك توك وروابطه برؤوس متصفح حقيقي (User-Agent) لتفادي الحظر
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
    }
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

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
    print(f"🤖 البوت شغال باسم: {bot.user.name}")

@bot.tree.command(name="playaudio", description="تشغيل مقطع تيك توك أو يوتيوب بالفويس مع تجاوز الحماية والتضخيم")
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
    await interaction.response.send_message("⏳ جاري تجاوز حماية المنصة والاتصال بالفويس...", ephemeral=True)

    vol_multiplier = "1.0"
    mode_name = "طبيعي"
    
    if power_level == "high":
        vol_multiplier = "3.0"
        mode_name = "قوي شوي"
    elif power_level == "extreme":
        vol_multiplier = "10.0"
        mode_name = "قوي جداً (دبل 10x 🔥)"

    try:
        channel_id_int = int(voice_channel_id)
        channel = bot.get_channel(channel_id_int)
        
        if not channel or not isinstance(channel, discord.VoiceChannel):
            await interaction.edit_original_response(content="❌ آيدي روم الفويس خطأ أو أن الروم غير موجود!")
            return

        # تنفيذ السحب مع إعدادات الحماية الجديدة
        data = ytdl.extract_info(query, download=False)
        if 'entries' in data:
            entries = data['entries']
            if not entries:
                await interaction.edit_original_response(content="❌ عذراً، لم يتم العثور على أي مقطع مطابق. جرب اختصار العنوان أو وضع كلمات مفتاحية واضحة.")
                return
            data = entries[0]
            
        audio_url = data.get('url')
        title = data.get('title', 'مقطع تيك توك')

        if not audio_url:
            await interaction.edit_original_response(content="❌ حماية تيك توك منعت استخراج الرابط المباشر.")
            return

        if interaction.guild.voice_client is not None:
            await interaction.guild.voice_client.move_to(channel)
            voice_client = interaction.guild.voice_client
        else:
            voice_client = await channel.connect()

        current_ffmpeg_options = ffmpeg_options.copy()
        current_ffmpeg_options['options'] += f' -filter:a "volume={vol_multiplier}"'

        source = discord.FFmpegPCMAudio(audio_url, **current_ffmpeg_options)

        if voice_client.is_playing():
            voice_client.stop()

        voice_client.play(source, after=lambda e: print(f'خطأ صوتي: {e}' if e else 'تم التشغيل بنجاح'))

        await interaction.edit_original_response(
            content=f"✅ **تم تجاوز الحماية وبث المقطع بنجاح!**\n🎵 **العنوان:** `{title}`\n🎚️ **القوة:** `{mode_name}`\n🔊 **الروم:** `{channel.name}`"
        )

    except Exception as e:
        await interaction.edit_original_response(content=f"❌ حدث خطأ أثناء المعالجة: `{e}`")

TOKEN = os.getenv("TOKEN")
if TOKEN:
    bot.run(TOKEN)
