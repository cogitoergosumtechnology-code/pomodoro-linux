"""Bipe equivalente a Console.Beep(880, 200), sem bloquear a UI."""

import io
import math
import os
import shutil
import struct
import subprocess
import wave

from .log import log

_RATE = 44100


def _wav_bytes(freq=880, ms=200, amp=0.5):
    n = int(_RATE * ms / 1000)
    fade = int(_RATE * 0.005)
    frames = bytearray()
    for i in range(n):
        env = min(1.0, i / fade, (n - 1 - i) / fade)
        v = amp * env * math.sin(2 * math.pi * freq * i / _RATE)
        frames += struct.pack("<h", int(v * 32767))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(_RATE)
        w.writeframes(bytes(frames))
    return buf.getvalue()


def _wav_file():
    # pw-play precisa de um arquivo com seek para detectar o formato; o WAV é
    # gerado em memória e deixado no diretório de runtime (tmpfs).
    base = os.environ.get("XDG_RUNTIME_DIR") or "/tmp"
    path = os.path.join(base, "pomodoro-beep.wav")
    if not os.path.exists(path):
        tmp = path + ".tmp"
        with open(tmp, "wb") as f:
            f.write(_wav_bytes())
        os.replace(tmp, path)
    return path


def beep():
    try:
        path = _wav_file()
        for player in ("pw-play", "paplay", "aplay"):
            exe = shutil.which(player)
            if not exe:
                continue
            args = [exe, "-q", path] if player == "aplay" else [exe, path]
            subprocess.Popen(
                args,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            return
    except Exception as e:
        log(f"falha no bipe: {e}")
