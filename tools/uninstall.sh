#!/usr/bin/env bash
# Desfaz o install.sh (a configuração em ~/.config/pomodoro é mantida).
set -uo pipefail

DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}"

[ -x "$HOME/.local/bin/pomodoro" ] && "$HOME/.local/bin/pomodoro" quit >/dev/null 2>&1
systemctl --user disable --now pomodoro.service >/dev/null 2>&1
rm -f "$CONFIG/systemd/user/pomodoro.service"
systemctl --user daemon-reload >/dev/null 2>&1

rm -f "$HOME/.local/bin/pomodoro" "$DATA/applications/pomodoro.desktop"
rm -rf "$DATA/pomodoro"
rm -f "$DATA/icons/hicolor/scalable/apps/pomodoro.svg"
for n in 16 24 32 48 64 128 256; do rm -f "$DATA/icons/hicolor/${n}x${n}/apps/pomodoro.png"; done

HYPR="$CONFIG/hypr"
if [ -f "$HYPR/hyprland.lua" ]; then
  sed -i '/^-- Pomodoro widget$/d; /^require("hypr.pomodoro")$/d' "$HYPR/hyprland.lua"
fi
if [ -f "$HYPR/hyprland.conf" ]; then
  sed -i '\|^source = ~/.config/hypr/pomodoro.conf$|d' "$HYPR/hyprland.conf"
fi
rm -f "$HYPR/pomodoro.lua" "$HYPR/pomodoro.conf"
command -v hyprctl >/dev/null && hyprctl reload >/dev/null 2>&1

if [ -d "$CONFIG/omarchy/plugins/aurelio.pomodoro" ]; then
  rm -rf "$CONFIG/omarchy/plugins/aurelio.pomodoro"
  echo "Remova {\"id\": \"aurelio.pomodoro\"} de $CONFIG/omarchy/shell.json se estiver na barra."
fi
echo "Pomodoro desinstalado."
