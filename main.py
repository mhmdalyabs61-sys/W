import asyncio
import os
import discord
from discord import app_commands
import yt_dlp

# قراءة التوكن من متغيرات البيئة (أمنياً لكي لا ينكشف في جيثب) أو تعيينه عبر متغير فارغ
TOKEN = os.getenv("DISCORD_TOKEN", "YOUR_TOKEN_HERE")

# إعدادات العميل (Self-bot)
class MyClient(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # مزامنة أوامر السلاش مع ديسكورد
        await self.tree.sync()
        print("[*] تم مزامنة أوامر السلاش بنجاح.")

client = MyClient()

# إعدادات تحميل الصوت
ytdl_format_options = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'quiet': True,
}
ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

@client.event
async def on_ready():
    print(f"[+] تم تسجيل الدخول بنجاح بحساب: {client.user}")
    print("[+] السكربت جاهز لاستقبال أوامر السلاش!")

# أمر سلاش لتشغيل الصوت
@client.tree.command(name="playaudio", description="يشغل الصوت من رابط يوتيوب باستخدام التوكن والرابط")
@app_commands.describe(
    url="رابط المقطع الصوتي أو يوتيوب",
    channel_id="ايدي الروم الصوتي المراد الانضمام إليه"
)
async def playaudio(interaction: discord.Interaction, url: str, channel_id: str):
    # الرد السريع لأن معالجة الصوت قد تأخذ ثواني
    await interaction.response.defer(thinking=True)

    try:
        target_channel_id = int(channel_id)
        channel = client.get_channel(target_channel_id)
        
        if not channel or not isinstance(channel, discord.VoiceChannel):
            await interaction.followup.send("[-] ايدي الروم الصوتي غير صحيح أو ليس روم صوتي!")
            return

        # الاتصال بالروم الصوتي
        if interaction.guild and interaction.guild.voice_client:
            voice_client = interaction.guild.voice_client
            await voice_client.move_to(channel)
        else:
            voice_client = await channel.connect(reconnect=False, self_deaf=True)

        await interaction.followup.send("[*] جاري جلب الصوت ومعالجته...")

        # استخراج بيانات الصوت
        data = await asyncio.get_event_loop().run_in_executor(
            None, lambda: ytdl.extract_info(url, download=False)
        )
        audio_url = data['url']

        source = discord.FFmpegPCMAudio(audio_url, options="-vn")

        if voice_client.is_playing():
            voice_client.stop()

        voice_client.play(source, after=lambda e: print(f"انتهى التشغيل: {e}"))
        
        await interaction.followup.send(f"[+] تم تشغيل المقطع بنجاح في الروم: `{channel.name}`!")

    except Exception as e:
        await interaction.followup.send(f"[-] حدث خطأ أثناء التشغيل: {e}")

if __name__ == "__main__":
    # التحقق من أن التوكن تم وضعه ولا يساوي القيمة الافتراضية
    active_token = TOKEN
    if active_token == "YOUR_TOKEN_HERE" or not active_token:
        print("[!] لم يتم العثور على توكن في متغيرات البيئة.")
        active_token = input("أدخل توكن حسابك الشخصي يدوياً: ").strip()
    
    if active_token:
        try:
            client.run(active_token)
        except Exception as e:
            print(f"[-] فشل تسجيل الدخول بالتوكن: {e}")
    else:
        print("[-] لم يتم إدخال التوكن، تم إيقاف السكربت.")
