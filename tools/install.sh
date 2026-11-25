#!/usr/bin/env bash
# Instala o Pomodoro para o usuário atual (idempotente, sem sudo).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}"
BIN="$HOME/.local/bin"
PY=/usr/bin/python3
[ -x "$PY" ] || PY="$(command -v python3 || true)"

echo "== Dependências"
missing=()
[ -n "$PY" ] || missing+=(python)
if [ -n "$PY" ]; then
  "$PY" -c "import gi; gi.require_version('Gtk','4.0'); from gi.repository import Gtk" 2>/dev/null || missing+=(python-gobject gtk4)
  "$PY" -c "import gi; gi.require_version('Gtk4LayerShell','1.0'); from gi.repository import Gtk4LayerShell" 2>/dev/null || missing+=(gtk4-layer-shell)
fi
command -v hyprctl >/dev/null || missing+=(hyprland)
command -v pw-play >/dev/null || missing+=(pipewire)
if [ ${#missing[@]} -gt 0 ]; then
  echo "Faltam pacotes. Instale com:"
  echo "  sudo pacman -S ${missing[*]}"
  [ -n "$PY" ] || exit 1
else
  echo "ok"
fi

echo "== Aplicativo"
# Sem pip/pipx no Omarchy: o pacote vai para ~/.local/share/pomodoro e um
# lançador em ~/.local/bin o executa com o Python do sistema.
mkdir -p "$DATA/pomodoro" "$BIN"
rm -rf "$DATA/pomodoro/pomodoro"
cp -r "$ROOT/pomodoro" "$DATA/pomodoro/pomodoro"
find "$DATA/pomodoro" -name __pycache__ -type d -prune -exec rm -rf {} +
cat > "$BIN/pomodoro" <<LAUNCHER
#!/bin/sh
PYTHONPATH="$DATA/pomodoro\${PYTHONPATH:+:\$PYTHONPATH}" exec $PY -m pomodoro "\$@"
LAUNCHER
chmod +x "$BIN/pomodoro"
echo "$BIN/pomodoro"

echo "== Lançador e ícone"
mkdir -p "$DATA/applications"
cp "$ROOT/data/pomodoro.desktop" "$DATA/applications/pomodoro.desktop"
"$PY" "$ROOT/tools/make-icon.py"
command -v update-desktop-database >/dev/null && update-desktop-database -q "$DATA/applications" || true

echo "== Serviço systemd (desabilitado até marcar \"Iniciar com o Omarchy\")"
mkdir -p "$CONFIG/systemd/user"
cp "$ROOT/data/pomodoro.service" "$CONFIG/systemd/user/pomodoro.service"
systemctl --user daemon-reload || true

echo "== Regras do Hyprland"
HYPR="$CONFIG/hypr"
if [ -f "$HYPR/hyprland.lua" ]; then
  cp "$ROOT/data/hypr-pomodoro.lua" "$HYPR/pomodoro.lua"
  if ! grep -q 'require("hypr.pomodoro")' "$HYPR/hyprland.lua"; then
    cp "$HYPR/hyprland.lua" "$HYPR/hyprland.lua.bak.$(date +%s)"
    printf '\n-- Pomodoro widget\nrequire("hypr.pomodoro")\n' >> "$HYPR/hyprland.lua"
  fi
elif [ -f "$HYPR/hyprland.conf" ]; then
  cp "$ROOT/data/hypr-pomodoro.conf" "$HYPR/pomodoro.conf"
  grep -q 'source = ~/.config/hypr/pomodoro.conf' "$HYPR/hyprland.conf" ||
    printf '\nsource = ~/.config/hypr/pomodoro.conf\n' >> "$HYPR/hyprland.conf"
else
  echo "config do Hyprland não encontrada; regras em $ROOT/data/"
fi
if command -v hyprctl >/dev/null && hyprctl reload >/dev/null 2>&1; then
  errors="$(hyprctl configerrors 2>/dev/null || true)"
  [ -z "$errors" ] && echo "ok" || { echo "hyprctl configerrors:"; echo "$errors"; }
fi

echo "== Barra"
if [ -d "$CONFIG/omarchy/plugins" ]; then
  mkdir -p "$CONFIG/omarchy/plugins/aurelio.pomodoro"
  cp "$ROOT/data/omarchy-plugin/"* "$CONFIG/omarchy/plugins/aurelio.pomodoro/"
  echo "Plugin instalado. Para colocar na barra:"
  echo "  omarchy bar put aurelio.pomodoro --section right --index 0"
else
  echo "Waybar: mescle o trecho abaixo em ~/.config/waybar/config.jsonc"
  cat "$ROOT/data/waybar-pomodoro.jsonc"
fi

cat <<'TXT'

== Atalhos sugeridos (~/.config/hypr/bindings.lua)
  o.bind("SUPER + SHIFT + P", "Pomodoro mostrar/esconder", "pomodoro toggle")
  o.bind("SUPER + SHIFT + O", "Pomodoro iniciar/pausar", "pomodoro start-pause")

Pronto. Rode: pomodoro
TXT
