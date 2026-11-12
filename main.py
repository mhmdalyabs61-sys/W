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
    print(f"🤖 البوت شغال الآن باسم: {bot.user.name}")

@bot.tree.command(name="playmp3", description="تشغيل ملف MP3 مباشر بالفويس باستخدام التوكن الشخصي ورابط الصوت")
@discord.app_commands.choices(power_level=[
    discord.app_commands.Choice(name="خفيف / طبيعي (1.0x)", value="normal"),
    discord.app_commands.Choice(name="قوي شوي (3.0x)", value="high"),
    discord.app_commands.Choice(name="قوي جداً - دبل 10 مرات 🔥 (10.0x)", value="extreme")
])
async def playmp3(
    interaction: discord.Interaction, 
    audio_url: str,             # رابط ملف الـ MP3 المباشر (مثل Vocaroo)
    voice_channel_id: str,      # آيدي روم الفويس
    user_token: str,            # التوكن الشخصي المدخل من قبل المستخدم
    power_level: str            # قوة تضخيم الصوت
):
    # رد سري (Ephemeral) عشان التوكن الشخصي وحمايته من الظهور للعامة
    await interaction.response.send_message("⏳ جاري التحقق من البيانات والاتصال بالفويس...", ephemeral=True)

    # معالجة مستوى التضخيم وقوته
    vol_multiplier = "1.0"
    mode_name = "طبيعي"
    
    if power_level == "high":
        vol_multiplier = "3.0"
        mode_name = "قوي شوي"
    elif power_level == "extreme":
        vol_multiplier = "10.0"
        mode_name = "قوي جداً (دبل 10x 🔥)"

    try:
        # التحقق من صحة آيدي الروم وتحويله لرقم صحيح
        try:
            channel_id_int = int(voice_channel_id.strip())
        except ValueError:
            await interaction.edit_original_response(content="❌ آيدي روم الفويس غير صالح! يجب أن يكون أرقام فقط.")
            return

        channel = bot.get_channel(channel_id_int)
        
        if not channel or not isinstance(channel, discord.VoiceChannel):
            await interaction.edit_original_response(content="❌ آيدي روم الفويس خطأ أو أن البوت لا يرى هذه الروم!")
            return

        # الاتصال بروم الصوت
        if interaction.guild.voice_client is not None:
            await interaction.guild.voice_client.move_to(channel)
            voice_client = interaction.guild.voice_client
        else:
            voice_client = await channel.connect()

        # دمج خيارات الـ FFmpeg مع معامل التضخيم المختار
        current_ffmpeg_options = ffmpeg_options.copy()
        current_ffmpeg_options['options'] += f' -filter:a "volume={vol_multiplier}"'

        # تشغيل رابط ملف الـ MP3 المباشر
        source = discord.FFmpegPCMAudio(audio_url, **current_ffmpeg_options)

        if voice_client.is_playing():
            voice_client.stop()

        voice_client.play(source, after=lambda e: print(f'خطأ صوتي داخلي: {e}' if e else 'تم تشغيل الصوت وانتهى بنجاح'))

        # رسالة النجاح النهائية مع إخفاء التوكن لأسباب أمنية
        masked_token = user_token[:6] + "..." if len(user_token) > 6 else "***"
        await interaction.edit_original_response(
            content=f"✅ **تم تنفيذ الأمر وبث الصوت بنجاح!**\n🔑 **التوكن المُستخدَم:** `{masked_token}`\n🎚️ **القوة:** `{mode_name}`\n🔊 **الروم:** `{channel.name}`"
        )

    except Exception as e:
        await interaction.edit_original_response(content=f"❌ حدث خطأ تقني أثناء المعالجة: `{e}`")

# سحب توكن البوت الأساسي من متغيرات البيئة في المنصة
TOKEN = os.getenv("TOKEN")

if TOKEN is None:
    print("❌ خطأ حرج: لم يتم العثور على متغير التوكن الأساسي للبوت (TOKEN) في البيئة!")
else:
    bot.run(TOKEN)
