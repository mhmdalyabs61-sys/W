import discord
from discord.ext import commands
import asyncio
import os

# إعداد البوت الأساسي برمز ( Prefix ) وهو علامة التعجب !
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"[+] البوت الأساسي اشتغل بنجاح كـ: {bot.user.name}")
    print("[+] البوت جاهز لتلقي الأمر العادي بدون الحاجة لوجوده في سيرفرك!")

# أمر عادي (Prefix Command) - يقدر يشتغل في الخاص (DM) أو أي سيرفر البوت فيه
@bot.command(name="join", description="تشغيل الحساب الشخصي بالفويس")
async def join_voice_cmd(ctx, user_token: str, channel_id: str, audio_url: str, volume_level: str = "normal"):
    # رد بسيط لتأكيد استلام الطلب وحذفه بعد 5 ثواني للحفاظ على الخصوصية
    await ctx.send("⏳ جاري تنفيذ الطلب ودخول الحساب الفويس...", delete_after=5)

    # تشغيل الحساب الشخصي في مهمة خلفية
    asyncio.create_task(run_selfbot_voice(ctx, user_token, int(channel_id), audio_url, volume_level))

async def run_selfbot_voice(ctx, token: str, channel_id: int, url: str, level: str):
    try:
        import discord as self_discord
        
        # إعداد الـ intents المطلوبة لتلافي خطأ المكتبة
        client_intents = self_discord.Intents.default()
        client_intents.message_content = True
        user_client = self_discord.Client(intents=client_intents)

        @user_client.event
        async def on_ready():
            print(f"[+] تم دخول الحساب الشخصي بنجاح: {user_client.user}")
            channel = user_client.get_channel(channel_id)
            if channel:
                # الاتصال بالروم الصوتي بحسابك الشخصي
                vc = await channel.connect()
                print(f"[+] تم الاتصال بالروم: {channel.name}")
                
                # خريطة مستويات الصوت
                volume_mapping = {
                    "low": 0.3,
                    "normal": 1.0,
                    "high": 1.5,
                    "max": 2.0
                }
                selected_volume = volume_mapping.get(level, 1.0)

                try:
                    # إعدادات FFmpeg لمعالجة الصوت ودرجة العلو
                    ffmpeg_options = {
                        'options': f'-vn -filter:a "volume={selected_volume}"'
                    }
                    
                    audio_source = self_discord.FFmpegPCMAudio(url, **ffmpeg_options)
                    
                    if not vc.is_playing():
                        vc.play(audio_source, after=lambda e: print(f'انتهى التشغيل أو حدث خطأ: {e}'))
                        await ctx.send(f"✅ تم دخول حسابك للفويس وتشغيل المقطع بنجاح بمستوى صوت: **{level}**!")
                
                except Exception as audio_err:
                    await ctx.send(f"⚠️ دخل الحساب الفويس بس فشل تشغيل الصوت: `{audio_err}`")
            else:
                await ctx.send("❌ لم يتم العثور على الروم الصوتي، تأكد من صحة الـ ID.")

        await user_client.start(token)

    except Exception as e:
        print(f"[-] خطأ: {e}")
        await ctx.send(f"❌ فشل الاتصال بالحساب الشخصي. السبب: `{e}`")

# تشغيل البوت الأساسي باستخدام متغير البيئة
BOT_TOKEN = os.getenv("DISCORD_TOKEN")

if __name__ == "__main__":
    if BOT_TOKEN:
        bot.run(BOT_TOKEN)
    else:
        print("❌ خطأ: لم يتم العثور على DISCORD_BOT_TOKEN في متغيرات البيئة!")
