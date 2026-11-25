"""Manter o PC acordado enquanto o timer conta.

Três mecanismos, todos tolerantes a falha:
1. org.freedesktop.ScreenSaver.Inhibit (D-Bus de sessão; hypridle e afins).
2. org.freedesktop.login1.Manager.Inhibit("idle:sleep") (aparece em
   `systemd-inhibit --list`; bloqueia a suspensão).
3. Protocolo idle-inhibit do Wayland via Gtk.Application.inhibit — é o que o
   shell do Omarchy (Quickshell IdleMonitor, respectInhibitors) honra para não
   abrir o protetor de tela nem bloquear.
"""

import os

from gi.repository import Gio, GLib, Gtk

from .log import log

APP = "Pomodoro"
REASON = "Pomodoro em andamento"
_TIMEOUT_MS = 2000


class KeepAwake:
    def __init__(self, app):
        self._app = app
        self.held = False
        self._cookie = None
        self._fd = None
        self._gtk_cookies = []
        self._logged = set()

    def _log_once(self, key, msg):
        if key not in self._logged:
            self._logged.add(key)
            log(msg)

    def set(self, want, windows=()):
        if want == self.held:
            if want:
                self._gtk_refresh(windows)
            return
        self.held = want
        if want:
            self._screensaver_inhibit()
            self._logind_inhibit()
            self._gtk_refresh(windows)
        else:
            self._screensaver_uninhibit()
            self._logind_release()
            self._gtk_release()

    # --- org.freedesktop.ScreenSaver -------------------------------------
    def _screensaver_inhibit(self):
        try:
            bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            res = bus.call_sync(
                "org.freedesktop.ScreenSaver", "/org/freedesktop/ScreenSaver",
                "org.freedesktop.ScreenSaver", "Inhibit",
                GLib.Variant("(ss)", (APP, REASON)), GLib.VariantType("(u)"),
                Gio.DBusCallFlags.NONE, _TIMEOUT_MS, None,
            )
            self._cookie = res.unpack()[0]
        except Exception as e:
            self._cookie = None
            self._log_once("ss", f"ScreenSaver.Inhibit indisponivel: {e}")

    def _screensaver_uninhibit(self):
        if self._cookie is None:
            return
        try:
            bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            bus.call_sync(
                "org.freedesktop.ScreenSaver", "/org/freedesktop/ScreenSaver",
                "org.freedesktop.ScreenSaver", "UnInhibit",
                GLib.Variant("(u)", (self._cookie,)), None,
                Gio.DBusCallFlags.NONE, _TIMEOUT_MS, None,
            )
        except Exception as e:
            log(f"ScreenSaver.UnInhibit falhou: {e}")
        self._cookie = None

    # --- org.freedesktop.login1 ------------------------------------------
    def _logind_inhibit(self):
        try:
            bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
            res, fds = bus.call_with_unix_fd_list_sync(
                "org.freedesktop.login1", "/org/freedesktop/login1",
                "org.freedesktop.login1.Manager", "Inhibit",
                GLib.Variant("(ssss)", ("idle:sleep", APP, REASON, "block")),
                GLib.VariantType("(h)"),
                Gio.DBusCallFlags.NONE, _TIMEOUT_MS, None, None,
            )
            self._fd = fds.get(res.unpack()[0])
        except Exception as e:
            self._fd = None
            self._log_once("logind", f"login1.Inhibit falhou: {e}")

    def _logind_release(self):
        if self._fd is not None:
            try:
                os.close(self._fd)
            except OSError:
                pass
            self._fd = None

    # --- Wayland idle-inhibit (por superfície visível) --------------------
    def _gtk_release(self):
        for cookie in self._gtk_cookies:
            try:
                self._app.uninhibit(cookie)
            except Exception:
                pass
        self._gtk_cookies = []

    def _gtk_refresh(self, windows):
        self._gtk_release()
        for w in windows:
            try:
                if w is None or not w.get_mapped():
                    continue
                cookie = self._app.inhibit(
                    w, Gtk.ApplicationInhibitFlags.IDLE | Gtk.ApplicationInhibitFlags.SUSPEND, REASON
                )
                if cookie:
                    self._gtk_cookies.append(cookie)
            except Exception as e:
                self._log_once("gtk", f"Gtk inhibit falhou: {e}")
