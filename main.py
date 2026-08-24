import discord, json, os, asyncio, random, time, io
from discord.ext import commands
from discord import app_commands
from datetime import timedelta, datetime
from typing import Union, Optional, List, Dict
from PIL import Image, ImageDraw


# ══════════════════════════════════════════════════════════════
#                   ضع التوكن هنا ↓
# ══════════════════════════════════════════════════════════════
TOKEN = 'YOUR_BOT_TOKEN_HERE'
# ══════════════════════════════════════════════════════════════

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
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

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

# --- الحماية الشاملة ---

@bot.event
async def on_guild_channel_delete(channel):
    if not bot_data['protection'].get('channel_del', True) or event_history.get(channel.id): return
    event_history[channel.id] = True
    
    # محاولة استعادة القناة
    try:
        if isinstance(channel, discord.VoiceChannel):
            new_ch = await channel.guild.create_voice_channel(name=channel.name, category=channel.category, position=channel.position, overwrites=channel.overwrites)
        else:
            new_ch = await channel.guild.create_text_channel(name=channel.name, category=channel.category, position=channel.position, overwrites=channel.overwrites)
        
        asyncio.create_task(queue_task(new_ch.id, asyncio.sleep(0))) # تسجيله في القفل
    except Exception as e:
        print(f"Error restoring channel: {e}")
        event_history.pop(channel.id, None)

@bot.event
async def on_guild_channel_create(channel):
    if event_history.get(channel.id) or not bot_data['protection'].get('channel_create', True): return
    
    await asyncio.sleep(1) # انتظار تحديث السجل
    async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_create):
        if entry.user.id != bot.user.id:
            event_history[channel.id] = True
            asyncio.create_task(queue_task(channel.id, channel.delete(reason="حماية: إنشاء غير مصرح")))
        break

@bot.event
async def on_guild_role_delete(role):
    if not bot_data['protection'].get('role_del', True) or event_history.get(role.id): return
    event_history[role.id] = True
    
    try:
        new_role = await role.guild.create_role(name=role.name, permissions=role.permissions, color=role.color, hoist=role.hoist, mentionable=role.mentionable)
        asyncio.create_task(queue_task(new_role.id, asyncio.sleep(0)))
    except: event_history.pop(role.id, None)

@bot.event
async def on_guild_role_create(role):
    if event_history.get(role.id) or not bot_data['protection'].get('role_create', True): return
    async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_create):
        if entry.user.id != bot.user.id:
            event_history[role.id] = True
            asyncio.create_task(queue_task(role.id, role.delete(reason="حماية: إنشاء غير مصرح")))
        break

@bot.event
async def on_webhooks_update(channel):
    if not bot_data['protection'].get('webhook', True): return
    try:
        webhooks = await channel.webhooks()
        for wh in webhooks:
            asyncio.create_task(queue_task(wh.id, wh.delete(reason="حماية: حذف ويب هوك")))
    except: pass

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




# قاموس حفظ النقاط المشترك
user_scores = {}

# دالة إصلاح الحروف العربية المقلوبة
def fix_arabic(text):
    return text[::-1]

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
# 3. لعبة خمن الدولة (الـ 60 دولة كاملة)
# ----------------------------------------------------
import random
import time
import discord
from discord.ext import commands

user_scores = {}

def fix_arabic(text):
    return text[::-1]

# قائمة الـ 60 دولة مع صور حقيقية لمعالم أو مناظر من داخل كل دولة
import random
import discord
from discord.ext import commands

user_scores = {}

def fix_arabic(text):
    return text[::-1]

# قائمة الـ 60 دولة بروابط صور مباشرة ومستقرة 100%
countries_images = [
    # الدول العربية
    {"name": "المملكة العربية السعودية", "img": "https://images.unsplash.com/photo-1586724237569-f3d029bf46e5?w=800", "hint": "معالم المملكة 🇸🇦"},
    {"name": "مصر", "img": "https://images.unsplash.com/photo-1572252009286-268acec5ca0a?w=800", "hint": "الأهرامات التاريخية 🇪🇬"},
    {"name": "الإمارات", "img": "https://images.unsplash.com/photo-1512453979798-5ea266f8880c?w=800", "hint": "برج خليفة ودبي 🇦🇪"},
    {"name": "الكويت", "img": "https://images.unsplash.com/photo-1565557623262-b51c2513a641?w=800", "hint": "أبراج الكويت 🇰🇼"},
    {"name": "قطر", "img": "https://images.unsplash.com/photo-1583089892998-d36183061124?w=800", "hint": "الدوحة وأبراجها 🇶🇦"},
    {"name": "البحرين", "img": "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?w=800", "hint": "معالم المنامة 🇧🇭"},
    {"name": "عمان", "img": "https://images.unsplash.com/photo-1580618672591-eb180b1a973f?w=800", "hint": "سلطنة عمان 🇴🇲"},
    {"name": "الأردن", "img": "https://images.unsplash.com/photo-1564507592333-c60657eea523?w=800", "hint": "البتراء الأثرية 🇯🇴"},
    {"name": "العراق", "img": "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?w=800", "hint": "معالم الرافدين 🇮🇶"},
    {"name": "سوريا", "img": "https://images.unsplash.com/photo-1541872703-74c5e44368f9?w=800", "hint": "التاريخ السوري 🇸🇾"},
    {"name": "لبنان", "img": "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?w=800", "hint": "بيروت ولبنان 🇱🇧"},
    {"name": "فلسطين", "img": "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?w=800", "hint": "القدس الشريف 🇵🇸"},
    {"name": "المغرب", "img": "https://images.unsplash.com/photo-1539650116574-8efeb43e2750?w=800", "hint": "المغرب العربي 🇲🇦"},
    {"name": "الجزائر", "img": "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?w=800", "hint": "الجزائر العاصمة 🇩🇿"},
    {"name": "تونس", "img": "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?w=800", "hint": "تونس الخضراء 🇹🇳"},

    # دول آسيا
    {"name": "تركيا", "img": "https://images.unsplash.com/photo-1541432901042-2d8bd64b4a9b?w=800", "hint": "إسطنبول وتركيا 🇹🇷"},
    {"name": "اليابان", "img": "https://images.unsplash.com/photo-1503899036084-c55cdd92da26?w=800", "hint": "طوكيو واليابان 🇯🇵"},
    {"name": "الصين", "img": "https://images.unsplash.com/photo-1508804052814-cd38ba552e4d?w=800", "hint": "سور الصين العظيم 🇨🇳"},
    {"name": "الهند", "img": "https://images.unsplash.com/photo-1524492412937-b28074a5d7da?w=800", "hint": "تاج محل 🇮🇳"},
    {"name": "كوريا الجنوبية", "img": "https://images.unsplash.com/photo-1538485399061-1774e402d294?w=800", "hint": "سيول كوريا 🇰🇷"},
    {"name": "إندونيسيا", "img": "https://images.unsplash.com/photo-1537996194471-e657df975ab4?w=800", "hint": "بالي وطبيعتها 🇮🇩"},
    {"name": "ماليزيا", "img": "https://images.unsplash.com/photo-1596422846543-75c6fc197f07?w=800", "hint": "كوالالمبور وبتروناس 🇲🇾"},
    {"name": "تايلاند", "img": "https://images.unsplash.com/photo-1552465011-b4e21bf6e79a?w=800", "hint": "بانكوك 🇹🇭"},
    {"name": "باكستان", "img": "https://images.unsplash.com/photo-1609137144813-7f9f5b770fb9?w=800", "hint": "باكستان التاريخية 🇵🇰"},
    {"name": "إيران", "img": "https://images.unsplash.com/photo-1584551246679-0daf3d275d0f?w=800", "hint": "المعالم الإيرانية 🇮🇷"},

    # دول أوروبا
    {"name": "فرنسا", "img": "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=800", "hint": "برج إيفل في باريس 🇫🇷"},
    {"name": "المملكة المتحدة", "img": "https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?w=800", "hint": "لندن وساعة بيغ بن 🇬🇧"},
    {"name": "إيطاليا", "img": "https://images.unsplash.com/photo-1516483638261-f4dbaf036963?w=800", "hint": "روما وإيطاليا 🇮🇹"},
    {"name": "ألمانيا", "img": "https://images.unsplash.com/photo-1467269204594-9661b134dd2b?w=800", "hint": "ألمانيا والمعالم 🇩🇪"},
    {"name": "إسبانيا", "img": "https://images.unsplash.com/photo-1543783207-ec64e4d95325?w=800", "hint": "مدريد وبرشلونة 🇪🇸"},
    {"name": "روسيا", "img": "https://images.unsplash.com/photo-1513326738677-b964603b136d?w=800", "hint": "موسكو وروسيا 🇷🇺"},
    {"name": "هولندا", "img": "https://images.unsplash.com/photo-1512470876302-972faa2aa9a4?w=800", "hint": "أمستردام 🇳🇱"},
    {"name": "سويسرا", "img": "https://images.unsplash.com/photo-1530122037265-a5f1f91d3b99?w=800", "hint": "جبال الألب السويسرية 🇨🇭"},
    {"name": "البرتغال", "img": "https://images.unsplash.com/photo-1515542622106-78bda8ba0e5b?w=800", "hint": "لشبونة البرتغال 🇵🇹"},
    {"name": "السويد", "img": "https://images.unsplash.com/photo-1509356843153-3f1b213bfa7a?w=800", "hint": "ستوكهولم السويد 🇸🇪"},
    {"name": "النرويج", "img": "https://images.unsplash.com/photo-1507034589631-9433cc6bc453?w=800", "hint": "طبيعة النرويج 🇳🇴"},
    {"name": "اليونان", "img": "https://images.unsplash.com/photo-1533105079780-92b9be482077?w=800", "hint": "أثينا واليونان 🇬🇷"},
    {"name": "النمسا", "img": "https://images.unsplash.com/photo-1516550893885-303ce2779fce?w=800", "hint": "فيينا النمسا 🇦🇹"},
    {"name": "بلجيكا", "img": "https://images.unsplash.com/photo-1551643206-8d6938a75e12?w=800", "hint": "بروكسل بلجيكا 🇧🇪"},
    {"name": "الدنمارك", "img": "https://images.unsplash.com/photo-1513622470522-26c3c8a854bc?w=800", "hint": "كوبنهاغن الدنمارك 🇩🇰"},

    # أمريكا الشمالية والجنوبية
    {"name": "الولايات المتحدة", "img": "https://images.unsplash.com/photo-1485738422979-f5c462d49f74?w=800", "hint": "نيويورك أمريكا 🇺🇸"},
    {"name": "كندا", "img": "https://images.unsplash.com/photo-1503614472-8c93d56e92ce?w=800", "hint": "تورنتو وكندا 🇨🇦"},
    {"name": "المكسيك", "img": "https://images.unsplash.com/photo-1512813277712-4d37537b7713?w=800", "hint": "المكسيك التاريخية 🇲🇽"},
    {"name": "البرازيل", "img": "https://images.unsplash.com/photo-1483729558449-99ef09a8c325?w=800", "hint": "ريو دي جانيرو البرازيل 🇧🇷"},
    {"name": "الأرجنتين", "img": "https://images.unsplash.com/photo-1589909202874-1779777f7223?w=800", "hint": "بوينس آيرس الأرجنتين 🇦🇷"},
    {"name": "كولومبيا", "img": "https://images.unsplash.com/photo-1590523277543-a94d2e4eb00b?w=800", "hint": "كولومبيا الساحرة 🇨🇴"},
    {"name": "تشيلي", "img": "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?w=800", "hint": "تشيلي الطبيعة 🇨🇱"},
    {"name": "بيرو", "img": "https://images.unsplash.com/photo-1526392060635-9d6019884377?w=800", "hint": "ماتشو بيشو بيرو 🇵🇪"},
    {"name": "كوبا", "img": "https://images.unsplash.com/photo-1500759285702-e7d61837f48c?w=800", "hint": "هافانا كوبا 🇨🇺"},

    # أوقيانوسيا وأفريقيا
    {"name": "أستراليا", "img": "https://images.unsplash.com/photo-1506973035872-a4ec16b8e8d9?w=800", "hint": "دار أوبرا سيدني 🇦🇺"},
    {"name": "نيوزيلندا", "img": "https://images.unsplash.com/photo-1469521669194-0384891ffc4f?w=800", "hint": "طبيعة نيوزيلندا 🇳🇿"},
    {"name": "جنوب إفريقيا", "img": "https://images.unsplash.com/photo-1580618672591-eb180b1a973f?w=800", "hint": "كيب تاون جنوب إفريقيا 🇿🇦"},
    {"name": "كينيا", "img": "https://images.unsplash.com/photo-1516426122078-c23e76319801?w=800", "hint": "سفاري كينيا 🇰🇪"},
    {"name": "نيجيريا", "img": "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?w=800", "hint": "نيجيريا 🇳🇬"},
    {"name": "أيسلندا", "img": "https://images.unsplash.com/photo-1504893524553-29586e1e191d?w=800", "hint": "أيسلندا والجليد 🇮🇸"},
    {"name": "أيرلندا", "img": "https://images.unsplash.com/photo-1590089415225-4034664ce935?w=800", "hint": "دبلن أيرلندا 🇮🇪"},
    {"name": "فندا", "img": "https://images.unsplash.com/photo-1517783997529-28f58c740a48?w=800", "hint": "فنلندا الشفق 🇫🇮"},
    {"name": "المجر", "img": "https://images.unsplash.com/photo-1549877452-9c387954fbc2?w=800", "hint": "بودابست المجر 🇭🇺"},
    {"name": "رومانيا", "img": "https://images.unsplash.com/photo-1584646098378-0874589d76b1?w=800", "hint": "رومانيا القلاع 🇷🇴"}
]

@bot.command(name="خمن", aliases=["guess"])
async def guess_country(ctx):
    item = random.choice(countries_images)
    target_country = item["name"]
    
    embed = discord.Embed(
        title="📸 تحدي خمن الدولة من المعلم السياحي!",
        description=f"💡 تلميح: **{item['hint']}**\n\n**وين الدولة اللي في الصورة؟ أسرع شخص يكتب اسمها بالشات!**",
        color=0x00e6b4
    )
    embed.set_image(url=item["img"])
    embed.set_footer(text="لديك 10 ثوانٍ فقط للتخمين!")
    
    await ctx.send(embed=embed)
    
    def check(m):
        user_text = m.content.strip()
        return m.channel == ctx.channel and (user_text == target_country or user_text == fix_arabic(target_country)) and not m.author.bot

    try:
        msg = await bot.wait_for('message', timeout=10.0, check=check)
        user_scores[msg.author.id] = user_scores.get(msg.author.id, 0) + 1
        await ctx.send(f"🎯 كفو يا <@{msg.author.id}>! الدولة هي **{target_country}** (+1 نقطة)")
    except Exception:
        await ctx.send(f"⏰ خلص الوقت! الدولة كانت: **{target_country}**")









# تشغيل البوت
import os
TOKEN = os.environ.get('MASTERGUARD_TOKEN') or 'YOUR_BOT_TOKEN_HERE'
bot.run(TOKEN)
