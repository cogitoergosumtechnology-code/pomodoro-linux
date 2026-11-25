# Pomodoro Widget — Omarchy / Hyprland

Port do `Pomodoro.exe` (Windows) para Linux: widget flutuante sem borda no canto
inferior direito, fases FOCO/PAUSA, alarme de tela cheia piscando com frase de
mindfulness e bipe. Python 3 + GTK 4 + gtk4-layer-shell.

## Instalar

```bash
tools/install.sh
```

Instala só para o usuário atual, sem sudo: `~/.local/bin/pomodoro`, o pacote em
`~/.local/share/pomodoro/`, `.desktop`, ícones, `pomodoro.service` (desabilitado)
e as regras de janela do Hyprland. `tools/uninstall.sh` desfaz.

Dependências (Arch): `python python-gobject gtk4 gtk4-layer-shell pipewire`.

## Usar

`pomodoro` inicia (ou mostra a instância que já roda). Comandos:

| Comando | Ação |
|---|---|
| `show` / `hide` / `toggle` | mostrar (encaixa no canto), esconder, alternar |
| `start-pause` | iniciar/pausar |
| `reset` | reiniciar a fase |
| `skip` | próxima fase, sem alarme |
| `compact` | modo compacto |
| `menu` | abrir o menu de contexto |
| `alarm` | testar o alarme |
| `status` | `Pomodoro {FASE} {MM}:{SS} {running\|paused}` |
| `quit` | encerrar |

No widget: clique em MM ou SS para editar (Enter grava, Esc cancela, Tab troca de
campo); botão direito abre o menu; arraste pelo fundo.

Atalhos sugeridos em `~/.config/hypr/bindings.lua`:

```lua
o.bind("SUPER + SHIFT + P", "Pomodoro mostrar/esconder", "pomodoro toggle")
o.bind("SUPER + SHIFT + O", "Pomodoro iniciar/pausar", "pomodoro start-pause")
```

## Arquivos

- Config: `~/.config/pomodoro/config.json` (mesmas chaves do Windows; um
  `config.json` copiado de lá funciona).
- Log: `~/.local/state/pomodoro/pomodoro.log`.
- Estado para a barra: `$XDG_RUNTIME_DIR/pomodoro.json`; socket:
  `$XDG_RUNTIME_DIR/pomodoro.sock`.

## Diferenças em relação à spec (ambiente Omarchy atual)

A spec foi escrita para Waybar + `hyprland.conf`. O Omarchy atual usa o shell
Quickshell e Hyprland com config em Lua, então:

- **Bandeja:** plugin de barra `aurelio.pomodoro` (`data/omarchy-plugin/`), que lê
  o mesmo arquivo de estado. Clique esquerdo `toggle`, direito `menu`, meio
  `start-pause`. Colocar na barra: `omarchy bar put aurelio.pomodoro --section right --index 0`.
  O trecho para Waybar continua em `data/waybar-pomodoro.jsonc`.
- **Regras de janela:** `~/.config/hypr/pomodoro.lua` + `require("hypr.pomodoro")`
  no `hyprland.lua`. A variante `.conf` é usada se existir `hyprland.conf`.
- **Posicionamento:** `hyprctl dispatch 'hl.dsp.window.move({...})'`, com fallback
  para `movewindowpixel`/`movewindow` em versões antigas.
- **Instalação:** sem pip/pipx; um lançador em `~/.local/bin` roda o pacote com o
  Python do sistema.
- **Manter acordado:** além do `login1` (`idle:sleep`, visível em
  `systemd-inhibit --list`) e do `org.freedesktop.ScreenSaver`, usa o protocolo
  idle-inhibit do Wayland, que é o que o shell do Omarchy honra. Esse último
  depende de a janela estar visível: com o widget escondido, o protetor de tela
  do Omarchy não é inibido (a suspensão continua bloqueada).
- **App id:** a aplicação GTK não define `application_id`, para que a classe
  Wayland seja `pomodoro`.
- **Alarme:** só fecha na soltura de uma tecla pressionada com o alarme já aberto.

Sem uwsm/systemd: `o.launch_on_start("pomodoro")` em `~/.config/hypr/autostart.lua`.
