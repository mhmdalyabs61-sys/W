import os
import discord
from discord.ext import commands

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

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
    print(f"🤖 البوت الرسمي شغال الآن باسم: {bot.user.name}")

@bot.tree.command(name="playmp3", description="تشغيل ملف صوتي مباشر MP3 بالفويس مع ميزة التضخيم")
@discord.app_commands.choices(power_level=[
    discord.app_commands.Choice(name="خفيف / طبيعي (1.0x)", value="normal"),
    discord.app_commands.Choice(name="قوي شوي (3.0x)", value="high"),
    discord.app_commands.Choice(name="قوي جداً - دبل 10 مرات 🔥 (10.0x)", value="extreme")
])
async def playmp3(
    interaction: discord.Interaction, 
    audio_url: str, 
    voice_channel_id: str,
    power_level: str
):
    await interaction.response.send_message("⏳ جاري الاتصال بالفويس وبث الملف الصوتي...", ephemeral=True)

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

        if interaction.guild.voice_client is not None:
            await interaction.guild.voice_client.move_to(channel)
            voice_client = interaction.guild.voice_client
        else:
            voice_client = await channel.connect()

        current_ffmpeg_options = ffmpeg_options.copy()
        current_ffmpeg_options['options'] += f' -filter:a "volume={vol_multiplier}"'

        # تشغيل رابط ملف الـ MP3 المباشر
        source = discord.FFmpegPCMAudio(audio_url, **current_ffmpeg_options)

        if voice_client.is_playing():
            voice_client.stop()

        voice_client.play(source, after=lambda e: print(f'خطأ صوتي: {e}' if e else 'تم التشغيل بنجاح'))

        await interaction.edit_original_response(
            content=f"✅ **تم تشغيل ملف الـ MP3 بنجاح!**\n🎚️ **القوة:** `{mode_name}`\n🔊 **الروم:** `{channel.name}`"
        )

    except Exception as e:
        await interaction.edit_original_response(content=f"❌ حدث خطأ أثناء المعالجة: `{e}`")

# سحب التوكن تلقائياً من متغيرات البيئة (Environment Variables) لجتهاب/المنصة
TOKEN = os.getenv("TOKEN")

if TOKEN is None:
    print("❌ خطأ: لم يتم العثور على متغير التوكن (TOKEN) في البيئة!")
else:
    bot.run(TOKEN)
