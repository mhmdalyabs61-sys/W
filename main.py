import os
import imageio_ffmpeg

# تعيين مسار الـ ffmpeg تلقائياً من المكتبة مباشرة
os.environ["PATH"] += os.pathsep + os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe())

import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp

# إعداد السلف-بوت باستخدام حسابك الشخصي
class MySelfBot(commands.Bot):
    def __init__(self):
        # استخدام self_bot=True عشان يفهم إنه حساب شخصي مو بوت رسمي
        super().__init__(command_prefix="!", self_bot=True)

    async def setup_hook(self):
        # مزامنة أوامر السلاش للسلف-بوت
        await self.tree.sync()
        print(f"تم تسجيل الدخول بنجاح بالحساب الشخصي: {self.user} (ID: {self.user.id})")
        print("---------------------------------------------")

client = MySelfBot()

@client.event
async def on_ready():
    print(f"السلف-بوت الشخصي جاهز ويعمل الآن!")

# أمر السلاش: /play
@client.tree.command(name="play", description="تشغيل مقطع صوتي عبر الحساب الشخصي في روم صوتي")
@app_commands.describe(
    url="رابط المقطع (مثل تيك توك)",
    channel_id="آيدي الروم الصوتي المراد الدخول إليه",
    volume_mode="مستوى الصوت المطلوب"
)
@app_commands.choices(volume_mode=[
    app_commands.Choice(name="خفيف (50%)", value="خفيف"),
    app_commands.Choice(name="عادي (100%)", value="عادي"),
    app_commands.Choice(name="قوي (150%)", value="قوي"),
    app_commands.Choice(name="قوي جداً (200%)", value="قوي_جدا"),
])
async def play(interaction: discord.Interaction, url: str, channel_id: str, volume_mode: str = "عادي"):
    # الرد الفوري عشان ديسكورد ما يعطيني خطأ انقضاء المهلة
    await interaction.response.defer(thinking=True)

    volumes = {
        "خفيف": 0.5,
        "عادي": 1.0,
        "قوي": 1.5,
        "قوي_جدا": 2.0
    }
    vol_multiplier = volumes.get(volume_mode, 1.0)

    try:
        ch_id = int(channel_id)
    except ValueError:
        await interaction.followup.send("❌ آيدي الروم الصوتي يجب أن يكون أرقاماً فقط!")
        return

    # جلب الروم الصوتي
    voice_channel = client.get_channel(ch_id)
    if not voice_channel or not isinstance(voice_channel, discord.VoiceChannel):
        await interaction.followup.send("❌ لم أتمكن من العثور على الروم الصوتي بهذا الآيدي، تأكد منه!")
        return

    try:
        # الاتصال بالروم الصوتي
        if interaction.guild.voice_client is None:
            voice_client = await voice_channel.connect()
        else:
            voice_client = interaction.guild.voice_client
            await voice_client.move_to(voice_channel)

        YDL_OPTIONS = {
            'format': 'bestaudio/best',
            'noplaylist': True,
        }
        
        FFMPEG_OPTIONS = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }

        # استخراج رابط الصوت المباشر
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(url, download=False)
            url2 = info.get('url', None)
            title = info.get('title', 'فيديو')

        if not url2:
            await interaction.followup.send("❌ فشل في استخراج رابط الصوت المباشر من هذا الرابط.")
            return

        if voice_client.is_playing():
            voice_client.stop()

        # تشغيل الصوت
        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(url2, executable=ffmpeg_path, **FFMPEG_OPTIONS)
        )
        source.volume = vol_multiplier  

        voice_client.play(source, after=lambda e: print(f'انتهى التشغيل: {e}'))

        await interaction.followup.send(f"▶️ دخل الحساب الروم وشغل المقطع: **{title}** (الوضع: {volume_mode})")

    except Exception as e:
        await interaction.followup.send(f"❌ حدث خطأ أثناء التشغيل: {e}")

# أمر إخراج الحساب من الروم: /leave
@client.tree.command(name="leave", description="إخراج الحساب الشخصي من الروم الصوتي")
async def leave(interaction: discord.Interaction):
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("👋 طلعت من الروم الصوتي.")
    else:
        await interaction.response.send_message("❌ أنا مو متصل بأي روم أصلاً!", ephemeral=True)

# تشغيل السلف-بوت باستخدام توكن حسابك الشخصي (أو الحساب الوهمي) في رايلواي
token = os.getenv("DISCORD_TOKEN")
if token:
    client.run(token)
else:
    print("خطأ: لم يتم العثور على متغير DISCORD_TOKEN في البيئة!")
