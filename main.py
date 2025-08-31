import discord
from discord.ext import commands
from datetime import datetime, timedelta
import json
import os
import unicodedata
import re
import asyncio
import logging
import threading
import sys
import platform
import socket
import uuid
import getpass
import io

# ===== UTF-8 OUTPUT SETUP =====
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ===== LOGGING SETUP =====
log_dir = f"log/{datetime.now().strftime('%Y-%m-%d')}"
os.makedirs(log_dir, exist_ok=True)
log_file = f"{log_dir}/log_{datetime.now().strftime('%H-%M-%S')}.txt"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

# ===== CONFIG HANDLING =====
CONFIG_FILE = "config.json"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        print(f"{CONFIG_FILE} not found!")
        return None
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=4)

config_data = load_config()
if not config_data:
    exit(1)

token = config_data["config"]["token"]
target_channel_id = int(config_data["config"]["default_target_channel_id"])

# ===== VERSION INFO =====
VERSION = config_data["config"]["version"]
AUTHOR = config_data["config"]["author"]

# ===== BOT SETUP =====
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

bot_started = False

# ===== SESSION CONTROL =====
async def startsession(message=None):
    global bot_started
    global startmessage
    startmessage = message
    if bot_started:
        print("Bot already running.")
        return
    bot_started = True
    try:
        await bot.start(token)
    except Exception as e:
        print(f"Error starting bot: {e}")
        bot_started = False

async def stopsession(message: str = None):
    global bot_started
    if not bot_started:
        logging.info("Bot is not running.")
        return

    channel = bot.get_channel(target_channel_id)
    if channel:
        try:
            await channel.send(message or "My papi or ISP or MEA is shutting me down nooo.")
        except Exception as e:
            logging.error(f"Failed to send stop message: {e}")

    bot_started = False
    logging.info("Bot stopped. Closing connection...")

    await bot.close()

# ===== UTILS =====
def normalize_message(text):
    text = unicodedata.normalize('NFKD', str(text)).encode('ASCII', 'ignore').decode('ASCII')
    text = re.sub(r'[\s\W_]+', '', text)
    text = ''.join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r'[\u200B-\u200F\uFE00-\uFE0F\u2060-\u206F]', '', text)
    text = ''.join(c for c in text if unicodedata.category(c)[0] != 'C')
    return str(unicodedata.normalize("NFKC", str(text)).lower())

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
    "nigga", "nigger", "niga", "n1gger", "์NIGGER",
    "นิกก้า", "นิกเกอร์", "นิกเก้อ"
}
save_banned_words()

# ===== BOT EVENTS =====
@bot.event
async def on_ready():
    logging.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    channel = bot.get_channel(target_channel_id)
    if channel:
        await channel.send(startmessage or "I am watching you.")
        logging.info(f"Sent startup message to channel ID: {target_channel_id}")
    else:
        logging.warning("Couldn't find startup channel.")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    logging.info(
        f"{message.author} ({message.author.id}) in #{message.channel.name} ({message.channel.id}): {message.content}"
    )
    content = normalize_message(message.content)
    await bot.process_commands(message)

    ctx = await bot.get_context(message)
    if ctx.valid:
        return

    if any(word in content for word in BANNED_WORDS):
        try:
            await message.delete()
            await message.author.timeout(timedelta(minutes=5), reason="You said the Banned word you dumb fuck.")
            await message.channel.send(f"{message.author.mention} has been timed out for using the fucking Banned word.")
            logging.info(f"Timed out: {message.author} for '{message.content}'")
        except discord.Forbidden:
            await message.channel.send(f"I can't ban {message.author.mention}, this mf should be ashamed of themself.")
            logging.error("Bot doesn't have permission to timeout this dumb fuck.")
        except Exception as e:
            logging.error(f"Error: {e}")

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
@bot.command(name="sessioninfo")
@commands.is_owner()
async def session_info(ctx):
    try:
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        info = (
            f"**Session Info**\n"
            f"Hostname: `{hostname}`\n"
            f"IPv4: `{ip_address}`\n"
            f"OS: `{platform.system()} {platform.release()}`\n"
            f"Version: `{platform.version()}`\n"
            f"Architecture: `{platform.machine()}`\n"
            f"User: `{getpass.getuser()}`\n"
            f"Session ID: `{uuid.uuid4()}`"
        )
        await ctx.send(info)
        logging.info(f"Session info sent by {ctx.author}")
    except Exception as e:
        await ctx.send("Error retrieving session info.")
        logging.error(f"Session info error: {e}")

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
@commands.has_role(1399766498246918216)
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

@bot.command(name="pewurselfnga")
@commands.is_owner()
@commands.has_role(1399766498246918216)
async def sessionend(ctx):
    await ctx.send(f"Ight {ctx.author.mention}... I'm out. 💀")
    await bot.close()

@bot.command(name="version")
async def version_command(ctx):
    await ctx.send(f"Bot version: {VERSION}\nMy papi is: {AUTHOR}")

@bot.command(name="agreewme")
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
@commands.has_role(1399766498246918216)
async def repeat(ctx, *, message: str):
    logging.info(f"[{ctx.author} ({ctx.author.id})] Called repeat with message: {message}")
    await ctx.send(message)

@bot.command(name="deplete")
@commands.has_role(1399766498246918216)
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
    await sessionend(ctx)

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
        with open(path, "r") as f:
            content = f.read()
        if len(content) < 1900:
            await ctx.send(f"```\n{content}\n```")
        else:
            await ctx.send("Log too large to send. Sending as file.", file=discord.File(path))
    else:
        await ctx.send("Log not found. I lost it or u dyslexic?")

@bot.command(name="thx")
async def thank_you(ctx):
    logging.info(f"[{ctx.author} ({ctx.author.id})] Called thx")
    await ctx.send("np")

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
        await ctx.send("-THE CREATOR")

# ===== CONSOLE INTERFACE =====
def console_interface():
    global target_channel_id, config_data

    print("Console ready. Commands: start [msg], stop [msg], targch [channel_id], exit")
    while True:
        cmd = input("console> ").strip().split()
        if not cmd:
            continue
        command, *args = cmd

        if command == "start":
            msg = " ".join(args) if args else None
            threading.Thread(target=lambda: asyncio.run(startsession(msg)), daemon=True).start()

        elif command == "stop":
            msg = " ".join(args) if args else None
            if bot.loop.is_running():
                asyncio.run_coroutine_threadsafe(stopsession(msg), bot.loop)
            else:
                print("Bot loop not running.")

        elif command == "targch" and args and args[0].isdigit():
            target_channel_id = int(args[0])
            config_data["config"]["default_target_channel_id"] = str(target_channel_id)
            save_config(config_data)
            print(f"Target channel set to {target_channel_id}")

        elif command == "exit":
            print("Exiting...")
            break

        else:
            print(f"Unknown command: {command}")

# ===== MAIN =====
if __name__ == "__main__":
    console_interface()
