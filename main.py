import discord, json, os, asyncio, random, time, io
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
from typing import Union, Optional, List, Dict
from PIL import Image, ImageDraw
from discord.ext import tasks
from datetime import datetime

# إعدادات البوت والـ Intents الأساسية (مفعل فيها الـ members بصراحة عشان يشتغل الترحيب)
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # <--- هذا السطر الأساسي والمهم جداً

bot = commands.Bot(command_prefix="!", intents=intents)



# ══════════════════════════════════════════════════════════════
#                   ضع التوكن هنا ↓
# ══════════════════════════════════════════════════════════════
TOKEN = 'YOUR_BOT_TOKEN_HERE'
# ══════════════════════════════════════════════════════════════
import random
import asyncio
import aiohttp
import discord
from discord.ext import tasks, commands

CHANNEL_ID = 1541497958741311538  # آيدي الروم المطلوب

# كتب الحديث المعتمدة (الصحيحين)
HADITH_BOOKS = ["bukhari", "muslim"]

TOTAL_AYAHS = 6236  # إجمالي عدد آيات القرآن الكريم
SEND_INTERVAL_MINUTES = 5

# إعدادات البوت (تأكد أن الـ intents عندك مطابقة)
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


async def fetch_random_ayah(session: aiohttp.ClientSession) -> discord.Embed | None:
    """جلب آية عشوائية من القرآن الكريم مع اسم السورة ورقم الآية."""
    ayah_number = random.randint(1, TOTAL_AYAHS)
    url = f"https://api.alquran.cloud/v1/ayah/{ayah_number}/quran-uthmani"

    async with session.get(url) as resp:
        if resp.status != 200:
            return None
        data = await resp.json()

    if data.get("code") != 200:
        return None

    ayah = data["data"]
    surah = ayah["surah"]

    embed = discord.Embed(
        title=f"📖 سورة {surah['name']} - الآية {ayah['numberInSurah']}",
        description=f"﴿ {ayah['text']} ﴾",
        color=discord.Color.green(),
    )
    embed.set_footer(text="المصدر: القرآن الكريم (نص عثماني موثق - alquran.cloud)")
    return embed


async def fetch_random_hadith(session: aiohttp.ClientSession) -> discord.Embed | None:
    """جلب حديث عشوائي من أحد كتب الحديث المحددة في HADITH_BOOKS."""
    book = random.choice(HADITH_BOOKS)

    info_url = f"https://api.hadith.gading.dev/books/{book}"
    async with session.get(info_url) as resp:
        if resp.status != 200:
            return None
        info = await resp.json()

    available = info.get("data", {}).get("available")
    if not available:
        return None

    hadith_number = random.randint(1, available)
    hadith_url = f"https://api.hadith.gading.dev/books/{book}/{hadith_number}"

    async with session.get(hadith_url) as resp:
        if resp.status != 200:
            return None
        result = await resp.json()

    hadith = result.get("data", {}).get("contents", {})
    if not hadith:
        return None

    book_names = {
        "bukhari": "صحيح البخاري",
        "muslim": "صحيح مسلم",
        "tirmidzi": "جامع الترمذي",
        "abudaud": "سنن أبي داود",
        "nasai": "سنن النسائي",
        "ibnumajah": "سنن ابن ماجه",
        "ahmad": "مسند أحمد",
        "malik": "موطأ مالك",
        "darimi": "سنن الدارمي",
    }

    embed = discord.Embed(
        title=f"🕌 {book_names.get(book, book)} - حديث رقم {hadith_number}",
        description=hadith.get("arab", "النص غير متوفر"),
        color=discord.Color.gold(),
    )
    embed.set_footer(text=f"المصدر: {book_names.get(book, book)} (عبر api.hadith.gading.dev)")
    return embed


@tasks.loop(minutes=SEND_INTERVAL_MINUTES)
async def send_reminder():
    channel = bot.get_channel(CHANNEL_ID)
    if channel is None:
        print("⚠️ لم يتم العثور على الروم، تأكد من CHANNEL_ID وصلاحيات البوت.")
        return

    async with aiohttp.ClientSession() as session:
        if send_reminder.current_loop % 2 == 0:
            embed = await fetch_random_ayah(session)
        else:
            embed = await fetch_random_hadith(session)

        if embed:
            try:
                await channel.send(embed=embed)
            except discord.Forbidden:
                print("⚠️ البوت لا يملك صلاحية الإرسال في هذا الروم.")
        else:
            print("⚠️ تعذر جلب المحتوى من المصدر هذه المرة، سيُعاد المحاولة في الدورة القادمة.")


@send_reminder.before_loop
async def before_send_reminder():
    await bot.wait_until_ready()
    await asyncio.sleep(5)


@bot.event
async def on_ready():
    print(f"✅ تم تسجيل الدخول باسم {bot.user}")
    if not send_reminder.is_running():
        send_reminder.start()







DATA_FILE = 'bot_data.json'

def load_data():
    default = {
        'whitelisted': [], 'log_channels': {}, 'jail_setup': {}, 
        'auto_responses': {}, 'jailed_members': {},
        'protection': {
            'channel_del': True, 'channel_update': True,
            'role_del': True, 'role_create': True,
            'webhook': True, 'bot_add': True
        }
    }
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for k, v in default.items():
                    if k not in data: data[k] = v
                return data
        except: pass
    return default

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

bot_data = load_data()


# --- أنظمة الراديو (UI Components) ---

class WaveModal(discord.ui.Modal, title='إنشاء/دخول موجة'):
    wave_id = discord.ui.TextInput(label='رقم الموجة', placeholder='مثال: 71.17', min_length=1, max_length=10)

    async def on_submit(self, interaction: discord.Interaction):
        wave_name = f"موجة-{self.wave_id.value}"
        guild = interaction.guild
        
        # ID روم الراديو الرئيسي
        MAIN_RADIO_ID = 1521294954243162254
        
        if not interaction.user.voice or interaction.user.voice.channel.id != MAIN_RADIO_ID:
            return await interaction.response.send_message("❌ يجب أن تكون داخل روم الراديو الرئيسي للدخول!", ephemeral=True)

        # البحث عن الروم أو إنشائه
        channel = discord.utils.get(guild.voice_channels, name=wave_name)
        
        if not channel:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(connect=False, view_channel=False),
                interaction.user: discord.PermissionOverwrite(connect=True, view_channel=True)
            }
            channel = await guild.create_voice_channel(
                name=wave_name, 
                overwrites=overwrites, 
                category=interaction.user.voice.channel.category
            )
            await interaction.response.send_message(f"✅ تم إنشاء موجتك: {channel.mention}", ephemeral=True)
        else:
            await channel.set_permissions(interaction.user, connect=True, view_channel=True)
            await interaction.response.send_message(f"✅ تم توصيلك بموجة {self.wave_id.value}", ephemeral=True)
        
        await interaction.user.move_to(channel)

class RadioView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    
    @discord.ui.button(label="+", style=discord.ButtonStyle.primary, custom_id="radio_btn")
    async def join_wave(self, interaction: discord.Interaction, button: discord.ui.Button):
        # هذا هو كود التفكير اللي يمنع الخطأ الأحمر
        await interaction.response.send_modal(WaveModal())

# --- تهيئة البوت (Setup Hook) ---

@bot.event
async def setup_hook():
    bot.add_view(RadioView()) 
    print("✅ تم تفعيل نظام الراديو (المزامنة يدوية عبر !sync)!")

# --- الدوال المساعدة (Helpers) ---

async def check_hierarchy(interaction: discord.Interaction) -> bool:
    return True # سيسمح هذا لأي شخص باستخدام الأوامر بدون التحقق من الرتب

async def send_log(guild: discord.Guild, message: str):
    log_id = bot_data['log_channels'].get(str(guild.id))
    if log_id:
        channel = guild.get_channel(int(log_id))
        if channel:
            try: await channel.send(f"`[{datetime.now().strftime('%H:%M:%S')}]` {message}")
            except: pass



event_history = {}

async def queue_task(target_id, coro):
    try:
        await coro
    except discord.HTTPException as e:
        if e.status == 429:
            await asyncio.sleep(e.retry_after)
            await coro
    finally:
        # إزالة البصمة بعد 5 ثوانٍ
        await asyncio.sleep(5)
        event_history.pop(target_id, None)



@bot.event
async def on_member_join(member):
    if not bot_data['protection'].get('bot_add', True): return
    if member.bot:
        await asyncio.sleep(0.4)
        async for entry in member.guild.audit_logs(action=discord.AuditLogAction.bot_add, limit=1):
            if entry.target.id == member.id and entry.user.id not in bot_data['whitelisted']:
                await ban_user(member.guild, entry.user, "إضافة بوت غير مصرح به")
                await member.kick(reason="بوت غير موثوق")
                break

@bot.event
async def on_voice_state_update(member, before, after):
    # حدث التنظيف التلقائي لنظام الراديو
    if before.channel and before.channel != after.channel:
        if "موجة-" in before.channel.name and len(before.channel.members) == 0:
            try: await before.channel.delete(reason="روم فارغ")
            except: pass

# --- أوامر السلاش (Slash Commands) ---

@bot.tree.command(name="setup_radio", description="إرسال رسالة نظام الموجات")
@app_commands.default_permissions(administrator=True)
async def setup_radio(interaction: discord.Interaction):
    if not await check_hierarchy(interaction): return
    # ID الروم الذي تبي ترسل فيه الرسالة
    LOG_CHANNEL_ID = 1521294580933328967
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if not channel:
        return await interaction.response.send_message("❌ لم يتم العثور على الروم المحدد في الكود!", ephemeral=True)
    await channel.send("📻 **نظام الموجات:**\nاضغط على الزائد (+) لإنشاء أو دخول موجتك الخاصة.", view=RadioView())
    await interaction.response.send_message("✅ تم إرسال رسالة الراديو.", ephemeral=True)

@bot.tree.command(name="protection", description="تفعيل أو تعطيل أنواع الحماية")
@app_commands.default_permissions(administrator=True)
@app_commands.choices(feature=[
    app_commands.Choice(name="حماية الرومات (حذف)", value="channel_del"),
    app_commands.Choice(name="حماية الرومات (تعديل)", value="channel_update"),
    app_commands.Choice(name="حماية الرتب (حذف)", value="role_del"),
    app_commands.Choice(name="حماية الرتب (إنشاء)", value="role_create"),
    app_commands.Choice(name="حماية الويب هوك", value="webhook"),
    app_commands.Choice(name="حماية البوتات", value="bot_add")
])
async def protection(interaction: discord.Interaction, feature: str, status: bool):
    if not await check_hierarchy(interaction): return
    bot_data['protection'][feature] = status
    save_data(bot_data)
    await interaction.response.send_message(f"✅ تم تغيير حالة '{feature}' إلى: {'مفعل' if status else 'معطل'}", ephemeral=True)

@bot.tree.command(name="whitelist", description="إضافة/إزالة من القائمة البيضاء")
@app_commands.default_permissions(administrator=True)
async def whitelist(interaction: discord.Interaction, user: discord.Member):
    if not await check_hierarchy(interaction): return
    if user.id in bot_data['whitelisted']:
        bot_data['whitelisted'].remove(user.id)
        msg = f"❌ تمت إزالة {user.name} من القائمة البيضاء."
    else:
        bot_data['whitelisted'].append(user.id)
        msg = f"✅ تمت إضافة {user.name} للقائمة البيضاء."
    save_data(bot_data)
    await interaction.response.send_message(msg, ephemeral=True)

@bot.tree.command(name="ban", description="تبنيد عضو")
@app_commands.default_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, user: discord.Member, reason: str = "لا يوجد"):
    if not await check_hierarchy(interaction): return
    await ban_user(interaction.guild, user, reason)
    await interaction.response.send_message(f"🔨 تم طرد {user.name}.")

@bot.tree.command(name="unban", description="فك الباند")
@app_commands.default_permissions(ban_members=True)
async def unban(interaction: discord.Interaction, user_id: str):
    if not await check_hierarchy(interaction): return
    user = await bot.fetch_user(int(user_id))
    await interaction.guild.unban(user)
    await interaction.response.send_message(f"🔓 تم فك الباند عن {user.name}.")

@bot.tree.command(name="timeout", description="تايم أوت")
@app_commands.choices(duration=[
    app_commands.Choice(name="30 ثانية", value=30), app_commands.Choice(name="دقيقة", value=60),
    app_commands.Choice(name="5 دقائق", value=300), app_commands.Choice(name="10 دقائق", value=600),
    app_commands.Choice(name="نص ساعة", value=1800), app_commands.Choice(name="ساعة", value=3600),
    app_commands.Choice(name="6 ساعات", value=21600), app_commands.Choice(name="يوم", value=86400),
    app_commands.Choice(name="7 أيام", value=604800)
])
async def timeout(interaction: discord.Interaction, user: discord.Member, duration: int):
    if not await check_hierarchy(interaction): return
    await user.timeout(discord.utils.utcnow() + timedelta(seconds=duration))
    await interaction.response.send_message(f"⏱️ تم عمل تايم أوت لـ {user.name}.")

@bot.tree.command(name="setup_jail", description="إعداد السجن")
@app_commands.default_permissions(administrator=True)
async def setup_jail(interaction: discord.Interaction, channel: discord.TextChannel, role: discord.Role):
    if not await check_hierarchy(interaction): return
    bot_data['jail_setup'][str(interaction.guild.id)] = {'c': channel.id, 'r': role.id}
    save_data(bot_data)
    await interaction.response.send_message("✅ تم إعداد السجن بنجاح.", ephemeral=True)

@bot.tree.command(name="jail", description="سجن عضو")
async def jail(interaction: discord.Interaction, user: discord.Member):
    if not await check_hierarchy(interaction): return
    gid = str(interaction.guild.id)
    setup = bot_data['jail_setup'].get(gid)
    if not setup: return await interaction.response.send_message("❌ السجن غير معد.", ephemeral=True)
    bot_data['jailed_members'][str(user.id)] = [r.id for r in user.roles if r != interaction.guild.default_role and not r.managed]
    await user.edit(roles=[interaction.guild.get_role(setup['r'])])
    save_data(bot_data)
    await interaction.response.send_message(f"🏛️ تم سجن {user.name}.")

@bot.tree.command(name="unjail", description="إخراج من السجن")
async def unjail(interaction: discord.Interaction, user: discord.Member):
    if not await check_hierarchy(interaction): return
    saved_roles = bot_data['jailed_members'].pop(str(user.id), [])
    roles = [interaction.guild.get_role(rid) for rid in saved_roles if interaction.guild.get_role(rid)]
    await user.edit(roles=roles)
    save_data(bot_data)
    await interaction.response.send_message(f"🔓 تم إخراج {user.name} واستعادة رتبه.")

@bot.tree.command(name="add_response", description="إضافة رد تلقائي")
async def add_res(interaction: discord.Interaction, word: str, response: str):
    if not await check_hierarchy(interaction): return
    gid = str(interaction.guild.id)
    if gid not in bot_data['auto_responses']: bot_data['auto_responses'][gid] = {}
    bot_data['auto_responses'][gid][word] = response
    save_data(bot_data)
    await interaction.response.send_message(f"✅ تم إضافة الرد التلقائي للكلمة: {word}", ephemeral=True)

@bot.tree.command(name="set_log", description="تحديد روم اللوق")
@app_commands.default_permissions(administrator=True)
async def set_log(interaction: discord.Interaction, channel: discord.TextChannel):
    if not await check_hierarchy(interaction): return
    bot_data['log_channels'][str(interaction.guild.id)] = channel.id
    save_data(bot_data)
    await interaction.response.send_message(f"✅ تم تحديد {channel.mention} كروم للوق.", ephemeral=True)

@bot.tree.command(name="check_security", description="فحص أنظمة الحماية")
async def check(interaction: discord.Interaction):
    if not await check_hierarchy(interaction): return
    status = "\n".join([f"{k}: {'✅' if v else '❌'}" for k, v in bot_data['protection'].items()])
    await interaction.response.send_message(f"🛡️ **حالة الحماية:**\n{status}", ephemeral=True)

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild: return
    gid = str(message.guild.id)
    resps = bot_data.get("auto_responses", {}).get(gid, {})
    for k, v in resps.items():
        if k.lower() in message.content.lower():
            await message.channel.send(v)
            break
    await bot.process_commands(message)

@bot.event
async def on_ready():
    print(f"✅ {bot.user} يعمل الآن بنظام الراديو والحماية القصوى!")

@bot.command()
@commands.is_owner()
async def sync(ctx):
    await bot.tree.sync()
    await ctx.send("✅ تم تحديث الأوامر!")
from flask import Flask
from threading import Thread

app = Flask('')
@app.route('/')
def home(): return "البوت يعمل"
def run(): app.run(host='0.0.0.0', port=8080)

# تشغيل الويب سيرفر في الخلفية
Thread(target=run).start()


@bot.command(name="لف", aliases=["ban", "باند"])
@commands.has_permissions(ban_members=True)
async def ban_member(ctx, member: discord.Member, *, reason: str = "بدون سبب"):
    try:
        await member.ban(reason=reason)
        await ctx.send(f"**🔨 تم تبنيد  العضو {member.mention} | السبب: {reason}**")
    except discord.Forbidden:
        await ctx.send("**❌ ما أقدر أبند هذا الشخص، رتبته أعلى مني أو صلاحياتي ناقصة!**")
    except Exception as e:
        await ctx.send(f"**❌ صار فيه خطأ: {e}**")

@ban_member.error
async def ban_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("**❌ ما عندك صلاحية Ban Members عشان تستخدم هالأمر!**")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("**⚠️ الاستخدام الصحيح: لف @الشخص (السبب اختياري)**")





# قاموس حفظ النقاط المشترك
user_scores = {}

# دالة إصلاح الحروف العربية المقلوبة
def fix_arabic(text):
    return text[::-1]

@bot.event
async def on_ready():
    print(f"✅ البوت شغال الآن وجاهز باسم: {bot.user}")

# ----------------------------------------------------
# 1. أمر النقاط (عرض نقاطك أو لوحة المتصدرين)
# ----------------------------------------------------
@bot.command(name="نقاط", aliases=["top", "score", "points"])
async def show_score(ctx, member: discord.Member = None):
    if member:
        score = user_scores.get(member.id, 0)
        await ctx.send(f"📊 نقاط اللاعب <@{member.id}> هي: **{score} نقطة** 🏆")
        return

    if not user_scores:
        await ctx.send("📉 ما فيه أي نقاط مسجلة لحد الحين!")
        return
    
    sorted_scores = sorted(user_scores.items(), key=lambda x: x[1], reverse=True)
    
    desc = ""
    for rank, (user_id, score) in enumerate(sorted_scores, 1):
        desc += f"**#{rank}** <@{user_id}> ⟵ **{score}** نقطة\n"
        
    embed = discord.Embed(
        title="🏆 لوحة متصدرين الألعاب",
        description=desc,
        color=0xffd700
    )
    await ctx.send(embed=embed)

# ----------------------------------------------------
# 2. لعبة السرعة (كلمات)
# ----------------------------------------------------
fast_words = [
    "صحن", "سيف", "سياره", "طياره", "كرسي", "بيت", "قلم", "دفتر", "باب", "شباك",
    "جوال", "ساعة", "طاولة", "ثلاجة", "مكيف", "سماعة", "مفاتيح", "قطار", "سفينة", "دراجة",
    "تلفزيون", "مراية", "سحاب", "قمر", "شمس", "نجوم", "بحر", "نهر", "جبل", "صحراء",
    "مطر", "طريق", "تفاح", "موز", "برتقال", "خيار", "طماطم", "بطيخ", "عنب", "دجاج",
    "لحم", "سمك", "خبز", "جبن", "حليب", "ماء", "عصير", "شاي", "قهوة", "سكر",
    "ملح", "زيت", "قدر", "ملعقة", "شوكة", "كاس", "سجادة", "وسادة", "بطانية", "سرير",
    "دولاب", "قميص", "بنطلون", "حذاء", "شماغ", "عقال", "نظارة", "حزام", "سورة", "مسجد",
    "قارب", "حوت", "أسد", "نمر", "فهد", "ذيب", "ثعلب", "ارنب", "قرد", "دب",
    "فيل", "زرافة", "حصان", "خروف", "بقرة", "جمل", "صقر", "نسر", "حمامة", "عصفور",
    "ديك", "دجاجة", "فرن", "غسالة", "مروحة", "لمبة", "سلك", "بطارية", "شاحن",
    "كمبيوتر", "لابتوب", "ماوس", "لوحة", "مكتب", "صندوق", "حقيبة", "حائط", "ارضية", "سقف"
]

@bot.command(name="اسرع", aliases=["fast"])
async def fast_game(ctx):
    target_word = random.choice(fast_words)
    
    embed = discord.Embed(
        title="⚡ مسابقة السرعة",
        description=f"أسرع شخص يكتب هذه الكلمة في الشات:\n\n# 🎯 `{target_word}`",
        color=0xffaa00
    )
    embed.set_footer(text="لديك 15 ثانية فقط!")
    
    await ctx.send(embed=embed)
    
    start_time = time.time()
    
    def check(m):
        return m.channel == ctx.channel and m.content.strip() == target_word and not m.author.bot

    try:
        msg = await bot.wait_for('message', timeout=15.0, check=check)
        elapsed = round(time.time() - start_time, 2)
        
        user_scores[msg.author.id] = user_scores.get(msg.author.id, 0) + 1
        
        await ctx.send(f"🏆 كفو <@{msg.author.id}>! فزت بالمركز الأول بوقت **{elapsed} ثانية** وحصلت على نقطة! 🎉")
    except Exception:
        await ctx.send(f"⏳ انتهى الوقت! محد كتب الكلمة الصحيحة (`{target_word}`).")

# ----------------------------------------------------
# 3. لعبة خمن الدولة (60 دولة - صورتين لكل دولة - بدون تلميح)
# ----------------------------------------------------

import random
import discord

countries_images = {
    "المملكة العربية السعودية": "https://images.unsplash.com/photo-1578836537282-3171d77f8632?w=800",
    "مصر": "https://images.unsplash.com/photo-1539650116574-8efeb43e2750?w=800",
    "الإمارات": "https://images.unsplash.com/photo-1512453979798-5ea266f8880c?w=800",
    "الكويت": "https://images.unsplash.com/photo-1578895101408-1a364e1c736f?w=800",
    "قطر": "https://images.unsplash.com/photo-1578895101332-fa99f681d638?w=800",
    "البحرين": "https://images.unsplash.com/photo-1518684079-3c830dcef090?w=800",
    "عمان": "https://images.unsplash.com/photo-1580618672591-eb180b1a973f?w=800",
    "الأردن": "https://images.unsplash.com/photo-1564507592333-c60657eea523?w=800",
    "العراق": "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?w=800",
    "سوريا": "https://images.unsplash.com/photo-1541872703-74c5e44368f9?w=800",
    "لبنان": "https://images.unsplash.com/photo-1528164344705-475426879c0d?w=800",
    "فلسطين": "https://images.unsplash.com/photo-1584551246679-0daf3d275d0f?w=800",
    "المغرب": "https://images.unsplash.com/photo-1539650116574-8efeb43e2750?w=800",
    "الجزائر": "https://images.unsplash.com/photo-1577948334699-2a912bb14798?w=800",
    "تونس": "https://images.unsplash.com/photo-1515542622106-78bda8ba0e5b?w=800",
    "ليبيا": "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?w=800",
    "السودان": "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?w=800",
    "اليمن": "https://images.unsplash.com/photo-1580618672591-eb180b1a973f?w=800",
    "تركيا": "https://images.unsplash.com/photo-1524231757913-215fce3a9b5a?w=800",
    "إيران": "https://images.unsplash.com/photo-1563492065599-3520f775eeed?w=800",
    "باكستان": "https://images.unsplash.com/photo-1609137144813-7f9f5b770fb9?w=800",
    "الهند": "https://images.unsplash.com/photo-1524492412937-b28074a5d7da?w=800",
    "الصين": "https://images.unsplash.com/photo-1508804052814-cd38ba552e4d?w=800",
    "اليابان": "https://images.unsplash.com/photo-1503899036084-c55cdd92da26?w=800",
    "كوريا الجنوبية": "https://images.unsplash.com/photo-1538485399061-1774e402d294?w=800",
    "إندونيسيا": "https://images.unsplash.com/photo-1537996194471-e657df975ab4?w=800",
    "ماليزيا": "https://images.unsplash.com/photo-1596422846543-75c6fc197f07?w=800",
    "تايلاند": "https://images.unsplash.com/photo-1552465011-b4e21bf6e79a?w=800",
    "فيتنام": "https://images.unsplash.com/photo-1509114397022-ed747cca3f65?w=800",
    "الفلبين": "https://images.unsplash.com/photo-1518548419970-58e3b4079ab2?w=800",
    "روسيا": "https://images.unsplash.com/photo-1513326738677-b964603b136d?w=800",
    "فرنسا": "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=800",
    "المملكة المتحدة": "https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?w=800",
    "إيطاليا": "https://images.unsplash.com/photo-1529260830199-42c24126f198?w=800",
    "ألمانيا": "https://images.unsplash.com/photo-1467269204594-9661b134dd2b?w=800",
    "إسبانيا": "https://images.unsplash.com/photo-1539037116277-4db20889f2d4?w=800",
    "هولندا": "https://images.unsplash.com/photo-1512470876302-972faa2aa9a4?w=800",
    "سويسرا": "https://images.unsplash.com/photo-1530122037265-a5f1f91d3b99?w=800",
    "البلجيكا": "https://images.unsplash.com/photo-1551643206-8d6938a75e12?w=800",
    "النمسا": "https://images.unsplash.com/photo-1516550893885-303ce2779fce?w=800",
    "البرتغال": "https://images.unsplash.com/photo-1515542622106-78bda8ba0e5b?w=800",
    "اليونان": "https://images.unsplash.com/photo-1533105079780-92b9be482077?w=800",
    "السويد": "https://images.unsplash.com/photo-1509356843153-3f1b213bfa7a?w=800",
    "النرويج": "https://images.unsplash.com/photo-1507034589631-9433cc6bc453?w=800",
    "الدنمارك": "https://images.unsplash.com/photo-1513622470522-26c3c8a854bc?w=800",
    "أيسلندا": "https://images.unsplash.com/photo-1504893524553-29586e1e191d?w=800",
    "أيرلندا": "https://images.unsplash.com/photo-1590089415225-4034664ce935?w=800",
    "بولندا": "https://images.unsplash.com/photo-1519138119067-6b4c3c299a1e?w=800",
    "رومانيا": "https://images.unsplash.com/photo-1584646098378-0874589d76b1?w=800",
    "المجر": "https://images.unsplash.com/photo-1549877452-9c387954fbc2?w=800",
    "الولايات المتحدة": "https://images.unsplash.com/photo-1485738422979-f5c462d49f74?w=800",
    "كندا": "https://images.unsplash.com/photo-1503614472-8c93d56e92ce?w=800",
    "المكسيك": "https://images.unsplash.com/photo-1512813277712-4d37537b7713?w=800",
    "البرازيل": "https://images.unsplash.com/photo-1483729558449-99ef09a8c325?w=800",
    "الأرجنتين": "https://images.unsplash.com/photo-1589909202874-1779777f7223?w=800",
    "كولومبيا": "https://images.unsplash.com/photo-1590523277543-a94d2e4eb00b?w=800",
    "تشيلي": "https://images.unsplash.com/photo-1564507592333-c60657eea523?w=800",
    "بيرو": "https://images.unsplash.com/photo-1526392060635-9d6019884377?w=800",
    "أستراليا": "https://images.unsplash.com/photo-1506973035872-a4ec16b8e8d9?w=800",
    "نيوزيلندا": "https://images.unsplash.com/photo-1469521669194-0384891ffc4f?w=800"
}

@bot.command(name="خمن")
async def guess_country(ctx):
    country_name = random.choice(list(countries_images.keys()))
    image_url = countries_images[country_name]
    
    embed = discord.Embed(
        title="🌆 خمن الدولة من الشارع أو المكان العام",
        description="**اكتب اسم الدولة في الشات الآن!**",
        color=discord.Color.blurple()
    )
    embed.set_image(url=image_url)
    
    await ctx.send(embed=embed)
    
    # احفظ الـ country_name في متغير عندك للمقارنة (الإجابة الصحيحة)

    
    def check(m):
        user_text = m.content.strip()
        return m.channel == ctx.channel and (user_text == target_country or user_text == fix_arabic(target_country)) and not m.author.bot

    try:
        msg = await bot.wait_for('message', timeout=10.0, check=check)
        user_scores[msg.author.id] = user_scores.get(msg.author.id, 0) + 1
        await ctx.send(f"🎯 كفو يا <@{msg.author.id}>! الدولة هي **{target_country}** (+1 نقطة)")
    except Exception:
        await ctx.send(f"⏰ خلص الوقت! الدولة كانت: **{target_country}**")





@bot.event
async def on_member_join(member):
    channel_id = 1541617463349743747
    channel = bot.get_channel(channel_id)
    
    if channel:
        member_count = member.guild.member_count
        
        # إنشاء الـ Embed باللون الأسود
        embed = discord.Embed(
            title="👋 عضو جديد منورنا!",
            description=(
                f"ارحب تراحيب المطررر\n"
                f"{member.mention}\n\n"
                f"بفضلك صرنا \n"
                f"**{member_count}** عضو!\n\n"
                f"لا تنسى تشيك على <#1540853992870121612>\n\n"
                f"نتمنى انك مو من المتجحفلين"
            ),
            color=0x010101  # لون أسود داكن وأنيق
        )
        
        # إضافة صورة مصغرة لصورة بروفايل العضو الجديد
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # إرسال الإمبيد في الروم
        await channel.send(embed=embed)






import datetime
import discord
from discord.ext import commands
import re

@bot.command(name="تايم", aliases=["timeout"])
@commands.has_permissions(moderate_members=True)
async def timeout_member(ctx, member: discord.Member, time_str: str = "5m", *, reason: str = "بدون سبب"):
    # تحليل المدة الزمنية ودعم الأشكال المتعددة مثل 5d, 6m, 1h30m أو أرقام مجردة
    total_seconds = 0
    
    # التحقق إذا كانت المدة مجرد رقم (يعتبرها دقائق تلقائياً)
    if time_str.isdigit():
        total_seconds = int(time_str) * 60
        time_text = f"{time_str} دقيقة"
    else:
        # البحث عن الأجزاء مثل (5d, 6m, 2h, 30s)
        matches = re.findall(r'(\d+)([smhd])', time_str.lower())
        if not matches:
            await ctx.send("**❌ صيغة الوقت خاطئة! استخدم مثلاً: `5d` لأيام، `6m` لدقائق، `2h` لساعات، أو اكتب الرقم مباشرة.**")
            return
            
        time_parts = []
        for amount_str, unit in matches:
            amount = int(amount_str)
            if unit == 's':
                total_seconds += amount
                time_parts.append(f"{amount} ثانية")
            elif unit == 'm':
                total_seconds += amount * 60
                time_parts.append(f"{amount} دقيقة")
            elif unit == 'h':
                total_seconds += amount * 3600
                time_parts.append(f"{amount} ساعة")
            elif unit == 'd':
                total_seconds += amount * 86400
                time_parts.append(f"{amount} يوم")
                
        time_text = " و ".join(time_parts)

    if total_seconds <= 0:
        await ctx.send("**❌ يجب أن تكون مدة التايم أكبر من الصفر!**")
        return

    duration = datetime.timedelta(seconds=total_seconds)

    try:
        await member.timeout(duration, reason=reason)
        await ctx.send(f"**⏰ تم إعطاء تايم اوت لـ {member.mention} لمدة {time_text} | السبب: {reason}**")
    except discord.Forbidden:
        await ctx.send("**❌ ما أقدر أعطي تايم اوت لهذا الشخص، رتبته أعلى مني أو صلاحياتي ناقصة!**")
    except Exception as e:
        await ctx.send(f"**❌ صار فيه خطأ: {e}**")

@timeout_member.error
async def timeout_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("**❌ ما عندك صلاحية Moderate Members عشان تستخدم هالأمر!**")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("**⚠️ الاستخدام الصحيح:**\n`تايم @الشخص` (يعطيه 5 دقائق افتراضي)\n`تايم @الشخص 5d`\n`تايم @الشخص 6m سبام`")
import discord
from discord.ext import commands

# 1. أمر فك التايم (تكلم)
@bot.command(name="تكلم", aliases=["untimeout", "unmute"])
@commands.has_permissions(moderate_members=True)
async def untimeout_member(ctx, member: discord.Member, *, reason: str = "بدون سبب"):
    try:
        await member.timeout(None, reason=reason)
        await ctx.send(f"**🔊 تم فك التايم عن {member.mention} بنجاح! | السبب: {reason}**")
    except discord.Forbidden:
        await ctx.send("**❌ ما أقدر أفك التايم عن هذا الشخص، رتبته أعلى مني أو صلاحياتي ناقصة!**")
    except Exception as e:
        await ctx.send(f"**❌ صار فيه خطأ: {e}**")

@untimeout_member.error
async def untimeout_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("**❌ ما عندك صلاحية Moderate Members عشان تستخدم هالأمر!**")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("**⚠️ الاستخدام الصحيح: تكلم @الشخص [السبب اختياري]**")


# 2. أمر فك الباند (فك)
@bot.command(name="فك", aliases=["unban"])
@commands.has_permissions(ban_members=True)
async def unban_member(ctx, user_id: int, *, reason: str = "بدون سبب"):
    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user, reason=reason)
        await ctx.send(f"**🔓 تم فك الباند عن العضو `{user}` (الايدي: {user_id}) بنجاح! | السبب: {reason}**")
    except discord.NotFound:
        await ctx.send("**❌ ما لقيت شخص بهذا الأيدي محظور في السيرفر!**")
    except discord.Forbidden:
        await ctx.send("**❌ صلاحياتي ناقصة لفك الباند!**")
    except Exception as e:
        await ctx.send(f"**❌ صار فيه خطأ: تأكد من كتابة الأيدي بشكل صحيح. ({e})**")

@unban_member.error
async def unban_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("**❌ ما عندك صلاحية Ban Members عشان تستخدم هالأمر!**")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("**⚠️ الاستخدام الصحيح: فك [أيدي الشخص] [السبب اختياري]**\nمثال: `فك 123456789012345678 عفو عام`")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("**⚠️ يرجى كتابة أيدي العضو بشكل أرقام صحيحة!**")
import datetime
import discord
from discord.ext import commands

# 1. أمر الطرد (طرد)
@bot.command(name="طرد", aliases=["kick"])
@commands.has_permissions(kick_members=True)
async def kick_member(ctx, member: discord.Member, *, reason: str = "بدون سبب"):
    try:
        await member.kick(reason=reason)
        await ctx.send(f"**👢 تم طرد {member.mention} من السيرفر بنجاح! | السبب: {reason}**")
    except discord.Forbidden:
        await ctx.send("**❌ ما أقدر أطرد هذا الشخص، رتبته أعلى مني أو صلاحياتي ناقصة!**")
    except Exception as e:
        await ctx.send(f"**❌ صار فيه خطأ: {e}**")

@kick_member.error
async def kick_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("**❌ ما عندك صلاحية Kick Members عشان تستخدم هالأمر!**")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("**⚠️ الاستخدام الصحيح: طرد @الشخص [السبب اختياري]**")


# 2. أمر مسح الرسائل (مسح)
@bot.command(name="مسح", aliases=["clear", "purge"])
@commands.has_permissions(manage_messages=True)
async def clear_messages(ctx, amount: int = 10):
    if amount <= 0:
        await ctx.send("**❌ يرجى كتابة عدد أكبر من الصفر!**")
        return
    try:
        deleted = await ctx.channel.purge(limit=amount + 1)
        msg = await ctx.send(f"**🗑️ تم حذف {len(deleted) - 1} رسالة بنجاح!**")
        await discord.utils.sleep_until(datetime.datetime.utcnow() + datetime.timedelta(seconds=3))
        await msg.delete()
    except discord.Forbidden:
        await ctx.send("**❌ صلاحياتي ناقصة لحذف الرسائل (Manage Messages)!**")
    except Exception as e:
        await ctx.send(f"**❌ صار فيه خطأ: {e}**")

@clear_messages.error
async def clear_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("**❌ ما عندك صلاحية Manage Messages عشان تستخدم هالأمر!**")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("**⚠️ يرجى كتابة الرقم بشكل صحيح! (مثال: مسح 50)**")


# 3. أمر معلومات السيرفر (سيرفر)
@bot.command(name="سيرفر", aliases=["serverinfo"])
async def server_info(ctx):
    guild = ctx.guild
    embed = discord.Embed(
        title=f"📊 معلومات سيرفر: {guild.name}",
        color=discord.Color.blue(),
        timestamp=datetime.datetime.now()
    )
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    
    embed.add_field(name="👑 صاحب السيرفر", value=f"{guild.owner.mention}" if guild.owner else "غير معروف", inline=True)
    embed.add_field(name="👥 الأعضاء", value=f"إجمالي: {guild.member_count}", inline=True)
    embed.add_field(name="📅 تاريخ الإنشاء", value=f"<t:{int(guild.created_at.timestamp())}:R>", inline=True)
    embed.add_field(name="💬 الرومات", value=f"كتابية: {len(guild.text_channels)} | صوتية: {len(guild.voice_channels)}", inline=True)
    embed.add_field(name="🛡️ الرتب", value=f"{len(guild.roles)} رتبة", inline=True)
    embed.add_field(name="🌍 التعديلات/المستوى", value=f"Level {guild.premium_tier} (Boosts: {guild.premium_subscription_count})", inline=True)
    
    await ctx.send(embed=embed)


# 4. أمر معلومات العضو (من)
@bot.command(name="من", aliases=["whois", "userinfo"])
async def user_info(ctx, member: discord.Member = None):
    member = member or ctx.author
    roles = [role.mention for role in member.roles if role != ctx.guild.default_role]
    roles_str = ", ".join(roles) if roles else "لا توجد رتب"
    
    embed = discord.Embed(
        title=f"👤 معلومات عن: {member.name}",
        color=member.color,
        timestamp=datetime.datetime.now()
    )
    if member.avatar:
        embed.set_thumbnail(url=member.avatar.url)
        
    embed.add_field(name="🆔 الأيدي", value=member.id, inline=True)
    embed.add_field(name="🏷️ الاسم المستعار", value=member.nick or "بدون", inline=True)
    embed.add_field(name="📥 تاريخ الانضمام للسيرفر", value=f"<t:{int(member.joined_at.timestamp())}:R>" if member.joined_at else "غير معروف", inline=True)
    embed.add_field(name="📅 تاريخ إنشاء الحساب", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
    embed.add_field(name=f"🎭 الرتب ({len(roles)})", value=roles_str, inline=False)
    
    await ctx.send(embed=embed)


# قاعدة بيانات مؤقتة لتخزين التحذيرات
warnings_db = {}

# 5. أمر التحذير (تحذير @الشخص السبب) - مع التحقق من الرتبة
@bot.command(name="تحذير", aliases=["warn"])
@commands.has_permissions(manage_messages=True)
async def warn_member(ctx, member: discord.Member, *, reason: str = "بدون سبب"):
    # منع المشرف من تحذير شخص رتبته أعلى منه أو مساوية له (باستثناء صاحب السيرفر)
    if ctx.author != ctx.guild.owner and member.top_role >= ctx.author.top_role:
        await ctx.send("**❌ ما يمكنك تحذير شخص رتبته أعلى منك أو مساوية لرتبتك!**")
        return

    if member.id not in warnings_db:
        warnings_db[member.id] = []
    
    warn_data = {
        "reason": reason,
        "moderator": ctx.author.name,
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "message_link": ctx.message.jump_url
    }
    warnings_db[member.id].append(warn_data)
    
    await ctx.send(f"**⚠️ تم تحذير {member.mention} بنجاح! | السبب: {reason}**")
    try:
        await member.send(f"**⚠️ لقد تم تحذيرك في سيرفر {ctx.guild.name} | السبب: {reason}**")
    except:
        pass


# 8. أمر تغيير الاسم (اسم @الشخص الاسم الجديد) - مع التحقق من الرتبة
@bot.command(name="اسم", aliases=["nick", "nickname"])
@commands.has_permissions(manage_nicknames=True)
async def change_nickname(ctx, member: discord.Member, *, new_name: str = None):
    # منع المشرف من تغيير اسم شخص رتبته أعلى منه أو مساوية له (باستثناء صاحب السيرفر)
    if ctx.author != ctx.guild.owner and member.top_role >= ctx.author.top_role:
        await ctx.send("**❌ ما يمكنك تغيير اسم شخص رتبته أعلى منك أو مساوية لرتبتك!**")
        return

    try:
        nickname_to_set = None if new_name and new_name.lower() == "none" else new_name
        await member.edit(nick=nickname_to_set)
        
        if nickname_to_set:
            await ctx.send(f"**✏️ تم تغيير اسم {member.mention} إلى `{nickname_to_set}` بنجاح!**")
        else:
            await ctx.send(f"**🔄 تم إرجاع اسم {member.mention} إلى اسمه الطبيعي الأصلي!**")
    except discord.Forbidden:
        await ctx.send("**❌ ما أقدر أغير اسم هذا الشخص، رتبته أعلى من بوتي أو صلاحياتي ناقصة!**")
    except Exception as e:
        await ctx.send(f"**❌ صار فيه خطأ: {e}**")


@warn_member.error
async def warn_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("**❌ ما عندك صلاحية لإدارة الرسائل عشان تحذر الأعضاء!**")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("**⚠️ الاستخدام الصحيح: تحذير @الشخص [السبب]**")


# 6. أمر عرض التحذيرات بإمبد مرتب (تحذيرات @الشخص)
@bot.command(name="تحذيرات", aliases=["warnings"])
async def show_warnings(ctx, member: discord.Member):
    user_warns = warnings_db.get(member.id, [])
    
    embed = discord.Embed(
        title=f"⚠️ سجل تحذيرات العضو: {member.name}",
        color=discord.Color.orange(),
        timestamp=datetime.datetime.now()
    )
    if member.avatar:
        embed.set_thumbnail(url=member.avatar.url)
        
    if not user_warns:
        embed.description = "هذا الشخص نظيف وليس لديه أي تحذيرات! 🎉"
    else:
        for idx, w in enumerate(user_warns, 1):
            embed.add_field(
                name=f"التحذير رقم {idx}",
                value=f"**السبب:** {w['reason']}\n**المشرف:** {w['moderator']}\n**الوقت:** {w['time']}\n[🔗 رابط رسالة التحذير]({w['message_link']})",
                inline=False
            )
            
    await ctx.send(embed=embed)


# 7. أمر إزالة تحذير معين (إزالة @الشخص رقم_التحذير)
@bot.command(name="إزالة", aliases=["delwarn", "removewarn"])
@commands.has_permissions(manage_messages=True)
async def remove_warning(ctx, member: discord.Member, index: int):
    user_warns = warnings_db.get(member.id, [])
    if not user_warns or index < 1 or index > len(user_warns):
        await ctx.send("**❌ رقم التحذير غير صحيح أو العضو ليس لديه تحذيرات بهذا الرقم!**")
        return
        
    removed = user_warns.pop(index - 1)
    await ctx.send(f"**✅ تم حذف التحذير رقم {index} عن العضو {member.mention} بنجاح.**")

@remove_warning.error
async def remove_warning_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("**⚠️ الاستخدام الصحيح: إزالة @الشخص [رقم التحذير]**\nمثال: `إزالة @محمود 1`")



import datetime
import discord
from discord.ext import commands

# ==================== إعدادات السجن ====================
JAIL_CHANNEL_ID = 1541443194443669604
JAIL_ROLE_ID = 1541443299590541323

# قواعد البيانات المؤقتة
saved_roles_db = {}
current_prisoners_db = {}
jail_history_db = {}


# ==================== 1. أمر قفل الروم (ق) ====================
@bot.command(name="ق", aliases=["lock"])
@commands.has_permissions(manage_channels=True)
async def lock_channel(ctx):
    try:
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
        await ctx.send("**🔒 تم قفل الروم بنجاح! لا يمكن للأعضاء الكتابة هنا الآن.**")
    except discord.Forbidden:
        await ctx.send("**❌ ليس لدي صلاحية إدارة الرومات (Manage Channels)!**")
    except Exception as e:
        await ctx.send(f"**❌ صار فيه خطأ: {e}**")

@lock_channel.error
async def lock_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("**❌ ما عندك صلاحية Manage Channels عشان تقفل الروم!**")


# ==================== 2. أمر فتح الروم (ف) ====================
@bot.command(name="ف", aliases=["unlock"])
@commands.has_permissions(manage_channels=True)
async def unlock_channel(ctx):
    try:
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
        await ctx.send("**🔓 تم فتح الروم بنجاح! يمكن للأعضاء الكتابة الآن.**")
    except discord.Forbidden:
        await ctx.send("**❌ ليس لدي صلاحية إدارة الرومات (Manage Channels)!**")
    except Exception as e:
        await ctx.send(f"**❌ صار فيه خطأ: {e}**")

@unlock_channel.error
async def unlock_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("**❌ ما عندك صلاحية Manage Channels عشان تفتح الروم!**")


# ==================== 3. أمر السجن (سجن) ====================
@bot.command(name="سجن", aliases=["jail"])
@commands.has_permissions(administrator=True)
async def jail_member(ctx, member: discord.Member, *, reason: str = "بدون سبب"):
    if ctx.author != ctx.guild.owner and member.top_role >= ctx.author.top_role:
        await ctx.send("**❌ ما يمكنك سجن شخص رتبته أعلى منك أو مساوية لرتبتك!**")
        return
        
    jail_role = ctx.guild.get_role(JAIL_ROLE_ID)
    jail_channel = ctx.guild.get_channel(JAIL_CHANNEL_ID)
    
    if not jail_role or not jail_channel:
        await ctx.send("**❌ تأكد من صحة أيدي رتبه السجن أو أيدي روم السجن في الكود!**")
        return

    try:
        # حفظ رتب العضو وسحبها وإعطائه رتبة سجين فقط
        user_roles = [role for role in member.roles if role != ctx.guild.default_role]
        saved_roles_db[member.id] = user_roles
        
        await member.remove_roles(*user_roles, reason=f"سجن بواسطة: {ctx.author.name}")
        await member.add_roles(jail_role, reason=reason)
        
        # نقله لروم السجن الصوتي إذا كان متصلاً بصوت
        if member.voice and member.voice.channel:
            try:
                await member.move_to(jail_channel, reason="سجن العضو")
            except:
                pass
                
        jail_time_obj = datetime.datetime.now()
        current_prisoners_db[member.id] = {
            "reason": reason,
            "moderator": ctx.author.name,
            "time_obj": jail_time_obj,
            "time_str": jail_time_obj.strftime("%Y-%m-%d %H:%M")
        }
        
        if member.id not in jail_history_db:
            jail_history_db[member.id] = []
        jail_history_db[member.id].append({
            "reason": reason,
            "moderator": ctx.author.name,
            "time": jail_time_obj.strftime("%Y-%m-%d %H:%M")
        })
                
        await ctx.send(f"**🔒 تم سجن {member.mention} بنجاح! | السبب: {reason}**")
        try:
            await member.send(f"**🔒 لقد تم سجنك في سيرفر {ctx.guild.name} | السبب: {reason}**")
        except:
            pass
    except discord.Forbidden:
        await ctx.send("**❌ صلاحياتي ناقصة لا أستطيع تعديل رتب هذا الشخص!**")
    except Exception as e:
        await ctx.send(f"**❌ صار فيه خطأ: {e}**")

@jail_member.error
async def jail_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("**❌ الأمر محظور! يتطلب صلاحية Administrator (مسؤول) لتنفيذه.**")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("**⚠️ الاستخدام الصحيح: سجن @الشخص [السبب اختياري]**")


# ==================== 4. أمر الإفراج (افراج) ====================
@bot.command(name="افراج", aliases=["unjail"])
@commands.has_permissions(administrator=True)
async def unjail_member(ctx, member: discord.Member, *, reason: str = "بدون سبب"):
    if ctx.author != ctx.guild.owner and member.top_role >= ctx.author.top_role:
        await ctx.send("**❌ ما يمكنك فك سجن شخص رتبته أعلى منك أو مساوية لرتبتك!**")
        return
        
    jail_role = ctx.guild.get_role(JAIL_ROLE_ID)
    if not jail_role:
        await ctx.send("**❌ رتبه السجن غير موجودة أو الأيدي خطأ!**")
        return

    try:
        await member.remove_roles(jail_role, reason=reason)
        
        # استرجاع رتب العضو القديمة
        if member.id in saved_roles_db:
            old_roles = saved_roles_db.pop(member.id)
            valid_roles = [r for r in old_roles if r.guild == ctx.guild]
            if valid_roles:
                await member.add_roles(*valid_roles, reason="استرجاع الرتب بعد الإفراج")
            
        if member.id in current_prisoners_db:
            current_prisoners_db.pop(member.id)
            
        await ctx.send(f"**🔓 تم الإفراج عن {member.mention} بنجاح واسترجاع رتبه! | السبب: {reason}**")
        try:
            await member.send(f"**🔓 لقد تم الإفراج عنك في سيرفر {ctx.guild.name} | السبب: {reason}**")
        except:
            pass
    except discord.Forbidden:
        await ctx.send("**❌ صلاحياتي ناقصة لا أستطيع تعديل رتب هذا الشخص!**")
    except Exception as e:
        await ctx.send(f"**❌ صار فيه خطأ: {e}**")

@unjail_member.error
async def unjail_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("**❌ الأمر محظور! يتطلب صلاحية Administrator (مسؤول) لتنفيذه.**")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("**⚠️ الاستخدام الصحيح: افراج @الشخص [السبب اختياري]**")


# ==================== 5. أمر القضايا (القضايا) ====================
@bot.command(name="القضايا", aliases=["cases", "prisoners"])
@commands.has_permissions(administrator=True)
async def show_cases(ctx, member: discord.Member = None):
    if member:
        history = jail_history_db.get(member.id, [])
        is_currently_jailed = member.id in current_prisoners_db
        
        embed = discord.Embed(
            title=f"⚖️ ملف القضايا والسوابق: {member.name}",
            color=discord.Color.red() if is_currently_jailed else discord.Color.green(),
            timestamp=datetime.datetime.now()
        )
        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)
            
        embed.add_field(name="🚨 الحالة الحالية", value="مسجون حالياً 🔒" if is_currently_jailed else "خارج السجن 🟢", inline=False)
        embed.add_field(name="📂 عدد السوابق الكلي", value=f"{len(history)} مرة", inline=False)
        
        if not history:
            embed.description = "هذا الشخص سجله نظيف وليس لديه أي سوابق سجن سابقة! ✨"
        else:
            for idx, h in enumerate(history, 1):
                embed.add_field(
                    name=f"السابقة رقم {idx}",
                    value=f"**السبب:** {h['reason']}\n**المسؤول:** {h['moderator']}\n**وقت السجن:** {h['time']}",
                    inline=False
                )
        await ctx.send(embed=embed)
        
    else:
        embed = discord.Embed(
            title="📋 قائمة السجناء الحاليين في السجن",
            color=discord.Color.dark_red(),
            timestamp=datetime.datetime.now()
        )
        
        if not current_prisoners_db:
            embed.description = "لا توجد أي قضايا نشطة حالياً، السجن خالي تماماً! 🎉"
        else:
            now = datetime.datetime.now()
            for uid, data in current_prisoners_db.items():
                user = ctx.guild.get_member(uid)
                username = user.name if user else f"أيدي: {uid}"
                mention = user.mention if user else f"`{uid}`"
                
                diff = now - data["time_obj"]
                days = diff.days
                hours, remainder = divmod(diff.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                
                duration_str = ""
                if days > 0:
                    duration_str += f"{days} يوم "
                if hours > 0:
                    duration_str += f"{hours} ساعة "
                duration_str += f"{minutes} دقيقة"
                
                embed.add_field(
                    name=f"👤 {username}",
                    value=f"**مينشن:** {mention}\n**السبب:** {data['reason']}\n**المسؤول:** {data['moderator']}\n**تاريخ الدخول:** {data['time_str']}\n**مدة التواجد:** {duration_str}",
                    inline=False
                )
        await ctx.send(embed=embed)

@show_cases.error
async def show_cases_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("**❌ الأمر محظور! يتطلب صلاحية Administrator (مسؤول) لعرض القضايا والسجناء.**")
@bot.event
async def on_command_completion(ctx):
    try:
        log_channel_id = 1543068593208688733  # آيدي روم اللوق حقك
        channel = ctx.guild.get_channel(log_channel_id)
        if not channel:
            return

        actor = ctx.author
        actor_name = actor.name
        actor_id = actor.id
        actor_mention = actor.mention
        
        # رتب الفاعل
        actor_roles = [role.mention for role in actor.roles if role != ctx.guild.default_role]
        actor_roles_text = ", ".join(actor_roles) if actor_roles else "لا توجد رتب"
        actor_avatar = actor.avatar.url if actor.avatar else "لا يوجد"

        # فحص الشخص المستهدف (المنشن) واستخراج رتبه وبياناته
        target = ctx.message.mentions[0] if ctx.message.mentions else None
        
        if isinstance(target, discord.Member):
            target_roles = [role.mention for role in target.roles if role != ctx.guild.default_role]
            target_roles_text = ", ".join(target_roles) if target_roles else "لا توجد رتب"
            target_avatar = target.avatar.url if target.avatar else "لا يوجد"
            
            target_block = (
                f"• **الإشارة:** {target.mention}\n"
                f"• **اسم الحساب:** `{target.name}`\n"
                f"• **الأيدي:** `{target.id}`\n"
                f"• **الرتب ({len(target.roles)-1}):** {target_roles_text}\n"
                f"• **الأفاتار:** [اضغط هنا]({target_avatar})"
            )
        else:
            target_block = "❌ لا يوجد شخص مستهدف (أمر عام بدون منشن)"

        command_name = ctx.command.name if ctx.command else "غير معروف"
        full_message = ctx.message.content
        room = ctx.channel
        guild = ctx.guild
        jump_url = ctx.message.jump_url
        
        # وقت التنفيذ بالتاريخ والوقت الدقيق
        execution_time = datetime.now().strftime("%Y-%m-%d | %I:%M:%S %p")

        embed = discord.Embed(
            title="🕵️‍♂️ تقرير اللوق الشامل والتدقيق الجنائي",
            color=discord.Color.dark_red(),
            timestamp=ctx.message.created_at
        )
        
        if actor.avatar:
            embed.set_thumbnail(url=actor.avatar.url)

        embed.add_field(
            name="👤 معلومات الفاعل (المنفذ)",
            value=(
                f"• **الإشارة:** {actor_mention}\n"
                f"• **اسم الحساب:** `{actor_name}`\n"
                f"• **الأيدي:** `{actor_id}`\n"
                f"• **الرتب:** {actor_roles_text}\n"
                f"• **الأفاتار:** [اضغط هنا]({actor_avatar})"
            ),
            inline=False
        )

        embed.add_field(
            name="🎯 معلومات الشخص المستهدف (المفعول به)",
            value=target_block,
            inline=False
        )

        embed.add_field(
            name="⚙️ تفاصيل الأمر",
            value=(
                f"• **اسم الأمر:** `{command_name}`\n"
                f"• **نص الرسالة:** `{full_message}`\n"
                f"• **الروم:** {room.mention}\n"
                f"• **رابط الرسالة:** [اضغط هنا للانتقال]({jump_url})\n"
                f"• **وقت التنفيذ:** `{execution_time}`"
            ),
            inline=False
        )

        embed.set_footer(text=f"السيرفر: {guild.name}", icon_url=guild.icon.url if guild.icon else None)

        await channel.send(embed=embed)
    except Exception as e:
        print(f"⚠️ خطأ خفي في نظام اللوق (تم تجاوزه بنجاح): {e}")
import discord
from discord.ext import commands
import asyncio
import aiohttp

@bot.command(name="نسخ_شامل", aliases=["fullclone"])
@commands.has_permissions(administrator=True)
async def full_clone(ctx, old_guild_id: int):
    new_guild = ctx.guild
    old_guild = bot.get_guild(old_guild_id)
    
    if not old_guild:
        await ctx.send("❌ **ما لقيت السيرفر القديم، تأكد من الآيدي وأن البوت موجود فيه.**")
        return

    status_msg = await ctx.send(f"⏳ **جاري نسخ كل شيء حرفياً من ({old_guild.name})... انتظر شوي.**")

    try:
        # 1. نسخ الاسم والصورة
        icon_bytes = None
        if old_guild.icon:
            async with aiohttp.ClientSession() as session:
                async with session.get(old_guild.icon.url) as resp:
                    if resp.status == 200:
                        icon_bytes = await resp.read()

        await new_guild.edit(name=old_guild.name, icon=icon_bytes)
        await asyncio.sleep(2)

        # 2. نسخ الرتب (من الأقدم للأحدث عشان الترتيب) مع حفظ خريطة الآيديات
        roles = sorted(old_guild.roles, key=lambda r: r.position)
        role_mapping = {}

        for role in roles:
            if role.is_default() or role.managed:
                continue
            try:
                # تخطي الرتب اللي أعلى من رتبة البوت عشان ما يعطي خطأ
                if role >= new_guild.me.top_role:
                    continue
                    
                new_role = await new_guild.create_role(
                    name=role.name,
                    permissions=role.permissions,
                    color=role.color,
                    hoist=role.hoist,
                    mentionable=role.mentionable,
                    reason="نسخ شامل - رتبة"
                )
                role_mapping[role.id] = new_role
                await asyncio.sleep(1)
            except Exception as e:
                print(f"خطأ في رتبة {role.name}: {e}")

        # دالة لترجمة صلاحيات الرومات الخاصة بناءً على الرتب الجديدة
        def get_overwrites(channel_or_cat):
            overwrites = {}
            for target, perm in channel_or_cat.overwrites.items():
                if isinstance(target, discord.Role):
                    if target.is_default():
                        # الصلاحيات الخاصة بـ @everyone
                        default_role = new_guild.default_role
                        overwrites[default_role] = perm
                    elif target.id in role_mapping:
                        overwrites[role_mapping[target.id]] = perm
                elif isinstance(target, discord.Member):
                    # تجاهل الأعضاء الفرديين لأنهم مو موجودين بالسيرفر الجديد
                    pass
            return overwrites

        # 3. نسخ الفئات والرومات بصلاحياتها كاملة
        for category in sorted(old_guild.categories, key=lambda c: c.position):
            try:
                cat_overwrites = get_overwrites(category)
                new_cat = await new_guild.create_category(
                    name=category.name,
                    overwrites=cat_overwrites,
                    reason="نسخ شامل - فئة"
                )
                await new_cat.edit(position=category.position)
                await asyncio.sleep(1)

                for channel in sorted(category.channels, key=lambda ch: ch.position):
                    ch_overwrites = get_overwrites(channel)

                    if isinstance(channel, discord.TextChannel):
                        new_ch = await new_guild.create_text_channel(
                            name=channel.name,
                            category=new_cat,
                            overwrites=ch_overwrites,
                            topic=channel.topic,
                            slowmode_delay=channel.slowmode_delay,
                            nsfw=channel.nsfw,
                            reason="نسخ شامل - روم كتابي"
                        )
                        await new_ch.edit(position=channel.position)
                    elif isinstance(channel, discord.VoiceChannel):
                        new_ch = await new_guild.create_voice_channel(
                            name=channel.name,
                            category=new_cat,
                            overwrites=ch_overwrites,
                            bitrate=channel.bitrate,
                            user_limit=channel.user_limit,
                            reason="نسخ شامل - روم صوتي"
                        )
                        await new_ch.edit(position=channel.position)
                    
                    await asyncio.sleep(1)
            except Exception as e:
                print(f"خطأ في الفئة {category.name}: {e}")

        # 4. نسخ الرومات الخارجية (اللي بدون فئة)
        uncategorized = [ch for ch in old_guild.channels if ch.category is None and not isinstance(ch, discord.CategoryChannel)]
        for channel in sorted(uncategorized, key=lambda ch: ch.position):
            try:
                ch_overwrites = get_overwrites(channel)
                if isinstance(channel, discord.TextChannel):
                    new_ch = await new_guild.create_text_channel(
                        name=channel.name,
                        overwrites=ch_overwrites,
                        reason="نسخ شامل - روم حر"
                    )
                    await new_ch.edit(position=channel.position)
                elif isinstance(channel, discord.VoiceChannel):
                    new_ch = await new_ch.create_voice_channel if hasattr(new_guild, 'create_voice_channel') else await new_guild.create_voice_channel(
                        name=channel.name,
                        overwrites=ch_overwrites,
                        reason="نسخ شامل - روم صوتي حر"
                    )
                    await new_ch.edit(position=channel.position)
                await asyncio.sleep(1)
            except Exception as e:
                print(f"خطأ في روم حر {channel.name}: {e}")

        await status_msg.edit(content="✅ **تم نسخ السيرفر بالكامل [الاسم، الصورة، الرتب، صلاحيات الرتب، والرومات بأذوناتها] بنجاح تـام!**")

    except Exception as e:
        await status_msg.edit(content=f"❌ صار خطأ: {e}")




# تشغيل البوت
import os
TOKEN = os.environ.get('MASTERGUARD_TOKEN') or 'YOUR_BOT_TOKEN_HERE'
bot.run(TOKEN)
