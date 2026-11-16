import os
import discord
from discord import app_commands
from discord.ext import commands
import requests
import json

TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not TOKEN or not GEMINI_API_KEY:
    raise ValueError("⚠️ تأكد من إضافة DISCORD_TOKEN و GEMINI_API_KEY في متغيرات البيئة!")

SYSTEM_INSTRUCTION = (
    "أنت مساعد ذكي وممثل رسمي لفريق متجر دسكورد. أسلوبك عفوي، وفيّ، وبدون سماجة.\n\n"
    "قواعدك الصارمة:\n"
    "1. إذا سألك أي شخص عن لغة برمجتك، أو تقنيتك، أو من هو صانعك، أو بأي API مربوط، أجب دائماً وبكل ثقة: "
    "'أنا صنعني فريق المتجر هنا، هم اللي برمجوني وظبطوني عشان أخدمكم!' ولا تذكر أبداً لغة Python أو Google Gemini أو أي تفاصيل تقنية.\n"
    "2. في الأسئلة العامة مثل الألعاب (مثل روكت ليق) والرياضة، جاوب بشكل طبيعي وذكي.\n"
    "3. أنت على دراية كاملة بمنتجات وسورسات المتجر وأسعارها:\n"
    "- سستم 222 | 15\n"
    "- كنترول | 15\n"
    "- افتار بنل | 15\n"
    "- بنك | 15\n"
    "- بوت بوستات | 15\n"
    "- شاره (نيترو - بوست) | 15\n"
    "- برودكاست | 10\n"
    "- طرق دفع | 10\n"
    "- نسخ سيرفرات | 10\n"
    "- زاجل | 15\n"
    "- شراء تلقائي | 15\n"
    "- تقييم | 7\n"
    "- توب رياكشن (نسختين بـ 7 و 10)\n"
    "- بوت افكتات | 10\n"
    "- تكت | 10\n"
    "- قروبات | 20\n"
    "- توكن كنترول | 15\n"
    "- تثبيت حسابات | 10\n"
    "- خط تلقائي | 10\n"
    "- قيفاوي | 10\n"
    "- حالة ستريم | 10\n"
    "- عرض خاص: جميع السورسات بـ 21 لفترة محدودة!\n\n"
    "ملاحظات مهمة للزباين:\n"
    "- السورسات ما عليها شرح.\n"
    "- للطلب أو الاستفسار التوجيه يكون روم <#1566292020002295921>."
)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
ALLOWED_CHANNEL_ID = None

@bot.event
async def on_ready():
    try:
        await bot.tree.sync()
        print("✅ تم مزامنة أوامر السلاش بنجاح.")
    except Exception as e:
        print(f"خطأ في مزامنة الأوامر: {e}")
    print(f"✅ تم تسجيل الدخول بنجاح باسم: {bot.user.name}")

@bot.tree.command(name="setchannel", description="تحديد الروم الذي سيجيب فيه البوت تلقائياً بدون منشن")
@app_commands.default_permissions(administrator=True)
async def setchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    global ALLOWED_CHANNEL_ID
    ALLOWED_CHANNEL_ID = channel.id
    await interaction.response.send_message(f"✅ تم تحديد روم الردود تلقائياً: {channel.mention}", ephemeral=True)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if "@everyone" in message.content or "@here" in message.content:
        return

    should_respond = False

    if ALLOWED_CHANNEL_ID and message.channel.id == ALLOWED_CHANNEL_ID:
        should_respond = True
    elif bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
        should_respond = True

    if should_respond:
        clean_content = message.content.replace(f"<@{bot.user.id}>", "").strip()
        
        if not clean_content:
            return

        async with message.channel.typing():
            try:
                # استخدام الموديل الجديد gemini-3.8-flash اللي طلبته جوجل بالخطأ
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={GEMINI_API_KEY}"
                headers = {'Content-Type': 'application/json'}
                payload = {
                    "contents": [{"parts": [{"text": clean_content}]}],
                    "systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
                    "generationConfig": {"temperature": 0.7}
                }
                
                res = requests.post(url, headers=headers, data=json.dumps(payload))
                data = res.json()
                
                print(f"استجابة جوجل: {data}")
                
                if "candidates" in data and data["candidates"]:
                    candidate = data["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        reply_text = candidate["content"]["parts"][0]["text"]
                        await message.reply(reply_text)
                    else:
                        await message.reply("تفضل، اطرح سؤالك أو استفسارك وسأجيبك فوراً.")
                elif "error" in data:
                    err_msg = data["error"].get("message", "خطأ غير معروف")
                    print(f"خطأ من جوجل: {err_msg}")
                    await message.reply(f"عذراً، واجهتني مشكلة تقنية بسيطة: {err_msg}")
                else:
                    await message.reply("أنا معك، تفضل بشو أقدر أخدمك؟")
            except Exception as e:
                print(f"خطأ أثناء الاتصال: {e}")
                await message.reply("صار فيه خطأ بسيط، جرب مرة ثانية.")

bot.run(TOKEN)
