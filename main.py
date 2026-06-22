import asyncio
import datetime
import logging
import os
import time
from collections import deque

import discord
from discord import app_commands
from discord.ext import commands

TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("DISCORD_BOT_TOKEN secret is not set.")

# ── Logging setup ──────────────────────────────────────────────────────────────
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

class _Colours:
    RESET   = "\033[0m"
    GREY    = "\033[90m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    RED     = "\033[91m"
    CYAN    = "\033[96m"
    MAGENTA = "\033[95m"
    BOLD    = "\033[1m"

_LEVEL_COLOURS = {
    "DEBUG":    _Colours.GREY,
    "INFO":     _Colours.CYAN,
    "WARNING":  _Colours.YELLOW,
    "ERROR":    _Colours.RED,
    "CRITICAL": _Colours.MAGENTA,
}

class _ColouredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        colour = _LEVEL_COLOURS.get(record.levelname, _Colours.RESET)
        record.levelname = f"{colour}{_Colours.BOLD}[{record.levelname}]{_Colours.RESET}"
        base = super().format(record)
        ts, rest = base.split(" ", 1)
        return f"{_Colours.GREY}{ts}{_Colours.RESET} {rest}"

_console_handler = logging.StreamHandler()
_console_handler.setFormatter(_ColouredFormatter(
    fmt="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
))

_file_handler = logging.FileHandler(os.path.join(LOG_DIR, "guard.log"), encoding="utf-8")
_file_handler.setFormatter(logging.Formatter(
    fmt="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
))

logging.root.setLevel(logging.INFO)
logging.root.handlers = [_console_handler, _file_handler]
logger = logging.getLogger("MasterGuard")

# In-memory action log (last 100 entries)
MAX_LOG_ENTRIES = 100
action_log: deque[dict] = deque(maxlen=MAX_LOG_ENTRIES)

def _embed_colour(result: str) -> discord.Colour:
    if result.startswith("✅"):
        return discord.Colour.green()
    if result.startswith("❌"):
        return discord.Colour.red()
    if result.startswith("⚠️"):
        return discord.Colour.yellow()
    return discord.Colour.blurple()

_ACTION_ICONS: dict[str, str] = {
    "BAN":             "🔨",
    "KICK":            "👢",
    "KICK_BOT":        "🤖",
    "TIMEOUT":         "🔇",
    "DELETE_MSG":      "🗑️",
    "DELETE_CHANNEL":  "🚫",
    "RESTORE_CHANNEL": "♻️",
    "RENAME_CHANNEL":  "✏️",
    "DELETE_ROLE":     "🚫",
    "RESTORE_ROLE":    "♻️",
    "DELETE_WEBHOOK":  "🕸️",
    "RESTORE_GUILD":   "🏠",
    "WHITELIST":       "📋",
    "ADD_RESPONSE":    "💬",
    "TOGGLE":          "⚙️",
}


async def _send_log_embed(channel_id: int, entry: dict):
    channel = bot.get_channel(channel_id)
    if not isinstance(channel, discord.TextChannel):
        return
    icon = _ACTION_ICONS.get(entry["action"], "📌")
    embed = discord.Embed(
        title=f"{icon} {entry['action']}",
        colour=_embed_colour(entry["result"]),
        timestamp=entry["time"],
    )
    embed.add_field(name="الهدف",    value=entry["target"] or "—", inline=True)
    embed.add_field(name="النتيجة", value=entry["result"],         inline=True)
    embed.add_field(name="السيرفر", value=entry["guild"],          inline=True)
    if entry["extra"]:
        embed.add_field(name="تفاصيل", value=entry["extra"], inline=False)
    embed.set_footer(text="MasterGuard")
    try:
        await channel.send(embed=embed)
    except (discord.Forbidden, discord.HTTPException):
        pass


def log_action(action: str, target: str, guild_name: str, result: str,
               extra: str = "", guild_id: int | None = None):
    now = datetime.datetime.now(datetime.timezone.utc)
    entry = {"time": now, "action": action, "target": target,
             "guild": guild_name, "result": result, "extra": extra}
    action_log.appendleft(entry)
    logger.info("[%s] %s | target=%s | result=%s%s",
                guild_name, action, target, result,
                f" | {extra}" if extra else "")
    if guild_id is not None:
        channel_id = bot.log_channels.get(guild_id)
        if channel_id:
            asyncio.get_event_loop().create_task(_send_log_embed(channel_id, entry))


LOG_CHANNEL_NAME = "security-log"

# Channel IDs created by the bot — on_guild_channel_create must ignore these
_bot_created_channel_ids: set[int] = set()
# Channel IDs currently being processed for deletion (prevents double-handling)
_processing_deletions: set[int] = set()
# Channel names mid-restore (name-based fallback guard)
_restoring_channels: set[str] = set()
# Channel IDs whose rename the bot is currently reverting
_reverting_renames: set[int] = set()


async def _ensure_log_channel(guild: discord.Guild) -> discord.TextChannel | None:
    if guild.id in bot.log_channels:
        ch = guild.get_channel(bot.log_channels[guild.id])
        if ch:
            return ch

    existing = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)
    if existing:
        bot.log_channels[guild.id] = existing.id
        logger.info("Found existing %s in '%s'", LOG_CHANNEL_NAME, guild.name)
        return existing

    try:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, embed_links=True),
        }
        for role in guild.roles:
            if role.permissions.administrator:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True)

        ch = await guild.create_text_channel(
            name=LOG_CHANNEL_NAME,
            overwrites=overwrites,
            topic="سجل إجراءات MasterGuard — Security log",
            reason="MasterGuard: auto-created security log channel",
        )
        _bot_created_channel_ids.add(ch.id)
        bot.log_channels[guild.id] = ch.id
        logger.info("Created %s in '%s' (ID: %s)", LOG_CHANNEL_NAME, guild.name, ch.id)
        return ch
    except discord.Forbidden:
        logger.warning("No permission to create %s in '%s'", LOG_CHANNEL_NAME, guild.name)
        return None
    except discord.HTTPException as e:
        if e.code == 30013:
            logger.warning("Max channels reached in '%s'.", guild.name)
        else:
            logger.warning("Failed to create %s in '%s': %s", LOG_CHANNEL_NAME, guild.name, e)
        return None


# ── Bot class ──────────────────────────────────────────────────────────────────
class MasterGuardBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
        self.whitelist: set[int] = set()
        self.auto_responses: dict[str, str] = {}
        self.msg_cache: dict[int, list[float]] = {}
        self.log_channels: dict[int, int] = {}
        self.settings = {
            "spam": True,
            "channels": True,
            "roles": True,
            "webhooks": True,
            "guild_update": True,
        }

    async def setup_hook(self):
        await self.tree.sync()
        logger.info("نظام الحماية يعمل الآن بكامل طاقته.")

    async def on_ready(self):
        logger.info("Logged in as %s (ID: %s)", self.user, self.user.id)
        for guild in self.guilds:
            await _ensure_log_channel(guild)
            await asyncio.sleep(1)

    async def on_guild_join(self, guild: discord.Guild):
        logger.info("Joined guild: %s (ID: %s)", guild.name, guild.id)
        await _ensure_log_channel(guild)


bot = MasterGuardBot()


# ── Helpers ────────────────────────────────────────────────────────────────────
def _can_moderate(guild: discord.Guild, member: discord.Member) -> bool:
    return guild.me.top_role > member.top_role

def _guild_name(guild: discord.Guild | None) -> str:
    return guild.name if guild else "DM"


async def _try_ban(guild: discord.Guild, user: discord.abc.Snowflake,
                   reason: str, guild_name: str):
    name = str(getattr(user, "name", user.id))
    try:
        await guild.ban(user, reason=reason, delete_message_days=0)
        log_action("BAN", name, guild_name, "✅ تم الباند", reason, guild_id=guild.id)
    except discord.Forbidden:
        log_action("BAN", name, guild_name, "❌ فشل (صلاحيات)", reason, guild_id=guild.id)
    except Exception as e:
        log_action("BAN", name, guild_name, f"❌ خطأ: {e}", reason, guild_id=guild.id)


async def _try_kick(member: discord.Member, reason: str, guild_name: str):
    try:
        await member.kick(reason=reason)
        log_action("KICK", str(member), guild_name, "✅ تم الكيك", reason, guild_id=member.guild.id)
    except discord.Forbidden:
        log_action("KICK", str(member), guild_name, "❌ فشل (صلاحيات)", reason, guild_id=member.guild.id)
    except Exception as e:
        log_action("KICK", str(member), guild_name, f"❌ خطأ: {e}", reason, guild_id=member.guild.id)


def _is_recent(entry: discord.AuditLogEntry, seconds: int = 5) -> bool:
    """Return True only if the audit log entry happened within the last N seconds."""
    age = (datetime.datetime.now(datetime.timezone.utc) - entry.created_at).total_seconds()
    return age <= seconds


def _ban_task(guild: discord.Guild, user, reason: str, guild_name: str, member=None):
    """Fire-and-forget ban — does NOT block the caller."""
    async def _do():
        if member is not None:
            if _can_moderate(guild, member):
                await _try_ban(guild, user, reason, guild_name)
            else:
                log_action("BAN", str(user), guild_name, "⚠️ تخطى (رتبة أعلى)", reason, guild_id=guild.id)
        else:
            await _try_ban(guild, user, reason, guild_name)
    asyncio.get_event_loop().create_task(_do())


# ── 1. Spam protection & auto-responses ───────────────────────────────────────
@bot.event
async def on_message(message: discord.Message):
    if message.author.id == bot.user.id:
        return

    guild_name = _guild_name(message.guild)
    gid = message.guild.id if message.guild else None

    if message.author.bot and bot.settings["spam"]:
        if message.author.id in bot.whitelist:
            return
        try:
            await message.delete()
            log_action("DELETE_MSG", str(message.author), guild_name, "✅ حُذفت",
                       f"بوت سبام في #{getattr(message.channel, 'name', '?')}", guild_id=gid)
        except (discord.Forbidden, discord.NotFound):
            log_action("DELETE_MSG", str(message.author), guild_name, "❌ فشل الحذف", "بوت سبام", guild_id=gid)

        member = message.guild.get_member(message.author.id) if message.guild else None
        if member and message.guild:
            if _can_moderate(message.guild, member):
                await _try_ban(message.guild, member, "بوت سبام — رسائل غير مصرح بها", guild_name)
            else:
                await _try_kick(member, "بوت سبام", guild_name)
        return

    if message.author.id in bot.whitelist:
        await bot.process_commands(message)
        return

    if bot.settings["spam"]:
        user_id = message.author.id
        curr = time.time()
        if user_id not in bot.msg_cache:
            bot.msg_cache[user_id] = []
        bot.msg_cache[user_id] = [t for t in bot.msg_cache[user_id] if curr - t < 3]
        bot.msg_cache[user_id].append(curr)
        if len(bot.msg_cache[user_id]) > 5:
            try:
                await message.author.timeout(discord.timedelta(minutes=10), reason="سبام")
                await message.channel.send(f"{message.author.mention} تم كتمك بسبب السبام!")
                log_action("TIMEOUT", str(message.author), guild_name, "✅ كتم 10 دقائق", "سبام", guild_id=gid)
            except discord.Forbidden:
                log_action("TIMEOUT", str(message.author), guild_name, "❌ فشل الكتم", "سبام", guild_id=gid)

    if message.content in bot.auto_responses:
        await message.channel.send(bot.auto_responses[message.content])

    await bot.process_commands(message)


# ── 2. Channel protection ──────────────────────────────────────────────────────
@bot.event
async def on_guild_channel_delete(channel: discord.abc.GuildChannel):
    if not bot.settings["channels"]:
        return

    logger.info("DELETE EVENT: #%s (id=%s)", channel.name, channel.id)

    if channel.id in _processing_deletions:
        logger.info("SKIP DUPLICATE DELETE: #%s", channel.name)
        return
    _processing_deletions.add(channel.id)

    guild_name = _guild_name(channel.guild)
    gid = channel.guild.id

    try:
        async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
            if not entry.user or not _is_recent(entry):
                return
            if entry.user.id == bot.user.id or entry.user.id in bot.whitelist:
                return

            _restoring_channels.add(channel.name)
            new = None
            try:
                new = await channel.clone()
                _bot_created_channel_ids.add(new.id)
                await new.edit(position=channel.position)
                if channel.name == LOG_CHANNEL_NAME:
                    bot.log_channels[gid] = new.id
                log_action("RESTORE_CHANNEL", channel.name, guild_name, "✅ استُعيد",
                           f"حذفه {entry.user}", guild_id=gid)

                member = channel.guild.get_member(entry.user.id)
                if member:
                    _ban_task(channel.guild, entry.user, "حذف روم", guild_name, member=member)
                else:
                    _ban_task(channel.guild, discord.Object(id=entry.user.id), "حذف روم (غادر)", guild_name)

                await asyncio.sleep(1)
                cat = getattr(new, "category", None)
                for dup in list(channel.guild.channels):
                    if (
                        dup.id != new.id
                        and dup.name == channel.name
                        and type(dup) is type(new)
                        and getattr(dup, "category", None) == cat
                    ):
                        try:
                            await dup.delete(reason="MasterGuard: duplicate restored channel")
                            log_action("DELETE_CHANNEL", dup.name, guild_name, "✅ حُذف (تكرار)",
                                       f"نسخة مكررة بعد استعادة {channel.name}", guild_id=gid)
                        except (discord.Forbidden, discord.NotFound):
                            pass

            except discord.Forbidden:
                log_action("RESTORE_CHANNEL", channel.name, guild_name, "❌ فشل الاسترجاع",
                           f"حذفه {entry.user}", guild_id=gid)
            finally:
                await asyncio.sleep(1)
                _restoring_channels.discard(channel.name)
    finally:
        _processing_deletions.discard(channel.id)


@bot.event
async def on_guild_channel_create(channel: discord.abc.GuildChannel):
    if not bot.settings["channels"]:
        return

    logger.info("CREATE EVENT: #%s (id=%s)", channel.name, channel.id)

    if channel.id in _bot_created_channel_ids:
        logger.info("SKIP BY ID (bot-created): #%s", channel.name)
        _bot_created_channel_ids.discard(channel.id)
        return

    if channel.name in _restoring_channels or channel.name == LOG_CHANNEL_NAME:
        logger.info("SKIP BY NAME: #%s", channel.name)
        return

    guild_name = _guild_name(channel.guild)
    gid = channel.guild.id
    async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_create):
        if not entry.user or not _is_recent(entry):
            return
        if entry.user.id == bot.user.id or entry.user.id in bot.whitelist:
            return
        try:
            await channel.delete()
            log_action("DELETE_CHANNEL", channel.name, guild_name, "✅ حُذف",
                       f"أنشأه {entry.user}", guild_id=gid)
        except discord.Forbidden:
            log_action("DELETE_CHANNEL", channel.name, guild_name, "❌ فشل الحذف",
                       f"أنشأه {entry.user}", guild_id=gid)

        member = channel.guild.get_member(entry.user.id)
        if member:
            _ban_task(channel.guild, entry.user, "إنشاء روم غير مصرح به", guild_name, member=member)
        else:
            _ban_task(channel.guild, discord.Object(id=entry.user.id), "إنشاء روم غير مصرح به", guild_name)


@bot.event
async def on_guild_channel_update(before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
    if not bot.settings["channels"]:
        return
    if before.name == after.name:
        return

    if after.id in _reverting_renames:
        return

    guild_name = _guild_name(after.guild)
    gid = after.guild.id

    async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_update):
        if not entry.user or not _is_recent(entry):
            return
        if entry.user.id == bot.user.id or entry.user.id in bot.whitelist:
            return

        _reverting_renames.add(after.id)
        try:
            await after.edit(name=before.name, reason="MasterGuard: reverting unauthorized rename")
            log_action("RENAME_CHANNEL", f"{before.name} ← {after.name}", guild_name,
                       "✅ أُعيد الاسم", f"غيّره {entry.user}", guild_id=gid)
        except discord.Forbidden:
            log_action("RENAME_CHANNEL", f"{before.name} ← {after.name}", guild_name,
                       "❌ فشل إعادة الاسم", f"غيّره {entry.user}", guild_id=gid)
        finally:
            await asyncio.sleep(2)
            _reverting_renames.discard(after.id)

        member = after.guild.get_member(entry.user.id)
        if member:
            _ban_task(after.guild, entry.user, "تغيير اسم روم", guild_name, member=member)
        else:
            _ban_task(after.guild, discord.Object(id=entry.user.id), "تغيير اسم روم (غادر)", guild_name)


# ── 3. Role protection ─────────────────────────────────────────────────────────
@bot.event
async def on_guild_role_delete(role: discord.Role):
    if not bot.settings["roles"]:
        return
    guild_name = _guild_name(role.guild)
    gid = role.guild.id
    async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
        if not entry.user or not _is_recent(entry):
            return
        if entry.user.id == bot.user.id or entry.user.id in bot.whitelist:
            return
        try:
            new_role = await role.guild.create_role(
                name=role.name,
                permissions=role.permissions,
                color=role.color,
                hoist=role.hoist,
                mentionable=role.mentionable,
                reason="MasterGuard: restoring deleted role",
            )
            try:
                await new_role.edit(position=role.position)
            except (discord.Forbidden, discord.HTTPException):
                pass
            log_action("RESTORE_ROLE", role.name, guild_name, "✅ استُعيدت (نفس المكان والصلاحيات)",
                       f"حذفها {entry.user}", guild_id=gid)
        except discord.Forbidden:
            log_action("RESTORE_ROLE", role.name, guild_name, "❌ فشل الاسترجاع",
                       f"حذفها {entry.user}", guild_id=gid)

        member = role.guild.get_member(entry.user.id)
        if member:
            _ban_task(role.guild, entry.user, "حذف رتبة", guild_name, member=member)
        else:
            _ban_task(role.guild, discord.Object(id=entry.user.id), "حذف رتبة (غادر)", guild_name)


@bot.event
async def on_guild_role_create(role: discord.Role):
    if not bot.settings["roles"]:
        return
    guild_name = _guild_name(role.guild)
    gid = role.guild.id
    async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_create):
        if not entry.user or not _is_recent(entry):
            return
        if entry.user.id == bot.user.id or entry.user.id in bot.whitelist:
            return
        try:
            await role.delete()
            log_action("DELETE_ROLE", role.name, guild_name, "✅ حُذفت",
                       f"أنشأها {entry.user}", guild_id=gid)
        except discord.Forbidden:
            log_action("DELETE_ROLE", role.name, guild_name, "❌ فشل الحذف",
                       f"أنشأها {entry.user}", guild_id=gid)

        member = role.guild.get_member(entry.user.id)
        if member:
            _ban_task(role.guild, entry.user, "إنشاء رتبة غير مصرح بها", guild_name, member=member)
        else:
            _ban_task(role.guild, discord.Object(id=entry.user.id), "إنشاء رتبة غير مصرح بها", guild_name)


# ── 4. Webhook & server protection ────────────────────────────────────────────
@bot.event
async def on_webhooks_update(channel: discord.abc.GuildChannel):
    if not bot.settings["webhooks"]:
        return
    guild_name = _guild_name(channel.guild)
    gid = channel.guild.id if channel.guild else None

    if channel.guild:
        async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.webhook_create):
            if not entry.user or not _is_recent(entry):
                return
            if entry.user.id == bot.user.id or entry.user.id in bot.whitelist:
                return

    try:
        webhooks = await channel.webhooks()
        for wb in webhooks:
            await wb.delete()
            log_action("DELETE_WEBHOOK", wb.name, guild_name, "✅ حُذف",
                       f"في #{getattr(channel, 'name', '?')}", guild_id=gid)
    except discord.Forbidden:
        log_action("DELETE_WEBHOOK", "?", guild_name, "❌ فشل (صلاحيات)",
                   f"في #{getattr(channel, 'name', '?')}", guild_id=gid)


@bot.event
async def on_guild_update(before: discord.Guild, after: discord.Guild):
    if not bot.settings["guild_update"]:
        return
    if before.name == after.name and before.icon == after.icon:
        return

    async for entry in after.audit_logs(limit=1, action=discord.AuditLogAction.guild_update):
        if not entry.user or not _is_recent(entry):
            return
        if entry.user.id == bot.user.id or entry.user.id in bot.whitelist:
            return

        guild_name = after.name
        gid = after.id
        try:
            icon_bytes = await before.icon.read() if before.icon else None
            await after.edit(name=before.name, icon=icon_bytes)
            log_action("RESTORE_GUILD", before.name, guild_name, "✅ استُعيدت البيانات",
                       f"غيّرها {entry.user}", guild_id=gid)
        except discord.Forbidden:
            log_action("RESTORE_GUILD", before.name, guild_name, "❌ فشل الاسترجاع",
                       f"غيّرها {entry.user}", guild_id=gid)

        _ban_task(after, entry.user, "تغيير اسم/صورة السيرفر", guild_name,
                  member=after.get_member(entry.user.id))


# ── 5. Unauthorized bot protection ────────────────────────────────────────────
@bot.event
async def on_member_join(member: discord.Member):
    if not member.bot:
        return
    guild_name = _guild_name(member.guild)
    gid = member.guild.id
    async for entry in member.guild.audit_logs(limit=1, action=discord.AuditLogAction.bot_add):
        if not entry.user or not _is_recent(entry):
            return
        if entry.target and entry.target.id == member.id and entry.user.id not in bot.whitelist:
            try:
                await member.kick()
                log_action("KICK_BOT", str(member), guild_name, "✅ طُرد البوت",
                           f"أضافه {entry.user}", guild_id=gid)
            except discord.Forbidden:
                log_action("KICK_BOT", str(member), guild_name, "❌ فشل الطرد",
                           f"أضافه {entry.user}", guild_id=gid)
            _ban_task(member.guild, entry.user, "إضافة بوت غير موثوق", guild_name,
                      member=member.guild.get_member(entry.user.id))


# ── 6. Slash commands ──────────────────────────────────────────────────────────
@bot.tree.command(name="setlog", description="تحديد روم اللوق")
async def cmd_setlog(interaction: discord.Interaction, channel: discord.TextChannel):
    if not interaction.guild:
        await interaction.response.send_message("هذا الأمر يعمل داخل السيرفر فقط.", ephemeral=True)
        return
    bot.log_channels[interaction.guild.id] = channel.id
    log_action("SETLOG", channel.name, interaction.guild.name, "✅ تم تعيين روم اللوق",
               f"بواسطة {interaction.user}", guild_id=interaction.guild.id)
    await interaction.response.send_message(
        f"✅ سيتم إرسال جميع إجراءات البوت إلى {channel.mention}", ephemeral=True
    )


@bot.tree.command(name="whitelist", description="إضافة/حذف من القائمة البيضاء")
async def whitelist_cmd(interaction: discord.Interaction, user: discord.Member, action: bool):
    if action:
        bot.whitelist.add(user.id)
    else:
        bot.whitelist.discard(user.id)
    status = "أُضيف إلى" if action else "حُذف من"
    gid = interaction.guild.id if interaction.guild else None
    log_action("WHITELIST", str(user),
               interaction.guild.name if interaction.guild else "DM",
               f"{'➕' if action else '➖'} {status} القائمة البيضاء",
               f"بواسطة {interaction.user}", guild_id=gid)
    await interaction.response.send_message(f"تم: {user.name} {status} القائمة البيضاء.", ephemeral=True)


@bot.tree.command(name="add_response", description="إضافة رد تلقائي")
async def add_response(interaction: discord.Interaction):
    class ResponseModal(discord.ui.Modal, title="إضافة رد تلقائي"):
        word = discord.ui.TextInput(label="الكلمة أو الجملة")
        resp = discord.ui.TextInput(label="الرد", style=discord.TextStyle.paragraph)

        async def on_submit(self, i: discord.Interaction):
            bot.auto_responses[str(self.word)] = str(self.resp)
            gid = i.guild.id if i.guild else None
            log_action("ADD_RESPONSE", str(self.word),
                       i.guild.name if i.guild else "DM",
                       "✅ تم الحفظ", f"بواسطة {i.user}", guild_id=gid)
            await i.response.send_message(f"تم حفظ الرد على: {self.word}", ephemeral=True)

    await interaction.response.send_modal(ResponseModal())


@bot.tree.command(name="check_protection", description="فحص حالة جميع الحمايات")
async def check_protection(interaction: discord.Interaction):
    s = bot.settings
    gid = interaction.guild.id if interaction.guild else None
    log_ch = f"<#{bot.log_channels[gid]}>" if gid and gid in bot.log_channels else "غير محدد"
    lines = [
        "**حالة الحماية الحالية:**",
        f"- الرومات: {'✅ مفعلة' if s['channels'] else '❌ معطلة'}",
        f"- تغيير اسم الروم: {'✅ مفعلة' if s['channels'] else '❌ معطلة'}",
        f"- الرتب: {'✅ مفعلة' if s['roles'] else '❌ معطلة'}",
        f"- الويب هوك: {'✅ مفعلة' if s['webhooks'] else '❌ معطلة'}",
        f"- بيانات السيرفر: {'✅ مفعلة' if s['guild_update'] else '❌ معطلة'}",
        f"- السبام: {'✅ مفعلة' if s['spam'] else '❌ معطلة'}",
        f"- القائمة البيضاء: {len(bot.whitelist)} مستخدم",
        f"- روم اللوق: {log_ch}",
        f"- إجمالي الإجراءات المسجلة: {len(action_log)}",
    ]
    await interaction.response.send_message("\n".join(lines), ephemeral=True)


@bot.tree.command(name="spam", description="تفعيل أو تعطيل حماية السبام")
async def cmd_spam(interaction: discord.Interaction, state: bool):
    bot.settings["spam"] = state
    txt = "✅ مفعلة" if state else "❌ معطلة"
    gid = interaction.guild.id if interaction.guild else None
    log_action("TOGGLE", "السبام", interaction.guild.name if interaction.guild else "DM",
               txt, f"بواسطة {interaction.user}", guild_id=gid)
    await interaction.response.send_message(f"حماية **السبام** الآن: {txt}", ephemeral=True)


@bot.tree.command(name="channels", description="تفعيل أو تعطيل حماية الرومات")
async def cmd_channels(interaction: discord.Interaction, state: bool):
    bot.settings["channels"] = state
    txt = "✅ مفعلة" if state else "❌ معطلة"
    gid = interaction.guild.id if interaction.guild else None
    log_action("TOGGLE", "الرومات", interaction.guild.name if interaction.guild else "DM",
               txt, f"بواسطة {interaction.user}", guild_id=gid)
    await interaction.response.send_message(f"حماية **الرومات** الآن: {txt}", ephemeral=True)


@bot.tree.command(name="roles", description="تفعيل أو تعطيل حماية الرتب")
async def cmd_roles(interaction: discord.Interaction, state: bool):
    bot.settings["roles"] = state
    txt = "✅ مفعلة" if state else "❌ معطلة"
    gid = interaction.guild.id if interaction.guild else None
    log_action("TOGGLE", "الرتب", interaction.guild.name if interaction.guild else "DM",
               txt, f"بواسطة {interaction.user}", guild_id=gid)
    await interaction.response.send_message(f"حماية **الرتب** الآن: {txt}", ephemeral=True)


@bot.tree.command(name="webhooks", description="تفعيل أو تعطيل حماية الويب هوك")
async def cmd_webhooks(interaction: discord.Interaction, state: bool):
    bot.settings["webhooks"] = state
    txt = "✅ مفعلة" if state else "❌ معطلة"
    gid = interaction.guild.id if interaction.guild else None
    log_action("TOGGLE", "الويب هوك", interaction.guild.name if interaction.guild else "DM",
               txt, f"بواسطة {interaction.user}", guild_id=gid)
    await interaction.response.send_message(f"حماية **الويب هوك** الآن: {txt}", ephemeral=True)


@bot.tree.command(name="server", description="تفعيل أو تعطيل حماية بيانات السيرفر")
async def cmd_server(interaction: discord.Interaction, state: bool):
    bot.settings["guild_update"] = state
    txt = "✅ مفعلة" if state else "❌ معطلة"
    gid = interaction.guild.id if interaction.guild else None
    log_action("TOGGLE", "بيانات السيرفر", interaction.guild.name if interaction.guild else "DM",
               txt, f"بواسطة {interaction.user}", guild_id=gid)
    await interaction.response.send_message(f"حماية **بيانات السيرفر** الآن: {txt}", ephemeral=True)


@bot.tree.command(name="logs", description="عرض آخر 10 إجراءات")
async def cmd_logs(interaction: discord.Interaction):
    if not action_log:
        await interaction.response.send_message("لا توجد إجراءات مسجلة بعد.", ephemeral=True)
        return
    lines = []
    for e in list(action_log)[:10]:
        ts = e["time"].strftime("%H:%M:%S")
        lines.append(f"`{ts}` **{e['action']}** — {e['target']} → {e['result']}")
    await interaction.response.send_message("\n".join(lines), ephemeral=True)


@bot.tree.command(name="server_info", description="معلومات السيرفر الحالي")
async def cmd_server_info(interaction: discord.Interaction):
    g = interaction.guild
    if not g:
        await interaction.response.send_message("هذا الأمر يعمل داخل السيرفر فقط.", ephemeral=True)
        return
    embed = discord.Embed(title=g.name, colour=discord.Colour.blurple())
    embed.add_field(name="الأعضاء",  value=str(g.member_count), inline=True)
    embed.add_field(name="الرومات",  value=str(len(g.channels)),  inline=True)
    embed.add_field(name="الرتب",    value=str(len(g.roles)),     inline=True)
    embed.add_field(name="المالك",   value=str(g.owner),          inline=True)
    embed.add_field(name="تاريخ الإنشاء", value=g.created_at.strftime("%Y-%m-%d"), inline=True)
    if g.icon:
        embed.set_thumbnail(url=g.icon.url)
    await interaction.response.send_message(embed=embed, ephemeral=True)


bot.run(TOKEN)
