import sys, os, threading, asyncio, re
from PyQt5 import QtWidgets, QtCore

# Ensure project root is on sys.path so `import main` finds main.py
proj_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)

try:
    import main as m
except Exception as exc:
    print("Failed to import main:", exc)
    print("Make sure you run this from project root or use: python -m ui.qt_ui")
    raise
class BotMainWindow(QtWidgets.QWidget):
    REFRESH_INTERVAL_MS = 3000
    TAIL_INTERVAL_MS = 1000

    def __init__(self):
        super().__init__()
        self.setWindowTitle("BestBotEver - UI")
        self.resize(900, 600)
        layout = QtWidgets.QVBoxLayout(self)

        # Command dropdown (Dropdown 1)
        self.cmd_combo = QtWidgets.QComboBox()
        self.cmd_combo.addItems(["start","stop","sendmsg","reply","sayinvc","react"])
        layout.addWidget(self.cmd_combo)

        self.execute_btn = QtWidgets.QPushButton("Execute")
        layout.addWidget(self.execute_btn)

        # Log controls (Dropdown 2 + file list)
        h = QtWidgets.QHBoxLayout()
        self.date_combo = QtWidgets.QComboBox()
        self.file_combo = QtWidgets.QComboBox()
        self.refresh_btn = QtWidgets.QPushButton("Refresh")
        h.addWidget(self.date_combo, 1)
        h.addWidget(self.file_combo, 2)
        h.addWidget(self.refresh_btn, 0)
        layout.addLayout(h)

        # Log viewer
        self.log_view = QtWidgets.QPlainTextEdit()
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view, 10)

        # tailing state
        self._tail_timer = QtCore.QTimer(self)
        self._tail_timer.setInterval(self.TAIL_INTERVAL_MS)
        self._tail_timer.timeout.connect(self._tail_update)
        self._tail_path = None
        self._tail_pos = 0

        # hooks
        self.execute_btn.clicked.connect(self.on_execute)
        self.refresh_btn.clicked.connect(self.populate_logs)
        self.date_combo.currentIndexChanged.connect(self.on_date_changed)
        self.file_combo.currentIndexChanged.connect(self.on_file_changed)

        self.populate_logs()

    def populate_logs(self):
        base = "log"
        dates = []
        if os.path.isdir(base):
            dates = sorted([d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))], reverse=True)
        self.date_combo.blockSignals(True)
        self.date_combo.clear()
        self.date_combo.addItems(dates or ["(no logs)"])
        self.date_combo.blockSignals(False)
        self.on_date_changed()

    def on_date_changed(self):
        date = self.date_combo.currentText()
        files = []
        if date and date != "(no logs)":
            p = os.path.join("log", date)
            if os.path.isdir(p):
                files = sorted(os.listdir(p), reverse=True)
        self.file_combo.blockSignals(True)
        self.file_combo.clear()
        self.file_combo.addItems(files or ["(no files)"])
        self.file_combo.blockSignals(False)
        self.on_file_changed()

    def on_file_changed(self):
        date = self.date_combo.currentText()
        fname = self.file_combo.currentText()
        if not date or not fname or date == "(no logs)" or fname == "(no files)":
            self.log_view.setPlainText("")
            # stop tailing when nothing selected
            self._tail_path = None
            self._tail_pos = 0
            self._tail_timer.stop()
            return
        path = os.path.join("log", date, fname)
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                data = f.read()
            self.log_view.setPlainText(data)
            # set up tailing: remember byte position and start timer
            try:
                self._tail_path = path
                self._tail_pos = os.path.getsize(path)
                if not self._tail_timer.isActive():
                    self._tail_timer.start()
            except Exception:
                self._tail_path = None
                self._tail_pos = 0
                self._tail_timer.stop()
        except Exception as e:
            self.log_view.setPlainText(f"Failed to load: {e}")
            self._tail_path = None
            self._tail_pos = 0
            self._tail_timer.stop()

    # popup for args and dispatch
    def on_execute(self):
        cmd = self.cmd_combo.currentText()
        text, ok = QtWidgets.QInputDialog.getText(self, "Args", f"Args for {cmd}:")
        if not ok:
            return
        args = text.strip()
        if cmd == "start":
            self.ui_start(args)
        elif cmd == "stop":
            self.ui_stop(args)
        elif cmd == "sendmsg":
            self.ui_sendmsg(args)
        elif cmd == "reply":
            self.ui_reply(args)
        elif cmd == "sayinvc":
            self.ui_sayinvc(args)
        elif cmd == "react":
            self.ui_react(args)

    # ------ UI command implementations (simple) ------
    def ui_start(self, argstr: str):
        if getattr(m, "bot_started", False):
            QtWidgets.QMessageBox.information(self, "Start", "Bot already running.")
            return
        # optional start message handling (simple)
        m.startmessage = argstr if argstr and argstr.lower() != "none" else None
        # create bot and run in new loop/thread
        try:
            m.bot = m.create_bot()
            m.bot_loop = asyncio.new_event_loop()
            def run_bot():
                asyncio.set_event_loop(m.bot_loop)
                try:
                    m.bot_loop.run_until_complete(m.bot.start(m.token))
                except asyncio.CancelledError:
                    pass
                except Exception:
                    m.logging.exception("Error starting bot (UI)")
            threading.Thread(target=run_bot, daemon=True).start()
            m.bot_started = True
            m.session_id = m.gen_session_id()
            QtWidgets.QMessageBox.information(self, "Start", "Bot started.")
        except Exception as e:
            m.logging.exception("Failed to start bot (UI)")
            QtWidgets.QMessageBox.critical(self, "Start failed", str(e))

    def ui_stop(self, argstr: str):
        if not getattr(m, "bot_started", False):
            QtWidgets.QMessageBox.information(self, "Stop", "Bot not running.")
            return
        # schedule shutdown coroutine
        async def _shutdown():
            try:
                if argstr:
                    await m.bot.close()
                else:
                    await m.bot.close()
            except Exception:
                m.logging.exception("Error during shutdown (UI)")
        try:
            fut = asyncio.run_coroutine_threadsafe(_shutdown(), m.bot_loop)
            fut.result(timeout=10)
        except Exception:
            m.logging.exception("Error shutting down bot (UI)")
        m.bot_started = False
        QtWidgets.QMessageBox.information(self, "Stop", "Bot stopped.")

    def ui_sendmsg(self, argstr: str):
        if not argstr:
            QtWidgets.QMessageBox.information(self, "SendMsg", "Provide message (optionally append {channel_id}).")
            return
        raw = argstr
        override = None
        if raw.endswith("}") and "{" in raw:
            mobj = re.search(r"\{(\d+)\}$", raw)
            if mobj:
                override = int(mobj.group(1))
                raw = raw[: raw.rfind("{")].strip()
        if not getattr(m, "bot_started", False):
            QtWidgets.QMessageBox.information(self, "SendMsg", "Bot not running.")
            return
        async def _send():
            try:
                ch_id = override or m.target_channel_id
                channel = m.bot.get_channel(ch_id) or await m.bot.fetch_channel(ch_id)
                text = await m.replace_placeholders(channel, raw)
                if text.strip():
                    await channel.send(text)
            except Exception:
                m.logging.exception("UI sendmsg failed")
        asyncio.run_coroutine_threadsafe(_send(), m.bot_loop)
        QtWidgets.QMessageBox.information(self, "SendMsg", "Scheduled.")

    def ui_reply(self, argstr: str):
        parts = argstr.split(None,1)
        if len(parts) < 2:
            QtWidgets.QMessageBox.information(self, "Reply", "Usage: <message_id> <text> {optional_channel}")
            return
        try:
            mid = int(parts[0])
        except ValueError:
            QtWidgets.QMessageBox.information(self, "Reply", "message_id must be integer.")
            return
        raw = parts[1]
        override = None
        if raw.endswith("}") and "{" in raw:
            mobj = re.search(r"\{(\d+)\}$", raw)
            if mobj:
                override = int(mobj.group(1))
                raw = raw[: raw.rfind("{")].strip()
        async def _reply():
            try:
                ch_id = override or m.target_channel_id
                channel = m.bot.get_channel(ch_id) or await m.bot.fetch_channel(ch_id)
                text = await m.replace_placeholders(channel, raw)
                tgt = await channel.fetch_message(mid)
                await tgt.reply(text, mention_author=False)
            except Exception:
                m.logging.exception("UI reply failed")
        asyncio.run_coroutine_threadsafe(_reply(), m.bot_loop)
        QtWidgets.QMessageBox.information(self, "Reply", "Scheduled.")

    def ui_sayinvc(self, argstr: str):
        if not argstr:
            QtWidgets.QMessageBox.information(self, "SayInVC", "Usage: <text> [ovr]")
            return
        parts = argstr.split()
        if parts[-1] in ("0","1"):
            ovr = int(parts[-1]); text = " ".join(parts[:-1])
        else:
            ovr = 1; text = argstr
        if not getattr(m, "bot_started", False):
            QtWidgets.QMessageBox.information(self, "SayInVC", "Bot not running.")
            return
        asyncio.run_coroutine_threadsafe(m.say_in_vc(m.bot, text, ovr), m.bot_loop)
        QtWidgets.QMessageBox.information(self, "SayInVC", "TTS scheduled.")

    def ui_react(self, argstr: str):
        parts = argstr.split()
        if len(parts) != 3:
            QtWidgets.QMessageBox.information(self, "React", "Usage: <channel_id> <message_id> <emoji>")
            return
        ch, mid, emoji = parts
        async def _react():
            try:
                channel = m.bot.get_channel(int(ch)) or await m.bot.fetch_channel(int(ch))
                message = await channel.fetch_message(int(mid))
                await message.add_reaction(emoji)
            except Exception:
                m.logging.exception("UI react failed")
        asyncio.run_coroutine_threadsafe(_react(), m.bot_loop)
        QtWidgets.QMessageBox.information(self, "React", "Scheduled.")

    def _tail_update(self):
        """Read appended data from the currently selected log file and append to the view."""
        path = self._tail_path
        if not path or not os.path.exists(path):
            self._tail_path = None
            self._tail_pos = 0
            self._tail_timer.stop()
            return
        try:
            cur_size = os.path.getsize(path)
            if cur_size < self._tail_pos:
                # rotated/truncated: reload full file
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    data = f.read()
                self.log_view.setPlainText(data)
                self._tail_pos = cur_size
                return
            if cur_size == self._tail_pos:
                return
            # read appended bytes
            with open(path, "rb") as f:
                f.seek(self._tail_pos)
                new_bytes = f.read()
            if not new_bytes:
                self._tail_pos = cur_size
                return
            try:
                new_text = new_bytes.decode("utf-8")
            except Exception:
                new_text = new_bytes.decode("utf-8", errors="replace")
            # append and scroll to bottom
            self.log_view.moveCursor(QtWidgets.QTextCursor.End) if hasattr(QtWidgets, "QTextCursor") else None
            # append preserving text (use appendPlainText to avoid clearing)
            self.log_view.appendPlainText(new_text)
            self.log_view.verticalScrollBar().setValue(self.log_view.verticalScrollBar().maximum())
            self._tail_pos = cur_size
        except Exception:
            # stop tailing on repeated error
            self._tail_timer.stop()

def main():
    app = QtWidgets.QApplication(sys.argv)
    w = BotMainWindow()
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()