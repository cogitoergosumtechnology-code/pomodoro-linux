"""Iniciar com o sistema: systemd --user pomodoro.service."""

import subprocess

from .log import log

UNIT = "pomodoro.service"


def is_enabled():
    try:
        r = subprocess.run(
            ["systemctl", "--user", "is-enabled", UNIT],
            capture_output=True, text=True, timeout=2,
        )
        return r.stdout.strip() == "enabled"
    except Exception as e:
        log(f"systemctl is-enabled falhou: {e}")
        return False


def set_enabled(on):
    """Habilita/desabilita sem iniciar/parar. Devolve None ou a mensagem de erro."""
    try:
        r = subprocess.run(
            ["systemctl", "--user", "enable" if on else "disable", UNIT],
            capture_output=True, text=True, timeout=2,
        )
        if r.returncode != 0:
            msg = (r.stderr or r.stdout).strip() or f"systemctl saiu com código {r.returncode}"
            log(f"falha no autostart: {msg}")
            return msg
        return None
    except Exception as e:
        log(f"falha no autostart: {e}")
        return str(e)
