import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import aiohttp
import os

# ==========================================
# إعداد البوت الأساسي (Slash Commands)
# ==========================================
BOT_TOKEN = os.getenv("DISCORD_TOKEN", "حط_توكن_البوت_الأساسي_هنا")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"[+] البوت الأساسي اشتغل بنجاح كـ: {bot.user.name}")
    try:
        synced = await bot.tree.sync()
        print(f"[+] تمت مزامنة {len(synced)} أمر بنجاح!")
    except Exception as e:
        print(f"[-] خطأ في المزامنة: {e}")

# ==========================================
# أمر السلاش للفويس (يعتمد على التوكن الشخصي مثل طريقة الـ Cloner)
# ==========================================
@bot.tree.command(name="join", description="دخول الحساب الشخصي للفويس وتشغيل الصوت عبر التوكن")
@app_commands.describe(
    user_token="التوكن الشخصي لحسابك (Self-bot token)",
    channel_id="آي دي الروم الصوتي المراد دخوله",
    audio_url="رابط التيك توك أو الصوت المراد تشغيله",
    volume_level="اختر مستوى الصوت"
)
@app_commands.choices(volume_level=[
    app_commands.Choice(name="منخفض (Low)", value="low"),
    app_commands.Choice(name="عادي (Normal)", value="normal"),
    app_commands.Choice(name="عالي (High)", value="high"),
    app_commands.Choice(name="أقصى شيء (Max)", value="max"),
])
async def join_voice_slash(interaction: discord.Interaction, user_token: str, channel_id: str, audio_url: str, volume_level: str = "normal"):
    # رد مخفي تماماً (Ephemeral) عشان ماحد يشوف توكنك نهائياً بالرسائل
    await interaction.response.send_message("⏳ جاري التحقق من التوكن والاتصال بالفويس...", ephemeral=True)
    
    # تنظيف وتجهيز المتغيرات
    clean_token = user_token.strip()
    try:
        ch_id_int = int(channel_id.strip())
    except ValueError:
        await interaction.edit_original_response(content="❌ آي دي الروم الصوتي غير صحيح، يجب أن يكون أرقام فقط!")
        return

    # التحقق المبدئي من التوكن عبر طلب API مباشر (نفس طريقة سكريبت الـ Go)
    is_valid = await verify_user_token(clean_token)
    if not is_valid:
        await interaction.edit_original_response(content="❌ التوكن الشخصي المدخل غير صالح أو مرفوض من ديسكورد!")
        return

    # تشغيل الاتصال الصوتي بالحساب الشخصي في الخلفية
    asyncio.create_task(run_selfbot_voice(interaction, clean_token, ch_id_int, audio_url.strip(), volume_level))

# دالة للتحقق من صحة التوكن الشخصي عبر الهيدرز المباشرة
async def verify_user_token(token: str) -> bool:
    headers = {
        "Authorization": token,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get("https://discord.com/api/v10/users/@me", headers=headers) as resp:
            return resp.status == 200

# دالة تشغيل السيلف بوت ودخول الفويس
async def run_selfbot_voice(interaction: discord.Interaction, token: str, channel_id: int, url: str, level: str):
    try:
        client_intents = discord.Intents.default()
        client_intents.message_content = True
        user_client = discord.Client(intents=client_intents)

        @user_client.event
        async def on_ready():
            print(f"[+] تم تسجيل الدخول بالحساب الشخصي بنجاح: {user_client.user}")
            try:
                print(f"[*] جاري البحث عن الروم الصوتي ID: {channel_id}...")
                channel = await user_client.fetch_channel(channel_id)
                
                if channel:
                    print(f"[+] تم العثور على الروم: {channel.name}. جاري الاتصال...")
                    vc = await channel.connect()
                    print("[+] تم الاتصال بالقناة الصوتية بنجاح!")
                    
                    # مستويات الصوت
                    volume_mapping = {
                        "low": 0.3,
                        "normal": 1.0,
                        "high": 1.5,
                        "max": 2.0
                    }
                    selected_volume = volume_mapping.get(level, 1.0)

                    # إعدادات FFmpeg لتشغيل الصوت
                    ffmpeg_options = {
                        'options': f'-vn -filter:a "volume={selected_volume}"'
                    }
                    
                    audio_source = discord.FFmpegPCMAudio(url, **ffmpeg_options)
                    
                    if not vc.is_playing():
                        vc.play(audio_source, after=lambda e: print(f'[-] انتهى التشغيل أو حدث خطأ: {e}'))
                        print(f"✅ جاري تشغيل المقطع الآن بمستوى صوت: {level}")
                        await interaction.edit_original_response(content=f"✅ تم دخول حسابك الشخصي للفويس بنجاح وتشغيل المقطع بمستوى صوت: **{level}**!")
                else:
                    await interaction.edit_original_response(content="❌ لم يتم العثور على الروم الصوتي، تأكد من الـ ID.")
                    
            except Exception as inner_e:
                print(f"[-] خطأ أثناء جلب الروم أو تشغيل الصوت: {inner_e}")
                await interaction.edit_original_response(content=f"❌ فشل الاتصال بالفويس: `{inner_e}`")

        await user_client.start(token)

    except Exception as e:
        print(f"[-] خطأ في تشغيل السيلف بوت: {e}")
        try:
            await interaction.edit_original_response(content=f"❌ خطأ في تشغيل التوكن الشخصي: `{e}`")
        except:
            pass

# ==========================================
# تشغيل السكربت
# ==========================================
if __name__ == "__main__":
    if BOT_TOKEN and BOT_TOKEN != "حط_توكن_البوت_الأساسي_هنا":
        bot.run(BOT_TOKEN)
    else:
        print("❌ خطأ: يرجى وضع توكن البوت الأساسي الصحيح.")
