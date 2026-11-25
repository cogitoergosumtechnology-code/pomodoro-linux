"""Configuração persistente (~/.config/pomodoro/config.json), mesmas chaves do Windows."""

import json
import os

from .log import log

DEFAULT_PRESETS = [15, 20, 25, 40, 50]


def config_path():
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, "pomodoro", "config.json")


def _int(v, default):
    return v if isinstance(v, int) and not isinstance(v, bool) else default


def _bool(v, default):
    return v if isinstance(v, bool) else default


class Config:
    def __init__(self):
        self.ScreenIndex = 0
        self.FocusSeconds = 1500
        self.BreakSeconds = 300
        self.Presets = list(DEFAULT_PRESETS)
        self.FlashAllScreens = True
        self.Scale = 1.0
        self.KeepAwake = True

    @classmethod
    def load(cls):
        c = cls()
        try:
            # utf-8-sig: o config.json gravado pelo Windows pode vir com BOM
            with open(config_path(), encoding="utf-8-sig") as f:
                d = json.load(f)
            if not isinstance(d, dict):
                return c
            c.ScreenIndex = _int(d.get("ScreenIndex"), c.ScreenIndex)
            c.FocusSeconds = _int(d.get("FocusSeconds"), c.FocusSeconds)
            c.BreakSeconds = _int(d.get("BreakSeconds"), c.BreakSeconds)
            p = d.get("Presets")
            if isinstance(p, list):
                p = [v for v in p if isinstance(v, int) and not isinstance(v, bool) and v > 0]
                if p:
                    c.Presets = p
            c.FlashAllScreens = _bool(d.get("FlashAllScreens"), c.FlashAllScreens)
            s = d.get("Scale")
            if isinstance(s, (int, float)) and not isinstance(s, bool):
                c.Scale = float(s)
            c.KeepAwake = _bool(d.get("KeepAwake"), c.KeepAwake)
        except Exception:
            return cls()
        return c

    @property
    def scale(self):
        return min(3.0, max(0.75, self.Scale))

    def save(self):
        try:
            path = config_path()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            data = {
                "ScreenIndex": self.ScreenIndex,
                "FocusSeconds": self.FocusSeconds,
                "BreakSeconds": self.BreakSeconds,
                "Presets": self.Presets,
                "FlashAllScreens": self.FlashAllScreens,
                "Scale": self.Scale,
                "KeepAwake": self.KeepAwake,
            }
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
                f.write("\n")
            os.replace(tmp, path)
        except Exception as e:
            log(f"falha ao salvar config: {e}")
