# 🤖 BestBotEver!!! 3.0.0 Documentation

---

## Overview
This bot is a **Discord moderation and utility assistant** with customizable features, logging, 
and command-line control. It uses the **discord.py** library with extended command functionality.  
The bot handles moderation (timeouts, banned words, forgiveness), system monitoring, log retrieval, 
and utility commands. It can also be controlled from both Discord and a console interface.

---

## Key Features
- Automatic banning of predefined offensive words.
- Logs all messages with timestamps to daily log files.
- Timeout functionality for users using banned words.
- Owner and admin-only commands for moderation.
- Utility commands for server interaction (repeat, version, etc.).
- Detailed session/system info reporting (CPU, GPU, Memory, Disk, Network).
- Custom console interface for starting, stopping, and managing the bot.
- Supports dynamic message placeholders `<{mention:ID}>`, `<{channel:ID}>`, `<{role:ID}>`.

---

## Configuration
The bot reads its configuration from **config.json**, which must include:

- `token`: The bot token for authentication.  
- `default_target_channel_id`: The channel ID for startup/shutdown messages.  
- `version`: Version string of the bot.  
- `author`: Author/maintainer of the bot.  
- `command_prefix`: Prefix for bot commands.  
- `admin_role_id`: Role ID required for some privileged commands.  

---

## Moderation System
The bot maintains a **banned_words.json** file storing blocked terms.  
If a user types or edits a message containing one, the bot will:
- Delete the message.  
- Timeout the user for 5 minutes.  
- Notify the channel.  

Admins can dynamically add/remove banned words with commands.

---

## Commands

### Moderation & Admin
- **sessioninfo** → *(Owner only)* Displays host system session information.  
- **banword `<word>`** → *(Admin)* Adds a word to banned list.  
- **rmword `<word>`** → *(Admin role)* Removes a banned word.  
- **listbanword** → *(Admin)* Lists all banned words.  
- **forgive `@user`** → *(Moderator)* Removes a timeout from a user.  
- **pewurselfnga** → *(Owner only)* Shuts down the bot.  

### Utility
- **version** → Shows bot version and author.  
- **agreewme `<msg>`** → Bot agrees with your statement.  
- **disagreewme `<msg>`** → Bot disagrees with your statement.  
- **repeat `<msg>`** → *(Admin role)* Repeats the message.  
- **deplete `<type> <value>`** → *(Owner)* Shuts down after a delay (ms, sec, min, hr, d).  
- **cfch `<id|current>`** → *(Admin)* Changes the default target channel.  
- **seelog `<date> <filename>`** → *(Admin)* Reads logs (or `recent`).  
- **doc** → Shows documentation link.  
- **thx** → Replies with `np`.  

---

## Console Interface
The bot includes a **console interface** for direct host control:

- `start [msg]` → Starts the bot with optional startup message.  
- `stop [msg]` → Stops the bot with optional shutdown message.  
- `targch <channel_id>` → Changes target channel.  
- `sendmsg <text>` → Sends a message (supports placeholders).  
- `status` → Displays bot status.  
- `exit` → Shuts down console.  

---

## Logging System
Logs are automatically created in **log/YYYY-MM-DD/** directories with timestamped filenames.  
They include user messages, commands, moderation actions, and errors.  
Admins can retrieve logs via the **seelog** command.

---

## Error Handling
The bot gracefully handles:
- Missing permissions.  
- Invalid commands.  
- Missing required roles.  
- File I/O errors in logs/config.  

Errors are logged to file and displayed where applicable.  

---

⚠️ **WARNING:**  
IF YOU FIND ANY ERROR TELL ME NOW OR I WILL `!pewurselfnga`

---

### 📌 Rights & Credits
All rights reserved **TonpalmUnmain and me only baka**.
