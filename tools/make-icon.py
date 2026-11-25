#!/usr/bin/env python3
"""Renderiza data/icons/pomodoro.svg em PNGs do tema hicolor do usuário."""

import os
import shutil
import subprocess
import sys

SIZES = (16, 24, 32, 48, 64, 128, 256)
HERE = os.path.dirname(os.path.abspath(__file__))
SVG = os.path.join(HERE, "..", "data", "icons", "pomodoro.svg")


def render(size, out):
    if shutil.which("rsvg-convert"):
        subprocess.run(["rsvg-convert", "-w", str(size), "-h", str(size), "-o", out, SVG], check=True)
        return
    import cairosvg  # type: ignore

    cairosvg.svg2png(url=SVG, write_to=out, output_width=size, output_height=size)


def main():
    data = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    base = os.path.join(data, "icons", "hicolor")
    for size in SIZES:
        d = os.path.join(base, f"{size}x{size}", "apps")
        os.makedirs(d, exist_ok=True)
        try:
            render(size, os.path.join(d, "pomodoro.png"))
        except Exception as e:
            print(f"aviso: PNG {size}px nao gerado: {e}", file=sys.stderr)
    d = os.path.join(base, "scalable", "apps")
    os.makedirs(d, exist_ok=True)
    shutil.copyfile(SVG, os.path.join(d, "pomodoro.svg"))
    if shutil.which("gtk-update-icon-cache"):
        subprocess.run(["gtk-update-icon-cache", "-q", "-t", "-f", base], check=False)


if __name__ == "__main__":
    main()
