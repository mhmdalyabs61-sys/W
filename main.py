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

import random
import time
import discord
from discord.ext import commands

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
countries_images = [
    {"name": "المملكة العربية السعودية", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c2/Makkah_Clock_Tower_02.jpg/800px-Makkah_Clock_Tower_02.jpg", "hint": "برج الساعة في مكة المكرمة 🇸🇦"},
    {"name": "مصر", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e3/Giza_Pyramids_to_Cairo_skyline_from_Citadel_crop.jpg/800px-Giza_Pyramids_to_Cairo_skyline_from_Citadel_crop.jpg", "hint": "الأهرامات 🇪🇬"},
    {"name": "الإمارات", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a4/Dubai_Marina_Skyline_2021.jpg/800px-Dubai_Marina_Skyline_2021.jpg", "hint": "دبي ومارينا دبي 🇦🇪"},
    {"name": "الكويت", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b5/Kuwait_Towers_at_night.jpg/800px-Kuwait_Towers_at_night.jpg", "hint": "أبراج الكويت 🇰🇼"},
    {"name": "قطر", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f9/Doha_West_Bay_skyline.jpg/800px-Doha_West_Bay_skyline.jpg", "hint": "أبراج الدوحة 🇶🇦"},
    {"name": "البحرين", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3d/Bahrain_World_Trade_Center_in_Manama.jpg/800px-Bahrain_World_Trade_Center_in_Manama.jpg", "hint": "مركز التجارة العالمي 🇧🇭"},
    {"name": "عمان", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/34/Mutrah_Corniche%2C_Muscat%2C_Oman.jpg/800px-Mutrah_Corniche%2C_Muscat%2C_Oman.jpg", "hint": "كورنيش مطرح في مسقط 🇴🇲"},
    {"name": "الأردن", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/aa/Petra_Jordan_Al-Khazneh_1.jpg/800px-Petra_Jordan_Al-Khazneh_1.jpg", "hint": "البتراء الأثرية 🇯🇴"},
    {"name": "العراق", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/Al-Faw_Palace_Baghdad.jpg/800px-Al-Faw_Palace_Baghdad.jpg", "hint": "معالم بغداد التاريخية 🇮🇶"},
    {"name": "سوريا", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/ce/Damascus_Citadel_View.jpg/800px-Damascus_Citadel_View.jpg", "hint": "قلعة دمشق 🇸🇾"},

    {"name": "لبنان", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4c/Jeita_Grotto_Lebanon.jpg/800px-Jeita_Grotto_Lebanon.jpg", "hint": "مغارة جعيتا 🇱🇧"},
    {"name": "فلسطين", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4e/Dome_of_the_Rock_Jerusalem.jpg/800px-Dome_of_the_Rock_Jerusalem.jpg", "hint": "مسجد قبة الصخرة في القدس 🇵🇸"},
    {"name": "المغرب", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8c/Hassan_II_Mosque_Casablanca.jpg/800px-Hassan_II_Mosque_Casablanca.jpg", "hint": "مسجد الحسن الثاني بالدار البيضاء 🇲🇦"},
    {"name": "الجزائر", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/Maqam_Echahid_Algiers.jpg/800px-Maqam_Echahid_Algiers.jpg", "hint": "مقام الشهيد بالعاصمة 🇩🇿"},
    {"name": "تونس", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d3/Sidi_Bou_Said_Tunisia.jpg/800px-Sidi_Bou_Said_Tunisia.jpg", "hint": "سيدي بو سعيد الساحرة 🇹🇳"},
    {"name": "ليبيا", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/91/Leptis_Magna_Arch_of_Septimius_Severus.jpg/800px-Leptis_Magna_Arch_of_Septimius_Severus.jpg", "hint": "لابتس ماغنا الأثرية 🇱🇾"},
    {"name": "السودان", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/53/Meroe_Pyramids_Sudan.jpg/800px-Meroe_Pyramids_Sudan.jpg", "hint": "أهرامات مروي التاريخية 🇸🇩"},
    {"name": "اليمن", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/36/Sana%27a_Old_City.jpg/800px-Sana%27a_Old_City.jpg", "hint": "بيوت صنعاء القديمة المميزة 🇾🇪"},
    {"name": "موريتانيا", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a2/Richat_Structure_Mauritania.jpg/800px-Richat_Structure_Mauritania.jpg", "hint": "قلب العين الصحراوي (ريشات) 🇲🇷"},
    {"name": "الصومال", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/Mogadishu_Beach.jpg/800px-Mogadishu_Beach.jpg", "hint": "شواطئ مقديشو الخلابة 🇸🇴"},

    {"name": "تركيا", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b8/Hagia_Sophia_Mars_2013.jpg/800px-Hagia_Sophia_Mars_2013.jpg", "hint": "آيا صوفيا في إسطنبول 🇹🇷"},
    {"name": "إيران", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Nasir_al-Molk_Mosque_Shiraz_Iran.jpg/800px-Nasir_al-Molk_Mosque_Shiraz_Iran.jpg", "hint": "مسجد الورد في شيراز 🇮🇷"},
    {"name": "باكستان", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8f/Badshahi_Mosque_Lahore.jpg/800px-Badshahi_Mosque_Lahore.jpg", "hint": "مسجد بادشاهي في لاهور 🇵🇰"},
    {"name": "الهند", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c8/Taj_Mahal_in_March_2004.jpg/800px-Taj_Mahal_in_March_2004.jpg", "hint": "تاج محل الشهير 🇮🇳"},
    {"name": "الصين", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/23/The_Great_Wall_of_China_-_July_2006.jpg/800px-The_Great_Wall_of_China_-_July_2006.jpg", "hint": "سور الصين العظيم 🇨🇳"},
    {"name": "اليابان", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1b/Mt._Fuji_from_Lake_Kawaguchiko_in_2021.jpg/800px-Mt._Fuji_from_Lake_Kawaguchiko_in_2021.jpg", "hint": "جبل فودجي الشهير 🇯🇵"},
    {"name": "كوريا الجنوبية", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6f/Seoul_Tower_and_city_view.jpg/800px-Seoul_Tower_and_city_view.jpg", "hint": "برج سيول 🇰🇷"},
    {"name": "إندونيسيا", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/91/Bali_Pura_Ulun_Danu_Bratan.jpg/800px-Bali_Pura_Ulun_Danu_Bratan.jpg", "hint": "معبد بالي الشهير 🇮🇩"},
    {"name": "ماليزيا", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/36/Petronas_Twin_Towers_2013.jpg/800px-Petronas_Twin_Towers_2013.jpg", "hint": "برجا بتروناس التوأم 🇲🇾"},
    {"name": "تايلاند", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f0/Bangkok_Grand_Palace_Thailand.jpg/800px-Bangkok_Grand_Palace_Thailand.jpg", "hint": "القصر الكبير في بانكوك 🇹🇭"},

    {"name": "فرنسا", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/85/Tour_Eiffel_Wikimedia_Commons_%28cropped%29.jpg/800px-Tour_Eiffel_Wikimedia_Commons_%28cropped%29.jpg", "hint": "برج إيفل في باريس 🇫🇷"},
    {"name": "ألمانيا", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e6/Neuschwanstein_Castle_and_Alpsee_Schwangau.jpg/800px-Neuschwanstein_Castle_and_Alpsee_Schwangau.jpg", "hint": "قلعة نويشفانشتاين الساحرة 🇩🇪"},
    {"name": "المملكة المتحدة", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/67/London_Eye_Twilight_2006.jpg/800px-London_Eye_Twilight_2006.jpg", "hint": "عين لندن وساعة بيغ بن 🇬🇧"},
    {"name": "إيطاليا", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/de/Colosseo_2020.jpg/800px-Colosseo_2020.jpg", "hint": "الكولوسيوم الروماني 🇮🇹"},
    {"name": "إسبانيا", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/18/Sagrada_Familia_Barcelona_Spain.jpg/800px-Sagrada_Familia_Barcelona_Spain.jpg", "hint": "كنيسة ساغرادا فاميليا في برشلونة 🇪🇸"},
    {"name": "روسيا", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/ba/St._Basil%27s_Cathedral_Moscow_2019.jpg/800px-St._Basil%27s_Cathedral_Moscow_2019.jpg", "hint": "كاتدرائية سانت باسيل في موسكو 🇷🇺"},
    {"name": "هولندا", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3b/Amsterdam_Canals_May_2007.jpg/800px-Amsterdam_Canals_May_2007.jpg", "hint": "قنوات أمستردام ومطاحن الهواء 🇳🇱"},
    {"name": "بلجيكا", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/68/Grand_Place_Brussels.jpg/800px-Grand_Place_Brussels.jpg", "hint": "الساحة الكبرى في بروكسل 🇧🇪"},
    {"name": "سويسرا", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/31/Matterhorn_from_Zermatt.jpg/800px-Matterhorn_from_Zermatt.jpg", "hint": "جبل ماترهورن الثلجي 🇨🇭"},
    {"name": "البرتغال", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/36/Lisbon_Tram_28_by_night.jpg/800px-Lisbon_Tram_28_by_night.jpg", "hint": "ترام لشبونة الشهير 🇵🇹"},

    {"name": "الولايات المتحدة", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7a/The_Statue_of_Liberty_and_New_York_City_Skyline_-_20060717_crop.jpg/800px-The_Statue_of_Liberty_and_New_York_City_Skyline_-_20060717_crop.jpg", "hint": "تمثال الحرية في نيويورك 🇺🇸"},
    {"name": "كندا", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d8/CN_Tower_from_Toronto_Islands.jpg/800px-CN_Tower_from_Toronto_Islands.jpg", "hint": "برج سي إن تورنتو 🇨🇦"},
    {"name": "البرازيل", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/98/Cristo_Redentor_-_Rio_de_Janeiro%2C_Brasil.jpg/800px-Cristo_Redentor_-_Rio_de_Janeiro%2C_Brasil.jpg", "hint": "تمثال المسيح الفادي في ريو 🇧🇷"},
    {"name": "الأرجنتين", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/09/Iguazu_Falls_Argentina.jpg/800px-Iguazu_Falls_Argentina.jpg", "hint": "شلالات إيغوازو الساحرة 🇦🇷"},
    {"name": "المكسيك", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4e/Chichen_Itza_3.jpg/800px-Chichen_Itza_3.jpg", "hint": "معالم تشيتشن إيتزا التاريخية 🇲🇽"},
    {"name": "كولومبيا", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8c/Cartagena_Colombia_Walled_City.jpg/800px-Cartagena_Colombia_Walled_City.jpg", "hint": "مدينة كارتاغينا التاريخية 🇨🇴"},
    {"name": "تشيلي", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/90/Torres_del_Paine_National_Park.jpg/800px-Torres_del_Paine_National_Park.jpg", "hint": "حديقة توريس ديل باينه الطبيعية 🇨🇱"},
    {"name": "بيرو", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/eb/Machu_Picchu%2C_Peru_%282018%29.jpg/800px-Machu_Picchu%2C_Peru_%282018%29.jpg", "hint": "مدينة ماتشو بيشو التاريخية 🇵🇪"},
    {"name": "فنزويلا", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d1/Salto_Angel_Kerepakupai_Meru_Auyan_Tepui.jpg/800px-Salto_Angel_Kerepakupai_Meru_Auyan_Tepui.jpg", "hint": "شلالات أنخيل أعلى شلال في العالم 🇻🇪"},
    {"name": "كوبا", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f6/Havana_Capitol_Building_Cuba.jpg/800px-Havana_Capitol_Building_Cuba.jpg", "hint": "العاصمة هافانا والسيارات الكلاسيكية 🇨🇺"},

    {"name": "أستراليا", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a0/Sydney_Australia._(21339175489).jpg/800px-Sydney_Australia._(21339175489).jpg", "hint": "دار أوبرا سيدني 🇦🇺"},
    {"name": "نيوزيلندا", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Milford_Sound_New_Zealand.jpg/800px-Milford_Sound_New_Zealand.jpg", "hint": "طبيعة نيوزيلندا الساحرة 🇳🇿"},
    {"name": "جنوب إفريقيا", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/ce/Table_Mountain_Cape_Town_South_Africa.jpg/800px-Table_Mountain_Cape_Town_South_Africa.jpg", "hint": "جبل تيبل في كيب تاون 🇿🇦"},
    {"name": "نيجيريا", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Abuja_National_Mosque.jpg/800px-Abuja_National_Mosque.jpg", "hint": "مسجد أبوجا الوطني 🇳🇬"},
    {"name": "كينيا", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3b/Maasai_Mara_Lion.jpg/800px-Maasai_Mara_Lion.jpg", "hint": "محمية ماساي مارا والحياة البرية 🇰🇪"},
    {"name": "السويد", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ab/Stockholm_Gamla_Stan_Stortorget.jpg/800px-Stockholm_Gamla_Stan_Stortorget.jpg", "hint": "مدينة ستوكهولم القديمة 🇸🇪"},
    {"name": "النرويج", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a2/Geirangerfjord_Norway.jpg/800px-Geirangerfjord_Norway.jpg", "hint": "مضايق النرويج الطبيعية 🇳🇴"},
    {"name": "الدنمارك", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b3/Nyhavn_Copenhagen_Denmark.jpg/800px-Nyhavn_Copenhagen_Denmark.jpg", "hint": "ميناء نيهفن الملون في كوبنهاغن 🇩🇰"},
    {"name": "فنلندا", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/bd/Helsinki_Cathedral_suurkirkko.jpg/800px-Helsinki_Cathedral_suurkirkko.jpg", "hint": "كاتدرائية هلسنكي 🇫🇮"},
    {"name": "اليونان", "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/da/The_Parthenon_in_Athens.jpg/800px-The_Parthenon_in_Athens.jpg", "hint": "معبد البارثينون في أثينا 🇬🇷"}
]

@bot.command(name="خمن", aliases=["guess"])
async def guess_country(ctx):
    item = random.choice(countries_images)
    target_country = item["name"]
    
    embed = discord.Embed(
        title="📸 تحدي خمن الدولة من المعلم السياحي!",
        description=f"💡 تلميح: {item['hint']}\n\n**وين الدولة اللي في الصورة؟ أسرع شخص يكتب اسمها بالشات!**",
        color=0x00e6b4
    )
    # تعيين صورة المعلم السياحي داخل الإمبيد عشان البوت هو اللي يرسلها للتشات
    embed.set_image(url=item["img"])
    embed.set_footer(text="لديك 10 ثوانٍ فقط للتخمين!")
    
    # البوت بيرسل الإمبيد مع الصورة مباشرة داخل الشات
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
