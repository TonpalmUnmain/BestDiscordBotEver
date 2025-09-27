import subprocess
import re

SERVER_PATH = "C:\Users\jimnd\Desktop\bedrock-server-1.21.102.1\bedrock_server.exe"
LOG_FILE = "mcbe_events.log"

JOIN_PATTERN = re.compile(r"Player connected: (\w+)")
LEAVE_PATTERN = re.compile(r"Player disconnected: (\w+)")

with open(LOG_FILE, "a") as log_file:
    process = subprocess.Popen(
        [SERVER_PATH],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )

    for line in process.stdout:
        line = line.strip()
        print(line)  # optional: print to console

        join_match = JOIN_PATTERN.search(line)
        leave_match = LEAVE_PATTERN.search(line)

        if join_match:
            player = join_match.group(1)
            log_file.write(f"JOIN:{player}\n")
            log_file.flush()
        elif leave_match:
            player = leave_match.group(1)
            log_file.write(f"LEAVE:{player}\n")
            log_file.flush()

