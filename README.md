# BestDiscordBotEver — v1.19.3

Lightweight Discord bot with moderation, voice playback, file management, Minecraft monitoring and a small console control UI.

---

## Quick Start

1. Create & activate virtual environment
```powershell
# Windows (from project root)
python -m venv venv
venv\Scripts\activate
```

2. Install dependencies
```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

3. Install FFmpeg (required for voice)
- Chocolatey:
```powershell
choco install ffmpeg
```
- Or download from https://ffmpeg.org and add the `ffmpeg\bin` folder to PATH. You may also set `ffmpeg_dir` in `config.json`.

4. Configure
- Copy `config.example.json` -> `config.json` and update fields (bot token must be placed in `token.config`).

  *If no `config.json` is present when the bot starts, an interactive wizard will prompt you for basic settings and create the file.*
- Ensure folders exist:
```powershell
mkdir log userdata feedback fdump tts_output
```

5. Run
```powershell
python main.py
```

To serve the docs (web folder) use:
```powershell
cd web
python -m http.server 8000
# open http://localhost:8000/index.html
```

---

## Version / Project Info
- Version: 1.19.3
- Author: TonpalmUnmain
- License: GNU GPL v3.0

---

## File / Config Summary

Example `config.json` (current project defaults):
```json
{
  "config": {
    "version": "1.19.3",
    "author": "TonpalmUnmain",
    "default_target_channel_id": "1371357608904228924",
    "admin_role_id": "1411139316171931738",
    "command_prefix": "!",
    "bot_test_channel_id": "1399900695993253970",
    "ffmpeg_dir": ""
  },
  "guilds": {
    "123456789012345678": {
      "target_channel_id": "1371357608904228924"
    },
    "876543210987654321": {
      "target_channel_id": "1421497953834631319"
    }
  },
  "MCS": {
    "mcsAdress": "multi-nor.gl.at.ply.gg",
    "mcsPort": 5355,
    "mcsChID": 1421497953834631319,
    "mcsDelay": 3600,
    "mcsRoleID": "1394542459538640977"
  }
}
```

The new `guilds` section allows per-server overrides (e.g. target channel) while the original `default_target_channel_id` acts as a fallback for any guild without its own entry.

Other important files:

  • `config.example.json` provides sample values for the wizard.
- `token.config` — bot token (plain text)
- `messages.json` — all bot user-visible message templates
- `banned_words.json` — banned / whitelisted words and translations
- `fdump/files.json` — file reference database
- `userdata/` — saved user snapshots
- `log/YYYY-MM-DD/` — runtime logs
- `web/` — static docs (privacy, terms, index)

---

## Requirements

Install from `requirements.txt`. Key packages:
- discord.py
- mcstatus
- prompt_toolkit
- yt-dlp
- colorama
- psutil
- GPUtil
- aiohttp
- ffmpeg (system binary)

---

## Features (high level)
- Moderation: banned words, whitelist, automatic timeouts, manual forgive.
- Voice: join/move/disconnect, play local files or URLs (yt-dlp + ffmpeg), queue, pause/resume/stop, TTS (gTTS).
- File management: add/list/get/delete file references stored in `fdump/`.
- Feedback system: bug reports / feature requests saved per-version.
- Minecraft Bedrock server status monitor and notifier.
- Console control: start/stop/send/reply/addfile/dump commands.
- Debugging: `!debug_var` to read/edit in-memory variables (owner only).
- Message templates configurable in `messages.json`.
- Web docs (privacy + terms) in `web/`.

---

## Commands

General
- `!help [command]` — command list / details
- `!repeat <message>` — owner only
- `!thx` — replies "np"
- `!version` — show bot version

Moderation / Admin
- `!banword <word>` — add banned word (admin)
- `!rmword <word>` — remove banned word (admin)
- `!listbanword` — list banned words (admin)
- `!whitelistword <word>` — add whitelist (owner)
- `!rmwhitelistword <word>` — remove whitelist (owner)
- `!listwhitelistword` — list whitelist (owner)
- `!forgive @user` — remove timeout (moderate_members)
- `!cfch <channel_id|current>` — set target channel for the current server (admin)
- `!seelog recent|YYYY-MM-DD filename` — view logs (admin)
- `!fcsguild <guild_id> [<guild_id> ...]` or `!fcsguild clear` — filter logs by guild IDs (admin)

Voice
- `!jvc` — join caller's voice channel
- `!jvc u <USER_ID>` — join user's VC
- `!jvc a <VC_ID>` or `!jvc <VC_ID>` — join VC by ID
- `!dvc` — disconnect
- `!plvc <URL|file_ref>` — enqueue and play (local file refs read from fdump DB)
- `!vcplay` — alias to `plvc`
- `!stvc` — stop + clear queue
- `!pavc` — pause
- `!revc` — resume
- `!sayinvc <text> [ovr]` — TTS into VC (console command)

Feedback / Polls
- `!bugreport <text>` — submit bug
- `!featurerequest <text>` — submit feature
- `!listfeedback [type]` — list feedback
- `!delfeedback <id> [reason]` — mark or hard-delete feedback (manage_messages)

Debug / Tools
- `!debug_var read <path>` — read in-memory variable + returns its type (owner)
- `!debug_var edit <path> <json_or_text>` — edit variable (owner)
- `!sessioninfo` — system / session diagnostics (owner)
- `!saveuinf` — force userinfo save (admin)

Console commands (local console):
- `start [msg]` `stop [msg]` `exit` `targch <id>` `sendmsg <text> {channel}` `reply <msg_id> <text> {channel}` `addfile ui|dir <ref>` `getfile <ref>` `delfile <ref>`

---

## Message templates

All bot messages are stored in `messages.json`. Use placeholders like `{mention}`, `{word}`, `{channel}`, `{seconds}`. Editing `messages.json` changes all bot responses without code edits.

---

## Banned words & translations

`banned_words.json` supports:
- `banned_words` — list of banned tokens
- `whitelisted_words` — whitelist tokens (prevents moderation)
- `translation` — custom normalize translations used in message normalization

Use bot commands to modify these lists.

---

## Web docs

- `web/index.html` — project index (reads local `config.json` and GitHub repo metadata)
- `web/privacy_policy.html`, `web/terms_of_service.html` — policy pages

Run a static server from `web/` to browse (see Quick Start).

---

## Security & Privacy

- Token must be stored in `token.config` (keep secret).
- All data stored locally on the host (logs, user snapshots, fdump). Operator controls retention & security.
- See `web/privacy_policy.html` for details.

---

## Development notes

- Use `DEBUGB` flag (console start with `{true}`) to enable debug() prints.
- `messages.json` and `config.json` must be valid JSON — malformed files will prevent the bot from starting.
- FFmpeg executable path auto-detected; set `ffmpeg_dir` in `config.json` if required.

---