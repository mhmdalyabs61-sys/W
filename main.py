import os
import imageio_ffmpeg

# تعيين مسار الـ ffmpeg تلقائياً من المكتبة اللي حملناها
os.environ["PATH"] += os.pathsep + os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe())

import os
import discord
from discord.ext import commands
import yt_dlp

# إعداد السلف-بوت باستخدام حسابك الشخصي
class MySelfBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", self_bot=True)

    async def setup_hook(self):
        print(f"تم تسجيل الدخول بنجاح بحسابك الشخصي: {self.user} (ID: {self.user.id})")
        print("---------------------------------------------")

client = MySelfBot()

@client.event
async def on_ready():
    print(f"السلف-بوت جاهز ويعمل بحسابك الشخصي الآن!")

# أمر التشغيل: !play [الرابط] [آيدي الروم] [مستوى الصوت: خفيف / عادي / قوي / قوي_جدا]
@client.command(name="play")
async def play(ctx, url: str, channel_id: int, volume_mode: str = "عادي"):
    
    # تحديد نسب الصوت بناءً على الخيار اللي تكتبه
    volumes = {
        "خفيف": 0.5,      # 50%
        "عادي": 1.0,      # 100%
        "قوي": 1.5,       # 150%
        "قوي_جدا": 2.0    # 200%
    }
    
    # اختيار النسبة أو جعلها افتراضية إذا كتب شي ثاني
    vol_multiplier = volumes.get(volume_mode, 1.0)

    # جلب الروم الصوتي باستخدام الآيدي المحدد
    voice_channel = client.get_channel(channel_id)
    if not voice_channel or not isinstance(voice_channel, discord.VoiceChannel):
        await ctx.send("❌ لم أتمكن من العثور على الروم الصوتي بهذا الآيدي، تأكد منه!")
        return

    try:
        # إدخال حسابك الشخصي للروم الصوتي وبث الصوت للجميع
        if ctx.guild.voice_client is None:
            voice_client = await voice_channel.connect()
        else:
            voice_client = ctx.guild.voice_client
            await voice_client.move_to(voice_channel)

        YDL_OPTIONS = {'format': 'bestaudio', 'noplaylist': 'True'}
        FFMPEG_OPTIONS = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }

        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(url, download=False)
            url2 = info['url']
            title = info.get('title', 'فيديو')

        if voice_client.is_playing():
            voice_client.stop()

        # تشغيل الصوت للجميع عبر حسابك مع التحكم بالقوة المطلوبة
        source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(url2, **FFMPEG_OPTIONS))
        source.volume = vol_multiplier  

        voice_client.play(source, after=lambda e: print(f'انتهى التشغيل: {e}'))

        await ctx.send(f"▶️ دخل حسابك الروم وشغل المقطع للجميع: **{title}** (الوضع: {volume_mode})")

    except Exception as e:
        await ctx.send(f"❌ حدث خطأ أثناء التشغيل: {e}")

# أمر إخراج حسابك من الروم: !leave
@client.command(name="leave")
async def leave(ctx):
    if ctx.guild.voice_client:
        await ctx.guild.voice_client.disconnect()
        await ctx.send("👋 طلعت من الروم الصوتي.")
    else:
        await ctx.send("❌ حسابي مو متصل بأي روم أصلاً!")

# تشغيل السلف-بوت باستخدام توكن حسابك الشخصي في المنصة
token = os.getenv("DISCORD_TOKEN")
if token:
    client.run(token)
else:
    print("خطأ: لم يتم العثور على متغير DISCORD_TOKEN في البيئة!")
