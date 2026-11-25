"""Gtk.Application: ciclo de vida, alarmes, inibição e servidor IPC."""

import signal

from gi.repository import Gdk, Gio, GLib, Gtk

from . import hypr, ipc
from .alarm_window import CSS as ALARM_CSS, AlarmWindow
from .config import Config
from .inhibit import KeepAwake
from .log import log
from .main_window import MainWindow
from .phrases import next_phrase
from .waybar import remove_state


class PomodoroApp(Gtk.Application):
    def __init__(self):
        # Sem application_id: o GTK4 usaria o id como app-id Wayland, e a classe
        # da janela precisa ser "pomodoro" (vem do prgname). A instância única
        # é garantida pelo socket IPC.
        super().__init__(application_id=None, flags=Gio.ApplicationFlags.NON_UNIQUE)
        self.cfg = None
        self.window = None
        self.awake = None
        self.server = None
        self._alarms = []
        self._closing_alarms = False
        self._quitting = False

    # ------------------------------------------------------------ ciclo de vida
    def do_startup(self):
        Gtk.Application.do_startup(self)
        self.cfg = Config.load()
        self.awake = KeepAwake(self)

        css = Gtk.CssProvider()
        css.load_from_string(ALARM_CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1
        )

        for sig in (signal.SIGTERM, signal.SIGINT):
            GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, sig, self._on_signal)

        try:
            self.server = ipc.Server(self._on_command)
        except Exception as e:
            log(f"falha ao abrir o socket IPC: {e}")

        try:
            Gdk.Display.get_default().get_monitors().connect("items-changed", self._on_monitors_changed)
        except Exception as e:
            log(f"falha ao observar monitores: {e}")

    def do_activate(self):
        if self.window is None:
            self.window = MainWindow(self, self.cfg)
            self.window.connect("map", lambda *_: self.update_awake())
        self.window.show_widget()

    def do_shutdown(self):
        self._cleanup()
        Gtk.Application.do_shutdown(self)

    def _on_signal(self):
        self.quit_app()
        return GLib.SOURCE_REMOVE

    def quit_app(self):
        if self._quitting:
            return
        self._quitting = True
        self._cleanup()
        self.quit()

    def _cleanup(self):
        self.close_alarms()
        if self.window is not None:
            self.window.shutdown()
        if self.awake is not None:
            self.awake.set(False)
        if self.server is not None:
            self.server.close()
            self.server = None
        remove_state()

    def _on_monitors_changed(self, *_):
        if self.window is not None:
            GLib.timeout_add(500, lambda: (self.window.reposition(snap=False), False)[1])

    # ----------------------------------------------------------------- inibição
    def update_awake(self):
        if self.awake is None or self.window is None or self._quitting:
            return
        want = self.window.running and self.cfg.KeepAwake
        self.awake.set(want, [self.window, *self._alarms])

    # ------------------------------------------------------------------- alarme
    def _target_monitors(self):
        mons = Gdk.Display.get_default().get_monitors()
        gdk_mons = [mons.get_item(i) for i in range(mons.get_n_items())]
        if self.cfg.FlashAllScreens or len(gdk_mons) <= 1:
            return gdk_mons
        hmons = hypr.monitors()
        idx = self.cfg.ScreenIndex
        if hmons:
            if not 0 <= idx < len(hmons):
                idx = 0
            name = hmons[idx].get("name")
            for m in gdk_mons:
                if m.get_connector() == name:
                    return [m]
        if not 0 <= idx < len(gdk_mons):
            idx = 0
        return [gdk_mons[idx]]

    def fire_alarm(self, message):
        self.close_alarms()
        phrase = next_phrase()  # a mesma frase em todas as telas
        for mon in self._target_monitors():
            try:
                win = AlarmWindow(self, mon, message, phrase, self.close_alarms)
                self._alarms.append(win)
                win.present()
            except Exception as e:
                log(f"falha ao abrir alarme: {e}")

    def close_alarms(self):
        if self._closing_alarms:
            return
        self._closing_alarms = True
        try:
            alarms, self._alarms = self._alarms, []
            for win in alarms:
                try:
                    win.dismiss()
                except Exception as e:
                    log(f"falha ao fechar alarme: {e}")
        finally:
            self._closing_alarms = False

    # ---------------------------------------------------------------------- IPC
    def _on_command(self, cmd):
        w = self.window
        if w is None:
            return "err ainda iniciando"
        if cmd == "show":
            w.show_widget()
        elif cmd == "hide":
            w.hide_widget()
        elif cmd == "toggle":
            w.toggle_visible()
        elif cmd == "start-pause":
            w.toggle_run()
        elif cmd == "reset":
            w.reset()
        elif cmd == "skip":
            w.next_phase(False)
        elif cmd == "compact":
            w.toggle_compact()
        elif cmd == "menu":
            if not w.get_visible():
                w.show_widget()
            GLib.timeout_add(150, lambda: (w.open_menu(), False)[1])
        elif cmd == "alarm":
            self.fire_alarm("TESTE")
        elif cmd == "status":
            return "ok " + w.status_text()
        elif cmd == "quit":
            GLib.idle_add(lambda: (self.quit_app(), False)[1])
        else:
            return f"err comando desconhecido: {cmd}"
        return "ok"
