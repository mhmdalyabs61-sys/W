import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import os

# إعداد البوت الرسمي
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"[+] تم تسجيل الدخول كـ بوت رسمي: {bot.user.name}")
    try:
        synced = await bot.tree.sync()
        print(f"[+] تم مزامنة {len(synced)} أمر سلاش بنجاح.")
    except Exception as e:
        print(f"[-] خطأ في مزامنة الأوامر: {e}")

# أمر السلاش مع إضافة رابط المقطع ومستوى الصوت
@bot.tree.command(name="join_voice", description="إدخال الحساب الشخصي للروم الصوتي مع تشغيل مقطع وبمستوى صوت محدد")
@app_commands.describe(
    user_token="التوكن الشخصي للحساب الذي سيدخل الفويس",
    channel_id="ID الروم الصوتي المراد الدخول إليه",
    audio_url="رابط المقطع المراد تشغيله (يوتيوب أو رابط مباشر)",
    volume_level="اختر قوة الصوت: خفيف، عادي، قوي، قوي_جدا"
)
@app_commands.choices(volume_level=[
    app_commands.Choice(name="خفيف (30%)", value="low"),
    app_commands.Choice(name="عادي (100%)", value="normal"),
    app_commands.Choice(name="قوي (150%)", value="high"),
    app_commands.Choice(name="قوي جداً (200%)", value="max")
])
async def join_voice(
    interaction: discord.Interaction, 
    user_token: str, 
    channel_id: str, 
    audio_url: str, 
    volume_level: str
):
    # رد مخفي عشان التوكن يكون بأمان تام وما يظهر لأحد غيرك
    await interaction.response.send_message("⏳ جاري تنفيذ الطلب ودخول الحساب الفويس...", ephemeral=True)

    # تشغيل الحساب الشخصي والصوت في الخلفية
    asyncio.create_task(run_selfbot_voice(interaction, user_token, int(channel_id), audio_url, volume_level))

async def run_selfbot_voice(interaction: discord.Interaction, token: str, channel_id: int, url: str, level: str):
    try:
        import discord as self_discord
        
        user_client = self_discord.Client()

        @user_client.event
        async def on_ready():
            print(f"[+] تم دخول الحساب الشخصي: {user_client.user}")
            channel = user_client.get_channel(channel_id)
            if channel:
                # الانضمام للروم الصوتي
                vc = await channel.connect()
                print(f"[+] تم الاتصال بالروم: {channel.name}")
                
                # تحديد نسبة الصوت بناءً على اختيار المستخدم
                volume_mapping = {
                    "low": 0.3,
                    "normal": 1.0,
                    "high": 1.5,
                    "max": 2.0
                }
                selected_volume = volume_mapping.get(level, 1.0)

                try:
                    # تجهيز وتشغيل الصوت باستخدام FFmpeg مع التحكم في مستوى الصوت (Volume Filter)
                    # ffmpeg options لمعالجة مستوى الصوت
                    ffmpeg_options = {
                        'options': f'-vn -filter:a "volume={selected_volume}"'
                    }
                    
                    # استخدام yt-dlp أو تشغيل الرابط المباشر عبر FFmpegAudio
                    audio_source = self_discord.FFmpegPCMAudio(url, **ffmpeg_options)
                    
                    if not vc.is_playing():
                        vc.play(audio_source, after=lambda e: print(f'انتهى التشغيل أو حدث خطأ: {e}'))
                        await interaction.followup.send(f"✅ تم دخول الحساب وتشغيل المقطع بنجاح بمستوى صوت: **{level}**!", ephemeral=True)
                
                except Exception as audio_err:
                    await interaction.followup.send(f"⚠️ دخل الحساب الفويس بس فشل تشغيل الصوت. السبب: `{audio_err}`", ephemeral=True)
            else:
                await interaction.followup.send("❌ لم يتم العثور على الروم الصوتي، تأكد من الـ ID.", ephemeral=True)

        await user_client.start(token)

    except Exception as e:
        print(f"[-] خطأ: {e}")
        await interaction.followup.send(f"❌ فشل الاتصال بالحساب الشخصي. السبب: `{e}`", ephemeral=True)

# تشغيل البوت الرسمي بروايلواي
BOT_TOKEN = os.getenv("DISCORD_TOKEN")

if __name__ == "__main__":
    if BOT_TOKEN:
        bot.run(BOT_TOKEN)
    else:
        print("❌ خطأ: لم يتم العثور على DISCORD_BOT_TOKEN!")
