import asyncio
from collections import defaultdict, deque
from datetime import datetime, timezone, timedelta
import json
import os
import re
import time
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

# --- إعدادات البوت والـ Intents ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True
intents.guilds = True
intents.moderation = True

DATA_FILE = "bot_data.json"
spam_tracker = defaultdict(deque)
ban_tracker = defaultdict(deque)

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def parse_time(time_str):
    match = re.match(r"^(\d+)([mhd])$", time_str.strip().lower())
    if not match:
        return None
    value, unit = int(match.group(1)), match.group(2)
    if unit == 'm':
        return timedelta(minutes=value)
    elif unit == 'h':
        return timedelta(hours=value)
    elif unit == 'd':
        return timedelta(days=value)
    return None

def black_embed(title=None, description=None, timestamp=None):
    return discord.Embed(title=title, description=description, color=discord.Color.from_rgb(0, 0, 0), timestamp=timestamp)

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(DynamicTicketControlView())
        self.add_view(TicketDeleteView())
        synced = await self.tree.sync()
        print(f"تمت مزامنة {len(synced)} أمر بنجاح!")

bot = MyBot()

@bot.event
async def on_ready():
    print(f"تم تسجيل الدخول بنجاح باسم: {bot.user}")

async def send_log(guild, log_type, embed):
    data = load_data()
    gid = str(guild.id)
    g_data = data.get(gid, {})
    log_config = g_data.get("log_channels", {})
    
    channel_id = log_config.get(log_type) or log_config.get("all")
    if channel_id:
        channel = guild.get_channel(channel_id)
        if channel:
            try:
                await channel.send(embed=embed)
            except Exception as e:
                print(f"Error sending log: {e}")

class SecurityPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="حماية السبام", emoji="⚡", style=discord.ButtonStyle.danger, row=0)
    async def toggle_spam(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        gid = str(interaction.guild_id)
        current = data.get(gid, {}).get("sec_spam", False)
        data.setdefault(gid, {})["sec_spam"] = not current
        save_data(data)
        status = "مفعلة ✅" if not current else "معطلة ❌"
        await interaction.response.send_message(f"⚡ حماية السبام أصبحت الآن: **{status}**", ephemeral=True)

    @discord.ui.button(label="فلتر الكلمات", emoji="🛡️", style=discord.ButtonStyle.primary, row=0)
    async def toggle_words(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        gid = str(interaction.guild_id)
        current = data.get(gid, {}).get("sec_words", False)
        data.setdefault(gid, {})["sec_words"] = not current
        save_data(data)
        status = "مفعل ✅" if not current else "معطل ❌"
        await interaction.response.send_message(f"🛡️ فلتر الكلمات المسيئة أصبح الآن: **{status}**", ephemeral=True)

    @discord.ui.button(label="حماية الروابط", emoji="🔗", style=discord.ButtonStyle.primary, row=0)
    async def toggle_links(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        gid = str(interaction.guild_id)
        current = data.get(gid, {}).get("sec_links", False)
        data.setdefault(gid, {})["sec_links"] = not current
        save_data(data)
        status = "مفعلة ✅" if not current else "معطلة ❌"
        await interaction.response.send_message(f"🔗 حماية الروابط الخارجية أصبحت: **{status}**", ephemeral=True)

    @discord.ui.button(label="حماية الباند السريع", emoji="🚨", style=discord.ButtonStyle.danger, row=1)
    async def toggle_fast_ban(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        gid = str(interaction.guild_id)
        current = data.get(gid, {}).get("sec_fast_ban", False)
        data.setdefault(gid, {})["sec_fast_ban"] = not current
        save_data(data)
        status = "مفعل ✅" if not current else "معطل ❌"
        await interaction.response.send_message(f"🚨 حماية الباند السريع (3 باندات/ثانية) أصبحت: **{status}**", ephemeral=True)

    @discord.ui.button(label="حماية الصلاحيات الخطيرة", emoji="👑", style=discord.ButtonStyle.danger, row=1)
    async def toggle_admin_protect(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        gid = str(interaction.guild_id)
        current = data.get(gid, {}).get("sec_admin_protect", False)
        data.setdefault(gid, {})["sec_admin_protect"] = not current
        save_data(data)
        status = "مفعل ✅" if not current else "معطل ❌"
        await interaction.response.send_message(f"👑 حماية إعطاء صلاحيات الأدمن الخطيرة أصبحت: **{status}**", ephemeral=True)

    @discord.ui.button(label="نسخ السيرفر (Backup)", emoji="💾", style=discord.ButtonStyle.success, row=2)
    async def backup_server(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        backup_data = {
            "roles": [{"name": r.name, "color": r.color.value, "permissions": r.permissions.value} for r in reversed(guild.roles) if not r.is_default() and not r.managed],
            "categories": {cat.name: [ch.name for ch in cat.channels] for cat in guild.categories}
        }
        data = load_data()
        data.setdefault(str(guild.id), {})["backup"] = backup_data
        save_data(data)
        await interaction.followup.send("💾 تم اخذ نسخة احتياطية (بصمة الرتب والرومات) بنجاح!", ephemeral=True)

    @discord.ui.button(label="استعادة السيرفر (Restore)", emoji="♻️", style=discord.ButtonStyle.success, row=2)
    async def restore_server(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        data = load_data()
        gid = str(guild.id)
        backup_data = data.get(gid, {}).get("backup")
        
        if not backup_data:
            await interaction.followup.send("❌ لا توجد نسخة احتياطية محفوظة لهذا السيرفر!", ephemeral=True)
            return

        try:
            for r_data in backup_data.get("roles", []):
                existing = discord.utils.get(guild.roles, name=r_data["name"])
                if not existing:
                    await guild.create_role(
                        name=r_data["name"],
                        color=discord.Color(r_data["color"]),
                        permissions=discord.permissions.Permissions(r_data["permissions"])
                    )

            for cat_name, channels in backup_data.get("categories", {}).items():
                existing_cat = discord.utils.get(guild.categories, name=cat_name)
                if not existing_cat:
                    cat = await guild.create_category(cat_name)
                else:
                    cat = existing_cat
                
                for ch_name in channels:
                    existing_ch = discord.utils.get(cat.channels, name=ch_name)
                    if not existing_ch:
                        await guild.create_text_channel(ch_name, category=cat)

            await interaction.followup.send("♻️ تمت استعادة الرتب والتصنيفات والرومات بنجاح!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ حدث خطأ أثناء الاستعادة: {e}", ephemeral=True)

class GiveawayView(discord.ui.View):
    def __init__(self, prize, end_time):
        super().__init__(timeout=None)
        self.participants = set()
        self.prize = prize
        self.end_time = end_time

    @discord.ui.button(label="مشاركة 🎉", style=discord.ButtonStyle.success, custom_id="join_giveaway")
    async def join_giveaway(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id in self.participants:
            await interaction.response.send_message("❌ أنت مشارك بالفعل في هذا القيف أواي !", ephemeral=True)
        else:
            self.participants.add(interaction.user.id)
            await interaction.response.send_message("✅ تم تسجيل مشاركتك بنجاح في القيف أواي ، بالتوفيق !", ephemeral=True)

class TicketDeleteView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="حذف التذكرة 🗑️", style=discord.ButtonStyle.danger, custom_id="ticket_delete_btn")
    async def delete_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("❌ لا تملك صلاحية لحذف التذكرة!", ephemeral=True)
            return
        await interaction.response.send_message("🔄 جاري حذف الروم...", ephemeral=True)
        await asyncio.sleep(1)
        await interaction.channel.delete()

class DynamicTicketControlView(discord.ui.View):
    def __init__(self, claimed_by=None):
        super().__init__(timeout=None)
        self.claimed_by = claimed_by

    @discord.ui.button(label="استلام ✋", style=discord.ButtonStyle.success, custom_id="ticket_claim_btn")
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("❌ هذه الأزرار خاصة بالإدارة فقط!", ephemeral=True)
            return

        self.claimed_by = interaction.user.id
        embed = interaction.message.embeds[0]
        
        ticket_owner = embed.fields[0].value if len(embed.fields) > 0 else "غير معروف"
        embed.description = f"**صاحب التذكرة:** {ticket_owner}\n**تم الاستلام بواسطة:** {interaction.user.mention} ✋\n**الحالة:** 🔒 قيد المتابعة"

        new_view = DynamicTicketControlView(claimed_by=interaction.user.id)
        await interaction.message.edit(embed=embed, view=new_view)
        await interaction.response.send_message(f"✅ تم استلام التذكرة بواسطة {interaction.user.mention}!", ephemeral=False)

    @discord.ui.button(label="ترك الاستلام 🔓", style=discord.ButtonStyle.primary, custom_id="ticket_unclaim_btn")
    async def unclaim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("❌ هذه الأزرار خاصة بالإدارة فقط!", ephemeral=True)
            return

        if self.claimed_by != interaction.user.id and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ لا يمكنك ترك استلام تذكرة لم تقم أنت باستلامها!", ephemeral=True)
            return

        self.claimed_by = None
        embed = interaction.message.embeds[0]
        ticket_owner = embed.fields[0].value if len(embed.fields) > 0 else "غير معروف"
        embed.description = f"**صاحب التذكرة:** {ticket_owner}\n**الحالة:** 🟢 متاحة للاستلام من قبل الإدارة"

        new_view = DynamicTicketControlView(claimed_by=None)
        await interaction.message.edit(embed=embed, view=new_view)
        await interaction.response.send_message(f"🔓 قام {interaction.user.mention} بترك استلام التذكرة.", ephemeral=False)

    @discord.ui.button(label="إغلاق 🔒", style=discord.ButtonStyle.danger, custom_id="ticket_close_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("❌ هذه الأزرار خاصة بالإدارة فقط!", ephemeral=True)
            return

        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, manage_channels=True)
        }
        await interaction.channel.edit(overwrites=overwrites, topic="تذكرة مغلقة")

        close_embed = discord.Embed(title="🔒 تم إغلاق التذكرة", description=f"بواسطة: {interaction.user.mention}\n\nللإدارة: اضغط الزر بالأسفل لحذف الروم نهائياً.", color=discord.Color.red())
        await interaction.channel.send(embed=close_embed, view=TicketDeleteView())
        
        log_embed = black_embed(
            title="🔒 إغلاق تذكرة",
            description=f"**اسم الروم:** `{interaction.channel.name}`\n**بواسطة الإداري:** {interaction.user.mention}",
            timestamp=datetime.now(timezone.utc)
        )
        await send_log(interaction.guild, "ticket", log_embed)
        await send_log(interaction.guild, "all", log_embed)

        await interaction.response.send_message("🔒 تم قفل التذكرة بنجاح.", ephemeral=True)

class DynamicTicketModal(discord.ui.Modal):
    def __init__(self, role_id, option_label):
        super().__init__(title=f"تقديم طلب: {option_label}")
        self.role_id = role_id
        self.option_label = option_label

        self.reason = discord.ui.TextInput(
            label="تفاصيل الطلب أو الشرح",
            placeholder="اكتب تفاصيل مشكلتك أو طلبك هنا...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        data = load_data()
        gid = str(guild.id)
        
        g_conf = data.setdefault(gid, {})
        ticket_counter = g_conf.get("ticket_counter", 0) + 1
        g_conf["ticket_counter"] = ticket_counter
        save_data(data)

        channel_name = f"ticket-{interaction.user.name}-{ticket_counter}"
        role = guild.get_role(self.role_id)
        role_mention = role.mention if role else "@هنا الإدارة"

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, view_channel=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        if role:
            overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, view_channel=True)

        ticket_channel = await guild.create_text_channel(channel_name, overwrites=overwrites)

        embed = black_embed(
            title="🎫 تذكرة دعم جديدة",
            description=f"**🟢 الحالة:** متاحة للاستلام من قبل الإدارة\n**رقم التذكرة:** `#{ticket_counter}`\n**نوع الطلب:** `{self.option_label}`\n**الشرح والتفاصيل:**\n`{self.reason.value}`"
        )
        embed.add_field(name="👤 صاحب التذكرة", value=interaction.user.mention, inline=False)
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        await ticket_channel.send(content=f"مرحباً {interaction.user.mention} | {role_mention}", embed=embed, view=DynamicTicketControlView())
        
        log_embed = black_embed(
            title="🎫 فتح تذكرة جديدة",
            description=f"**صاحب التذكرة:** {interaction.user.mention} (`{interaction.user.name}`)\n**رقم التذكرة:** `#{ticket_counter}`\n**روم التذكرة:** {ticket_channel.mention}\n**النوع:** `{self.option_label}`",
            timestamp=datetime.now(timezone.utc)
        )
        await send_log(guild, "ticket", log_embed)
        await send_log(guild, "all", log_embed)

        await interaction.response.send_message(f"✅ تم فتح تذكرتك بنجاح: {ticket_channel.mention}", ephemeral=True)

class DynamicTicketSelect(discord.ui.Select):
    def __init__(self, options_data):
        self.options_data = options_data
        select_options = [discord.SelectOption(label=opt["label"], description=opt.get("description", "")) for opt in options_data]
        super().__init__(placeholder="اختر نوع الطلب من القائمة...", min_values=1, max_values=1, options=select_options)

    async def callback(self, interaction: discord.Interaction):
        selected_label = self.values[0]
        role_id = None
        for opt in self.options_data:
            if opt["label"] == selected_label:
                role_id = opt["role_id"]
                break
        await interaction.response.send_modal(DynamicTicketModal(role_id, selected_label))

class DynamicTicketView(discord.ui.View):
    def __init__(self, options_data):
        super().__init__(timeout=None)
        self.add_item(DynamicTicketSelect(options_data))

class TicketSetupModal(discord.ui.Modal, title="إعداد لوحة التذاكر الشامل"):
    def __init__(self, channel):
        super().__init__()
        self.channel = channel

        self.panel_title = discord.ui.TextInput(
            label="عنوان لوحة التذاكر (Embed Title)",
            placeholder="مثال: نظام تذاكر السيرفر",
            style=discord.TextStyle.short,
            required=True,
            max_length=100
        )
        self.add_item(self.panel_title)

        self.options_input = discord.ui.TextInput(
            label="الخيارات والرتب (الاسم | ID الرتبة بكل سطر)",
            placeholder="دعم فني عام | 123456789123456789\nطلب رتبة | 987654321987654321",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1500
        )
        self.add_item(self.options_input)

    async def on_submit(self, interaction: discord.Interaction):
        lines = self.options_input.value.strip().split('\n')
        options_data = []

        for line in lines:
            if "|" in line:
                parts = line.split("|")
                label = parts[0].strip()
                role_id_str = parts[1].strip()
                if role_id_str.isdigit():
                    options_data.append({"label": label, "role_id": int(role_id_str)})

        if not options_data:
            await interaction.response.send_message("❌ صيغة الخيارات غير صحيحة! يجب أن تكون: `اسم الخيار | ID الرتبة` في كل سطر.", ephemeral=True)
            return

        data = load_data()
        gid = str(interaction.guild_id)
        data.setdefault(gid, {})["ticket_config"] = options_data
        save_data(data)

        embed = black_embed(
            title=self.panel_title.value,
            description="لفتح تذكرة جديدة، اختر القسم المناسب من القائمة بالأسفل 👇"
        )
        if interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)

        view = DynamicTicketView(options_data)
        await self.channel.send(embed=embed, view=view)
        await interaction.response.send_message(f"✅ تم إرسال لوحة التذاكر بنجاح إلى {self.channel.mention}!", ephemeral=True)

@bot.tree.command(name="ticket_setup", description="إرسال لوحة فتح التذاكر في الروم عبر نافذة المودل")
@app_commands.checks.has_permissions(administrator=True)
async def ticket_setup(interaction: discord.Interaction, channel: discord.TextChannel):
    await interaction.response.send_modal(TicketSetupModal(channel))

class AddReplyModal(discord.ui.Modal, title="إضافة رد تلقائي جديد"):
    trigger = discord.ui.TextInput(
        label="الكلمة المفتاحية (Trigger)",
        placeholder="مثال: رابط",
        style=discord.TextStyle.short,
        required=True,
        max_length=100
    )
    response_text = discord.ui.TextInput(
        label="نص الرد التلقائي",
        placeholder="ممنوع نشر الروابط!",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1500
    )

    async def on_submit(self, interaction: discord.Interaction):
        data = load_data()
        gid = str(interaction.guild_id)
        trig_lower = self.trigger.value.strip().lower()
        data.setdefault(gid, {}).setdefault("auto_replies", {})[trig_lower] = self.response_text.value
        save_data(data)
        await interaction.response.send_message(f"✅ تم إضافة الرد التلقائي بكلمة : `{self.trigger.value}`", ephemeral=True)

class DelReplySelect(discord.ui.Select):
    def __init__(self, triggers):
        options = [discord.SelectOption(label=trigger, description=f"حذف الرد الخاص بـ: {trigger}") for trigger in triggers]
        super().__init__(placeholder="اختر الكلمة المفتاحية لحذفها...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_trigger = self.values[0]
        data = load_data()
        gid = str(interaction.guild_id)
        triggers = data.get(gid, {}).get("auto_replies", {})
        
        if selected_trigger in triggers:
            del triggers[selected_trigger]
            save_data(data)
            await interaction.response.send_message(f"🗑️ تم حذف الرد الخاص بـ `{selected_trigger}` بنجاح !", ephemeral=True)
        else:
            await interaction.response.send_message(f"⚠️ الكلمة غير موجودة !", ephemeral=True)

class DelReplyView(discord.ui.View):
    def __init__(self, triggers):
        super().__init__(timeout=None)
        self.add_item(DelReplySelect(triggers))

@bot.tree.command(name="add_reply", description="فتح نافذة إضافة رد تلقائي جديد")
@app_commands.checks.has_permissions(administrator=True)
async def add_reply_slash(interaction: discord.Interaction):
    await interaction.response.send_modal(AddReplyModal())

@bot.tree.command(name="del_reply", description="اختيار وحذف رد تلقائي من القائمة")
@app_commands.checks.has_permissions(administrator=True)
async def del_reply_slash(interaction: discord.Interaction):
    data = load_data()
    gid = str(interaction.guild_id)
    triggers = list(data.get(gid, {}).get("auto_replies", {}).keys())
    
    if not triggers:
        await interaction.response.send_message("❌ لا توجد ردود تلقائية مضافة في هذا السيرفر لحذفها!", ephemeral=True)
        return

    view = DelReplyView(triggers)
    await interaction.response.send_message("الرجاء اختيار الكلمة التي تريد حذفها من القائمة:", view=view, ephemeral=True)

class AddStickerModal(discord.ui.Modal, title="إضافة ستيكر جديد"):
    sticker_name = discord.ui.TextInput(
        label="اسم الستيكر",
        placeholder="مثال: hype",
        style=discord.TextStyle.short,
        required=True,
        max_length=32
    )
    emoji_code = discord.ui.TextInput(
        label="كود الستيكر أو الإيموجي",
        placeholder="مثال: <a:hype:123456789123456789>",
        style=discord.TextStyle.short,
        required=True,
        max_length=100
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            match = re.search(r'<(?P<animated>a)?:(?P<name>\w+):(?P<id>\d+)>', self.emoji_code.value.strip())
            if not match:
                await interaction.response.send_message("❌ صيغة الكود غير صحيحة! يرجى إدخال الكود الكامل للإيموجي (مثل `<:name:id>` أو `<a:name:id>`).", ephemeral=True)
                return

            anim = match.group('animated')
            eid = match.group('id')
            ext = 'gif' if anim else 'png'
            url = f"https://cdn.discordapp.com/emojis/{eid}.{ext}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        await interaction.response.send_message("❌ تعذر تحميل الصورة من الرابط الخاص بهذا الكود!", ephemeral=True)
                        return
                    image_bytes = await resp.read()

            new_emoji = await interaction.guild.create_custom_emoji(name=self.sticker_name.value.strip(), image=image_bytes)
            await interaction.response.send_message(f"✅ تم إضافة الستيكر/الإيموجي **{new_emoji.name}** بنجاح للسيرفر !", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ تعذر إضافة الستيكر : {e}", ephemeral=True)

@bot.tree.command(name="addsticker", description="فتح نافذة إضافة ستيكر جديد باستخدام الكود فقط")
@app_commands.checks.has_permissions(manage_emojis=True)
async def addsticker_slash(interaction: discord.Interaction):
    await interaction.response.send_modal(AddStickerModal())

@bot.tree.command(name="security", description="عرض لوحة التحكم في الحماية والأمان بالسيرفر")
@app_commands.checks.has_permissions(administrator=True)
async def security_panel(interaction: discord.Interaction):
    embed = black_embed(
        title="🔒 لوحة حماية وأمان السيرفر",
        description="من هنا يمكنك التحكم بكافة أنظمة الحماية:\n\n• **حماية السبام :** منع التكرار السريع وإعطاء تايم أوت أو باند .\n• **فلتر الكلمات :** حذف الشتائم والكلمات الممنوعة تلقائياً .\n• **حماية الروابط :** منع الروابط الخارجية الضارة .\n• **حماية الباند السريع :** باند لمن يقوم بـ 3 باندات بنفس الثانية .\n• **حماية الصلاحيات :** معاقبة من يمنح صلاحيات خطيرة للأعضاء .\n• **نسخ واستعادة السيرفر :** حفظ واسترجاع الرتب والرومات بضغطة زر ."
    )
    view = SecurityPanelView()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="set_log", description="إنشاء رومات وتصنيف الـ Log تلقائياً في أواخر السيرفر (مع روم تيكت)")
@app_commands.checks.has_permissions(administrator=True)
async def set_log(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    try:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, manage_channels=True)
        }
        category = await guild.create_category("📊 SERVER LOGS", overwrites=overwrites, position=999)
        
        ch_ban = await guild.create_text_channel("log-ban", category=category)
        ch_time = await guild.create_text_channel("log-time", category=category)
        ch_room = await guild.create_text_channel("log-room", category=category)
        ch_join = await guild.create_text_channel("log-join", category=category)
        ch_ticket = await guild.create_text_channel("log-ticket", category=category)
        ch_all = await guild.create_text_channel("log-all", category=category)

        data = load_data()
        gid = str(guild.id)
        data.setdefault(gid, {})["log_channels"] = {
            "ban": ch_ban.id,
            "time": ch_time.id,
            "room": ch_room.id,
            "join": ch_join.id,
            "ticket": ch_ticket.id,
            "all": ch_all.id
        }
        save_data(data)

        await interaction.followup.send("✅ تم إنشاء تصنيف ورومات الـ Log (بما فيها log-ticket) بنجاح في نهاية السيرفر وربطها تلقائياً!", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ حدث خطأ أثناء إنشاء رومات اللوق: {e}", ephemeral=True)

@bot.tree.command(name="auto_line", description="تحديد روم وإرسال صورة أو خط تلقائياً بعد كل رسالة")
@app_commands.checks.has_permissions(administrator=True)
async def auto_line(interaction: discord.Interaction, channel: discord.TextChannel, image_url: str = None, attachment: discord.Attachment = None):
    await interaction.response.defer(ephemeral=True)
    target_url = None
    if attachment:
        target_url = attachment.url
    elif image_url:
        target_url = image_url

    if not target_url:
        await interaction.followup.send("❌ يرجى إرفاق صورة أو وضع رابط صالح للـ Auto Line!", ephemeral=True)
        return

    data = load_data()
    gid = str(interaction.guild_id)
    data.setdefault(gid, {}).setdefault("auto_lines", {})[str(channel.id)] = target_url
    save_data(data)
    await interaction.followup.send(f"✅ تم تفعيل الـ Auto Line بنجاح في الروم {channel.mention} !", ephemeral=True)

@bot.tree.command(name="remove_auto_line", description="إلغاء تفعيل الـ Auto Line من روم معين")
@app_commands.checks.has_permissions(administrator=True)
async def remove_auto_line(interaction: discord.Interaction, channel: discord.TextChannel):
    await interaction.response.defer(ephemeral=True)
    data = load_data()
    gid = str(interaction.guild_id)
    
    if gid in data and "auto_lines" in data[gid] and str(channel.id) in data[gid]["auto_lines"]:
        del data[gid]["auto_lines"][str(channel.id)]
        save_data(data)
        await interaction.followup.send(f"🗑️ تم إلغاء تفعيل الـ Auto Line من الروم {channel.mention} بنجاح !", ephemeral=True)
    else:
        await interaction.followup.send(f"⚠️ لا يوجد Auto Line مفعل أصلاً في الروم {channel.mention} !", ephemeral=True)

@bot.tree.command(name="set_autorole", description="تحديد رتبه تلقائية تعطى للأعضاء الجدد عند دخولهم")
@app_commands.checks.has_permissions(administrator=True)
async def set_autorole(interaction: discord.Interaction, role: discord.Role):
    await interaction.response.defer(ephemeral=True)
    data = load_data()
    gid = str(interaction.guild_id)
    data.setdefault(gid, {})["auto_role_id"] = role.id
    save_data(data)
    await interaction.followup.send(f"✅ تم تحديد رتبة الترحيب التلقائية بنجاح: **{role.name}**", ephemeral=True)

@bot.tree.command(name="remove_autorole", description="إلغاء تفعيل الرتبة التلقائية للأعضاء الجدد")
@app_commands.checks.has_permissions(administrator=True)
async def remove_autorole(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    data = load_data()
    gid = str(interaction.guild_id)
    if gid in data and "auto_role_id" in data[gid]:
        del data[gid]["auto_role_id"]
        save_data(data)
        await interaction.followup.send("🗑️ تم إلغاء تفعيل الرتبة التلقائية بنجاح !", ephemeral=True)
    else:
        await interaction.followup.send("⚠️ لا توجد رتبة تلقائية مفعلة أصلاً !", ephemeral=True)

@bot.event
async def on_member_join(member):
    data = load_data()
    gid = str(member.guild.id)
    g_data = data.get(gid, {})
    
    if "auto_role_id" in g_data:
        role = member.guild.get_role(g_data["auto_role_id"])
        if role:
            try:
                await member.add_roles(role, reason="Auto Role عند الانضمام")
            except Exception:
                pass

    embed = black_embed(
        title="📥 دخول عضو جديد",
        description=f"العضو {member.mention} (`{member.name}`) انضم إلى السيرفر.",
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    await send_log(member.guild, "join", embed)
    await send_log(member.guild, "all", embed)

    if "welcome" in g_data:
        config = g_data["welcome"]
        channel = member.guild.get_channel(config["channel_id"])
        if channel:
            welcome_text = config["message"].replace("{user}", member.mention).replace("{count}", str(member.guild.member_count))
            wel_embed = black_embed(title="👋 عضو جديد انضم إلينا !", description=welcome_text)
            if member.avatar:
                wel_embed.set_thumbnail(url=member.avatar.url)
            wel_embed.set_footer(text=f"ID: {member.id}")
            await channel.send(embed=wel_embed)

@bot.event
async def on_member_remove(member):
    embed = black_embed(
        title="📤 مغادرة عضو",
        description=f"العضو {member.mention} (`{member.name}`) غادر السيرفر.",
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    await send_log(member.guild, "join", embed)
    await send_log(member.guild, "all", embed)

@bot.event
async def on_member_ban(guild, user):
    reason = "بدون سبب تحديد"
    actor = "غير معروف"
    try:
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
            if entry.target.id == user.id:
                reason = entry.reason or "بدون سبب"
                actor = entry.user.mention
                
                data = load_data()
                if data.get(str(guild.id), {}).get("sec_fast_ban", False):
                    now = time.time()
                    b_timestamps = ban_tracker[entry.user.id]
                    b_timestamps.append(now)
                    while b_timestamps and b_timestamps[0] < now - 1.0:
                        b_timestamps.popleft()
                    if len(b_timestamps) >= 3:
                        try:
                            await guild.ban(entry.user, reason="تجاوز حد الباندات السريعة (حماية أوتوماتيكية)")
                        except:
                            pass
                break
    except:
        pass

    embed = black_embed(
        title="🔨 حظر عضو (Ban)",
        description=f"المسؤول: {actor}\nتم حظر: {user.mention} (`{user.name}`)\nالسبب: `{reason}`",
        timestamp=datetime.now(timezone.utc)
    )
    await send_log(guild, "ban", embed)
    await send_log(guild, "all", embed)

@bot.event
async def on_member_unban(guild, user):
    actor = "غير معروف"
    try:
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.unban):
            if entry.target.id == user.id:
                actor = entry.user.mention
                break
    except:
        pass

    embed = black_embed(
        title="🔓 فك حظر عضو (Unban)",
        description=f"المسؤول: {actor}\nتم فك الحظر عن: {user.mention} (`{user.name}`)",
        timestamp=datetime.now(timezone.utc)
    )
    await send_log(guild, "ban", embed)
    await send_log(guild, "all", embed)

@bot.event
async def on_member_update(before, after):
    guild = after.guild
    data = load_data()
    if data.get(str(guild.id), {}).get("sec_admin_protect", False):
        old_has_admin = any(r.permissions.administrator for r in before.roles)
        new_has_admin = any(r.permissions.administrator for r in after.roles)
        
        if not old_has_admin and new_has_admin:
            try:
                async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.member_role_update):
                    if entry.target.id == after.id:
                        actor = entry.user
                        if actor.id != guild.owner_id and actor != guild.me:
                            await guild.ban(actor, reason="محاولة إعطاء صلاحيات أدمن خطيرة بدون اذن")
                            break
            except:
                pass

    if before.timed_out_until != after.timed_out_until:
        if after.timed_out_until:
            actor = "غير معروف"
            reason = "بدون سبب"
            try:
                async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.member_update):
                    if entry.target.id == after.id:
                        actor = entry.user.mention
                        reason = entry.reason or "بدون سبب"
                        break
            except:
                pass

            now_time = datetime.now(timezone.utc)
            duration = after.timed_out_until - now_time
            total_secs = int(duration.total_seconds())
            if total_secs < 0:
                total_secs = 0
            
            hours = total_secs // 3600
            minutes = (total_secs % 3600) // 60
            
            time_str = ""
            if hours > 0:
                time_str += f"{hours} ساعة "
            if minutes > 0 or hours == 0:
                time_str += f"{minutes} دقيقة"

            embed = black_embed(
                title="🔇 إعطاء تايم أوت (Timeout)",
                description=f"المسؤول: {actor}\nالعضو: {after.mention} (`{after.name}`)\nالمدة: **{time_str.strip()}**\nالسبب: `{reason}`",
                timestamp=datetime.now(timezone.utc)
            )
            await send_log(guild, "time", embed)
            await send_log(guild, "all", embed)

@bot.event
async def on_guild_channel_create(channel):
    guild = channel.guild
    actor = "غير معروف"
    try:
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_create):
            if entry.target.id == channel.id:
                actor = entry.user.mention
                break
    except:
        pass

    embed = black_embed(
        title="📁 إنشاء روم جديدة",
        description=f"المسؤول: {actor}\nاسم الروم: **{channel.name}**\nالنوع: `{channel.type}`",
        timestamp=datetime.now(timezone.utc)
    )
    await send_log(guild, "room", embed)
    await send_log(guild, "all", embed)

@bot.event
async def on_guild_channel_delete(channel):
    guild = channel.guild
    actor = "غير معروف"
    try:
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
            if entry.target.id == channel.id:
                actor = entry.user.mention
                break
    except:
        pass

    embed = black_embed(
        title="🗑️ حذف روم",
        description=f"المسؤول: {actor}\nاسم الروم المحذوف: **{channel.name}**",
        timestamp=datetime.now(timezone.utc)
    )
    await send_log(guild, "room", embed)
    await send_log(guild, "all", embed)

@bot.tree.command(name="giveaway", description="إنشاء مسابقة قيف أواي جديدة واختيار فائز تلقائياً")
@app_commands.checks.has_permissions(administrator=True)
async def giveaway_cmd(interaction: discord.Interaction, prize: str, duration_minutes: int):
    await interaction.response.defer()
    
    end_time = int(time.time() + (duration_minutes * 60))
    embed = black_embed(
        title="🎉 مسابقة قيف أواي جديدة 🎉",
        description=f"الجائزة الكبرى : **{prize}**\n\nاضغط على الزر بالأسفل للمشاركة !\n\n⏳ ينتهي بعد : <t:{end_time}:R>"
    )
    view = GiveawayView(prize, end_time)
    msg = await interaction.followup.send(embed=embed, view=view)

    await asyncio.sleep(duration_minutes * 60)

    for item in view.children:
        item.disabled = True

    if view.participants:
        import random
        winner_id = random.choice(list(view.participants))
        winner = interaction.guild.get_member(winner_id)
        winner_mention = winner.mention if winner else f"<@{winner_id}>"
        
        end_embed = black_embed(
            title="🎊 انتهت مسابقة القيف أواي 🎊",
            description=f"الجائزة : **{prize}**\n\n🏆 الفائز الحظيظ هو : {winner_mention}\n\nألف مبروك يا معلم!"
        )
        await msg.edit(embed=end_embed, view=view)
        await interaction.channel.send(f"مبرووك لـ {winner_mention} الفوز بـ **{prize}** ! 🎉")
    else:
        end_embed = black_embed(
            title="❌ انتهت مسابقة القيف أواي",
            description=f"الجائزة : **{prize}**\n\nللأسف لم يشارك أحد في المسابقة!"
        )
        await msg.edit(embed=end_embed, view=view)

@bot.tree.command(name="server", description="عرض معلومات وإحصائيات السيرفر")
async def server(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=False)
    guild = interaction.guild
    created_at = guild.created_at
    now = datetime.now(created_at.tzinfo)
    days_passed = (now - created_at).days
    owner = guild.owner
    owner_mention = owner.mention if owner else "غير معروف"
    
    embed = black_embed(title=f"📊 معلومات سيرفر : {guild.name}")
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="👑 مالك السيرفر", value=owner_mention, inline=True)
    embed.add_field(name="👥 عدد الأعضاء", value=str(guild.member_count), inline=True)
    embed.add_field(name="📅 تم إنشاء السيرفر قبل", value=f"{days_passed} يوم", inline=False)
    embed.set_footer(text=f"Server ID: {guild.id}")
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="set_welcome", description="تحديد روم ونص الترحيب")
@app_commands.checks.has_permissions(administrator=True)
async def set_welcome(interaction: discord.Interaction, channel: discord.TextChannel, message: str):
    await interaction.response.defer(ephemeral=True)
    data = load_data()
    gid = str(interaction.guild_id)
    data.setdefault(gid, {})["welcome"] = {"channel_id": channel.id, "message": message}
    save_data(data)
    await interaction.followup.send(f"✅ تم حفظ الترحيب في {channel.mention} !", ephemeral=True)

@bot.tree.command(name="set_custom_command", description="تحديد كلمة مخصصة لأمر معين")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.choices(action=[
    app_commands.Choice(name="حظر (Ban)", value="ban"),
    app_commands.Choice(name="فك الحظر (Unban)", value="unban"),
    app_commands.Choice(name="طرد (Kick)", value="kick"),
    app_commands.Choice(name="إسكات (Timeout)", value="timeout"),
    app_commands.Choice(name="إلغاء الإسكات (Untimeout)", value="untimeout"),
    app_commands.Choice(name="تغيير النيك نيم (Nickname)", value="nickname"),
    app_commands.Choice(name="رتبة (Role)", value="role"),
    app_commands.Choice(name="مسح الرسائل (Clear)", value="clear"),
    app_commands.Choice(name="قفل الروم (Lock)", value="lock"),
    app_commands.Choice(name="فتح الروم (Unlock)", value="unlock")
])
async def set_custom_command(interaction: discord.Interaction, action: str, word: str):
    await interaction.response.defer(ephemeral=True)
    data = load_data()
    gid = str(interaction.guild_id)
    data.setdefault(gid, {}).setdefault("custom_commands", {})[action] = word.strip().lower()
    save_data(data)
    await interaction.followup.send(f"✅ تم ربط الكلمة **{word}** بنجاح لأمر الـ ({action}) !", ephemeral=True)

@bot.tree.command(name="afk", description="وضع نفسك في حالة عدم انشغال (AFK)")
async def afk_slash(interaction: discord.Interaction, reason: str = "بدون سبب"):
    await interaction.response.defer(ephemeral=False)
    gid = str(interaction.guild_id)
    uid = str(interaction.user.id)
    data = load_data()
    data.setdefault(gid, {}).setdefault("afk_users", {})[uid] = {
        "reason": reason,
        "time": datetime.now(timezone.utc).timestamp(),
        "mentions": []
    }
    save_data(data)
    embed = black_embed(description=f"💤 {interaction.user.mention} **أنت الآن في وضع afk**\nالسبب : `{reason}`")
    await interaction.followup.send(embed=embed)

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    data = load_data()
    gid = str(message.guild.id)
    g_data = data.get(gid, {})
    
    msg_content = message.content.strip()
    msg_lower = msg_content.lower()
    custom_cmds = g_data.get("custom_commands", {})
    content = msg_content.split()

    if content:
        first_word = content[0].lower()
        timeout_word = custom_cmds.get("timeout")
        bot_member = message.guild.me

        if timeout_word and first_word == timeout_word:
            if not message.author.guild_permissions.administrator:
                await message.channel.send("❌ لا تملك صلاحية لفعل هذا!")
                return
            if message.mentions:
                target = message.mentions[0]
                if target.top_role >= bot_member.top_role:
                    await message.channel.send("❌ عذرا لا يمكنني إعطاء تايم أوت بسبب ترتيب الرتب!")
                    return
                
                duration = timedelta(minutes=10)
                reason = "بدون سبب"
                
                if len(content) > 2:
                    parsed = parse_time(content[2])
                    if parsed:
                        duration = parsed
                        reason = " ".join(content[3:]) if len(content) > 3 else "بدون سبب"
                    else:
                        reason = " ".join(content[2:])
                
                try:
                    await target.timeout(duration, reason=reason)
                    hours = int(duration.total_seconds() // 3600)
                    mins = int((duration.total_seconds() % 3600) // 60)
                    time_str = f"{hours} ساعة" if hours > 0 else f"{mins} دقيقة"
                    await message.channel.send(f"🔇 تم إعطاء تايم أوت لـ {target.mention} لمدة {time_str} بنجاح !")
                except Exception as e:
                    await message.channel.send(f"❌ تعذر إعطاء التايم أوت : {e}")
            else:
                await message.channel.send("⚠️ يرجى منشن العضو المراد إعطاؤه تايم أوت!")
            return

    auto_lines = g_data.get("auto_lines", {})
    if str(message.channel.id) in auto_lines:
        try:
            await message.channel.send(auto_lines[str(message.channel.id)])
        except Exception:
            pass

    if g_data.get("sec_spam", False):
        now = time.time()
        uid = message.author.id
        timestamps = spam_tracker[uid]
        timestamps.append(now)
        while timestamps and timestamps[0] < now - 1.0:
            timestamps.popleft()
        
        if len(timestamps) >= 5:
            try:
                if "@here" in message.content or "@everyone" in message.content:
                    await message.guild.ban(message.author, reason="سبام مع منشن عام")
                    await message.channel.send(f"🚨 تم حظر {message.author.mention} تلقائياً بسبب تكرار الرسائل مع منشن عام !")
                else:
                    dur = timedelta(hours=2)
                    await message.author.timeout(dur, reason="تجاوز حد الرسائل المسموح به (سبام)")
                    await message.channel.send(f"🔇 تم إعطاء تايم أوت ساعتين لـ {message.author.mention} بسبب السبام السريع .")
                timestamps.clear()
                return
            except Exception:
                pass

    if g_data.get("sec_links", False):
        content_lower = message.content.lower()
        if "http://" in content_lower or "https://" in content_lower or "www." in content_lower:
            if not any(safe in content_lower for safe in ["discord.gg", "discord.com/gifts", "discord.gift", "tenor.com", "giphy.com"]):
                try:
                    await message.delete()
                    await message.channel.send(f"⚠️ {message.author.mention} ممنوع نشر الروابط الخارجية هنا !", delete_after=5)
                    return
                except:
                    pass

    auto_replies = g_data.get("auto_replies", {})
    for trig, resp in auto_replies.items():
        if trig in msg_lower:
            await message.reply(resp, mention_author=True)
            break

# --- تشغيل البوت باستخدام المتغير البيئي Token ---
if __name__ == "__main__":
    Token = os.environ.get("Token")
    if not Token:
        print("❌ خطأ: لم يتم العثور على متغير البيئي Token!")
    else:
        bot.run(Token)
