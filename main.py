import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))

import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import json
import unicodedata
import re
import asyncio
import logging
import threading
import platform
import socket
import getpass
import io
import psutil
import GPUtil
import traceback
from mcstatus import BedrockServer
from prompt_toolkit import prompt
from prompt_toolkit.patch_stdout import patch_stdout
import tkinter as tk
from tkinter import filedialog
import shutil
import colorama
import hashlib
import time

try:
    # ===== SETUP =====
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, "buffer"):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    colorama.init()


    # ===== FILE HANDLING =====
    DUMP_DIR = "fdump"
    FILE_DB = "fdump/files.json"
    os.makedirs(DUMP_DIR, exist_ok=True)
    
    def browse_file():
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)  # bring window to front
        return filedialog.askopenfilename(title="Select a file")

    def load_filedb():
        return load_json(FILE_DB, default={})

    def save_filedb(data):
        save_json(FILE_DB, data)

    def add_file(mode, file_reference):
        db = load_filedb()

        if mode == "ui":
            file_path = browse_file()
            if not file_path:
                print("No file selected.")
                return
        elif mode == "dir":
            file_path = input("Enter file path: ").strip()
        else:
            print("Usage: addfile <ui|dir> <file_reference>")
            return

        if not os.path.isfile(file_path):
            print("File not found.")
            return

        # Keep original filename
        original_name = os.path.basename(file_path)
        dest_path = os.path.join(DUMP_DIR, original_name)

        shutil.copy2(file_path, dest_path)

        # Save reference in JSON, but do NOT rename file
        db[file_reference] = {
            "original_path": os.path.abspath(file_path),
            "dump_path": os.path.abspath(dest_path),
            "filename": original_name
        }
        save_filedb(db)

        print(f"File '{file_reference}' added. Original filename preserved: {original_name}")

    def get_file(file_reference):
        db = load_filedb()
        if file_reference not in db:
            print(f"reference '{file_reference}' not found.")
            return None
        info = db[file_reference]
        return info["dump_path"], info["filename"]

    def del_file(file_reference):
        db = load_filedb()
        if file_reference not in db:
            print(f"No such reference name '{file_reference}'.")
            return

        dump_path = db[file_reference].get("dump_path")
        if dump_path and os.path.exists(dump_path):
            try:
                os.remove(dump_path)
            except Exception as e:
                logging.warning(f"Failed to remove file {dump_path}: {e}")

        del db[file_reference]
        save_filedb(db)
        print(f"Deleted reference '{file_reference}'")
    
    # ===== LOGGING SETUP =====
    class ConsoleFriendlyHandler(logging.StreamHandler):
        lock = threading.Lock()
        def emit(self, record):
            try:
                with self.lock:
                    msg = self.format(record)
                    sys.stdout.write("\r\033[K" + msg + "\n")
                    sys.stdout.flush()
            except Exception:
                self.handleError(record)

    log_dir = f"log/{datetime.now().strftime('%Y-%m-%d')}"
    os.makedirs(log_dir, exist_ok=True)

    # Log file path
    log_file = f"{log_dir}/log_{datetime.now().strftime('%H-%M-%S')}.txt"

    # Create handlers manually
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    console_handler = ConsoleFriendlyHandler()

    # Formatter (you can adjust the format)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Configure root logger
    logging.basicConfig(level=logging.INFO, handlers=[file_handler, console_handler])

    log = logging.getLogger(__name__)

    # ===== JSON HANDLING =====
    CONFIG_FILE = "config.json"
    
    def get_latest_userinfo_file():
        folder = "userdata"
        os.makedirs(folder, exist_ok=True)

        files = [f for f in os.listdir(folder) if f.endswith(".json")]
        if not files:
            # No file found — create a default one
            return os.path.join(folder, "uinfo_latest.json")

        # Sort chronologically (filenames start with date)
        files.sort()
        return os.path.join(folder, files[-1])  # most recent

    USER_INFO_FILE = get_latest_userinfo_file()

    def load_json(file_path, default=None):
        if not os.path.exists(file_path):
            logging.warning(f"{file_path} not found, creating new file...")
            if default is not None:
                save_json(file_path, default)
                return default
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logging.error(f"Failed to read {file_path}: invalid JSON format.")
            return None

    def save_json(file_path, data):
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Failed to write to {file_path}: {e}")

    def load_userinfo():
        return load_json(USER_INFO_FILE, default={"discord_users": {}, "last_saved": None})

    def save_userinfo(data, session_id):
        # Ensure userdata folder exists
        os.makedirs("userdata", exist_ok=True)

        # Format: YYYY-MM-DD_HH-MM-SS-sessionID
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_path = f"userdata/{timestamp}-{session_id}.json"

        # Save JSON data
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            logging.info(f"User info saved to {file_path}")
        except Exception as e:
            logging.error(f"Failed to write to {file_path}: {e}")

    config_data = load_json(CONFIG_FILE)
    if not config_data:
        exit(1)

    user_info = load_json(USER_INFO_FILE, default={"discord_users": {}, "last_saved": None})
    if not user_info or "discord_users" not in user_info:
        user_info = {"discord_users": {}, "last_saved": None}

    token = open("token.config", "r").read().strip()
    target_channel_id = int(config_data["config"]["default_target_channel_id"]) or None

    # ===== INTERNAL USERINFO FUNCTIONS =====
    def get_userinfo(uid: int):
        return user_info.get("discord_users", {}).get(str(uid))

    def set_userinfo(uid: int, dispname: str, var1=None, var2=None, roles=None):
        if "discord_users" not in user_info:
            user_info["discord_users"] = {}

        if str(uid) not in user_info["discord_users"]:
            user_info["discord_users"][str(uid)] = {
                "id": str(uid),
                "dispname": dispname,
                "var1": "N/A",
                "var2": "N/A",
                "roles": roles or ""
            }

        if var1 is not None:
            user_info["discord_users"][str(uid)]["var1"] = var1
        if var2 is not None:
            user_info["discord_users"][str(uid)]["var2"] = var2
        if roles is not None:
            user_info["discord_users"][str(uid)]["roles"] = roles

        save_json(USER_INFO_FILE, user_info)
        return user_info["discord_users"][str(uid)]
    
    def update_user_var(uid_or_name, var1=None, var2=None):
        if "discord_users" not in user_info:
            user_info["discord_users"] = {}

        # First try by ID
        if str(uid_or_name) in user_info["discord_users"]:
            user_data = user_info["discord_users"][str(uid_or_name)]
        else:
            # Try by display name
            user_data = None
            for u in user_info["discord_users"].values():
                if u.get("dispname") == uid_or_name:
                    user_data = u
                    break

        if not user_data:
            return None

        if var1 is not None:
            user_data["var1"] = var1
        if var2 is not None:
            user_data["var2"] = var2

        save_json(USER_INFO_FILE, user_info)
        return user_data

    @tasks.loop(hours=24)
    async def auto_save_users():
        await bot.wait_until_ready()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if "discord_users" not in user_info:
            user_info["discord_users"] = {}

        for guild in bot.guilds:
            async for member in guild.fetch_members(limit=None):  # Fetch all members
                if member.bot:
                    continue

                roles = [r.name for r in member.roles if r.name != "@everyone"]

                # Keep existing var1/var2 if present
                old_data = user_info["discord_users"].get(str(member.id), {})
                user_info["discord_users"][str(member.id)] = {
                    "id": str(member.id),
                    "dispname": member.display_name,
                    "username": str(member),  # full username with #1234
                    "joined_at": str(member.joined_at) if member.joined_at else "Unknown",
                    "created_at": str(member.created_at),
                    "roles": ", ".join(roles),
                    "var1": old_data.get("var1", "N/A"),
                    "var2": old_data.get("var2", "N/A")
                }

        user_info["last_saved"] = now
        save_userinfo(user_info, session_id=session_id)
        logging.info(f"Auto-saved {len(user_info.get('discord_users', {}))} users at {now}")

    # ===== MINECRAFT SERVER MONITORING SETUP =====
    BEDROCK_HOST = config_data["MCS"]["mcsAdress"] or "multi-nor.gl.at.ply.gg"
    BEDROCK_PORT = config_data["MCS"]["mcsPort"] or 5355
    ServerUpdateChannelID = config_data["MCS"]["mcsChID"] or 1421497953834631319
    MCSDURATION = int(config_data["MCS"]["mcsDelay"]) or 3600  # in seconds
    MCSROLEID = int(config_data["MCS"]["mcsRoleID"]) or 1394542459538640977

    # ===== VERSION INFO =====
    VERSION = config_data["config"]["version"]
    AUTHOR = config_data["config"]["author"]
    CMD_PREFIX = config_data["config"]["command_prefix"]
    ADMIN_ROLE_ID = int(config_data["config"].get("admin_role_id", 0)) or None

    # ===== GLOBALS =====
    bot_started = False
    bot = None
    bot_loop = None
    manual_shutdown = False

    # ===== MESSAGES =====
    startmessage: str | None = None
    stopmessage: str | None = None

    # ===== BOT SETUP =====
    if "bot" in globals():
        del globals()["bot"]

    bot_started = False

    # ===== INTERNAL SESSION CONTROL =====
    async def startsession(): # FOR INTERNAL USE ONLY
        global bot_started
        if bot_started:
            logging.info("Bot is already running.")
            return

        async def runner():
            try:
                await bot.start(token)
                
            except Exception as e:
                logging.error(f"Error starting bot: {e}")

        bot_loop.create_task(runner())
        bot_started = True
        logging.info("Bot started.")

    async def stopsession(message: str = None): # FOR INTERNAL USE ONLY
        global bot_started
        if not bot_started:
            logging.info("Bot is not running.")
            return

        logging.info("Bot stopped. Closing connection...")
        if stopmessage:
            channel = bot.get_channel(target_channel_id)
            if channel:
                try:
                    await channel.send(message)
                    logging.info(f"Sent stop message to channel ID: {target_channel_id}")
                except Exception as e:
                    logging.error(f"Failed to send stop message: {e}")
        try:
            await bot.close()
        except Exception as e:
            logging.error(f"Error shutting down bot cleanly: {e}")

        bot_started = False

    def gen_session_id():
        raw_data = os.urandom(32) + str(time.time()).encode()
        session_id = hashlib.sha256(raw_data).hexdigest()
        return session_id

    # ===== UTILS =====
    def parse_duration(dur_str: str) -> timedelta | None:
        match = re.match(r"^(\d+)([hdw])$", dur_str.lower())
        if not match:
            return None

        value, unit = match.groups()
        value = int(value)
        if unit == "s":
            return timedelta(seconds=value)
        elif unit == "m":
            return timedelta(minutes=value)
        elif unit == "h":
            return timedelta(hours=value)
        elif unit == "d":
            return timedelta(days=value)
        elif unit == "w":
            return timedelta(weeks=value)
        else:
            return None
        
    def normalize_message(text):
        text = unicodedata.normalize('NFKD', str(text)).encode('ASCII', 'ignore').decode('ASCII')
        text = re.sub(r'[\s\W_]+', '', text)
        text = ''.join(c for c in text if not unicodedata.combining(c))
        text = re.sub(r'[\u200B-\u200F\uFE00-\uFE0F\u2060-\u206F]', '', text)
        text = ''.join(c for c in text if unicodedata.category(c)[0] != 'C')
        text = unicodedata.normalize("NFKC", str(text)).lower()

        # Extended number-to-letter replacements
        replacements = str.maketrans({
            '0': 'o',
            '1': 'i',
            '2': 'z',
            '3': 'e',
            '4': 'a',
            '5': 's',
            '6': 'g',
            '7': 't',
            '8': 'a',
            '9': 'g'
        })
        
        text = text.translate(replacements)

        return text

    async def replace_placeholders(ctx, text, self_id: int = 1260198579067420722):
        pattern = r"<\{(\w+):([^}]*)\}>"
        output = []
        last_end = 0

        for m in re.finditer(pattern, text):
            output.append(text[last_end:m.start()])
            p_type, p_value = m.groups()
            p_type = p_type.lower()

            if p_type == "mention":
                if p_value.lower() == "a":
                    output.append(f"<@{self_id}>")
                elif p_value.isdigit():
                    output.append(f"<@{p_value}>")
                else:
                    output.append(m.group(0))

            elif p_type == "channel":
                output.append(f"<#{p_value}>" if p_value.isdigit() else m.group(0))

            elif p_type == "role":
                output.append(f"<@&{p_value}>" if p_value.isdigit() else m.group(0))

            elif p_type == "file":
                file_reference = p_value.strip()
                path_info = get_file(file_reference)
                if path_info:
                    path, filename = path_info
                    if os.path.isfile(path):
                        await ctx.send(file=discord.File(path, filename=filename))
                    else:
                        await ctx.send(f"File not found: {file_reference}")
                else:
                    await ctx.send(f"File not found: {file_reference}")

            else:
                output.append(m.group(0))

            last_end = m.end()

        output.append(text[last_end:])
        return "".join(output).strip()

    
    # ===== BANNED WORDS =====
    BANNED_WORDS_FILE = "banned_words.json"

    def load_banned_words():
        if os.path.exists(BANNED_WORDS_FILE):
            with open(BANNED_WORDS_FILE, "r") as f:
                return set(json.load(f))
        return set()

    def save_banned_words():
        with open(BANNED_WORDS_FILE, "w") as f:
            json.dump(list(BANNED_WORDS), f)

    BANNED_WORDS = load_banned_words() or {
        "nigga", "nigger", "niga", "n1gger",
        "นิกก้า", "นิกเกอร์", "นิกเก้อ"
    }
    save_banned_words()

    # ===== BOT CREATION =====
    def create_bot():
        intents = discord.Intents.default()
        intents.messages = True
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        bot = commands.Bot(command_prefix=CMD_PREFIX, intents=intents)

        # ===== BOT EVENTS =====
        @bot.event
        async def on_ready():
            global startmessage
            logging.info(f"Logged in as {bot.user} (ID: {bot.user.id})")

            if startmessage is None:
                logging.info("No startmessage set.")
                return

            channel = bot.get_channel(target_channel_id)
            if channel:
                try:
                    await channel.send(startmessage)
                    logging.info(f"Sent startup message to channel ID: {target_channel_id}")
                except Exception as e:
                    logging.error(f"Failed to send startup message: {e}")

            if not auto_save_users.is_running():
                auto_save_users.start()
                
            await auto_save_users()

        @bot.event
        async def on_message(message):
            logging.info(
                f"{message.id}:{message.author} ({message.author.id}) in #{message.channel.name} ({message.channel.id}): {message.content}"
            )

            content = normalize_message(message.content)
            ctx = await bot.get_context(message)

            if "commandIgnore" in message.content and commands.is_owner():
                return
        
            if (
                any(word in content for word in BANNED_WORDS)
                and not (ctx.command and ctx.command.name in ["banword", "rmword"])
                and not (message.author == bot.user)
                and not any(role.id == 1411139316171931738 for role in message.author.roles)
            ):
                try:
                    await message.delete()
                    await message.author.timeout(
                        timedelta(minutes=5),
                        reason="You said a banned word."
                    )
                    await message.channel.send(
                        f"{message.author.mention} has been timed out for using a banned word."
                    )
                    logging.info(f"Timed out: {message.author} for '{message.content}'")
                except discord.Forbidden:
                    await message.channel.send(
                        f"I can't timeout {message.author.mention}, missing permissions."
                    )
                    logging.error("Bot doesn't have permission to timeout this user.")
                except Exception as e:
                    logging.error(f"Error: {e}")

            if any(word in content.lower() for word in ["goodboy", "good boy"]) and bot.user.mentioned_in(message):
                try:
                    await message.channel.send(f"☆*: .｡. o(≧▽≦)o .｡.:*☆, thanks papi {message.author.mention} 😩.")
                    logging.info(f"Sent Goodboy response to {message.author}")
                except Exception as e:
                    logging.error(f"Error sending good boy response: {e}")

            if any(word in content.lower() for word in ["badboy", "bad boy"]) and bot.user.mentioned_in(message):
                try:
                    await message.channel.send(f"ヾ(≧へ≦)〃, Fuck you {message.author.mention}.")
                    logging.info(f"Sent Goodboy response to {message.author}")
                except Exception as e:
                    logging.error(f"Error sending 'Insulting' response: {e}")

            await bot.process_commands(message)

            if ctx.valid:
                return

        @bot.event
        async def on_message_edit(before, after):
            if after.author.bot:
                return

            ctx = await bot.get_context(after)
            if ctx.valid:
                return

            content = normalize_message(after.content)
            if any(word in content for word in BANNED_WORDS):
                try:
                    await after.delete()
                    await after.author.timeout(timedelta(minutes=5), reason="You tried to sneak in a banned word by editing, you dumb fuck.")
                    await after.channel.send(f"{after.author.mention} has been timed out for editing in a fucking banned word.")
                    logging.info(f"[EDIT] Timed out: {after.author} for '{after.content}'")
                except discord.Forbidden:
                    await after.channel.send(f"I can't ban {after.author.mention}, but they tried to be sneaky.")
                    logging.error("[EDIT] Bot doesn't have permission to timeout this sneaky dumb fuck.")
                except Exception as e:
                    logging.error(f"[EDIT] Error: {e}")

        # ===== ADMIN COMMANDS =====
        @bot.command(name="saveuinf")
        @commands.has_permissions(administrator=True)
        async def saveall(ctx):
            await auto_save_users()
            await ctx.send("Manual save completed.")

        @bot.command(name="userinfo")
        async def userinfo_cmd(ctx, action: str = None, key: str = None, *, value: str = None):
            uid = str(ctx.author.id)
            if uid not in user_info:
                user_info[uid] = {
                    "id": uid,
                    "dispname": ctx.author.display_name,
                    "var1": "",
                    "var2": "",
                    "roles": ""
                }

            if action == "view":
                info = user_info[uid]
                embed = discord.Embed(title=f"User Info: {ctx.author.display_name}", color=discord.Color.blue())
                for k, v in info.items():
                    embed.add_field(name=k, value=v or "N/A", inline=False)
                await ctx.send(embed=embed)

            elif action == "edit":
                if key not in user_info[uid]:
                    await ctx.send(f"Invalid key: `{key}`")
                    return
                user_info[uid][key] = value
                save_userinfo(user_info)
                await ctx.send(f"`{key}` updated to `{value}`")

            elif action == "roles":
                roles = [r.name for r in ctx.author.roles if r.name != "@everyone"]
                user_info[uid]["roles"] = ", ".join(roles)
                save_userinfo(user_info)
                await ctx.send(f"Roles updated: `{user_info[uid]['roles']}`")

            else:
                await ctx.send("Usage: `!userinfo view` | `!userinfo edit <key> <value>` | `!userinfo roles`")

        @bot.command(name="editvar")
        @commands.has_permissions(administrator=True)
        async def editvar(ctx, identifier: str, var1: str = None, var2: str = None):
            """
            Edit a user's var1/var2 by ID or display name.
            Usage: !editvar <ID or dispname> <var1> <var2>
            """
            updated = update_user_var(identifier, var1, var2)
            if not updated:
                await ctx.send(f"User `{identifier}` not found in user info.")
                return

            await ctx.send(
                f"Updated user `{updated['dispname']}`:\nvar1 = `{updated.get('var1','N/A')}`\nvar2 = `{updated.get('var2','N/A')}`"
            )

        @bot.command(name="sessioninfo")
        @commands.is_owner()
        async def session_info(ctx):
            """Display full system, network, and runtime info for diagnostics."""
            try:
                # Date, Time, and Session ID
                dtc = datetime.now()
                dtc_utc = datetime.now(datetime.timezone.utc)
                
                date_str = dtc.strftime("%Y-%m-%d")
                time_str = dtc.strftime("%H:%M:%S")
                
                utc_date_str = dtc_utc.strftime("%Y-%m-%d")
                utc_time_str = dtc_utc.strftime("%H:%M:%S")

                hostname = socket.gethostname()
                try:
                    ip_address = socket.gethostbyname(hostname)
                except Exception:
                    ip_address = "Unavailable"

                os_info = f"{platform.system()} {platform.release()} ({platform.version()})"
                architecture = platform.machine()
                user = getpass.getuser()
                
                cpu_count = psutil.cpu_count(logical=True)
                cpu_freq = psutil.cpu_freq()
                cpu_usage = psutil.cpu_percent(interval=1)
                
                mem = psutil.virtual_memory()
                swap = psutil.swap_memory()

                disk_info = []
                for d in psutil.disk_partitions(all=False):
                    try:
                        usage = psutil.disk_usage(d.mountpoint)
                        disk_info.append(f"{d.device} ({d.mountpoint}): {usage.percent}% used")
                    except PermissionError:
                        disk_info.append(f"{d.device} ({d.mountpoint}): Permission denied")
                    except OSError:
                        disk_info.append(f"{d.device} ({d.mountpoint}): Not ready")

                gpu_info = []
                if GPUtil:
                    try:
                        gpus = GPUtil.getGPUs()
                        if gpus:
                            for gpu in gpus:
                                gpu_info.append(
                                    f"{gpu.name} ({gpu.memoryTotal}MB) - {gpu.load * 100:.1f}% load"
                                )
                        else:
                            gpu_info.append("No GPU detected")
                    except Exception:
                        gpu_info.append("Error retrieving GPU info")
                else:
                    gpu_info.append("GPUtil not installed")

                net_if_addrs = psutil.net_if_addrs()
                net_info = []
                for interface_name, addrs in net_if_addrs.items():
                    for addr in addrs:
                        if addr.family == socket.AF_INET:
                            net_info.append(f"{interface_name}: {addr.address}")
                try:
                    import discord
                    discord_ver = discord.__version__
                except Exception:
                    discord_ver = "Unknown"

                try:
                    import pkg_resources
                    libs = ", ".join(
                        sorted([p.project_name for p in pkg_resources.working_set])
                    )
                except Exception:
                    libs = "Unavailable"

                embed = discord.Embed(
                    title="Session Information",
                    color=discord.Color.blurple(),
                    timestamp=datetime.now(),
                )

                embed.add_field(
                    name="Date / Time",
                    value=f"**Date:** `{date_str}`\n**Time:** `{time_str}`",
                    inline=False,
                )
                                                                
                embed.add_field(
                    name="Date / Time (UTC)",
                    value=f"**Date:** `{utc_date_str}`\n**Time:** `{utc_time_str}`",
                    inline=False,
                )
                
                embed.add_field(name="Session ID", value=f"`{session_id}`", inline=False)
                embed.add_field(
                    name="Host Info",
                    value=f"**Hostname:** `{hostname}`\n**IPv4:** `{ip_address}`\n**User:** `{user}`",
                    inline=False,
                )
                embed.add_field(
                    name="OS",
                    value=f"`{os_info}`\n**Architecture:** `{architecture}`",
                    inline=False,
                )
                embed.add_field(
                    name="Bot / Environment",
                    value=(
                        f"**Python:** `{platform.python_version()}`\n"
                        f"**Discord.py:** `{discord_ver}`\n"
                        f"**Libraries:** {libs}\n"
                        f"**Bot Version:** `{VERSION}`"
                    ),
                    inline=False,
                )
                embed.add_field(
                    name="CPU",
                    value=f"**Cores:** `{cpu_count}`\n**Frequency:** `{cpu_freq.current:.2f} MHz`\n**Usage:** `{cpu_usage}%`",
                    inline=False,
                )
                embed.add_field(
                    name="Memory",
                    value=(
                        f"**Total:** `{mem.total // (1024**2)}MB`\n"
                        f"**Used:** `{mem.used // (1024**2)}MB` ({mem.percent}%)\n"
                        f"**Available:** `{mem.available // (1024**2)}MB`\n"
                        f"**Swap:** `{swap.used // (1024**2)}MB / {swap.total // (1024**2)}MB`"
                    ),
                    inline=False,
                )
                embed.add_field(
                    name="Disk Usage", value="\n".join(disk_info) or "Unavailable", inline=False
                )
                embed.add_field(name="GPU", value="\n".join(gpu_info), inline=False)
                embed.add_field(
                    name="Network Interfaces",
                    value="\n".join(net_info) or "No active interfaces",
                    inline=False,
                )
                
                await ctx.send(embed=embed)
                logging.info(f"Session info sent by {ctx.author}")

            except Exception as e:
                await ctx.send("Error retrieving session info.")
                logging.error(f"Error: {e}")

        @bot.command(name="banword")
        @commands.has_permissions(administrator=True)
        async def ban_word(ctx, *, word: str):
            word = word.lower().strip()
            if word in BANNED_WORDS:
                await ctx.send(f"'{word}' is already banned, dumbass.")
            else:
                BANNED_WORDS.add(word)
                save_banned_words()
                await ctx.send(f"Added '{word}' to the list of fucking banned words.")
                logging.info(f"Added banned word: {word}")

        @bot.command(name="rmword")
        @commands.has_role(ADMIN_ROLE_ID)
        @commands.has_permissions(administrator=True)
        async def remove_ban_word(ctx, *, word: str):
            word = word.lower().strip()
            if word in BANNED_WORDS:
                BANNED_WORDS.remove(word)
                save_banned_words()
                await ctx.send(f"Removed '{word}' from the fucking list.")
                logging.info(f"Removed banned word: {word}")
            else:
                await ctx.send(f"'{word}' isn't even banned, idiot.")

        @bot.command(name="listbanword")
        @commands.has_permissions(administrator=True)
        async def list_ban_words(ctx):
            if BANNED_WORDS:
                await ctx.send("Here's the shit we're banning:\n" + ", ".join(sorted(BANNED_WORDS)))
            else:
                await ctx.send("No banned words, go wild.")

        @bot.command(name="forgive")
        @commands.has_permissions(moderate_members=True)
        async def forgive(ctx, member: discord.Member):
            try:
                await member.edit(timed_out_until=None)
                await ctx.send(f"{member.mention} has been forgiven and their timeout has been lifted, don't say that again dumb fuck.")
            except discord.Forbidden:
                await ctx.send("Shit, I don't have permission to forgive this user.")
            except discord.HTTPException as e:
                await ctx.send(f"Something went wrong while forgiving. DEBUG: {e}")

        @bot.command(name="pewthyself")
        @commands.is_owner()
        async def sessionend(ctx):
            await stopsession(f"Ight {ctx.author.mention}... I'm out. 💀")

        @bot.command(name="version")
        async def version_command(ctx):
            await ctx.send(f"Bot version: {VERSION}\nMy papi is: {AUTHOR}")

        @bot.command(name="agreewme")
        @commands.is_owner()
        async def agree_with_me(ctx, *, message: str = None):
            if message:
                await ctx.send(f"Yes, daddy {ctx.author.mention}😩. You're absolutely right about: \"{message}\".")
            else:
                await ctx.send(f"Yes, daddy {ctx.author.mention}😩.")

        @bot.command(name="disagreewme")
        async def disagree_with_me(ctx, *, message: str = None):
            if message:
                await ctx.send(f"No, daddy {ctx.author.mention}😩. \"{message}\" is not true.")
            else:
                await ctx.send(f"No, daddy {ctx.author.mention}😩.")

        @bot.command(name="repeat")
        @commands.is_owner()
        async def repeat(ctx, *, message: str):
            logging.info(f"[{ctx.author} ({ctx.author.id})] Called repeat with message: {message}")
            await ctx.send(message)

        @bot.command(name="deplete")
        @commands.is_owner()
        async def deplete(ctx, type: str, value: int):
            logging.info(f"[{ctx.author} ({ctx.author.id})] Called deplete with type: {type}, value: {value}")
            units = {"ms": 0.001, "sec": 1, "min": 60, "hr": 3600, "d": 86400}
            type = type.lower()
            if type not in units:
                await ctx.send("Invalid type. Use ms, sec, min, hr, or d.")
                return
            seconds = value * units[type]
            await ctx.send(f"After finishing I will deplete myself in {seconds:.2f}s, I AM STILL WATCHING.")
            await asyncio.sleep(seconds)
            await stopsession(f"Ight {ctx.author.mention}... I'm out. 💀")

        @bot.command(name="cfch")
        @commands.has_permissions(administrator=True)
        async def cfch(ctx, channel_id: str):
            global target_channel_id
            if channel_id.lower() == "current":
                target_channel_id = ctx.channel.id
                await ctx.send(f"Target channel set to this channel: {ctx.channel.name} (ID: {target_channel_id})")
            else:
                try:
                    new_id = int(channel_id)
                    channel = bot.get_channel(new_id)
                    if channel:
                        target_channel_id = new_id
                        await ctx.send(f"Target channel set to {channel.name} (ID: {target_channel_id})")
                    else:
                        await ctx.send("Invalid channel ID.")
                except ValueError:
                    await ctx.send("Please provide a valid channel ID or use current.")

        @bot.command(name="seelog")
        @commands.has_permissions(administrator=True)
        async def see_log(ctx, date: str = None, filename: str = None):
            logging.info(f"[{ctx.author} ({ctx.author.id})] Called see_log with date: {date}, filename: {filename}")

            if date == "recent":
                log_dirs = sorted(os.listdir("log"), reverse=True)
                if not log_dirs:
                    await ctx.send("No logs found.")
                    return
                recent_dir = log_dirs[0]
                log_files = sorted(os.listdir(f"log/{recent_dir}"), reverse=True)
                if not log_files:
                    await ctx.send("No log files found in the most recent directory.")
                    return
                date, filename = recent_dir, log_files[0]

            if not date or not filename:
                await ctx.send("Please provide a valid date and filename, or use 'recent'.")
                return

            path = f"log/{date}/{filename}"
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()

                    if len(content) < 1900:
                        await ctx.send(f"```\n{content}\n```")
                    else:
                        # Send just the last 1900 chars for readability
                        await ctx.send(f"```{content[-1900:]}```")
                        # Or send full log file as attachment
                        await ctx.send("Full log attached:", file=discord.File(path))

                except Exception as e:
                    await ctx.send(f"Error reading log file: {e}")
            else:
                await ctx.send("Log not found. I lost it or u dyslexic?")

        @bot.command(name="thx")
        async def thank_you(ctx):
            logging.info(f"[{ctx.author} ({ctx.author.id})] Called thx")
            await ctx.send("np")

        @bot.command(name="mcstat")
        async def mcstat(ctx, option: str = None):
            server = BedrockServer.lookup(f"{BEDROCK_HOST}:{BEDROCK_PORT}")
            try:
                address = f"{BEDROCK_HOST}:{BEDROCK_PORT}"
                status = server.status()
                players = status.players.online
                latency = status.latency

                # Add role mention only if "tagmcr" was provided
                role_mention = f"<@&{MCSROLEID}>\n" if option == "tagmcr" else ""

                await ctx.send(
                    f"{role_mention}"
                    f"🟢 **Minecraft Bedrock Server is ONLINE**\n"
                    f"Address: {address}\n"
                    f"Players: {players}\n"
                    f"Latency: {latency:.1f} ms"
                )
            except Exception as e:
                role_mention = f"<@&{MCSROLEID}>\n" if option == "tagmcr" else ""
                await ctx.send(
                    f"{role_mention}"
                    "🔴 **Minecraft Bedrock Server is OFFLINE**"
                    f"({e})"
                )
                logging.error(f"mcstat command failed: {e}")
                
        @bot.command(name="mkpoll")
        async def make_poll(ctx, question: str, *args):
            # Validation
            if len(args) < 2:
                return await ctx.send("You need at least **2 options** and a **duration** (e.g. 1h, 3d, 1w).")

            duration_str = args[-1]
            options = args[:-1]

            if len(options) < 2:
                return await ctx.send("You must have at least **2 options** before the duration.")
            if len(options) > 10:
                return await ctx.send("You can only have up to **10 options.**")

            duration = parse_duration(duration_str)
            if duration is None:
                return await ctx.send("Invalid duration format. Use **1h**, **4h**, **3d**, or **1w**.")

            # ====== Check Duration Limit ======
            one_week = timedelta(weeks=1)
            if duration > one_week:
                return await ctx.send("Poll duration cannot be longer than **1 week** (7 days).")

            # ====== Create Poll ======
            poll = discord.Poll(question=question, duration=duration)
            for option in options:
                poll.add_answer(text=option)

            await ctx.send(poll=poll)
            await ctx.message.delete()

        # ===== ERROR HANDLERS =====
        @ban_word.error
        @remove_ban_word.error
        @list_ban_words.error
        async def perm_error(ctx, error):
            if isinstance(error, commands.MissingPermissions):
                logging.warning(f"Permission denied: {ctx.author} tried to use admin command.")
                await ctx.send("You don't have permission, bro. Sit down.")

        @sessionend.error
        @deplete.error
        async def privileged_error(ctx, error):
            if isinstance(error, commands.MissingRole):
                await ctx.send("*I, the creator of this bot, have the right to end it. You don't, stoobid.*")
                await ctx.send("-THE GREATEST BOT CREATOR THAT EVER LIVED")
        
        @bot.listen("on_command_completion")
        async def log_command_done(ctx):
            logging.info(f"Command completed: {ctx.command} by {ctx.author}")

        @bot.listen("on_command_error")
        async def log_command_error(ctx, error):
            logging.error(f"Error in command {ctx.command} by {ctx.author}: {error}")

        return bot

    # ===== CONSOLE INTERFACE =====
    def console_interface():
        global target_channel_id, config_data
        global bot_started, bot, bot_loop

        print("Console ready. Commands: start [msg], stop [msg], targch [channel_id], exit")
        with patch_stdout():
            while True:
                cmd = prompt("console> ").strip().split()
                if not cmd:
                    continue
                command, *args = cmd

                if command[0] == "&":
                    print("Console isn't closed, proceeding to exit.")
                    sys.exit(0)

                if command == "start":
                    if bot_started:
                        print("Bot already running.")
                        continue
                        
                    try:
                        global startmessage
                        if not args:
                            startmessage = "I am watching you."   # default
                        elif args[0].lower() == "none":
                            startmessage = None                   # skip
                        else:
                            startmessage = " ".join(args)         # var

                        bot = create_bot()  # NEW bot each time
                        bot_loop = asyncio.new_event_loop()  # NEW loop each time
                        asyncio.set_event_loop(bot_loop)

                        def run_bot():
                            try:
                                bot_loop.run_until_complete(bot.start(token))
                            except asyncio.CancelledError:
                                pass
                            except Exception as e:
                                print("Error starting bot:", e)
                            finally:
                                bot_loop.close()

                        threading.Thread(target=run_bot, daemon=True).start()
                        bot_started = True
                        print("Bot started.")
                        global session_id
                        session_id = gen_session_id()
                        logging.info(f"Session ID: {session_id}")
                    except Exception as e:
                        print("Failed to start bot:", e)

                elif command == "stop": 
                    if not bot_started:
                        print("Bot is not running.")
                        continue

                    global manual_shutdown, stop_message
                    manual_shutdown = True

                    if not args:
                        stop_message = "My papi or ISP or MEA is shutting me down nooo."
                    elif args[0].lower() == "none":
                        stop_message = None
                    else:
                        stop_message = " ".join(args)

                    async def shutdown():
                        try:
                            logging.info("Shutting down bot...")

                            if stop_message and target_channel_id:
                                channel = bot.get_channel(target_channel_id)
                                if channel:
                                    await channel.send(stop_message)
                                    logging.info(f"Sent shutdown message to #{channel} ({channel.id}): {stop_message}")
                                else:
                                    logging.warning(f"Could not find channel with ID {target_channel_id}")

                            # Cancel all background tasks except current
                            for task in asyncio.all_tasks(bot_loop):
                                if task is not asyncio.current_task(bot_loop):
                                    task.cancel()
                            
                            await bot.close()  # Properly close connection
                            logging.info("Bot shutdown complete.")
                        except Exception as e:
                            logging.error(f"Error during shutdown: {e}")
                    try:
                    # Run shutdown safely in the bot's loop
                        fut = asyncio.run_coroutine_threadsafe(shutdown(), bot_loop)

                        logging.info("Waiting for bot to shut down...")
                        fut.result(timeout=10)  # Wait max 10s for shutdown
                    except asyncio.CancelledError:
                        logging.info("CancelledError during shutdown. No threat.")
                    except Exception as e:
                        logging.error(f"Error shutting down: {e}")

                    bot_started = False
                    logging.info("Bot stopped.")

                elif command == "exit":
                    if bot_started and bot_loop:
                        while True:
                            decision = input("Bot isn't shutdown, exit? (y/n/f(fuq u)): ").strip().lower()
                            if decision in ("y", ""):
                                try:
                                    fut = asyncio.run_coroutine_threadsafe(stopsession(), bot_loop)
                                    fut.result(timeout=10)
                                    print("Bot shutdown complete.")
                                except asyncio.TimeoutError:
                                    logging.error("Bot shutdown timed out.")
                                except Exception as e:
                                    logging.error(f"Error shutting down bot: {e}")
                                finally:
                                    sys.exit(0)
                            elif decision == "f":
                                print("Committing suicide...")
                                sys.exit(0)
                            elif decision == "n":
                                break
                            else:
                                logging.info("Pick something.")
                    else:
                        sys.exit(0)

                elif command == "targch" and args and args[0].isdigit():
                    target_channel_id = int(args[0])
                    config_data["config"]["default_target_channel_id"] = str(target_channel_id)
                    save_json(CONFIG_FILE, config_data)
                    print(f"Target channel set to {target_channel_id}")

                elif command == "reply" and args and args[0].isdigit():
                    message_to_re = int(args[0])
                    if len(args) < 2:
                        print("Usage: reply <message_id> <message>")
                        continue

                    raw_msg = " ".join(args[1:])

                    override_channel_id = None
                    possible_override = None

                    # Check if last arg is {something}
                    if raw_msg.endswith("}"):
                        match = re.search(r"\{(\d+)\}$", raw_msg)
                        if match:
                            possible_override = int(match.group(1))

                    if bot_started and bot_loop:
                        async def reply_to_message():
                            nonlocal raw_msg, override_channel_id, possible_override
                            try:
                                ch_id = target_channel_id
                                msg_text = raw_msg

                                if possible_override:
                                    # Try to fetch the channel
                                    channel = bot.get_channel(possible_override)
                                    if channel is None:
                                        try:
                                            channel = await bot.fetch_channel(possible_override)
                                        except:
                                            channel = None

                                    if channel:
                                        override_channel_id = possible_override
                                        ch_id = override_channel_id
                                        # remove the {id} from the text
                                        msg_text = raw_msg[: raw_msg.rfind("{")].strip()

                                # Apply placeholder replacement
                                msg_text = replace_placeholders(msg_text)

                                # Fetch target channel
                                channel = bot.get_channel(ch_id)
                                if channel is None:
                                    channel = await bot.fetch_channel(ch_id)

                                # Fetch the message to reply to
                                target_msg = await channel.fetch_message(message_to_re)

                                # Send reply
                                await target_msg.reply(msg_text, mention_author=False)
                                print(f"Replied to message {message_to_re} in channel {ch_id}.")
                            except Exception as e:
                                print("Failed to reply:", e)

                        asyncio.run_coroutine_threadsafe(reply_to_message(), bot_loop)
                    else:
                        print("Bot is not running.")

                elif command == "sendmsg" and args:
                    raw_msg = " ".join(args)

                    override_channel_id = None
                    possible_override = None

                    # Check if last arg is {channel_id}
                    if raw_msg.endswith("}"):
                        match = re.search(r"\{(\d+)\}$", raw_msg)
                        if match:
                            possible_override = int(match.group(1))
                            # remove {id} from the text
                            raw_msg = raw_msg[: raw_msg.rfind("{")].strip()

                    if bot_started and bot_loop:
                        async def send_message():
                            try:
                                ch_id = possible_override or target_channel_id
                                channel = bot.get_channel(ch_id)
                                if channel is None:
                                    channel = await bot.fetch_channel(ch_id)

                                if channel is None:
                                    print(f"Channel {ch_id} not found.")
                                    return

                                # Replace placeholders and send files
                                msg_text = await replace_placeholders(channel, raw_msg)

                                # Send remaining text if any
                                if msg_text.strip():
                                    await channel.send(msg_text)

                                print(f"Message sent to channel {ch_id}.")

                            except Exception as e:
                                print("Failed to send message:", e)

                        asyncio.run_coroutine_threadsafe(send_message(), bot_loop)
                    else:
                        print("Bot is not running.")

                
                elif command == "addfile":
                    if len(args) != 2:
                        print("Usage: addfile <ui|dir> <file_reference>")
                        continue
                    add_file(args[0], args[1])

                elif command == "getfile":
                    if len(args) != 1:
                        print("Usage: getfile <file_reference>")
                        continue
                    get_file(args[0])

                elif command == "delfile":
                    if len(args) != 1:
                        print("Usage: delfile <file_reference>")
                        continue
                    del_file(args[0])

    # ===== MAIN =====
    if __name__ == "__main__":
        try:
            bot = create_bot()
        except Exception:
            logging.critical("Unhandled exception:\n" + traceback.format_exc())
            input("Press Enter to exit...")
            sys.exit(1)
        
        try:
            console_interface()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting console.")
            sys.exit(0)
except Exception as e:
    logging.critical("Critical error :\n" + traceback.format_exc())
    print(f"Critical error : {e}")
    input("Press Enter to exit...")
    sys.exit(1)