"""Log em ~/.local/state/pomodoro/pomodoro.log (nunca lança exceção)."""

import os
import sys
import traceback
from datetime import datetime


def _path():
    base = os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state")
    return os.path.join(base, "pomodoro", "pomodoro.log")


def log(msg):
    try:
        path = _path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        stamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{stamp} {msg}\n")
    except Exception:
        pass


def install_handlers():
    def hook(etype, value, tb):
        log("excecao nao tratada: " + "".join(traceback.format_exception(etype, value, tb)).rstrip())

    sys.excepthook = hook
    try:
        from gi.repository import GLib

        def glib_handler(domain, level, message, *_):
            log(f"glib [{domain}] {message}")

        flags = GLib.LogLevelFlags.LEVEL_CRITICAL | GLib.LogLevelFlags.LEVEL_ERROR
        for domain in (None, "Gtk", "Gdk", "GLib", "GLib-GObject", "GLib-GIO"):
            GLib.log_set_handler(domain, flags, glib_handler)
    except Exception:
        pass
