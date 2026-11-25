"""Alarme de tela cheia piscando (uma superfície layer-shell por monitor)."""

from gi.repository import Gdk, GLib, Gtk, Pango

from . import ALARM_CLASS
from .log import log
from .sound import beep

try:
    import gi

    gi.require_version("Gtk4LayerShell", "1.0")
    from gi.repository import Gtk4LayerShell as LayerShell
except Exception:  # fallback: janela toplevel em tela cheia
    LayerShell = None

HINT = "clique ou pressione uma tecla para fechar"

CSS = """
window.pomodoro-alarm { background: #FF0000; color: #FFFFFF; }
window.pomodoro-alarm.black { background: #000000; }
window.pomodoro-alarm .alarm-msg { font-family: sans-serif; font-weight: bold; font-size: 48pt; color: #FFFFFF; }
window.pomodoro-alarm .alarm-phrase { font-family: sans-serif; font-weight: normal; font-size: 26pt; color: #FFFFFF; }
window.pomodoro-alarm .alarm-hint { font-family: sans-serif; font-style: italic; font-size: 14pt; color: #FFE6E6; }
"""


class AlarmWindow(Gtk.Window):
    def __init__(self, app, monitor, message, phrase, on_close):
        super().__init__(application=app, title="Pomodoro")
        self._on_close = on_close
        self._blink_id = 0
        self._black = False
        self._keys_down = set()
        self._closed = False
        self.add_css_class("pomodoro-alarm")
        self.set_decorated(False)

        geo = monitor.get_geometry()
        w, h = geo.width, geo.height

        self._layer = False
        if LayerShell is not None and LayerShell.is_supported():
            try:
                LayerShell.init_for_window(self)
                LayerShell.set_namespace(self, ALARM_CLASS)
                LayerShell.set_layer(self, LayerShell.Layer.OVERLAY)
                LayerShell.set_monitor(self, monitor)
                for edge in (LayerShell.Edge.TOP, LayerShell.Edge.BOTTOM,
                             LayerShell.Edge.LEFT, LayerShell.Edge.RIGHT):
                    LayerShell.set_anchor(self, edge, True)
                LayerShell.set_exclusive_zone(self, -1)
                LayerShell.set_keyboard_mode(self, LayerShell.KeyboardMode.EXCLUSIVE)
                self._layer = True
            except Exception as e:
                log(f"layer-shell falhou, usando fallback: {e}")
        if not self._layer:
            self.set_default_size(w, h)
            self.fullscreen_on_monitor(monitor)

        # 3 linhas: 30% / 55% / 15% da área interna
        pad_h, pad_top, pad_bottom = w // 10, h // 12, h // 16
        inner_h = max(1, h - pad_top - pad_bottom)
        inner_w = max(1, w - 2 * pad_h)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.set_margin_start(pad_h)
        box.set_margin_end(pad_h)
        box.set_margin_top(pad_top)
        box.set_margin_bottom(pad_bottom)

        def row(text, css, frac, wrap=False):
            lbl = Gtk.Label(label=text)
            lbl.add_css_class(css)
            lbl.set_justify(Gtk.Justification.CENTER)
            lbl.set_halign(Gtk.Align.FILL)
            lbl.set_valign(Gtk.Align.FILL)
            lbl.set_xalign(0.5)
            lbl.set_yalign(0.5)
            if wrap:
                lbl.set_wrap(True)
                lbl.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
            # o overflow fica cortado em vez de empurrar as outras linhas
            wrapper = Gtk.ScrolledWindow()
            wrapper.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.EXTERNAL)
            wrapper.set_child(lbl)
            wrapper.set_size_request(inner_w, int(inner_h * frac))
            wrapper.set_can_target(False)
            box.append(wrapper)

        row(message, "alarm-msg", 0.30)
        row(phrase, "alarm-phrase", 0.55, wrap=True)
        row(HINT, "alarm-hint", 0.15)
        self.set_child(box)
        self.set_cursor(Gdk.Cursor.new_from_name("pointer"))

        click = Gtk.GestureClick()
        click.set_button(0)
        click.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        click.connect("pressed", lambda *_: self._request_close())
        self.add_controller(click)

        keys = Gtk.EventControllerKey()
        keys.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        keys.connect("key-pressed", self._on_key_pressed)
        keys.connect("key-released", self._on_key_released)
        self.add_controller(keys)

        self.connect("close-request", self._on_close_request)
        self.connect("map", self._on_map)

    def _on_map(self, *_):
        if not self._blink_id:
            self._blink_id = GLib.timeout_add(300, self._blink)
        beep()

    def _blink(self):
        self._black = not self._black
        if self._black:
            self.add_css_class("black")
        else:
            self.remove_css_class("black")
        return True

    def _on_key_pressed(self, _ctrl, keyval, *_):
        self._keys_down.add(keyval)
        return True

    def _on_key_released(self, _ctrl, keyval, *_):
        # Fecha na soltura, e só de uma tecla pressionada com o alarme já
        # aberto: assim a tecla que o usuário estava digitando não o fecha.
        if keyval in self._keys_down:
            self._request_close()

    def _on_close_request(self, *_):
        self._request_close()
        return True

    def _request_close(self):
        self._on_close()

    def dismiss(self):
        if self._closed:
            return
        self._closed = True
        if self._blink_id:
            GLib.source_remove(self._blink_id)
            self._blink_id = 0
        self.destroy()
