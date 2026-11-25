"""Entrada: CLI, instância única e Gtk.Application."""

import sys

from . import WM_CLASS, __version__, ipc

USAGE = """uso: pomodoro [comando]

Sem comando: inicia o widget (ou mostra o que já está rodando).

Comandos (enviados à instância ativa):
  show          mostra e encaixa no canto
  hide          esconde (continua rodando)
  toggle        alterna mostrar/esconder
  start-pause   inicia/pausa a contagem
  reset         reinicia a fase atual
  skip          pula para a próxima fase, sem alarme
  compact       alterna o modo compacto
  menu          abre o menu de contexto
  alarm         testa o alarme
  status        imprime "Pomodoro {FASE} {MM}:{SS} {running|paused}"
  quit          encerra
"""


def _client(cmd):
    reply = ipc.send(cmd)
    if reply is None:
        print("pomodoro: não está rodando", file=sys.stderr)
        return 1
    if reply.startswith("err"):
        print(f"pomodoro: {reply[3:].strip()}", file=sys.stderr)
        return 1
    rest = reply[2:].strip()
    if rest:
        print(rest)
    return 0


def _run_app():
    # gtk4-layer-shell precisa ser carregada antes da libwayland-client
    try:
        from ctypes import CDLL

        CDLL("libgtk4-layer-shell.so")
    except OSError:
        pass

    import gi

    gi.require_version("Gtk", "4.0")
    gi.require_version("Gdk", "4.0")
    gi.require_version("Graphene", "1.0")
    from gi.repository import GLib

    GLib.set_prgname(WM_CLASS)
    GLib.set_application_name("Pomodoro")

    from .log import install_handlers

    install_handlers()

    from .app import PomodoroApp

    return PomodoroApp().run([])


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in ("-h", "--help", "help"):
        print(USAGE, end="")
        return 0
    if args and args[0] in ("-V", "--version"):
        print(__version__)
        return 0
    if args:
        if args[0] not in ipc.COMMANDS:
            print(f"pomodoro: comando desconhecido: {args[0]}\n", file=sys.stderr)
            print(USAGE, end="", file=sys.stderr)
            return 2
        return _client(args[0])

    # instância única: se o socket responde, apenas mostra o widget
    if ipc.send("show") is not None:
        return 0
    return _run_app()


if __name__ == "__main__":
    sys.exit(main())
