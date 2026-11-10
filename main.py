import os
import imageio_ffmpeg

# تعيين مسار الـ ffmpeg تلقائياً
os.environ["PATH"] += os.pathsep + os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe())

import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp

class UniversalSelfBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.voice_states = True
        # هنا السر: self_bot=True عشان يشتغل كحساب شخصي حر طليق بأي سيرفر
        super().__init__(command_prefix="!", intents=intents, self_bot=True)

    async def setup_hook(self):
        # مزامنة أوامر السلاش (للسلف بوت تظهر عندك بالسيرفرات اللي أنت فيها)
        await self.tree.sync()
        print(f"تم تسجيل الدخول بنجاح بالحساب الشخصي: {self.user} (ID: {self.user.id})")
        print("---------------------------------------------")

client = UniversalSelfBot()

@client.event
async def on_ready():
    print(f"السلف-بوت العالمي جاهز ويستجيب في كل السيرفرات!")

@client.tree.command(name="play", description="تشغيل مقطع صوتي في أي روم صوتي عبر الحساب الشخصي")
@app_commands.describe(
    url="رابط المقطع (تيك توك أو غيره)",
    channel_id="آيدي الروم الصوتي",
    volume_mode="مستوى الصوت"
)
@app_commands.choices(volume_mode=[
    app_commands.Choice(name="خفيف (50%)", value="خفيف"),
    app_commands.Choice(name="عادي (100%)", value="عادي"),
    app_commands.Choice(name="قوي (150%)", value="قوي"),
    app_commands.Choice(name="قوي جداً (200%)", value="قوي_جدا"),
])
async def play(interaction: discord.Interaction, url: str, channel_id: str, volume_mode: str = "عادي"):
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

    voice_channel = client.get_channel(ch_id)
    if not voice_channel or not isinstance(voice_channel, discord.VoiceChannel):
        await interaction.followup.send("❌ لم أتمكن من العثور على الروم الصوتي بهذا الآيدي، تأكد منه!")
        return

    try:
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

        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(url, download=False)
            url2 = info.get('url', None)
            title = info.get('title', 'فيديو')

        if not url2:
            await interaction.followup.send("❌ فشل في استخراج رابط الصوت المباشر.")
            return

        if voice_client.is_playing():
            voice_client.stop()

        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(url2, executable=ffmpeg_path, **FFMPEG_OPTIONS)
        )
        source.volume = vol_multiplier  

        voice_client.play(source, after=lambda e: print(f'انتهى التشغيل: {e}'))

        await interaction.followup.send(f"▶️ دخل الحساب الروم وشغل: **{title}** (الوضع: {volume_mode})")

    except Exception as e:
        await interaction.followup.send(f"❌ حدث خطأ أثناء التشغيل: {e}")

@client.tree.command(name="leave", description="إخراج الحساب من الروم الصوتي")
async def leave(interaction: discord.Interaction):
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("👋 طلعت من الروم.")
    else:
        await interaction.response.send_message("❌ أنا مو متصل بأي روم أصلاً!", ephemeral=True)

token = os.getenv("DISCORD_TOKEN")
if token:
    client.run(token)
else:
    print("خطأ: لم يتم العثور على متغير DISCORD_TOKEN في البيئة!")
