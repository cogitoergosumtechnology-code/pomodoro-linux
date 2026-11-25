"""Arquivo de estado da "bandeja" ($XDG_RUNTIME_DIR/pomodoro.json).

Formato do módulo custom do Waybar (return-type json); o widget de barra do
Omarchy shell lê o mesmo arquivo.
"""

import json
import os


def state_path():
    base = os.environ.get("XDG_RUNTIME_DIR") or "/tmp"
    return os.path.join(base, "pomodoro.json")


def write_state(mm_ss, phase, is_break, running):
    try:
        path = state_path()
        data = {
            "text": mm_ss,
            "tooltip": f"Pomodoro {phase} {mm_ss}",
            "class": "break" if is_break else "focus",
            "alt": "running" if running else "paused",
        }
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp, path)
    except Exception:
        pass


def remove_state():
    try:
        os.unlink(state_path())
    except OSError:
        pass
