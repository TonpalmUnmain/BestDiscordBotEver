# BestDiscordBotEver Function Documentation

## Command Functions

### General Commands

#### !help
- **Description**: Shows command list or details for specific command
- **Usage**: `!help [command_name]`
- **Logging**: `[{author} ({author.id})] Called help with: {command_name}`

#### !repeat
- **Description**: Repeats the given message verbatim
- **Usage**: `!repeat [message]`
- **Logging**: `[{author} ({author.id})] Called repeat with message: {message}`
- **Permission**: Owner only

#### !thx
- **Description**: Replies with "np"
- **Usage**: `!thx`
- **Logging**: `[{author} ({author.id})] Called thx`

#### !agreewme
- **Description**: Agrees with provided message
- **Usage**: `!agreewme [message]`
- **Response**: "Yes, daddy @user😩. You're absolutely right about: [message]"
- **Permission**: Owner only

#### !disagreewme
- **Description**: Disagrees with provided message
- **Usage**: `!disagreewme [message]`
- **Response**: "No, daddy @user😩. [message] is not true."

### Admin Commands

#### !banword
- **Description**: Adds word to banned list
- **Usage**: `!banword [word]`
- **Logging**: Added banned word: {word}
- **Permission**: Administrator

#### !rmword
- **Description**: Removes word from banned list
- **Usage**: `!rmword [word]`
- **Logging**: Removed banned word: {word}
- **Permission**: Administrator + Admin Role

#### !listbanword
- **Description**: Lists all banned words
- **Usage**: `!listbanword`
- **Permission**: Administrator

#### !whitelistword
- **Description**: Adds word to whitelist
- **Usage**: `!whitelistword [word]`
- **Permission**: Owner only

#### !rmwhitelistword
- **Description**: Removes word from whitelist
- **Usage**: `!rmwhitelistword [word]`
- **Permission**: Owner only

#### !listwhitelistword
- **Description**: Lists all whitelisted words
- **Usage**: `!listwhitelistword`
- **Permission**: Owner only

#### !forgive
- **Description**: Removes timeout from user
- **Usage**: `!forgive @user`
- **Permission**: Moderate Members

#### !pewthyself
- **Description**: Shuts down the bot
- **Usage**: `!pewthyself`
- **Permission**: Owner only

#### !deplete
- **Description**: Sets delayed shutdown
- **Usage**: `!deplete [type] [value]`
- **Types**: ms, sec, min, hr, d
- **Permission**: Owner only

#### !seelog
- **Description**: Views log files
- **Usage**: 
  - `!seelog recent`
  - `!seelog [date] [filename]`
- **Permission**: Administrator

### Minecraft Commands

#### !mcstat
- **Description**: Checks Minecraft server status
- **Usage**: `!mcstat [tagmcr]`
- **Options**: tagmcr - mentions role

### User Management

#### !userinfo
- **Description**: Views/edits user information
- **Usage**: 
  - `!userinfo view`
  - `!userinfo edit [key] [value]`
  - `!userinfo roles`

#### !editvar
- **Description**: Edits user variables
- **Usage**: `!editvar [ID|dispname] [var1] [var2]`
- **Permission**: Administrator

#### !saveuinf
- **Description**: Manually saves user information
- **Usage**: `!saveuinf`
- **Permission**: Administrator

### Feedback System

#### !bugreport
- **Description**: Submits bug report
- **Usage**: `!bugreport [text]`

#### !featurerequest
- **Description**: Submits feature request
- **Usage**: `!featurerequest [text]`

#### !listfeedback
- **Description**: Lists feedback entries
- **Usage**: `!listfeedback [type]`

#### !delfeedback
- **Description**: Deletes/marks feedback as deleted
- **Usage**: `!delfeedback [id] [reason]`
- **Permission**: Manage Messages

## Console Commands

### Basic Controls
- `start [msg]` - Starts bot with optional message
- `stop [msg]` - Stops bot with optional message
- `exit` - Exits console interface

### Channel Management
- `targch [channel_id]` - Sets target channel

### Message Controls
- `sendmsg [text] {channel_id}` - Sends message
- `reply [message_id] [text] {channel_id}` - Replies to message

### File Management
- `addfile ui [reference]` - Adds file via UI
- `addfile dir [reference]` - Adds file via path
- `getfile [reference]` - Gets file info
- `delfile [reference]` - Removes file

## Logging System
All actions are logged with:
- Timestamp
- Action type
- User information
- Command details
- Channel information
- Message content

Format: `YYYY-MM-DD HH:MM:SS [LEVEL] message`

## Error Handling
All commands include:
- Permission checking
- Input validation
- Error logging
- User feedback

## File Structure
```
/log/YYYY-MM-DD/          # Daily logs
/userdata/                # User information
/feedback/                # Feedback storage
/fdump/                   # File storage
config.json              # Configuration
token.config            # Bot token
banned_words.json       # Banned words list
```

## Configuration Files

### config.json
```json
{
    "config": {
        "version": "1.14.5",
        "author": "TonpalmUnmain",
        "command_prefix": "!",
        "admin_role_id": "1399766498246918216",
        "default_target_channel_id": "1371357608904228924",
        "sreenshotdir": "scs"
    },
    "MCS": {
        "mcsAdress": "YOUR_MC_SERVER_IP",
        "mcsPort": 5355,
        "mcsChID": "CHANNEL_ID_FOR_MC_STATUS",
        "mcsDelay": 3600,
        "mcsRoleID": "ROLE_ID_FOR_MC_NOTIFICATIONS"
    }
}
```

### banned_words.json
```json
{
    "banned_words": [
        "word1",
        "word2"
    ],
    "whitelist": [
        "allowed1",
        "allowed2"
    ]
}
```

### token.config
Contains the bot token in plain text:
```
YOUR_BOT_TOKEN_HERE
```

### userdata/uinfo.json
```json
{
    "discord_users": {
        "user_id": {
            "id": "user_id",
            "dispname": "display_name",
            "username": "username#0000",
            "joined_at": "YYYY-MM-DD HH:MM:SS",
            "created_at": "YYYY-MM-DD HH:MM:SS",
            "roles": "role1, role2",
            "var1": "custom_value1",
            "var2": "custom_value2"
        }
    },
    "last_saved": "YYYY-MM-DD HH:MM:SS"
}
```
At this time, ```var1``` and ```var2``` is not in use, but referenced.

### fdump/files.json
```json
{
    "reference_name": {
        "original_path": "C:/original/path/to/file",
        "dump_path": "fdump/filename",
        "filename": "original_filename"
    }
}
```

---


# Quick Start Guide

1. **Install Dependencies**
```bash
pip install -r requirements.txt
```

2. **Configure Files**
- Copy `config.example.json` to `config.json` and fill in your values
- Create `token.config` with your bot token
- Ensure all directories exist:
  ```bash
  mkdir log userdata feedback fdump scs
  ```
*"scs" is not yet implemented.*

3. **Run the Bot**
```bash
python main.py
```

## Packages and Modules

### Required Packages
```
discord.py>=2.3.2
mcstatus>=10.0.3
prompt_toolkit>=3.0.39
colorama>=0.4.6
psutil>=5.9.5
GPUtil>=1.4.0
aiohttp>=3.8.5
async-timeout>=4.0.3
attrs>=23.1.0
dnspython>=2.4.2
idna>=3.4
multidict>=6.0.4
yarl>=1.9.2
wcwidth>=0.2.6
```

### Internal Modules
- **discord**: Core bot functionality and Discord API interactions
- **logging**: Comprehensive logging system
- **asyncio**: Asynchronous I/O operations
- **json**: Configuration and data storage
- **datetime**: Timestamp management
- **os/sys**: System operations and file handling
- **threading**: Console input handling
- **tkinter**: File browser interface
- **colorama**: Console color formatting

## Internal Functions

### Core System Functions
```python
def load_json(file_path, default=None)
    """Loads JSON file with error handling and default values."""

def save_json(file_path, data)
    """Saves data to JSON file with error handling."""

def normalize_message(content)
    """Normalizes message content for consistency."""

class PTKHandler(logging.Handler)
    """Custom logging handler for prompt_toolkit."""
```

### File Management
```python
def browse_file()
    """Opens file browser dialog."""

def load_filedb()
    """Loads file database from fdump/files.json."""

def save_filedb(data)
    """Saves file database to fdump/files.json."""

def add_file(mode, file_reference)
    """Adds file to dump directory with reference."""

def get_file(file_reference)
    """Retrieves file information by reference."""

def del_file(file_reference)
    """Deletes file and its reference."""
```

### User Management
```python
def load_userinfo()
    """Loads user information from latest userinfo file."""

def save_userinfo(data, session_id)
    """Saves user information with session ID."""

def set_userinfo(uid, dispname, var1=None, var2=None, roles=None)
    """Sets or updates user information."""

def update_user_var(uid_or_name, var1=None, var2=None)
    """Updates user variables by ID or display name."""
```

### Minecraft Server
```python
async def check_server_status()
    """Checks Minecraft server status."""

@tasks.loop(seconds=3600)
async def auto_check_server()
    """Automated server status checking."""
```

### Console Interface
```python
def console_input()
    """Handles console input in separate thread."""

async def process_console_command(cmd)
    """Processes console commands."""
```
---
BestBotEver!!! 1.14.5

*Not intended to be used in other servers.*
*Under GNU General Public License Version 3, 29 June 2007.*
*© 2025 Warat Thongsuwan (TonpalmUnmain)*
