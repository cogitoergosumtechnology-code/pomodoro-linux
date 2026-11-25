"""Wrapper de hyprctl: monitores, cliente e posicionamento da janela."""

import json
import subprocess

from . import WM_CLASS
from .log import log

_SELECTOR = f"class:^({WM_CLASS})$"
_failed_once = False


def _run(args):
    global _failed_once
    try:
        r = subprocess.run(["hyprctl", *args], capture_output=True, text=True, timeout=2)
        if r.returncode != 0:
            raise RuntimeError((r.stderr or r.stdout).strip())
        return r.stdout
    except Exception as e:
        if not _failed_once:
            _failed_once = True
            log(f"hyprctl falhou ({' '.join(args)}): {e}")
        return None


def _json(cmd):
    out = _run([cmd, "-j"])
    if out is None:
        return None
    try:
        return json.loads(out)
    except Exception as e:
        log(f"hyprctl {cmd}: json invalido: {e}")
        return None


def monitors():
    """Monitores ativos ordenados por id ([] fora do Hyprland)."""
    data = _json("monitors")
    if not isinstance(data, list):
        return []
    return sorted((m for m in data if not m.get("disabled")), key=lambda m: m.get("id", 0))


def usable_area(m):
    """(left, top, right, bottom) em pixels lógicos, já sem a área reservada."""
    scale = m.get("scale") or 1.0
    w, h = m["width"] / scale, m["height"] / scale
    if m.get("transform", 0) % 2 == 1:
        w, h = h, w
    res = m.get("reserved") or [0, 0, 0, 0]
    left, top, right, bottom = (list(res) + [0, 0, 0, 0])[:4]
    return (m["x"] + left, m["y"] + top, m["x"] + w - right, m["y"] + h - bottom)


def client():
    """Janela do widget como o Hyprland a vê (None se não mapeada)."""
    data = _json("clients")
    if not isinstance(data, list):
        return None
    for c in data:
        if c.get("class") == WM_CLASS and c.get("mapped", True):
            return c
    return None


def _dispatch(lua_expr, legacy):
    """Hyprland 0.55+ (config Lua) recebe expressões; versões antigas, dispatchers."""
    out = _run(["dispatch", lua_expr])
    if out is not None and out.strip() == "ok":
        return True
    out2 = _run(["dispatch", *legacy])
    if out2 is not None and out2.strip() == "ok":
        return True
    log(f"hyprctl dispatch falhou: {(out or out2 or '').strip()}")
    return False


def move_exact(x, y):
    x, y = int(round(x)), int(round(y))
    return _dispatch(
        f'hl.dsp.window.move({{ x = {x}, y = {y}, window = "{_SELECTOR}" }})',
        ["movewindowpixel", f"exact {x} {y},{_SELECTOR}"],
    )


def move_to_monitor(name):
    safe = str(name).replace("\\", "").replace('"', "")
    return _dispatch(
        f'hl.dsp.window.move({{ monitor = "{safe}", window = "{_SELECTOR}" }})',
        ["movewindow", f"mon:{safe},{_SELECTOR}"],
    )
