#BestBotEver!!! 2

if __name__ == "__main__":
    print("Starting BestBotEver!!!...")

import sys, os
import discord
from discord import FFmpegPCMAudio
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import json
import unicodedata
import re
import asyncio
import logging
from logging.handlers import TimedRotatingFileHandler
import threading
import platform
import socket
import getpass
import io
import psutil
import pynvml
import traceback
from mcstatus import BedrockServer
import tkinter as tk
from tkinter import filedialog
import shutil
import colorama
import hashlib
import time
import yt_dlp
from homoglyphs import Homoglyphs
import subprocess
from unidecode import unidecode
from gtts import gTTS
from typing import Optional
from conintf_ptk import ConsoleInterface
from collections import defaultdict  # used for per-guild silenced sets
import contextvars  # for guild context tracking

try:
    global DEBUGB
    DEBUGB = False
    def debug(txt: str, id: str):
        if DEBUGB == True:
            print("Debug Print ", id, ": ",txt)
    
    # ===== GUILD CONTEXT FOR LOGGING =====
    current_guild_context = contextvars.ContextVar('current_guild', default={'id': None, 'name': 'Unknown'})
    
    def set_guild_context(guild_id: int, guild_name: str):
        """Set the current guild context for logging."""
        current_guild_context.set({'id': guild_id, 'name': guild_name})
    
    def get_guild_context():
        """Get the current guild context."""
        return current_guild_context.get()
        
    # ===== SETUP =====
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, "buffer"):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    colorama.init()

    # ===== PLACEHOLDER =====
    MESSAGES_FILE = "messages.json"

    def get_bot_message(category_or_key: str, key: str | None = None, **kwargs) -> str:
        """Get bot message from messages.json.
        Usage:
          get_bot_message("startup")                             -> direct key under "bot"
          get_bot_message("responses", "np", mention="@me")      -> nested category + key
          get_bot_message("moderation.timeout_message", None, ...) -> dot-path in category_or_key
        """
        try:
            messages = load_json(MESSAGES_FILE) or {}
            bot_msgs = messages.get("bot", {})

            if category_or_key == "v":
                return "Version "+ messages.get("config", {}).get("version", "Not Specified")
            
            if key is None and "." in category_or_key:
                parts = category_or_key.split(".")
                msg = bot_msgs
                for p in parts[:-1]:
                    msg = msg[p]
                return msg[parts[-1]].format(**kwargs)
            
            if key is None:
                val = bot_msgs.get(category_or_key)
                if isinstance(val, str):
                    return val.format(**kwargs)
                raise KeyError

            parts = category_or_key.split(".")
            msg = bot_msgs
            for p in parts:
                msg = msg[p]
            return msg[key].format(**kwargs)

        except Exception as e:
            logging.error(f"Message not found: {category_or_key}{'.' + key if key else ''} -> {e}")
            return f"MESSAGE_NOT_FOUND:{category_or_key}{'.' + key if key else ''}"

    # ===== FILE HANDLING =====
    DUMP_DIR = "fdump"
    FILE_DB = "fdump/files.json"
    os.makedirs(DUMP_DIR, exist_ok=True)
    
    def browse_file():
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
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
                logging.info("No file selected.")
                return
        elif mode == "dir":
            file_path = input("Enter file path: ").strip()
        else:
            print("Usage: addfile <ui|dir> <file_reference>")
            return

        if not os.path.isfile(file_path):
            logging.info("File not found.")
            return

        original_name = os.path.basename(file_path)
        dest_path = os.path.join(DUMP_DIR, original_name)

        shutil.copy2(file_path, dest_path)

        db[file_reference] = {
            "original_path": os.path.abspath(file_path),
            "dump_path": os.path.abspath(dest_path),
            "filename": original_name
        }
        save_filedb(db)

        logging.info(f"File '{file_reference}' added. Original filename preserved: {original_name}")

    def get_file(file_reference):
        db = load_filedb()
        if file_reference not in db:
            logging.info(f"reference '{file_reference}' not found.")
            return None
        info = db[file_reference]
        return info["dump_path"], info["filename"]

    def del_file(file_reference):
        db = load_filedb()
        if file_reference not in db:
            logging.info(f"No such reference name '{file_reference}'.")
            return

        dump_path = db[file_reference].get("dump_path")
        if dump_path and os.path.exists(dump_path):
            try:
                os.remove(dump_path)
            except Exception as e:
                logging.warning(f"Failed to remove file {dump_path}: {e}")

        del db[file_reference]
        save_filedb(db)
        logging.info(f"Deleted reference '{file_reference}'")
    
    # ===== LOGGING SETUP =====
    class GuildAwareFormatter(logging.Formatter):
        """Formatter that includes guild context in log messages."""
        def format(self, record):
            guild_info = get_guild_context()
            guild_str = f' in "{guild_info["name"]}"' if guild_info['name'] != 'Unknown' else ""
            record.msg = str(record.msg)  # ensure message is string
            formatted = super().format(record)
            # insert guild info after timestamp and before [LEVEL]
            parts = formatted.split('] ', 1)
            if len(parts) == 2 and '[' in parts[0]:
                level_part = parts[1].split(']', 1)[0]
                remainder = parts[1].split('] ', 1)[1] if '] ' in parts[1] else parts[1]
                return f"{parts[0]}]{guild_str} [{level_part}] {remainder}"
            return formatted

    class GuildRoutingFileHandler(TimedRotatingFileHandler):
        """File handler that routes logs to guild-specific directories and a main log."""
        def __init__(self, base_dir="log"):
            self.base_dir = base_dir
            self.guild_handlers = {}  # cache of handlers per guild
            self.main_log_dir = f"{base_dir}/{datetime.now().strftime('%Y-%m-%d')}"
            os.makedirs(self.main_log_dir, exist_ok=True)
            main_log_file = f"{self.main_log_dir}/log_{datetime.now().strftime('%H-%M-%S')}.txt"
            super().__init__(main_log_file, when="h", interval=6, backupCount=14, encoding="utf-8")

        def get_guild_handler(self, guild_id, guild_name):
            """Get or create a handler for a specific guild."""
            key = str(guild_id)
            if key not in self.guild_handlers:
                guild_safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', guild_name)
                guild_log_dir = f"{self.base_dir}/{guild_safe_name}/{datetime.now().strftime('%Y-%m-%d')}"
                os.makedirs(guild_log_dir, exist_ok=True)
                guild_log_file = f"{guild_log_dir}/log_{datetime.now().strftime('%H-%M-%S')}.txt"
                handler = TimedRotatingFileHandler(guild_log_file, when="h", interval=6, backupCount=14, encoding="utf-8")
                handler.setFormatter(GuildAwareFormatter("%(asctime)s [%(levelname)s] %(message)s"))
                self.guild_handlers[key] = handler
            return self.guild_handlers[key]

        def emit(self, record):
            # always write to main log
            super().emit(record)
            # also write to guild-specific log if guild context is set
            guild_info = get_guild_context()
            if guild_info['id'] is not None:
                guild_handler = self.get_guild_handler(guild_info['id'], guild_info['name'])
                try:
                    guild_handler.emit(record)
                except Exception:
                    self.handleError(record)

        def doRollover(self):
            super().doRollover()
            try:
                if platform.system() == "Windows":
                    try:
                        subprocess.Popen("upload_log.bat", cwd=os.getcwd())
                        super().emit(logging.LogRecord(
                            "logging", logging.INFO, "", 0, "Triggered log upload batch file.", (), None
                        ))
                    except Exception as e:
                        pass
            except Exception as e:
                pass

    class PTKHandler(logging.Handler):
        lock = threading.Lock()
        
        def emit(self, record):
            try:
                msg = self.format(record)
                with self.lock:
                    from prompt_toolkit import print_formatted_text
                    print_formatted_text(msg)
            except Exception:
                self.handleError(record)

    # Initialize handlers
    routing_handler = GuildRoutingFileHandler(base_dir="log")
    console_handler = PTKHandler()

    # Set formatters
    routing_handler.setFormatter(GuildAwareFormatter("%(asctime)s [%(levelname)s] %(message)s"))
    console_handler.setFormatter(GuildAwareFormatter("%(asctime)s [%(levelname)s] %(message)s"))

    logging.basicConfig(level=logging.INFO, handlers=[routing_handler, console_handler])

    log = logging.getLogger(__name__)

    # ===== JSON HANDLING =====
    CONFIG_FILE = "config.json"
    
    def get_latest_userinfo_file():
        folder = "userdata"
        os.makedirs(folder, exist_ok=True)

        files = [f for f in os.listdir(folder) if f.endswith(".json")]
        if not files:
            return os.path.join(folder, "uinfo_latest.json")

        files.sort()
        return os.path.join(folder, files[-1])

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

    def create_config_wizard():
        """Interactive wizard to generate a basic config.json when none exists."""
        print("\nNo valid config.json found. Running interactive configuration wizard.")
        cfg = {"config": {}}
        # basic config entries
        cfg["config"]["version"] = input("Version (default 3.1.0): ").strip() or "3.1.0"
        cfg["config"]["author"] = input("Author name: ").strip() or "Unknown"
        cfg["config"]["default_target_channel_id"] = input("Default target channel ID (optional): ").strip()
        cfg["config"]["admin_role_id"] = input("Admin role ID (optional): ").strip()
        cfg["config"]["command_prefix"] = input("Command prefix (default !): ").strip() or "!"
        cfg["config"]["bot_test_channel_id"] = input("Bot test channel ID (optional): ").strip()
        cfg["config"]["ffmpeg_dir"] = input("FFmpeg directory (optional): ").strip()

        # guild-level section start empty
        cfg.setdefault("guilds", {})

        # MCS settings
        print("\nMinecraft server monitoring (optional) settings:")
        mcs = {}
        mcs["mcsAdress"] = input("MCS address: ").strip()
        try:
            mcs["mcsPort"] = int(input("MCS port (default 9260): ").strip() or 9260)
        except ValueError:
            mcs["mcsPort"] = 9260
        mcs["mcsChID"] = input("MCS channel ID (optional): ").strip()
        try:
            mcs["mcsDelay"] = int(input("MCS delay seconds (default 3600): ").strip() or 3600)
        except ValueError:
            mcs["mcsDelay"] = 3600
        mcs["mcsRoleID"] = input("MCS role ID (optional): ").strip()
        cfg["MCS"] = mcs

        save_json(CONFIG_FILE, cfg)
        print(f"Configuration saved to {CONFIG_FILE}. Please edit further if needed and rerun the bot.")
        return cfg

    def save_json(file_path, data):
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Failed to write to {file_path}: {e}")

    def load_userinfo():
        return load_json(USER_INFO_FILE, default={"discord_users": {}, "last_saved": None})

    def save_userinfo(data, session_id):
        os.makedirs("userdata", exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_path = f"userdata/{timestamp}-{session_id}.json"

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            logging.info(f"User info saved to {file_path}")
        except Exception as e:
            logging.error(f"Failed to write to {file_path}: {e}")

    config_data = load_json(CONFIG_FILE)
    if not config_data or "config" not in config_data:
        # attempt interactive wizard to create a new config
        try:
            config_data = create_config_wizard()
        except Exception as e:
            logging.error(f"Configuration wizard failed: {e}")
            sys.exit(1)
    # ensure basic structure exists
    config_data.setdefault("config", {})

    user_info = load_json(USER_INFO_FILE, default={"discord_users": {}, "last_saved": None})
    if not user_info or "discord_users" not in user_info:
        user_info = {"discord_users": {}, "last_saved": None}

    try:
        with open("token.config", "r", encoding="utf-8") as tf:
            token = tf.read().strip()
            if not token:
                logging.info("token.config is empty.")
                print("Would you like to try and decrypt the token (IF YOU ARE TONPALMUNMAIN, IF NOT FUCK OFF AND MAKE A NEW ONE)")
                result = input(">>>")
                if result == "y" or None:
                    # Cross-platform virtual environment activation
                    venv_script = os.path.join(".venv", "Scripts", "activate") if platform.system() == "Windows" else os.path.join(".venv", "bin", "activate")
                    print(f"USE> source {venv_script} && decrypt token.config.enc token.config" if platform.system() != "Windows" else f"USE> {venv_script} && decrypt token.config.enc token.config")
                    print("USE> python token/tokener.py")
                    # Alternatively, run directly with the venv's python
                    venv_python = os.path.join(".venv", "Scripts", "python.exe") if platform.system() == "Windows" else os.path.join(".venv", "bin", "python")
                    subprocess.run([venv_python, "token/tokener.py"])
    except FileNotFoundError:
        logging.critical("token.config not found. Create the file with your bot token.")
        sys.exit(1)
    # backward compatible default (global) for any guild that doesn't override
    target_channel_id = int(config_data["config"].get("default_target_channel_id") or 0) or None

    # per-guild silenced users/roles
    silenced_users = defaultdict(set)   # guild_id -> set(user_id)
    silenced_roles = defaultdict(set)   # guild_id -> set(role_id)
    recent_warnings = {}  # still global per-user

    # ===== MULTI-GUILD CONFIG HELPERS =====
    # store per-guild settings under config_data["guilds"]
    config_data.setdefault("guilds", {})

    def get_guild_config(guild_id: int) -> dict:
        return config_data["guilds"].setdefault(str(guild_id), {})

    def get_guild_setting(guild_id: int, key: str, default=None):
        return get_guild_config(guild_id).get(key, default)

    def set_guild_setting(guild_id: int, key: str, value):
        cfg = get_guild_config(guild_id)
        cfg[key] = str(value)
        save_json(CONFIG_FILE, config_data)

    def get_target_channel_id_for_guild(guild_id: int):
        # return a numeric channel id, falling back to global default
        val = get_guild_setting(guild_id, "target_channel_id")
        if val:
            try:
                return int(val)
            except ValueError:
                return None
        return target_channel_id

    # ===== CONFIG EDIT UTILS =====
    def set_config_value(dot_path: str, value):
        """Set a nested key in config_data given a dot-separated path."""
        parts = dot_path.split(".")
        d = config_data
        for part in parts[:-1]:
            if part not in d or not isinstance(d[part], dict):
                d[part] = {}
            d = d[part]
        d[parts[-1]] = value
        save_json(CONFIG_FILE, config_data)

    def get_config_value(dot_path: str):
        parts = dot_path.split(".")
        d = config_data
        for part in parts:
            if not isinstance(d, dict) or part not in d:
                return None
            d = d[part]
        return d

    def get_target_channel_for_guild(guild):
        cid = get_target_channel_id_for_guild(guild.id)
        return bot.get_channel(cid) if cid else None

    # ===== VERSION INFO =====
    VERSION = config_data["config"]["version"]
    AUTHOR = config_data["config"]["author"]
    CMD_PREFIX = config_data["config"]["command_prefix"]
    
    # ===== SERVER CONFIG =====
    ADMIN_ROLE_ID = int(config_data["config"].get("admin_role_id", 0)) or None
    BOTTEST_CHANNEL_ID = int(config_data["config"].get("bot_test_channel_id", 0)) or None
    
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

        if str(uid_or_name) in user_info["discord_users"]:
            user_data = user_info["discord_users"][str(uid_or_name)]
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
            async for member in guild.fetch_members(limit=None): 
                if member.bot:
                    continue

                roles = [r.name for r in member.roles if r.name != "@everyone"]
                old_data = user_info["discord_users"].get(str(member.id), {})
                user_info["discord_users"][str(member.id)] = {
                    "id": str(member.id),
                    "dispname": member.display_name,
                    "username": str(member),
                    "joined_at": str(member.joined_at) if member.joined_at else "Unknown",
                    "created_at": str(member.created_at),
                    "roles": ", ".join(roles),
                    "var1": old_data.get("var1", "N/A"),
                    "var2": old_data.get("var2", "N/A")
                }

        user_info["last_saved"] = now
        save_userinfo(user_info, session_id=session_id)
        logging.info(f"Auto-saved {len(user_info.get('discord_users', {}))} users at {now}")

    FEEDBACK_DIR = "feedback"
    FEEDBACK_FILE = f"{FEEDBACK_DIR}/{VERSION}_feedback.json"

    os.makedirs(FEEDBACK_DIR, exist_ok=True)

    def load_feedback():
        if not os.path.exists(FEEDBACK_FILE):
            return []
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_feedback(data):
        with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def create_feedback_entry(ctx, content: str, type_: str, file_path: str):
        data = load_feedback()
        prefix = format_version_prefix(VERSION)
        entry_number = len(data) + 1
        entry_id = f"{prefix}{entry_number:02d}"

        entry = {
            "id": entry_id,
            "type": type_,
            "version": VERSION,
            "reporter": {
                "name": ctx.author.name,
                "id": ctx.author.id
            },
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "ACTIVE",
            "delete_reason": None,
            "deleted_by": None
        }

        data.append(entry)
        save_feedback(data)
        return entry_id

    def format_version_prefix(version: str) -> str:
        return version.replace(".", "")
    
    # ===== MCS =====
    BEDROCK_HOST = config_data["MCS"]["mcsAdress"] or "multi-nor.gl.at.ply.gg"
    BEDROCK_PORT = config_data["MCS"]["mcsPort"] or 5355
    ServerUpdateChannelID = config_data["MCS"]["mcsChID"] or 1421497953834631319
    MCSDURATION = int(config_data["MCS"]["mcsDelay"]) or 3600  # in seconds
    MCSROLEID = int(config_data["MCS"]["mcsRoleID"]) or 1394542459538640977

    # ===== GLOBALS =====
    bot_started = False
    bot = None
    bot_loop = None
    manual_shutdown = False
    filtered_guild_ids = set()  # for fcsguild log filtering

    # ===== MESSAGES =====
    startmessage: str | None = None
    stop_message: str | None = None  # renamed from stopmessage for consistency

    # ===== AUDIO =====
    guild_queues = {}
    guild_paused = {}

    def get_queue(ctx):
        return guild_queues.setdefault(ctx.guild.id, [])

    def get_paused(ctx):
        return guild_paused.setdefault(ctx.guild.id, False)

    def probe_ffmpeg(input_url: str, ffmpeg_exec: str, timeout: int = 12):
        """Run a short ffmpeg probe to capture stderr for diagnostics."""
        cmd = [
            ffmpeg_exec,
            "-v", "error",
            "-i", input_url,
            "-t", "1",
            "-f", "null",
            "-"
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return proc.returncode, proc.stderr.strip()
        except subprocess.TimeoutExpired:
            return None, "probe timeout"
        except FileNotFoundError:
            return None, f"ffmpeg executable not found: {ffmpeg_exec}"
        except Exception as e:
            return None, f"probe exception: {e}"

    async def play_next(ctx):
        queue = get_queue(ctx)
        vc = ctx.guild.voice_client
        if not vc or not queue:
            return

        item = queue.pop(0)
        source_type, source = item

        import shutil
        ffmpeg_exec = shutil.which("ffmpeg")
        
        # Fallback paths for different OSes
        if not ffmpeg_exec:
            if platform.system() == "Windows":
                ffmpeg_exec = r"C:\Program Files\FFmpeg\bin\ffmpeg.exe"
            elif platform.system() == "Darwin":  # macOS
                ffmpeg_exec = "/usr/local/bin/ffmpeg"
            else:  # Linux and other Unix-like systems
                ffmpeg_exec = "/usr/bin/ffmpeg"
        
        logging.info(f"Using ffmpeg executable: {ffmpeg_exec}")

        try:
            if source_type == "file":
                if not os.path.exists(source):
                    await ctx.send(f"File not found: `{source}`")
                    return

                ffmpeg_opts = {
                    "before_options": "-nostdin",
                    "options": "-vn"
                }
                audio_source = FFmpegPCMAudio(
                    source,
                    **ffmpeg_opts,
                    executable=ffmpeg_exec
                )

            else:
                ytdlp_opts = {
                    "format": "bestaudio[ext=m4a]/bestaudio/best",
                    "quiet": True,
                    "no_warnings": True,
                    "default_search": "auto",
                    "source_address": "0.0.0.0",
                    "noplaylist": True,
                    "extract_flat": False,
                }
                ffmpeg_opts = {
                    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
                    "options": "-vn",
                }
                loop = asyncio.get_running_loop()

                def blocker():
                    with yt_dlp.YoutubeDL(ytdlp_opts) as ytdl:
                        return ytdl.extract_info(source, download=False)

                try:
                    info = await asyncio.wait_for(loop.run_in_executor(None, blocker), timeout=25)
                except asyncio.TimeoutError:
                    await ctx.send(f"Timed out while resolving URL: `{source}`")
                    logging.error(f"yt-dlp timed out for: {source}")
                    return
                except Exception as e:
                    await ctx.send(f"Failed to resolve URL: `{e}`")
                    logging.exception(f"yt-dlp extraction failed for {source}: {e}")
                    return

                if "entries" in info and info["entries"]:
                    info = info["entries"][0]

                stream_url = info.get("url")
                if not stream_url:
                    await ctx.send("Could not get a playable audio URL from yt-dlp result.")
                    logging.error(f"No playable url in yt-dlp info for {source}: {info}")
                    return

                retcode, stderr = probe_ffmpeg(stream_url, ffmpeg_exec)
                if retcode is None or retcode != 0:
                    logging.error(f"ffmpeg probe failed (ret={retcode}): {stderr}")
                    await ctx.send(f"ffmpeg probe failed. See logs for details.")
                    return

                audio_source = FFmpegPCMAudio(
                    stream_url,
                    **ffmpeg_opts,
                    executable=ffmpeg_exec
                )

            def _after_play(err):
                if err:
                    logging.exception(f"Error during playback: {err}")
                try:
                    asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)
                except Exception:
                    logging.exception("Failed to schedule play_next after track end.")

            vc.play(audio_source, after=_after_play)

        except Exception as e:
            logging.exception(f"Unhandled error in play_next: {e}")
            try:
                asyncio.get_running_loop().call_later(1, lambda: asyncio.create_task(play_next(ctx)))
            except Exception:
                logging.exception("Failed to schedule retry of play_next")
            return
    
    # ===== TTS =====
    async def say_in_vc(bot, text: str, ovr: int = 1):
        """Speaks text in the currently connected voice channel using gTTS."""
        try:
            if not bot.voice_clients:
                print("Not connected to any voice channel.")
                return

            vc = bot.voice_clients[0]
            if not vc or not vc.is_connected():
                print("Voice client not connected.")
                return

            logging.info(f"Generating TTS: \"{text}\" (ovr={ovr})")
            
            try:
                tts = gTTS(text=text, lang="en")
            except Exception as e:
                logging.info(f"Language 'en' failed ({e}), using fallback 'en-us'.")
                tts = gTTS(text=text, lang="en-us")

            now = datetime.now()
            timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
            tts_file = "tts_output/" + timestamp + ".mp3"
            tts.save(tts_file)
            print(f"Saved TTS file as {tts_file}")

            source = discord.FFmpegPCMAudio(tts_file)
            
            if ovr == 0:
                if vc.is_playing():
                    vc.stop()
                vc.play(source, after=lambda e: logging.info("Finished speaking."))
            else:
                logging.info("Overlay mode: playing without stopping current audio.")
                vc.play(source, after=lambda e: logging.info("Finished speaking."))

            logging.info(f"Speaking in {vc.channel.name}: {text}")

        except Exception as e:
            logging.info(f"Error in say_in_vc: {e}")

    # ===== MISC =====
    async def fetch_app_emojis(bot: commands.Bot):
        route = discord.http.Route(
            "GET",
            "/applications/{application_id}/emojis",
            application_id=bot.application_id
        )

        data = await bot.http.request(route)

        emojis_by_name = {}
        emojis_by_id = {}

        for e in data:
            emoji = discord.PartialEmoji.from_dict(e)
            emojis_by_name[e["name"]] = emoji
            emojis_by_id[int(e["id"])] = emoji

        return emojis_by_name, emojis_by_id
    
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

    async def stopsession(message: str = None, guild=None): # FOR INTERNAL USE ONLY
        """Shut down the bot and optionally post a message to a specific guild's configured channel.
        If `guild` is None the message is broadcast to every guild using its configured channel.
        """
        global bot_started
        if not bot_started:
            logging.info("Bot is not running.")
            return

        logging.info("Bot stopped. Closing connection...")
        if stop_message and message:
            if guild is not None:
                channel = get_target_channel_for_guild(guild)
                if channel:
                    try:
                        await channel.send(message)
                        logging.info(f"Sent stop message to channel ID: {channel.id} for guild {guild.id}")
                    except Exception as e:
                        logging.error(f"Failed to send stop message in guild {guild.id}: {e}")
            else:
                # broadcast to all guilds
                for g in bot.guilds:
                    channel = get_target_channel_for_guild(g)
                    if channel:
                        try:
                            await channel.send(message)
                            logging.info(f"Sent stop message to channel ID: {channel.id} for guild {g.id}")
                        except Exception as e:
                            logging.error(f"Failed to send stop message in guild {g.id}: {e}")
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
    def parse_duration(dur_str: str) -> Optional[timedelta]:
        """Support ms, s/sec, m/min, h/hr, d, w (returns timedelta or None)."""
        s = dur_str.strip().lower()
        m = re.match(r"^(\d+)\s*(ms|s|sec|m|min|h|hr|d|w)$", s)
        if not m:
            return None
        value, unit = m.groups()
        value = int(value)
        units = {
            "ms": 0.001, "s": 1, "sec": 1,
            "m": 60, "min": 60,
            "h": 3600, "hr": 3600,
            "d": 86400, "w": 604800
        }
        seconds = value * units.get(unit, 0)
        return timedelta(seconds=seconds)

    hg = Homoglyphs()
    custom_translations = {}
    
    def normalize_message(text: str) -> str:
        text = str(text)

        def is_thai(text: str) -> bool:
            return all('\u0E00' <= c <= '\u0E7F' or c.isspace() for c in text if c.strip())
        
        if is_thai(text):
            return text.strip()

        def regional_to_letter(char):
            code = ord(char)
            if 0x1F1E6 <= code <= 0x1F1FF:
                return chr(code - 0x1F1E6 + ord('a'))
            return char

        text = ''.join(regional_to_letter(c) for c in text)

        text = unidecode(text)
        text = unicodedata.normalize("NFKC", text).lower()
        text = re.sub(r'[\s\W_]+', '', text)
        text = ''.join(c for c in text if not unicodedata.combining(c))
        text = re.sub(r'[\u200B-\u200F\uFE00-\uFE0F\u2060-\u206F]', '', text)
        text = ''.join(c for c in text if unicodedata.category(c)[0] != 'C')
        text = re.sub(r'[\s\W_]+', '', text)
        
        replacements = str.maketrans({
            '0': 'o',
            '1': 'i',
            '2': 'z',
            '3': 'e',
            '4': 'a',
            '5': 's',
            '6': 'g',
            '7': 't',
            '8': 'b',
            '9': 'g'
        })
        text = text.translate(replacements)
        for a, b in custom_translations.items():
            text = text.replace(a, b)

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
    bwdisable = True
    BANNED_WORDS_FILE = "banned_words.json"

    def load_banwjson(type: str):
        banned = set()
        whitelist = set()
        translations = {}

        if os.path.exists(BANNED_WORDS_FILE):
            try:
                with open(BANNED_WORDS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    banned = set(data.get("banned_words", []))
                    whitelist = set(data.get("whitelisted_words", []))
                    translations = dict(data.get("translation", {}))
            except (json.JSONDecodeError, OSError) as e:
                logging.info(f"Error loading banned words file: {e}")

        match type.lower():
            case "banned":
                return banned
            case "whitelist":
                return whitelist
            case "translation":
                return translations
            case _:
                return banned


    def save_banwjson(type: str, data):
        if os.path.exists(BANNED_WORDS_FILE):
            try:
                with open(BANNED_WORDS_FILE, "r", encoding="utf-8") as f:
                    current = json.load(f)
            except (json.JSONDecodeError, OSError):
                current = {}
        else:
            current = {}

        current.setdefault("banned_words", [])
        current.setdefault("whitelisted_words", [])
        current.setdefault("translation", {})

        t = type.lower()
        if t == "banned":
            current["banned_words"] = sorted(list(data))
        elif t == "whitelist":
            current["whitelisted_words"] = sorted(list(data))
        elif t == "translation":
            current["translation"] = dict(data)
        else:
            raise ValueError("mode must be 'banned', 'whitelist', or 'translation'")

        with open(BANNED_WORDS_FILE, "w", encoding="utf-8") as f:
            json.dump(current, f, ensure_ascii=False, indent=4)

    BANNED_WORDS = load_banwjson("banned")
    WHITELISTED_WORDS = load_banwjson("whitelist")
    save_banwjson("banned", BANNED_WORDS)
    save_banwjson("whitelist", WHITELISTED_WORDS)

    PENDING_MOD = {}
    
    async def setstat(stat: str, text: str):
        stat = stat.lower()

        if stat in ["play", "game"]:
            activity = discord.Game(text)

        elif stat == "watch":
            activity = discord.Activity(type=discord.ActivityType.watching, name=text)

        elif stat == "listen":
            activity = discord.Activity(type=discord.ActivityType.listening, name=text)

        elif stat == "compete":
            activity = discord.Activity(type=discord.ActivityType.competing, name=text)

        elif stat == "stream":
            activity = discord.Streaming(name=text, url=text)

        else:
            print("Invalid status type. Use: play, watch, listen, compete, stream")
            return

        await bot.change_presence(activity=activity)


    # ===== BOT CREATION =====
    def create_bot():
        intents = discord.Intents.default()
        intents.messages = True
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        client = discord.Client(intents=intents)
        bot = commands.Bot(command_prefix=CMD_PREFIX, intents=intents, help_command=None)
        
        # ===== BOT EVENTS =====
        @bot.event
        async def on_ready():
            global startmessage
            logging.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
            # make sure every guild has an entry in the persistent config
            for guild in bot.guilds:
                cfg = get_guild_config(guild.id)
                if "target_channel_id" not in cfg and target_channel_id:
                    cfg["target_channel_id"] = str(target_channel_id)
            save_json(CONFIG_FILE, config_data)
            
            stattype = config_data["config"]["stattype"]
            stattext = config_data["config"]["stattext"]
            
            try:
                await setstat(stattype, stattext)
            except:
                logging.error("Invalid status")
            
            if startmessage is None:
                logging.info("No startmessage set.")
                return

            # send startup message to each guild's configured channel
            for guild in bot.guilds:
                channel = get_target_channel_for_guild(guild)
                if channel:
                    try:
                        await channel.send(startmessage)
                        logging.info(f"Sent startup message to channel ID: {channel.id} for guild {guild.id}")
                    except Exception as e:
                        logging.error(f"Failed to send startup message in guild {guild.id}: {e}")

            if not auto_save_users.is_running():
                auto_save_users.start()
                
            await auto_save_users()
                
        @bot.event
        async def on_guild_join(guild):
            # ensure configuration entry exists for the guild (copy global defaults)
            cfg = config_data.setdefault("guilds", {})
            if str(guild.id) not in cfg:
                cfg[str(guild.id)] = {"target_channel_id": config_data["config"].get("default_target_channel_id")}
                save_json(CONFIG_FILE, config_data)
                logging.info(f"Initialized configuration for new guild {guild.id}")

        @bot.event
        async def on_message(message):
            # set guild context for logging
            if message.guild:
                set_guild_context(message.guild.id, message.guild.name)
            
            logging.info(
                f"{message.id}:{message.author} ({message.author.id}) in #{message.channel.name} ({message.channel.id}): {message.content}"
            )

            if message.author == bot.user:
                return

            ctx = await bot.get_context(message)
            app_info = await bot.application_info()
            owner = app_info.owner
            
            # === Normalize ===
            content = normalize_message(message.content)
            content = re.sub(r'[^a-z0-9]', '', content)
            content = re.sub(r'(.)\1{2,}', r'\1', content)
            debug(content, "Content (Before Moderation)")
            
            # === Detection ===
            banned = load_banwjson("banned")
            whitelist = {normalize_message(w) for w in load_banwjson("whitelist")}

            user = message.author
            # check per-guild silenced lists
            guild_id = message.guild.id if message.guild else None
            if (guild_id and ((user.id in silenced_users.get(guild_id, set())) or any(r.id in silenced_roles.get(guild_id, set()) for r in user.roles))) and user.id != owner.id:
                try:
                    await message.delete()
                    now = time.time()
                    last_warn = recent_warnings.get(user.id, 0)
                    if now - last_warn >= 5:
                        recent_warnings[user.id] = now
                        warn_msg = get_bot_message("silence", "warn", mention=user.mention)
                        await message.channel.send(warn_msg, delete_after=3)
                except discord.Forbidden:
                    print(f"Cannot delete message or send warning in {message.channel}")
                return
        
            def is_banned(text: str) -> bool:
                for word in banned:
                    if word in text and not any(white in text for white in whitelist):
                        return True
                return False

            if (
                is_banned(content)
                and not (ctx.command and ctx.command.name in ["banword", "rmword","whitelistword","rmwhitelistword"]) and not bwdisable
            ):
                if any(role.id == 1411139316171931738 for role in message.author.roles):
                    logging.info(f"User {message.author} has GOD role, not timeouted.")
                    return

                try:
                    await message.delete()
                    await message.author.timeout(
                        timedelta(minutes=5),
                        reason="You said a banned word."
                    )
                    await message.channel.send(
                        get_bot_message("moderation", "timeout_message", mention=message.author.mention)
                    )
                    logging.info(f"Timed out: {message.author} for '{message.content}'")
                except discord.Forbidden:
                    await message.channel.send(
                        get_bot_message("moderation", "timeout_no_permission", mention=ctx.author.mention)
                    )
                    logging.error("Bot doesn't have permission to timeout this user.")
                except Exception as e:
                    logging.error(f"Error: {e}")
                    
            if any(word in content.lower() for word in ["goodboy", "good boy"]) and bot.user.mentioned_in(message):
                try:
                    await message.channel.send(get_bot_message("responses", "goodboy", mention=message.author.mention))
                    logging.info(f"Sent Goodboy response to {message.author}")
                except Exception as e:
                    logging.error(f"Error sending good boy response: {e}")

            if any(word in content.lower() for word in ["badboy", "bad boy"]) and bot.user.mentioned_in(message):
                try:
                    await message.channel.send(get_bot_message("responses", "badboy", mention=message.author.mention))
                    logging.info(f"Sent Badboy response to {message.author}")
                except Exception as e:
                    logging.error(f"Error sending 'Insulting' response: {e}")

            await bot.process_commands(message)

            if ctx.valid:
                return

        @bot.event
        async def on_message_edit(before, after):
            # set guild context for logging
            if after.guild:
                set_guild_context(after.guild.id, after.guild.name)
            
            if after.author.bot:
                return

            ctx = await bot.get_context(after)
            if ctx.valid:
                return

            message = after
            bmessage = before
            
            logging.info(
                f"{message.id}:{message.author} ({message.author.id}) in #{message.channel.name} ({message.channel.id}) Edited from ({bmessage.content}) to {message.content}"
            )
                        
            content = normalize_message(after.content)
            if (
                any(word in content for word in BANNED_WORDS)
                and not (ctx.command and ctx.command.name in ["banword", "rmword"])
                and not (after.author == bot.user)
                and not any(role.id == 1411139316171931738 for role in after.author.roles)
            ):
                try:
                    await after.delete()
                    await after.author.timeout(timedelta(minutes=5), reason="You tried to sneak in a banned word by editing, you dumb fuck.")
                    await after.channel.send(get_bot_message("moderation", "timeout_edit", mention=after.author.mention))
                    logging.info(f"[EDIT] Timed out: {after.author} for '{after.content}'")
                except discord.Forbidden:
                    await after.channel.send(get_bot_message("moderation", "timeout_no_permission"))
                    logging.error("[EDIT] Bot doesn't have permission to timeout this sneaky user.")
                except Exception as e:
                    logging.error(f"[EDIT] Error: {e}")
                    
        @bot.event
        async def on_voice_state_update(member, before, after):
            set_guild_context(member.guild.id, member.guild.name)
            if before.channel is None and after.channel is not None:
                logging.info(f"{member} joined {after.channel.name}")
            if before.channel is not None and after.channel is None:
                logging.info(f"{member} left {before.channel.name}")
            if before.channel != after.channel and before.channel and after.channel:
                logging.info(f"{member} moved from {before.channel.name} to {after.channel.name}")
            if before.self_mute != after.self_mute:
                if after.self_mute:
                    logging.info(f"{member} muted themselves")
                else:
                    logging.info(f"{member} unmuted themselves")
            if before.self_deaf != after.self_deaf:
                if after.self_deaf:
                    logging.info(f"{member} deafened themselves")
                else:
                    logging.info(f"{member} undeafened themselves")
            if before.mute != after.mute:
                if after.mute:
                    logging.info(f"{member} was SERVER MUTED")
                else:
                    logging.info(f"{member} was SERVER UNMUTED")
            if before.deaf != after.deaf:
                if after.deaf:
                    logging.info(f"{member} was SERVER DEAFENED")
                else:
                    logging.info(f"{member} was SERVER UNDEAFENED")     
                           
        @bot.event
        async def on_member_join(member):
            set_guild_context(member.guild.id, member.guild.name)
            channel = get_target_channel_for_guild(member.guild)
            if channel:
                guild_owner_mention = member.guild.owner.mention
                bot_mention = bot.user.mention
                bot_owner_user = await bot.fetch_user("1260198579067420722")
                bot_owner_mention = bot_owner_user.mention

                embed = discord.Embed(
                    title="🎉 Welcome!",
                    description=(
                        f"Welcome to the server, {member.mention}! 🎈\n\n"
                        f"👽 {guild_owner_mention} (Server Owner)\n"
                        f"🤖 {bot_mention} (Bot)\n"
                        f"😎 {bot_owner_mention} (Bot Owner)\n\n"
                        f"Of course this is written by {bot_owner_mention}."
                        f" Enjoy your stay!"
                    ),
                    color=discord.Color.green()
                )
                embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
                embed.set_footer(text=f"BestBotEver v.{VERSION}")

                await channel.send(embed=embed)
        async def on_member_remove(member):
            set_guild_context(member.guild.id, member.guild.name)
            logging.info(f"{member} left the server")

        @bot.event
        async def on_member_update(before, after):
            set_guild_context(before.guild.id, before.guild.name)
            if before.communication_disabled_until != after.communication_disabled_until:
                
                if after.communication_disabled_until is not None:
                    until = after.communication_disabled_until.isoformat()
                    logging.info(f"{after} was timed out until {until}")

                elif before.communication_disabled_until is not None and after.communication_disabled_until is None:
                    logging.info(f"{after} timeout ended")

        @bot.event
        async def on_reaction_add(reaction, user):
            logging.info(f"{user} added {reaction.emoji} in #{reaction.message.channel}")

        @bot.event
        async def on_reaction_remove(reaction, user):
            logging.info(f"{user} removed {reaction.emoji}")

        @bot.event
        async def on_reaction_clear(message, reactions):
            logging.info(f"Reactions cleared in #{message.channel}")
            
        @bot.event
        async def on_guild_channel_create(channel):
            logging.info(f"Channel created: {channel} ({channel.id})")

        @bot.event
        async def on_guild_channel_delete(channel):
            logging.info(f"Channel deleted: {channel} ({channel.id})")

        @bot.event
        async def on_guild_channel_update(before, after):
            logging.info(f"Channel updated: {before} > {after}")
            
        @bot.event
        async def on_guild_role_create(role):
            logging.info(f"Role created: {role}")

        @bot.event
        async def on_guild_role_delete(role):
            logging.info(f"Role deleted: {role}")

        @bot.event
        async def on_guild_role_update(before, after):
            logging.info(f"Role updated: {before.name}")

        @bot.event
        async def on_thread_create(thread):
            logging.info(f"Thread created: {thread.name}")

        @bot.event
        async def on_thread_delete(thread):
            logging.info(f"Thread deleted: {thread.name}")

        @bot.event
        async def on_thread_update(before, after):
            logging.info(f"Thread updated: {before.name}")

        @bot.event
        async def on_thread_join(thread):
            logging.info(f"Bot joined thread: {thread.name}")

        @bot.event
        async def on_invite_create(invite):
            logging.info(f"Invite created: {invite.code}")

        @bot.event
        async def on_invite_delete(invite):
            logging.info(f"Invite deleted: {invite.code}")

        @bot.event
        async def on_member_ban(guild, user):
            set_guild_context(guild.id, guild.name)
            logging.info(f"{user} was banned from {guild.name}")

        @bot.event
        async def on_member_unban(guild, user):
            set_guild_context(guild.id, guild.name)
            logging.info(f"{user} was unbanned from {guild.name}")

        @bot.event
        async def on_guild_emojis_update(guild, before, after):
            logging.info(f"Emoji update in {guild.name}")

        @bot.event
        async def on_guild_stickers_update(guild, before, after):
            logging.info(f"Sticker update in {guild.name}")
    
        @bot.command(name="help")
        async def help_cmd(ctx, command_name: str = None):
            """Show command list or details for a specific command."""
            logging.info(f"[{ctx.author} ({ctx.author.id})] Called help with: {command_name}")

            if command_name:
                cmd = bot.get_command(command_name)
                if not cmd:
                    await ctx.send(f"No command named `{command_name}` found.")
                    return

                usage = cmd.signature if hasattr(cmd, "signature") else ""
                desc = cmd.help or "No description available."
                await ctx.send(f"**{CMD_PREFIX}{cmd.name} {usage}**\n{desc}")
                return

            embed = discord.Embed(title="BestBotEver Command Reference", color=discord.Color.blurple())
            embed.add_field(
                name="General",
                value=(
                    f"`{CMD_PREFIX}repeat [message]` - Repeat your message\n"
                    f"`{CMD_PREFIX}thx` - Replies `np`\n"
                    f"`{CMD_PREFIX}agreewme [message]` - Agree with message\n"
                    f"`{CMD_PREFIX}disagreewme [message]` - Disagree with message\n"
                    f"`{CMD_PREFIX}version` - Show bot version"
                ),
                inline=False
            )

            embed.add_field(
                name="For Debugging",
                value=(
                    f"`{CMD_PREFIX}banword [word]` - Add banned word\n"
                    f"`{CMD_PREFIX}rmword [word]` - Remove banned word\n"
                    f"`{CMD_PREFIX}listbanword` - List banned words\n"
                    f"`{CMD_PREFIX}forgive @user` - Remove timeout\n"
                    f"`{CMD_PREFIX}pewthyself` - Shutdown bot (owner)\n"
                    f"`{CMD_PREFIX}deplete [ms|sec|min|hr|d] [value]` - Delayed shutdown\n"
                    f"`{CMD_PREFIX}seelog [date] [filename]` or `seelog recent` - View logs\n"
                    f"`{CMD_PREFIX}edit <path> <value>` - Edit config.json key (owner)\n"
                    f"`{CMD_PREFIX}cfch [channel_id|current]` - Change target channel for this guild (admin)"
                ),
                inline=False
            )

            embed.add_field(
                name="Minecraft",
                value=(
                    f"`{CMD_PREFIX}mcstat [tagmcr]` - Check Bedrock server status\n"
                    f"`(Automatic server monitoring is also active)`"
                ),
                inline=False
            )

            embed.add_field(
                name="Feedback / Polls",
                value=(
                    f"`{CMD_PREFIX}bugreport <text>` - Submit a bug\n"
                    f"`{CMD_PREFIX}featurerequest <text>` - Submit a feature\n"
                    f"`{CMD_PREFIX}listfeedback [type]` - List feedback\n"
                    f"`{CMD_PREFIX}mkpoll <question> <opt1> <opt2> ... <duration>` - Create poll"
                ),
                inline=False
            )

            embed.set_footer(text=f"Use `{CMD_PREFIX}help <command>` for details on a specific command.")
            await ctx.send(embed=embed)

        @bot.command(name="saveuinf")
        @commands.has_permissions(administrator=True)
        async def saveall(ctx):
            """Trigger a manual save of user information (runs auto-save)."""
            await auto_save_users()
            await ctx.send("Manual save completed.")

        @bot.command(name="userinfo")
        async def userinfo_cmd(ctx, action: str = None, key: str = None, *, value: str = None):
            """View or edit stored user info. Usage: !userinfo view|edit|roles ..."""
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
            """Edit a user's var1/var2 by ID or display name. Usage: !editvar <ID|dispname> <var1> <var2>"""
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
            """Show diagnostic session/system information (owner only)."""
            try:
                dtc = datetime.now()
                dtc_utc = datetime.utcnow()
                
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

                try:
                    import pynvml
                    pynvml.nvmlInit()

                    count = pynvml.nvmlDeviceGetCount()
                    if count == 0:
                        gpu_info.append("No GPU detected")
                    else:
                        for i in range(count):
                            handle = pynvml.nvmlDeviceGetHandleByIndex(i)

                            name = pynvml.nvmlDeviceGetName(handle).decode()
                            mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
                            util = pynvml.nvmlDeviceGetUtilizationRates(handle)

                            gpu_info.append(
                                f"{name} ({mem.total // (1024**2)}MB) - {util.gpu:.1f}% load"
                            )

                except Exception:
                    gpu_info.append("Error retrieving GPU info")


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

                cpu_temp_str = "N/A"
                gpu_temp_str = "N/A"

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
                        f"**Message Version:** `{get_bot_message("v")}"
                    ),
                    inline=False,
                )
                embed.add_field(
                    name="CPU",
                    value=f"**Cores:** `{cpu_count}`\n**Frequency:** `{cpu_freq.current:.2f} MHz`\n**Usage:** `{cpu_usage}%`",
                    inline=False,
                )
                
                embed.add_field(
                    name="Temperature",
                    value=f"**CPU:** `{cpu_temp_str}`\n**GPU:** `{gpu_temp_str}`",
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
                
        @bot.command(name="exec")
        @commands.is_owner()
        async def exec_str(ctx, *, code: str = None):
            """execute Python code (owner only). Usage: !exec <code>"""
            if not code:
                await ctx.send("Usage: `!exec <code>`")
                return
            
            try:
                result = exec(code)
                await ctx.send(f"Result: `{result}`")
                logging.info(f"[EXEC] {ctx.author} executed: {code}")
            except Exception as e:
                await ctx.send(f"Error: `{type(e).__name__}: {e}`")
                logging.error(f"[EXEC] Error by {ctx.author}: {e}")
        
        @bot.command(name="bitchvariable")
        async def bitch(ctx):
            bitch = ctx.guild.get_member(913994744953196614)
            await ctx.send(f"Bitch variable set to: {bitch.mention}")
            await ctx.send("bozo bitch")
                    
        @bot.command(name="banword")
        @commands.has_permissions(administrator=True)
        async def ban_word(ctx, *, word: str):
            """Add a word to the banned-words list (admin only)."""
            word = word.lower().strip()
            if word in BANNED_WORDS:
                await ctx.send(get_bot_message("moderation", "banned_word_exists", word=word))
            else:
                BANNED_WORDS.add(word)
                save_banwjson("banned", BANNED_WORDS)
                await ctx.send(get_bot_message("moderation", "banned_word_added", word=word))
                logging.info(f"Added banned word: {word}")

        @bot.command(name="rmword")
        @commands.has_role(ADMIN_ROLE_ID)
        @commands.has_permissions(administrator=True)
        async def remove_ban_word(ctx, *, word: str):
            """Remove a word from the banned list (admin only)."""
            word = word.lower().strip()
            if word in BANNED_WORDS:
                BANNED_WORDS.remove(word)
                save_banwjson("banned", BANNED_WORDS)
                await ctx.send(get_bot_message("moderation", "banned_word_removed", word=word))
                logging.info(f"Removed banned word: {word}")
            else:
                await ctx.send(get_bot_message("moderation", "banned_word_not_exists", word=word))

        @bot.command(name="listbanword")
        @commands.has_permissions(administrator=True)
        async def list_ban_words(ctx):
            """List all currently banned words (admin only)."""
            if BANNED_WORDS:
                words = ", ".join(sorted(BANNED_WORDS))
                await ctx.send(get_bot_message("moderation", "banned_list", words=words))
            else:
                await ctx.send(get_bot_message("moderation", "no_banned_words"))
                
        @bot.command()
        @commands.is_owner()
        async def whitelistword(ctx, *, word: str):
            """Add a word to the whitelist (owner only)."""
            word = word.lower()
            WHITELISTED_WORDS.add(word)
            save_banwjson("whitelist", WHITELISTED_WORDS)
            await ctx.send(get_bot_message("whitelist", "added", word=word))


        @bot.command()
        @commands.is_owner()
        async def rmwhitelistword(ctx, *, word: str):
            """Remove a word from the whitelist (owner only)."""
            word = word.lower()
            if word in WHITELISTED_WORDS:
                WHITELISTED_WORDS.remove(word)
                save_banwjson("whitelist", WHITELISTED_WORDS)
                await ctx.send(get_bot_message("whitelist", "removed", word=word))
            else:
                await ctx.send(get_bot_message("whitelist", "not_exists", word=word))


        @bot.command()
        @commands.is_owner()
        async def listwhitelistword(ctx):
            """List all words in the whitelist (owner only)."""
            if WHITELISTED_WORDS:
                words = ", ".join(sorted(WHITELISTED_WORDS))
                await ctx.send(get_bot_message("whitelist", "current", words=words))
            else:
                await ctx.send(get_bot_message("whitelist", "empty"))
                

        @bot.command(name="forgive")
        @commands.has_permissions(moderate_members=True)
        async def forgive(ctx, member: discord.Member):
            """Remove a timeout from a member (requires moderate_members permission)."""
            try:
                await member.edit(timed_out_until=None)
                await ctx.send(get_bot_message("moderation", "timeout_removed", mention=member.mention))
            except discord.Forbidden:
                await ctx.send(get_bot_message("moderation", "timeout_no_permission"))
            except discord.HTTPException as e:
                await ctx.send(get_bot_message("errors", "failed_to_send", error=e))

        @bot.command(name="pewthyself")
        @commands.is_owner()
        async def sessionend(ctx):
            """Shut down the bot gracefully (owner only)."""
            await stopsession(get_bot_message("shutdown", mention=ctx.author.mention), guild=ctx.guild)

        @bot.command(name="version")
        async def version_command(ctx):
            """Show the bot version."""
            await ctx.send(f"Bot version: {VERSION}\nMessage.json Version {get_bot_message("v")}")

        @bot.command(name="agreewme")
        @commands.is_owner()
        async def agree_with_me(ctx, *, message: str = None):
            """Respond with agreement to the provided message (owner only)."""
            if message:
                await ctx.send(get_bot_message("responses", "agree", mention=ctx.author.mention, message=message))
            else:
                await ctx.send(get_bot_message("responses", "agree_no_msg", mention=ctx.author.mention, message=message))

        @bot.command(name="disagreewme")
        async def disagree_with_me(ctx, *, message: str = None):
            """Respond with disagreement to the provided message."""
            if message:
                await ctx.send(get_bot_message("responses", "disagree", mention=ctx.author.mention, message=message))
            else:
                await ctx.send(get_bot_message("responses", "disagree_no_msg", mention=ctx.author.mention, message=message))

        @bot.command(name="repeat")
        @commands.is_owner()
        async def repeat(ctx, *, message: str):
            """Repeat the given message verbatim (owner only)."""
            logging.info(f"[{ctx.author} ({ctx.author.id})] Called repeat with message: {message}")
            await ctx.send(message)

        @bot.command(name="deplete")
        @commands.is_owner()
        async def deplete(ctx, type: str, value: int):
            """Countdown then shut down the bot. Usage: !deplete [ms|sec|min|hr|d] [value] (owner only)."""
            logging.info(f"[{ctx.author} ({ctx.author.id})] Called deplete with type: {type}, value: {value}")
            units = {"ms": 0.001, "sec": 1, "min": 60, "hr": 3600, "d": 86400}
            type = type.lower()
            if type not in units:
                await ctx.send(get_bot_message("errors", "invalid_duration"))
                return
            seconds = value * units[type]
            await ctx.send(get_bot_message("responses", "deplete_countdown", seconds=seconds))
            await asyncio.sleep(seconds)
            await stopsession(get_bot_message("shutdown", mention=ctx.author.mention), guild=ctx.guild)
            global manual_shutdown
            manual_shutdown = True

        @bot.command(name="edit")
        @commands.is_owner()
        async def edit_config(ctx, path: str, *, value: str):
            """Edit a value in config.json.
            Usage: !edit config.version 1.2.3
            The path is dot-separated and the value is stored as text.
            (Owner only)
            """
            try:
                set_config_value(path, value)
                await ctx.send(f"Config updated: {path} = {value}")
            except Exception as e:
                await ctx.send(f"Failed to update config: {e}")

        @bot.command(name="cfch")
        @commands.has_permissions(administrator=True)
        async def cfch(ctx, channel_id: str):
            """Change the target channel for this server. Use 'current' to set to the invoking channel (admin only)."""
            if channel_id.lower() == "current":
                new_id = ctx.channel.id
            else:
                try:
                    new_id = int(channel_id)
                except ValueError:
                    await ctx.send("Please provide a valid channel ID or use current.")
                    return
            channel = bot.get_channel(new_id)
            if channel:
                set_guild_setting(ctx.guild.id, "target_channel_id", new_id)
                await ctx.send(f"Target channel for this server set to {channel.name} (ID: {new_id})")
            else:
                await ctx.send("Invalid channel ID.")

        @bot.command(name="seelog")
        @commands.has_permissions(administrator=True)
        async def see_log(ctx, guild_or_date: str = None, date_or_filename: str = None, filename: str = None):
            """Send the specified log file or the most recent log.
            Usage: !seelog recent - most recent main log
                   !seelog GUILDNAME recent - most recent guild log  
                   !seelog GUILDNAME YYYY-MM-DD filename.log - specific guild log
                   !seelog YYYY-MM-DD filename.log - specific main log
            If guild filters are set (!fcsguild), only shows lines from those guilds."""
            logging.info(f"[{ctx.author} ({ctx.author.id})] Called see_log")

            # Determine if first arg is guild name or date
            path = None
            is_guild_log = False
            
            if guild_or_date == "recent":
                # Get most recent main log
                log_dirs = sorted([d for d in os.listdir("log") if os.path.isdir(f"log/{d}") and re.match(r'\d{4}-\d{2}-\d{2}', d)], reverse=True)
                if log_dirs:
                    date = log_dirs[0]
                    log_files = sorted(os.listdir(f"log/{date}"), reverse=True)
                    if log_files:
                        filename = log_files[0]
                        path = f"log/{date}/{filename}"
            elif guild_or_date and date_or_filename:
                # Could be guild_name + recent, or guild_name + date + filename, or date + filename
                guild_dir = f"log/{guild_or_date}"
                if os.path.isdir(guild_dir):
                    # This is a guild name
                    is_guild_log = True
                    if date_or_filename == "recent":
                        log_dirs = sorted([d for d in os.listdir(guild_dir) if os.path.isdir(f"{guild_dir}/{d}") and re.match(r'\d{4}-\d{2}-\d{2}', d)], reverse=True)
                        if log_dirs:
                            date = log_dirs[0]
                            log_files = sorted(os.listdir(f"{guild_dir}/{date}"), reverse=True)
                            if log_files:
                                filename = log_files[0]
                                path = f"{guild_dir}/{date}/{filename}"
                    elif filename:
                        path = f"{guild_dir}/{date_or_filename}/{filename}"
                else:
                    # Try as main log with date and filename
                    path = f"log/{guild_or_date}/{date_or_filename}"
            elif guild_or_date and date_or_filename == "recent":
                # Might be a guild name with recent
                guild_dir = f"log/{guild_or_date}"
                if os.path.isdir(guild_dir):
                    is_guild_log = True
                    log_dirs = sorted([d for d in os.listdir(guild_dir) if os.path.isdir(f"{guild_dir}/{d}") and re.match(r'\d{4}-\d{2}-\d{2}', d)], reverse=True)
                    if log_dirs:
                        date = log_dirs[0]
                        log_files = sorted(os.listdir(f"{guild_dir}/{date}"), reverse=True)
                        if log_files:
                            filename = log_files[0]
                            path = f"{guild_dir}/{date}/{filename}"
                else:
                    path = f"log/{guild_or_date}/{date_or_filename}"
            elif guild_or_date:
                await ctx.send("Usage: !seelog recent | !seelog GUILDNAME recent | !seelog GUILDNAME YYYY-MM-DD filename | !seelog YYYY-MM-DD filename")
                return

            if not path or not os.path.exists(path):
                await ctx.send("Log not found. Check guild name, date format (YYYY-MM-DD), and filename.")
                return

            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
                
                # filter by guild if fcsguild is set
                if filtered_guild_ids:
                    filtered_lines = []
                    for line in lines:
                        if any(f'in "{guild_name}"' in line or f"({gid})" in line for gid in filtered_guild_ids for guild_name in [g for g in os.listdir(f"log") if os.path.isdir(f"log/{g}") and g not in [d for d in os.listdir("log") if re.match(r'\d{4}-\d{2}-\d{2}', d)]]):
                            filtered_lines.append(line)
                    content = "".join(filtered_lines)
                else:
                    content = "".join(lines)

                if len(content) < 1900:
                    await ctx.send(f"```\n{content}\n```")
                else:
                    await ctx.send(f"```{content[-1900:]}```")
                    if filtered_guild_ids:
                        await ctx.send(f"(Filtered to guilds: {', '.join(map(str, sorted(filtered_guild_ids)))})")

            except Exception as e:
                await ctx.send(f"Error reading log file: {e}")

        @bot.command(name="fcsguild")
        @commands.has_permissions(administrator=True)
        async def filter_guild(ctx, *, guild_ids: str = None):
            """Filter logs by guild ID(s). Usage: !fcsguild 12345 67890 or !fcsguild clear
            Multiple guild IDs separated by space or comma.
            !fcsguild clear - remove all filters.
            !fcsguild - show current filters.
            """
            global filtered_guild_ids
            
            if guild_ids is None or guild_ids.lower() == "":
                # show current filters
                if filtered_guild_ids:
                    await ctx.send(f"Current guild filters: {', '.join(map(str, sorted(filtered_guild_ids)))}")
                else:
                    await ctx.send("No guild filters set. Use `!fcsguild <guild_id> [<guild_id> ...]` to set.")
                return
            
            if guild_ids.lower() == "clear":
                filtered_guild_ids.clear()
                await ctx.send("Guild filters cleared.")
                return
            
            # parse guild IDs (support both space and comma separation)
            guild_ids = guild_ids.replace(",", " ")
            try:
                new_ids = set(int(gid.strip()) for gid in guild_ids.split() if gid.strip())
                if not new_ids:
                    await ctx.send("No valid guild IDs provided.")
                    return
                filtered_guild_ids = new_ids
                await ctx.send(f"Guild filters set to: {', '.join(map(str, sorted(filtered_guild_ids)))}")
                logging.info(f"Guild log filter set by {ctx.author}: {filtered_guild_ids}")
            except ValueError:
                await ctx.send("Invalid guild IDs. Please provide numeric values.")

        @bot.command(name="thx")
        async def thank_you(ctx):
            """Reply with 'np' when thanked."""
            logging.info(f"[{ctx.author} ({ctx.author.id})] Called thx")
            await ctx.send("np")

        @bot.command(name="mcstat")
        async def mcstat(ctx, option: str = None):
            """Check Minecraft Bedrock server status. Option 'tagmcr' will mention the role."""
            server = BedrockServer.lookup(f"{BEDROCK_HOST}:{BEDROCK_PORT}")
            try:
                address = f"{BEDROCK_HOST}:{BEDROCK_PORT}"
                status = server.status()
                players = status.players.online
                latency = status.latency

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
            """Create a poll. Usage: !mkpoll <question> <opt1> <opt2> ... <duration>"""
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
        
        # ===== FEEDBACK =====
        
        @bot.command(name="bugreport")
        async def bugreport(ctx, *, content: str = None):
            """Submit a bug report. Usage: !bugreport <text>"""
            bugs = load_feedback()
            prefix = format_version_prefix(VERSION)

            bug_number = len(bugs) + 1
            bug_id = f"{prefix}{bug_number:02d}"

            bug_data = {
                "id": bug_id,
                "version": VERSION,
                "reporter": {
                    "name": ctx.author.name,
                    "id": ctx.author.id
                },
                "content": content,
                "timestamp": datetime.utcnow().isoformat(),
                "deleted": False,
                "delete_reason": None
            }

            bugs.append(bug_data)
            save_feedback(bugs)

            await ctx.reply(f"Bug report **#{bug_id}** submitted. Thank you!")

        @bot.command(name="featurerequest")
        async def featurerequest(ctx, *, content: str = None):
            """Submit a feature request. Usage: !featurerequest <text>"""
            if not content:
                await ctx.reply("Please provide a feature request. Usage: `!featurerequest <text>`")
                return

            feature_id = create_feedback_entry(ctx, content, "feature", FEEDBACK_FILE)
            await ctx.reply(f"Feature request **#{feature_id}** submitted. Thank you!")

        @bot.command(name="listfeedback")
        async def list_feedback(ctx, type_filter: str = None):
            """List feedback entries. Optionally filter by type."""
            data = load_feedback()
            if type_filter:
                type_filter = type_filter.lower()
                data = [f for f in data if f.get("type") == type_filter]

            if not data:
                await ctx.reply("No feedback found.")
                return

            embed = discord.Embed(
                title=f"Feedback (Version {VERSION})",
                color=discord.Color.orange()
            )

            for f in data:
                status = f.get("status", "ACTIVE")
                reporter = f.get("reporter") or {}
                reporter_name = reporter.get("name", "Unknown")
                content_preview = (f.get("content") or "")[:200] + ("..." if len(f.get("content") or "") > 200 else "")
                f_type = f.get("type", "Unknown").capitalize()
                embed.add_field(
                    name=f"#{f.get('id', 'N/A')} [{f_type}] by {reporter_name} ({status})",
                    value=content_preview,
                    inline=False
                )

            await ctx.reply(embed=embed)

        @bot.command(name="delfeedback")
        @commands.has_permissions(manage_messages=True)
        async def del_feedback(ctx, entry_id: str, *, reason: str = "No reason provided"):
            """Delete or mark feedback as deleted. Usage: !delfeedback <id> [reason] (requires manage_messages)."""
            hard_delete_triggers = ["iwanttoforgetaboutit", "pd"]
            data = load_feedback()
            entry = next((f for f in data if f.get("id") == entry_id), None)

            if not entry:
                await ctx.reply(f"Feedback #{entry_id} not found.")
                return

            words = reason.split()
            if words and words[-1].lower() in hard_delete_triggers:
                data = [f for f in data if f.get("id") != entry_id]
                save_feedback(data)
                await ctx.reply(f"Feedback **#{entry_id}** completely removed from records.")
                return

            if entry.get("status") == "DELETED":
                await ctx.reply(f"Feedback #{entry_id} is already deleted.")
                return

            entry_reason = " ".join(words)
            entry["status"] = "DELETED"
            entry["delete_reason"] = entry_reason
            entry["deleted_by"] = {
                "name": ctx.author.name,
                "id": ctx.author.id,
                "timestamp": datetime.utcnow().isoformat()
            }

            save_feedback(data)
            await ctx.reply(f"Feedback **#{entry_id}** marked as DELETED. Reason: `{entry_reason}`")

        @bot.command(name='jvc')
        @commands.guild_only()
        @commands.bot_has_guild_permissions(connect=True, speak=True)
        async def jvc(ctx, mode: str = None, id_or_none: str = None):
            """
            Voice connection debugger command.
            Usage:
            !jvc                     -> join caller's VC
            !jvc u <USER_ID>         -> join that user's VC
            !jvc a <VC_ID>           -> join VC by ID (alone)
            !jvc <VC_ID>             -> same as 'a'
            """
            guild = ctx.guild
            existing_vc = guild.voice_client
            channel = None

            logging.info(f"[COMMAND] jvc called by {ctx.author} | mode={mode} | id={id_or_none}")

            if mode is None and id_or_none is None:
                member = ctx.author
                if not member.voice or not member.voice.channel:
                    await ctx.reply(get_bot_message("voice", "not_in_vc"))
                    return
                channel = member.voice.channel

            elif id_or_none is None and mode is not None:
                id_str = mode
                mode_flag = "a"
            else:
                id_str = id_or_none
                mode_flag = (mode or "").lower()

            if not channel:
                if not id_str or not id_str.isdigit():
                    await ctx.reply(get_bot_message("voice", "invalid_id"))
                    return
                target_id = int(id_str)

                try:
                    if mode_flag == "u":
                        member = guild.get_member(target_id) or await guild.fetch_member(target_id)
                        if not member or not member.voice or not member.voice.channel:
                            await ctx.reply(get_bot_message("voice", "user_not_found"))
                            return
                        channel = member.voice.channel
                    else:
                        channel = guild.get_channel(target_id) or await bot.fetch_channel(target_id)
                        if not isinstance(channel, discord.VoiceChannel):
                            await ctx.reply(get_bot_message("voice", "vc_not_found"))
                            return
                except Exception as e:
                    logging.exception(f"[ERROR] Failed to resolve target for jvc: {e}")
                    await ctx.reply(get_bot_message("errors", "failed_to_send", error=str(e)))
                    return

            async def attempt_connect(max_retries: int = 3, delay: int = 5) -> bool:
                nonlocal existing_vc
                for attempt in range(1, max_retries + 1):
                    try:
                        if existing_vc and existing_vc.channel.id == channel.id:
                            await ctx.reply(get_bot_message("voice", "already_connected", channel=channel.name))
                            logging.info(f"[INFO] Already in channel {channel.name}")
                            return True

                        if existing_vc:
                            await existing_vc.move_to(channel)
                            await ctx.reply(get_bot_message("voice", "moved_to", channel=channel.name))
                            logging.info(f"[INFO] Moved to {channel.name}")
                            return True

                        logging.info(f"[INFO] Attempt {attempt}: connecting to {channel.name} ({channel.id})...")
                        vc = await channel.connect(reconnect=False)
                        await ctx.reply(get_bot_message("voice", "connected_to", channel=channel.name, attempt=attempt))
                        logging.info(f"[SUCCESS] Connected to {channel.name}")
                        return True

                    except discord.errors.ConnectionClosed as e:
                        logging.error(f"[ERROR] Voice WebSocket closed (code={getattr(e, 'code', 'N/A')}). Retrying in {delay}s...")
                        await asyncio.sleep(delay)
                    except discord.ClientException as e:
                        logging.error(f"[ERROR] ClientException while connecting: {e}. Retrying in {delay}s...")
                        await asyncio.sleep(delay)
                    except Exception as e:
                        logging.exception(f"[ERROR] Unexpected connection error on attempt {attempt}: {e}")
                        await asyncio.sleep(delay)

                await ctx.reply(get_bot_message("voice", "connection_failed"))
                return False

            success = await attempt_connect()
            if not success:
                logging.error(f"[FATAL] jvc failed to connect to channel {channel} after retries.")
            return
        

        @bot.command(name='dvc')
        @commands.guild_only()
        async def dvc(ctx):
            """Disconnect the bot from its current voice channel in the guild. Usage: !dvc"""
            vc = ctx.guild.voice_client
            if not vc or not vc.is_connected():
                await ctx.reply(get_bot_message("voice", "not_connected"))
                return

            try:
                await vc.disconnect()
                await ctx.reply(get_bot_message("voice", "disconnected"))
                logging.info(f"[VOICE] Disconnected from voice in guild {ctx.guild.id}")
            except Exception as e:
                logging.exception(f"[VOICE] Failed to disconnect: {e}")
                await ctx.reply(get_bot_message("errors", "failed_to_send", error=str(e)))

        @bot.command(name='vcplay')
        @commands.guild_only()
        async def vcplay(ctx, source: str = None):
            """Alias to plvc — play an audio file or stream in the current voice channel."""
            await plvc(ctx, source)

        @bot.command(name="plvc")
        @commands.guild_only()
        async def plvc(ctx, source: str = None):
            """Play audio from local file or URL. Adds to queue and triggers playback."""
            vc = ctx.guild.voice_client
            if vc is None:
                await ctx.reply(get_bot_message("voice", "not_connected"))
                return

            if source is None:
                await ctx.reply(get_bot_message("voice", "invalid_id"))
                return

            queue = get_queue(ctx)

            file_data = get_file(source)
            if file_data:
                file_path, filename = file_data
                queue.append(("file", file_path))
                await ctx.reply(get_bot_message("voice", "file_queued", filename=filename))
                logging.info(f"[VOICE] Queued local file {filename} for guild {ctx.guild.id}")
                if not vc.is_playing() and not get_paused(ctx):
                    await play_next(ctx)
                return

            queue.append(("url", source))
            await ctx.reply(get_bot_message("voice", "url_queued", source=source))
            logging.info(f"[VOICE] Queued URL {source} for guild {ctx.guild.id}")
            if not vc.is_playing() and not get_paused(ctx):
                await play_next(ctx)
            return

        @bot.command(name="stvc")
        @commands.guild_only()
        async def vcstop(ctx):
            """Stop playback and clear queue."""
            vc = ctx.guild.voice_client
            if vc and vc.is_playing():
                try:
                    vc.stop()
                except Exception:
                    logging.exception("Error stopping playback")
            get_queue(ctx).clear()
            guild_paused[ctx.guild.id] = False
            await ctx.send(get_bot_message("voice", "playback_stopped"))
            logging.info(f"[VOICE] Stopped playback and cleared queue in guild {ctx.guild.id}")

        @bot.command(name="pavc")
        @commands.guild_only()
        async def vcpause(ctx):
            """Pause playback."""
            vc = ctx.guild.voice_client
            if vc and vc.is_playing():
                try:
                    vc.pause()
                    guild_paused[ctx.guild.id] = True
                    await ctx.send(get_bot_message("voice", "playback_paused"))
                    logging.info(f"[VOICE] Paused playback in guild {ctx.guild.id}")
                except Exception as e:
                    logging.exception(f"[VOICE] Failed to pause: {e}")
                    await ctx.send(get_bot_message("errors", "failed_to_send", error=str(e)))
            else:
                await ctx.send(get_bot_message("voice", "not_connected"))

        @bot.command(name="revc")
        @commands.guild_only()
        async def vcresume(ctx):
            """Resume playback."""
            vc = ctx.guild.voice_client
            if vc and vc.is_paused():
                try:
                    vc.resume()
                    guild_paused[ctx.guild.id] = False
                    await ctx.send(get_bot_message("voice", "playback_resumed"))
                    logging.info(f"[VOICE] Resumed playback in guild {ctx.guild.id}")
                except Exception as e:
                    logging.exception(f"[VOICE] Failed to resume: {e}")
                    await ctx.send(get_bot_message("errors", "failed_to_send", error=str(e)))
            else:
                await ctx.send(get_bot_message("voice", "not_connected"))
                
        @bot.command(name="debug_var")
        @commands.is_owner()
        async def debug_var(ctx, mode: str = None, *args):
            """Read or edit an in-memory variable. Usage: !debug_var read <path> | !debug_var edit <path> <json_or_text>"""
            logging.info(f"[{ctx.author} ({ctx.author.id})] Called debug_var with mode={mode} args={args}")

            if not mode:
                await ctx.send("Usage: `!debug_var read <path>` or `!debug_var edit <path> <value>`")
                return

            mode = mode.lower()

            def resolve(path: str):
                """Resolve a dotted path against module globals (and nested dict/attr/list)."""
                parts = path.split(".")
                g = globals()
                if parts[0] in g:
                    obj = g[parts[0]]
                else:
                    return None, f"Root name `{parts[0]}` not found"
                for p in parts[1:]:
                    if obj is None:
                        return None, f"Reached None while resolving `{p}`"
                    if isinstance(obj, dict):
                        if p in obj:
                            obj = obj[p]
                        else:
                            return None, f"Key `{p}` not found in dict"
                    elif isinstance(obj, (list, tuple)):
                        try:
                            idx = int(p)
                            obj = obj[idx]
                        except Exception:
                            return None, f"Invalid index `{p}` for list/tuple"
                    else:
                        if hasattr(obj, p):
                            obj = getattr(obj, p)
                        else:
                            return None, f"Attribute `{p}` not found on {type(obj).__name__}"
                return obj, None

            if mode == "read":
                if not args:
                    await ctx.send("Usage: `!debug_var read <path>`")
                    return
                path = args[0]
                val, err = resolve(path)
                if err:
                    await ctx.send(f"Error: {err}")
                    return

                val_type = type(val).__name__
                try:
                    payload = json.dumps(val, default=str, ensure_ascii=False, indent=2)
                except Exception:
                    payload = str(val)

                max_len = 1800
                if len(payload) > max_len:
                    truncated = payload[:max_len] + "\n... (truncated)"
                    await ctx.send(f"Type: `{val_type}`\nValue (truncated):\n```json\n{truncated}\n```")
                else:
                    await ctx.send(f"Type: `{val_type}`\nValue:\n```json\n{payload}\n```")
                return

            if mode == "edit":
                if len(args) < 2:
                    await ctx.send("Usage: `!debug_var edit <path> <json_or_text>`")
                    return
                path = args[0]
                new_raw = " ".join(args[1:]).strip()

                try:
                    new_val = json.loads(new_raw)
                except Exception:
                    new_val = new_raw

                if "." in path:
                    parent_path, last = path.rsplit(".", 1)
                    parent, err = resolve(parent_path)
                    if err:
                        await ctx.send(f"Error resolving parent `{parent_path}`: {err}")
                        return
                else:
                    parent = globals()
                    last = path

                try:
                    if isinstance(parent, dict):
                        parent[last] = new_val
                    elif hasattr(parent, last):
                        setattr(parent, last, new_val)
                    else:
                        if parent is globals():
                            globals()[last] = new_val
                        else:
                            await ctx.send(f"Cannot set `{last}` on parent of type {type(parent).__name__}")
                            return
                except Exception as e:
                    await ctx.send(f"Failed to set value: {e}")
                    logging.exception("debug_var edit failed")
                    return

                try:
                    if path.startswith("config_data") or (path == "config_data"):
                        save_json(CONFIG_FILE, config_data)
                    if path.startswith("BANNED_WORDS") or path.startswith("WHITELISTED_WORDS") or path.startswith("banned_words.json"):
                        if isinstance(BANNED_WORDS, set):
                            save_banwjson("banned", BANNED_WORDS)
                        if isinstance(WHITELISTED_WORDS, set):
                            save_banwjson("whitelist", WHITELISTED_WORDS)
                    if path.startswith("user_info") or path == "user_info":
                        save_json(USER_INFO_FILE, user_info)
                except Exception:
                    logging.exception("debug_var persistence hook failed")

                try:
                    payload = json.dumps(new_val, default=str, ensure_ascii=False, indent=2)
                except Exception:
                    payload = str(new_val)
                val_type = type(new_val).__name__
                if len(payload) > 1800:
                    payload = payload[:1800] + "\n... (truncated)"
                await ctx.send(f"Set `{path}` -> Type: `{val_type}`\n```json\n{payload}\n```")
                logging.info(f"debug_var: set {path} to {new_val}")
                return

            await ctx.send("Unknown mode. Use `read` or `edit`.")
            
        @bot.command(name="add_translation")
        @commands.has_permissions(administrator=True)
        async def add_translation(ctx, *, raw_args: str = None):
            """Add a normalization rule.
            Usage:
              !add_translation a="str" b="strrr"
              OR
              !add_translation <from> <to>
            The raw_args capture prevents discord.py's argument parser from choking on quotes/backslashes.
            """
            if not raw_args:
                await ctx.send("Usage: `!add_translation a=\"str\" b=\"strrr\"` or `!add_translation <from> <to>`")
                return

            def _unescape(s: str) -> str:
                try:
                    return bytes(s, "utf-8").decode("unicode_escape")
                except Exception:
                    return re.sub(r'\\(.)', r'\1', s)

            a_val = None
            b_val = None

            m_a = re.search(r'a\s*=\s*"((?:\\.|[^"\\])*)"', raw_args)
            m_b = re.search(r'b\s*=\s*"((?:\\.|[^"\\])*)"', raw_args)
            if m_a and m_b:
                a_val = _unescape(m_a.group(1))
                b_val = _unescape(m_b.group(1))

            if (a_val is None or b_val is None):
                parts = raw_args.strip().split(None, 1)
                if len(parts) >= 2:
                    a_val = parts[0]
                    b_val = parts[1]

            if not a_val or not b_val:
                await ctx.send("Invalid arguments. Usage: `!add_translation a=\"str\" b=\"strrr\"` or `!add_translation <from> <to>`")
                return

            a_key = a_val.lower()
            b_value = b_val.lower()

            custom_translations[a_key] = b_value
            save_banwjson("translation", custom_translations)
            await ctx.send(get_bot_message("translation", "added_trans", a=a_key, b=b_value))

        @bot.command(name="del_translation")
        @commands.has_permissions(administrator=True)
        async def del_translation(ctx, a: str):
            """Delete an existing translation rule"""
            a = a.lower()
            if a in custom_translations:
                del custom_translations[a]
                save_banwjson("translation", custom_translations)
                await ctx.send(get_bot_message("translation", "del_trans", a=a))
            else:
                await ctx.send(get_bot_message("translation", "trans_not_found", a=a))

        @bot.command(name="list_translations")
        @commands.has_permissions(administrator=True)
        async def list_translations(ctx):
            """List all translation rules"""
            if not custom_translations:
                await ctx.send(get_bot_message("translation", "none_set"))
                return
            msg = "\n".join(f"`{a}` → `{b}`" for a, b in custom_translations.items())
            await ctx.send(get_bot_message("translation", "list_trans", message=msg))     
                

        @bot.command(name="fsilence")
        @commands.has_permissions(administrator=True)
        async def fsilence(ctx, target: discord.Member | discord.Role = None):
            """Force silence a user or role."""
            if not target:
                return await ctx.send(get_bot_message("silence", "none_provided"))

            guild = ctx.guild

            muted_role = discord.utils.get(guild.roles, name="Muted")
            if muted_role is None:
                muted_role = await guild.create_role(name="Muted", reason="For fsilence command")

            for channel in guild.channels:
                overwrite = channel.overwrites_for(muted_role)
                overwrite.send_messages = False
                overwrite.speak = False
                overwrite.add_reactions = False
                await channel.set_permissions(muted_role, overwrite=overwrite)

            if isinstance(target, discord.Member):
                await target.add_roles(muted_role)
                silenced_users[guild.id].add(target.id)
                await ctx.send(get_bot_message("silence", "muted", mention=target.mention))

            elif isinstance(target, discord.Role):
                for channel in guild.channels:
                    overwrite = channel.overwrites_for(target)
                    overwrite.send_messages = False
                    overwrite.speak = False
                    overwrite.add_reactions = False
                    await channel.set_permissions(target, overwrite=overwrite)
                silenced_roles[guild.id].add(target.id)
                await ctx.send(get_bot_message("silence", "r_muted", mention=target.mention))

            else:
                await ctx.send(get_bot_message("silence", "invalid"))

        @bot.command(name="unsilence")
        @commands.has_permissions(administrator=True)
        async def unsilence(ctx, target: discord.Member | discord.Role = None):
            """Remove silence."""
            if not target:
                return await ctx.send(get_bot_message("silence", "none_provided"))

            guild = ctx.guild
            muted_role = discord.utils.get(guild.roles, name="Muted")

            if isinstance(target, discord.Member):
                if muted_role in target.roles:
                    await target.remove_roles(muted_role)
                silenced_users[guild.id].discard(target.id)
                await ctx.send(get_bot_message("unsilence", "unmuted", mention=target.mention))

            elif isinstance(target, discord.Role):
                for channel in guild.channels:
                    overwrite = channel.overwrites_for(target)
                    overwrite.send_messages = None
                    overwrite.speak = None
                    overwrite.add_reactions = None
                    await channel.set_permissions(target, overwrite=overwrite)
                silenced_roles[guild.id].discard(target.id)
                await ctx.send(get_bot_message("unsilence", "r_unmuted", mention=target.mention))

        @bot.command(name="listsilenced")
        @commands.has_permissions(administrator=True)
        async def listsilenced(ctx):
            """List silenced users and roles in this guild."""
            guild = ctx.guild
            uset = silenced_users.get(guild.id, set())
            rset = silenced_roles.get(guild.id, set())
            if not uset and not rset:
                return await ctx.send(get_bot_message("silence", "none_active"))

            users = [guild.get_member(uid).mention for uid in uset if guild.get_member(uid)]
            roles = [guild.get_role(rid).mention for rid in rset if guild.get_role(rid)]
            msg = get_bot_message("silence", "list", users=", ".join(users) or "None", roles=", ".join(roles) or "None")
            await ctx.send(msg)
                
        # ===== ERROR HANDLERS =====
        @ban_word.error
        @remove_ban_word.error
        @list_ban_words.error
        async def perm_error(ctx, error):
            if isinstance(error, commands.MissingPermissions):
                logging.warning(f"Permission denied: {ctx.author} tried to use admin command.")
                await ctx.send(get_bot_message("errors", "no_permission"))

        @sessionend.error
        @deplete.error
        async def privileged_error(ctx, error):
            if isinstance(error, commands.MissingRole):
                await ctx.send(get_bot_message("errors", "no_permission"))
        
        @bot.listen("on_command_completion")
        async def log_command_done(ctx):
            logging.info(f"Command completed: {ctx.command} by {ctx.author}")

        @bot.listen("on_command_error")
        async def log_command_error(ctx, error):
            logging.error(f"Error in command {ctx.command} by {ctx.author}: {error}")

        return bot
            
    # ===== CONSOLE INTERFACE =====
    def console_interface():
        """Console UI using conintf_ptk.ConsoleInterface (replaces previous prompt_toolkit loop)."""
        global target_channel_id, config_data
        global bot_started, bot, bot_loop, token, startmessage, DEBUGB, session_id, manual_shutdown, stop_message

        def _banner():
            ver = globals().get("VERSION", "—")
            return f"BestBotEver!!! {ver}\n© 2025 TonpalmUnmain\nUnder GNU general public license v3.0\n{datetime.now().strftime('%Y-%m-%d')}\n------------------------------------------\nConsole ready. Commands: start [msg], stop [msg], targch [channel_id], editcfg <path> <value>, exit"

        console = ConsoleInterface(name="BestDiscordBotEver", version=str(globals().get("VERSION", "—")), prompt="console> ", banner=_banner)

        async def _cmd_start(args):
            nonlocal console
            global bot_started, bot, bot_loop, startmessage, DEBUGB, session_id
            if bot_started:
                print("Bot already running.")
                return
            full_args = " ".join(args).strip()
            debug_flag = False
            if "{" in full_args and "}" in full_args:
                start_part, debug_part = full_args.split("{", 1)
                startmessage = start_part.strip() or None
                debug_value = debug_part.split("}", 1)[0].strip().lower()
                debug_flag = debug_value in ("true", "1", "yes", "on")
            else:
                startmessage = full_args or None
            if startmessage and startmessage.lower() == "none":
                startmessage = None
            DEBUGB = debug_flag
            try:
                bot = create_bot()
                bot_loop = asyncio.new_event_loop()

                def run_bot():
                    asyncio.set_event_loop(bot_loop)
                    try:
                        bot_loop.run_until_complete(bot.start(token))
                    except asyncio.CancelledError:
                        pass
                    except Exception:
                        logging.exception("Error starting bot")
                    finally:
                        try:
                            bot_loop.close()
                        except Exception:
                            pass

                threading.Thread(target=run_bot, daemon=True).start()
                bot_started = True
                session_id = gen_session_id()
                print(f"Bot started. Debug: {DEBUGB}")
                logging.info(f"Session ID: {session_id}")
            except Exception:
                logging.exception("Failed to start bot")
                print("Failed to start bot (see logs).")

        async def _cmd_stop(args):
            global bot_started, bot_loop, manual_shutdown, stop_message, target_channel_id
            if not bot_started:
                print("Bot is not running.")
                return
            manual_shutdown = True
            if not args:
                stop_message = get_bot_message("shutdown") if callable(get_bot_message) else None
            elif args[0].lower() == "none":
                stop_message = None
            else:
                stop_message = " ".join(args)
            async def _shutdown():
                try:
                    logging.info("Shutting down bot...")
                    if stop_message:
                        # send shutdown message to each guild based on per-guild config
                        for guild in bot.guilds:
                            channel = get_target_channel_for_guild(guild)
                            if channel:
                                try:
                                    await channel.send(stop_message)
                                    logging.info(f"Sent shutdown message to #{channel} ({channel.id}) in guild {guild.id}: {stop_message}")
                                except Exception as e:
                                    logging.error(f"Failed to send shutdown message in guild {guild.id}: {e}")
                    for t in asyncio.all_tasks(loop=bot_loop):
                        if t is not asyncio.current_task(loop=bot_loop):
                            t.cancel()
                    await bot.close()
                    logging.info("Bot shutdown complete.")
                except Exception:
                    logging.exception("Error during shutdown")
            try:
                fut = asyncio.run_coroutine_threadsafe(_shutdown(), bot_loop)
                fut.result(timeout=10)
            except Exception:
                logging.exception("Error shutting down bot")
            bot_started = False
            print("Bot stopped.")

        async def _cmd_exit(args):
            if bot_started and bot_loop:
                await _cmd_stop([])
            print("Exiting console.")
            os._exit(0)

        async def _fexit(args):
            print("Console is not closed.")
            sys.exit()
            
        async def _cmd_targch(args):
            global target_channel_id, config_data
            # usage: targch <channel_id>          -> change global default
            #        targch <guild_id> <channel_id> -> change for specific guild
            if not args or not all(a.isdigit() for a in args):
                print("Usage: targch <channel_id> OR targch <guild_id> <channel_id>")
                return
            if len(args) == 1:
                # update global fallback
                target_channel_id = int(args[0])
                config_data["config"]["default_target_channel_id"] = str(target_channel_id)
                save_json(CONFIG_FILE, config_data)
                logging.info(f"Global default target channel set to {target_channel_id}")
                print(f"Global default target channel set to {target_channel_id}")
            else:
                guild_id = int(args[0])
                channel_id = int(args[1])
                set_guild_setting(guild_id, "target_channel_id", channel_id)
                logging.info(f"Target channel for guild {guild_id} set to {channel_id}")
                print(f"Target channel for guild {guild_id} set to {channel_id}")

        async def _cmd_editcfg(args):
            if len(args) < 2:
                print("Usage: editcfg <path> <value>")
                return
            path = args[0]
            value = " ".join(args[1:])
            try:
                set_config_value(path, value)
                print(f"Config updated: {path} = {value}")
                logging.info(f"Config updated via console: {path} = {value}")
            except Exception as e:
                print(f"Failed to update config: {e}")

        async def _cmd_reply(args):
            if len(args) < 2:
                print("Usage: reply <message_id> <message>")
                return

            try:
                message_to_re = int(args[0])
            except ValueError:
                print("Error: message_id must be an integer.")
                return

            raw_msg = " ".join(args[1:])
            possible_override = None
            match = re.search(r"\{(\d+)\}$", raw_msg)
            if match:
                possible_override = int(match.group(1))
                raw_msg = raw_msg[: raw_msg.rfind("{")].strip()

            if not (bot_started and bot_loop):
                print("Bot is not running.")
                return

            async def reply_to_message():
                try:
                    ch_id = possible_override or target_channel_id

                    channel = bot.get_channel(ch_id)
                    if channel is None:
                        try:
                            channel = await bot.fetch_channel(ch_id)
                        except Exception:
                            logging.warning(f"Could not fetch channel {ch_id}")
                            return

                    msg_text = await replace_placeholders(channel, raw_msg)
                    target_msg = await channel.fetch_message(message_to_re)
                    await target_msg.reply(msg_text, mention_author=False)
                    logging.info(f"Replied to message {message_to_re} in channel {ch_id}.")

                except Exception as e:
                    logging.exception(f"Failed to reply to message {message_to_re}: {e}")

            asyncio.run_coroutine_threadsafe(reply_to_message(), bot_loop)

        async def _cmd_sendmsg(args):
            if not args:
                print("Usage: sendmsg <message> [{channel_id}]")
                return
            raw_msg = " ".join(args)

            override_channel_id = None
            possible_override = None

            if raw_msg.endswith("}"):
                match = re.search(r"\{(\d+)\}$", raw_msg)
                if match:
                    possible_override = int(match.group(1))
                    raw_msg = raw_msg[: raw_msg.rfind("{")].strip()

            if bot_started and bot_loop:
                async def send_message():
                    try:
                        ch_id = possible_override or target_channel_id
                        channel = bot.get_channel(ch_id)
                        if channel is None:
                            channel = await bot.fetch_channel(ch_id)

                        if channel is None:
                            logging.info(f"Channel {ch_id} not found.")
                            return

                        msg_text = await replace_placeholders(channel, raw_msg)

                        if msg_text.strip():
                            await channel.send(msg_text)

                        logging.info(f"Message sent to channel {ch_id}.")

                    except Exception as e:
                        logging.info("Failed to send message:", e)

                asyncio.run_coroutine_threadsafe(send_message(), bot_loop)
            else:
                print("Bot is not running.")

        async def _cmd_addfile(args):
            if len(args) != 2:
                print("Usage: addfile <ui|dir> <file_reference>")
                return
            add_file(args[0], args[1])
            print("File added.")

        async def _cmd_getfile(args):
            if len(args) != 1:
                print("Usage: getfile <file_reference>")
                return
            get_file(args[0])
            print("getfile executed (check output).")

        async def _cmd_delfile(args):
            if len(args) != 1:
                print("Usage: delfile <file_reference>")
                return
            del_file(args[0])
            print("File deleted (if existed).")

        async def _cmd_sayinvc(args):
            if not args:
                print("Usage: sayinvc <text> [ovr]")
                return
            if args[-1] in ("0", "1"):
                ovr = int(args[-1])
                text = " ".join(args[:-1])
            else:
                ovr = 1
                text = " ".join(args)
            if not text.strip():
                print("Please provide text to speak.")
                return
            if not bot_started or not bot_loop:
                print("Bot is not running.")
                return
            fut = asyncio.run_coroutine_threadsafe(say_in_vc(bot, text, ovr), bot_loop)
            try:
                fut.result(timeout=1)
                print("TTS scheduled.")
            except asyncio.TimeoutError:
                print("TTS task running asynchronously...")
            except Exception:
                logging.exception("TTS failed to start")
                print("TTS failed (see logs).")

        async def _add_reaction(args):
            if len(args) != 3:
                print("Usage: react <channel_id> <message_id> <emoji>")
                return

            channel_id, message_id, emoji_arg = args

            try:
                channel = bot.get_channel(int(channel_id))
                if channel is None:
                    print(f"Channel {channel_id} not found")
                    return
            except Exception as e:
                print("Invalid channel ID:", e)
                return

            try:
                message = await channel.fetch_message(int(message_id))
            except Exception as e:
                print("Could not fetch message:", e)
                return

            if isinstance(emoji_arg, str) and emoji_arg.startswith("<:"):
                try:
                    await message.add_reaction(emoji_arg)
                except Exception as e:
                    print("Failed to add raw emoji:", e)
                return

            if isinstance(emoji_arg, str) and not emoji_arg.isdigit():
                emoji = bot.app_emojis_by_name.get(emoji_arg)
                if emoji is None:
                    print(f"Emoji name '{emoji_arg}' not found")
                    return
                try:
                    await message.add_reaction(emoji)
                except Exception as e:
                    print("Failed to add emoji:", e)
                return

            try:
                emoji_id = int(emoji_arg)
            except ValueError:
                print("Invalid emoji input")
                return

            emoji = bot.app_emojis_by_id.get(emoji_id)
            if emoji is None:
                print(f"Emoji ID '{emoji_id}' not found")
                return
            try:
                await message.add_reaction(emoji)
            except Exception as e:
                print("Failed to add emoji:", e)
                
        def _react(args):
            """
            Synchronous console wrapper for _add_reaction
            """
            if not hasattr(bot, "loop") or bot.loop is None:
                print("Bot loop not available.")
                return
            bot.loop.create_task(_add_reaction(args))

        async def _exec(args):
            try:
                exec(' '.join(args))
            except Exception as e:
                logging.info(f"EXEC failed: {e}")
        
        async def _statusset(args):
            if len(args) < 2:
                print("Wrong args!")
                return

            status = args[0]
            TEXT = " ".join(args[1:]).strip('"') 

            config_data["config"]["stattype"] = status
            config_data["config"]["stattext"] = TEXT
            save_json(CONFIG_FILE, config_data)
            
            await setstat(status, TEXT)
            logging.info(f"Set status text to {TEXT} ({status}).")
                
        console.add_command("start", _cmd_start, "Start the bot: start [start_message] {debug}")
        console.add_command("stop", _cmd_stop, "Stop the bot: stop [message|none]")
        console.add_command("exit", _cmd_exit, "Exit console (will stop bot if running)")
        console.add_command("&", _fexit)
        console.add_command("targch", _cmd_targch, "Set default target channel id")
        console.add_command("reply", _cmd_reply, "Reply to a message: reply <message_id> <message> {channel_id}")
        console.add_command("sendmsg", _cmd_sendmsg, "Send message: sendmsg <message> {channel_id}")
        console.add_command("addfile", _cmd_addfile, "Add file reference: addfile <ui|dir> <ref>")
        console.add_command("getfile", _cmd_getfile, "Get file by reference: getfile <ref>")
        console.add_command("delfile", _cmd_delfile, "Delete file reference: delfile <ref>")
        console.add_command("sayinvc", _cmd_sayinvc, "TTS into VC: sayinvc <text> [ovr]")
        console.add_command("react", _react, "Add reaction to message: react <channel_id> <message_id> <emoji_name|emoji_id>")
        console.add_command("exec",_exec,"Execute string: exec <str>")
        console.add_command("statset", _statusset, "Set status text: <type> <text>")
        
        try:
            asyncio.run(console.start())
        except Exception:
            logging.exception("Console terminated unexpectedly")
            
    # ===== MAIN =====
    if __name__ == "__main__":
        try:
            bot = create_bot()
        except Exception:
            os.system("cls" if os.name == "nt" else "clear")
            logging.critical("Unhandled exception:\n" + traceback.format_exc())
            input("Press Enter to exit...")
            sys.exit(1)
        
        try:
            os.system("cls" if os.name == "nt" else "clear")
            console_interface()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting console.")
            sys.exit(0)
except Exception as e:
    os.system("cls" if os.name == "nt" else "clear")
    logging.critical("Critical error :\n" + traceback.format_exc())
    logging.info(f"Critical error : {e}")
    input("Press Enter to exit...")
    sys.exit(1)

'''
BestBotEver!!!
A discord bot, not intended to be used in other servers.
Under GNU General Public License Version 3.0, 29 June 2007.
© 2025 Warat Thongsuwan (TonpalmUnmain)
'''
