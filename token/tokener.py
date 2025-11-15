import os
import base64
import hashlib
from cryptography.fernet import Fernet, InvalidToken
from conintf_ptk import ConsoleInterface
import asyncio
import getpass

def password_to_key(password: str) -> bytes:
    sha = hashlib.sha256(password.encode()).digest()
    return base64.urlsafe_b64encode(sha)

def resolve_path(path: str) -> str | None:
    """
    Resolve a file path: try as given, then relative to this script's directory.
    Returns absolute path if found, otherwise None.
    """
    if os.path.isabs(path):
        return path if os.path.exists(path) else None
    # try current working dir
    cand = os.path.abspath(path)
    if os.path.exists(cand):
        return cand
    # try script directory
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cand = os.path.join(base_dir, path)
    if os.path.exists(cand):
        return cand
    return None

def encrypt_file(path, password, dest=None):
    if not os.path.exists(path):
        # try resolving relative to script dir / cwd
        resolved = resolve_path(path)
        if not resolved:
            return None, "File not found."
        path = resolved

    key = password_to_key(password)
    fernet = Fernet(key)

    with open(path, "rb") as f:
        data = f.read()

    encrypted = fernet.encrypt(data)
    
    # Default destination
    out_path = dest if dest else path + ".enc"

    with open(out_path, "wb") as f:
        f.write(encrypted)

    return out_path, None

async def ask_password(prompt_text: str = "Password: ") -> str:
    """
    Prompt for a password using getpass in a thread to avoid blocking the event loop.

    Returns:
        str: Entered password (may be empty).
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, getpass.getpass, prompt_text)

def _banner():
    return "ENCRYPT ZUKA BLYATT"

async def encrypt(args):
    """
    Usage: encrypt <file> [dest]
    """
    if len(args) < 1:
        print("Usage: encrypt <file> [dest]")
        return

    file_path = args[0]
    dest = args[1] if len(args) > 1 else None

    password = await ask_password("Password: ")
    
    out_path, err = encrypt_file(file_path, password, dest)
    if err:
        print("Error:", err)
        return

    print(f"Encrypted → {out_path}")

async def decrypt(args):
    """
    Usage: decrypt <file> <dest|print>
    """
    if len(args) < 2:
        print("Usage: decrypt <file> <dest|print>")
        return

    file_path = args[0]
    dest = args[1]

    password = await ask_password("Password: ")

    key = password_to_key(password)
    fernet = Fernet(key)

    resolved = resolve_path(file_path)
    if not resolved:
        print("File not found.")
        return
    file_path = resolved

    with open(file_path, "rb") as f:
        encrypted = f.read()

    try:
        data = fernet.decrypt(encrypted)
    except InvalidToken:
        print("Invalid password or corrupted file.")
        return

    if dest.lower() == "print":
        print(data.decode(errors="replace"))
    else:
        with open(dest, "wb") as f:
            f.write(data)
        print(f"Decrypted → {dest}")

# ==========================
# Console setup
# ==========================
console = ConsoleInterface(
    name="Encrypt",
    prompt="console> ",
    banner=_banner
)

console.add_command("encrypt", encrypt, "Encrypt the given input.")
console.add_command("decrypt", decrypt, "Decrypt the given input.")


if __name__ == "__main__":
    asyncio.run(console.start())
