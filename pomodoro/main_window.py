"""Widget principal: timer, presets, controles, modo compacto, menu e posicionamento."""

from gi.repository import Gdk, Gio, GLib, Graphene, Gtk

from . import TITLE, hypr, startup
from .log import log
from .waybar import write_state

BREAK_OPTIONS = (3, 5, 10, 15, 20)
SIZE_OPTIONS = (("Pequeno", 0.75), ("Normal", 1.0), ("Grande", 1.5), ("Enorme", 2.0))

# U+FE0E força a apresentação em texto (sem emoji colorido)
GLYPH_PLAY = "\u25B6\uFE0E"
GLYPH_PAUSE = "\u23F8\uFE0E"
GLYPH_RESET = "\u27F2"
GLYPH_SKIP = "\u23ED\uFE0E"
GLYPH_COMPACT = "\u2500"
GLYPH_CLOSE = "\u2715"

CSS_TEMPLATE = """
window.pomodoro-widget {{ background: #1E1E1E; color: #FFFFFF; }}
window.pomodoro-widget.compact {{ background: #282828; }}
.pm-focus {{ color: #FF6347; }}
.pm-break {{ color: #90EE90; }}
.pm-phase {{ font-family: sans-serif; font-weight: bold; font-size: {phase}pt; }}
.pm-clock {{ font-family: monospace; font-weight: bold; font-size: {clock}pt; color: #FFFFFF; }}
button.pm-btn {{
  background-image: none; background-color: #323232; color: #FFFFFF;
  border: none; border-radius: 0; box-shadow: none; text-shadow: none; outline: none;
  min-width: 0; min-height: 0; padding: 0; margin: 0;
  font-family: sans-serif; font-weight: normal; font-size: {btn}pt;
}}
button.pm-btn.pm-preset {{ font-weight: bold; font-size: {preset}pt; }}
button.pm-btn.pm-preset.active {{ background-color: #C83C28; }}
.pm-compact {{
  font-family: monospace; font-weight: bold; font-size: {compact}pt;
  background: #282828; border: 2px solid;
}}
.pm-compact.pm-focus {{ border-color: #FF6347; }}
.pm-compact.pm-break {{ border-color: #90EE90; }}
entry.pm-edit {{
  font-family: monospace; font-weight: bold; font-size: {clock}pt;
  color: #FFFF00; caret-color: #FFFF00; background: #3C3C3C;
  border: 1px solid #7A7A7A; border-radius: 0; box-shadow: none; outline: none;
  min-height: 0; min-width: 0; padding: 0; margin: 0;
}}
entry.pm-edit > text {{ min-height: 0; padding: 0; margin: 0; }}
entry.pm-edit > text > selection {{ background: #5A5A2A; color: #FFFF00; }}
window.pomodoro-widget popover {{ color: #FFFFFF; font-family: sans-serif; font-size: 10pt; font-weight: normal; }}
window.pomodoro-widget popover > contents {{ background: #2B2B2B; color: #FFFFFF; border: 1px solid #555555; border-radius: 0; }}
window.pomodoro-widget popover modelbutton:hover {{ background: #454545; }}
"""


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, app, cfg):
        super().__init__(application=app, title=TITLE)
        self.app = app
        self.cfg = cfg

        self._remaining = max(1, cfg.FocusSeconds)
        self._running = False
        self._is_break = False
        self._compact = False
        self._tick_id = 0
        self._editor = None
        self._edit_field = None
        self._resume_after_edit = False
        self._popover = None
        self._drag_moved = False
        self._drag_watch_id = 0
        self._repos_ids = []

        self.set_decorated(False)
        self.set_resizable(False)
        self.set_icon_name("pomodoro")
        self.add_css_class("pomodoro-widget")

        self._css = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), self._css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1
        )

        self.fixed = Gtk.Fixed()
        self.set_child(self.fixed)

        drag = Gtk.GestureDrag()
        drag.set_button(1)
        drag.connect("drag-begin", self._on_drag_begin)
        drag.connect("drag-update", self._on_drag_update)
        drag.connect("drag-end", self._on_drag_end)
        self.add_controller(drag)
        self._drag = drag

        rclick = Gtk.GestureClick()
        rclick.set_button(3)
        rclick.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        rclick.connect("pressed", self._on_right_click)
        self.add_controller(rclick)

        motion = Gtk.EventControllerMotion()
        motion.connect("enter", lambda *_: self._drag_finished())
        motion.connect("motion", lambda *_: self._drag_finished())
        self.add_controller(motion)

        self.connect("close-request", self._on_close_request)

        self._build()
        self.reset()

    # ------------------------------------------------------------------ UI
    def _px(self, v):
        return int(round(v * self.cfg.scale))

    def _build(self):
        s = self.cfg.scale
        child = self.fixed.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.fixed.remove(child)
            child = nxt
        self._editor = None

        self._css.load_from_string(CSS_TEMPLATE.format(
            phase=10 * s, clock=40 * s, btn=11 * s, preset=10 * s, compact=13 * s,
        ))

        pad = self._px(6)
        btn_w, btn_h = self._px(48), self._px(30)
        phase_h, clock_h = self._px(22), self._px(64)
        total_w = 5 * btn_w + 10
        self._full_size = (total_w + 2 * pad, 2 * pad + phase_h + clock_h + (btn_h + 4) + btn_h)
        side = self._px(72)
        self._compact_size = (side, side)

        # fase
        self.phase_lbl = Gtk.Label()
        self.phase_lbl.add_css_class("pm-phase")
        self.phase_lbl.set_size_request(total_w, phase_h)
        self.fixed.put(self.phase_lbl, pad, pad)

        # relógio [MM][:][SS]
        self.clock_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.clock_box.set_size_request(total_w, clock_h)
        self.mm_lbl = self._clock_label("m", Gtk.Align.END)
        colon = Gtk.Label(label=":")
        colon.add_css_class("pm-clock")
        self.ss_lbl = self._clock_label("s", Gtk.Align.START)
        self.clock_box.append(self.mm_lbl)
        self.clock_box.append(colon)
        self.clock_box.append(self.ss_lbl)
        self.fixed.put(self.clock_box, pad, pad + phase_h)

        # presets
        self.preset_btns = []
        n = max(1, len(self.cfg.Presets))
        pw = max(1, (total_w - 2 * n) // n)
        y = pad + phase_h + clock_h + 4
        for i, minutes in enumerate(self.cfg.Presets):
            b = self._button(str(minutes), lambda _b, m=minutes: self.apply_preset(m))
            b.add_css_class("pm-preset")
            b.set_size_request(pw, btn_h)
            self.fixed.put(b, pad + 1 + i * (pw + 2), y)
            self.preset_btns.append((minutes, b))

        # controles
        y = pad + phase_h + clock_h + btn_h + 4
        self.play_btn = self._button(GLYPH_PLAY, lambda _b: self.toggle_run())
        controls = [
            self.play_btn,
            self._button(GLYPH_RESET, lambda _b: self.reset()),
            self._button(GLYPH_SKIP, lambda _b: self.next_phase(False)),
            self._button(GLYPH_COMPACT, lambda _b: self.set_compact(True)),
            self._button(GLYPH_CLOSE, lambda _b: self.app.quit_app()),
        ]
        self.control_btns = controls
        for i, b in enumerate(controls):
            b.set_size_request(btn_w, btn_h)
            self.fixed.put(b, pad + 1 + i * (btn_w + 2), y)

        # compacto (borda de 2 px desenhada 1 px para dentro)
        self.compact_lbl = Gtk.Label()
        self.compact_lbl.add_css_class("pm-compact")
        self.compact_lbl.set_size_request(side - 2, side - 2)
        self.compact_lbl.set_cursor(Gdk.Cursor.new_from_name("pointer"))
        self.fixed.put(self.compact_lbl, 1, 1)

        self._apply_mode()

    def _clock_label(self, field, align):
        lbl = Gtk.Label()
        lbl.add_css_class("pm-clock")
        lbl.set_hexpand(True)
        lbl.set_halign(align)
        lbl.set_cursor(Gdk.Cursor.new_from_name("text"))
        click = Gtk.GestureClick()
        click.set_button(1)

        def pressed(gesture, *_):
            gesture.set_state(Gtk.EventSequenceState.CLAIMED)
            self.begin_edit(field)

        click.connect("pressed", pressed)
        lbl.add_controller(click)
        return lbl

    def _button(self, text, callback):
        b = Gtk.Button(label=text)
        b.add_css_class("pm-btn")
        b.set_focusable(False)  # nunca recebe foco de teclado
        b.set_focus_on_click(False)
        b.set_can_shrink(True)
        b.connect("clicked", callback)
        return b

    def _apply_mode(self):
        full = not self._compact
        for w in (self.phase_lbl, self.clock_box, *self.control_btns, *(b for _, b in self.preset_btns)):
            w.set_visible(full)
        self.compact_lbl.set_visible(not full)
        if self._compact:
            self.add_css_class("compact")
        else:
            self.remove_css_class("compact")
        w, h = self._compact_size if self._compact else self._full_size
        self.fixed.set_size_request(w, h)
        self.set_default_size(w, h)
        self._refresh_phase()
        self._refresh_time()

    @property
    def win_size(self):
        return self._compact_size if self._compact else self._full_size

    # --------------------------------------------------------------- timer
    @property
    def phase_name(self):
        return "PAUSA" if self._is_break else "FOCO"

    def mm_ss(self):
        return f"{self._remaining // 60:02d}:{self._remaining % 60:02d}"

    def status_text(self):
        return f"Pomodoro {self.phase_name} {self.mm_ss()} {'running' if self._running else 'paused'}"

    def _refresh_time(self):
        self.mm_lbl.set_label(f"{self._remaining // 60:02d}")
        self.ss_lbl.set_label(f"{self._remaining % 60:02d}")
        self.compact_lbl.set_label(self.mm_ss())
        write_state(self.mm_ss(), self.phase_name, self._is_break, self._running)

    def _refresh_phase(self):
        self.phase_lbl.set_label(self.phase_name)
        add, rem = ("pm-break", "pm-focus") if self._is_break else ("pm-focus", "pm-break")
        for w in (self.phase_lbl, self.compact_lbl):
            w.remove_css_class(rem)
            w.add_css_class(add)
        for minutes, b in self.preset_btns:
            if not self._is_break and minutes * 60 == self.cfg.FocusSeconds:
                b.add_css_class("active")
            else:
                b.remove_css_class("active")

    def _stop_tick(self):
        if self._tick_id:
            GLib.source_remove(self._tick_id)
            self._tick_id = 0

    def _set_running(self, running):
        self._running = running
        self._stop_tick()
        if running:
            self._tick_id = GLib.timeout_add(1000, self._tick)
        self.play_btn.set_label(GLYPH_PAUSE if running else GLYPH_PLAY)
        self.app.update_awake()
        self._refresh_time()

    def reset(self):
        self.cancel_edit(resume=False)
        self._set_running(False)
        self._remaining = max(1, self.cfg.BreakSeconds if self._is_break else self.cfg.FocusSeconds)
        self._refresh_phase()
        self._refresh_time()

    def toggle_run(self):
        self._set_running(not self._running)

    def _tick(self):
        self._remaining -= 1
        self._refresh_time()
        if self._remaining <= 0:
            self._tick_id = 0
            self.next_phase(True)
            return False
        return True

    def next_phase(self, fire):
        was_break = self._is_break
        self._is_break = not self._is_break
        self.reset()
        if fire:
            self.app.fire_alarm("VOLTA AO FOCO" if was_break else "HORA DA PAUSA")

    @property
    def running(self):
        return self._running

    def apply_preset(self, minutes):
        self.cancel_edit(resume=False)
        self._is_break = False
        self.cfg.FocusSeconds = minutes * 60
        self.cfg.save()
        self.reset()

    # -------------------------------------------------------- edição inline
    def begin_edit(self, field):
        if self._editor is not None:
            resume = self._resume_after_edit
            self._commit_edit(resume=False)
            self._resume_after_edit = resume
        else:
            self._resume_after_edit = self._running
            if self._running:
                self._set_running(False)

        lbl = self.mm_lbl if field == "m" else self.ss_lbl
        ok, rect = lbl.compute_bounds(self.fixed)
        if not ok:
            rect = Graphene.Rect().init(0, 0, self._px(60), self._px(64))
        entry = Gtk.Entry()
        entry.add_css_class("pm-edit")
        entry.set_has_frame(True)
        entry.set_alignment(0.5)
        entry.set_max_length(3 if field == "m" else 2)
        entry.set_width_chars(1)
        entry.set_max_width_chars(1)
        entry.set_input_purpose(Gtk.InputPurpose.DIGITS)
        entry.set_text(lbl.get_label())
        # largura = rótulo + 8 px; nos minutos, espaço para 3 dígitos,
        # crescendo para a esquerda (o rótulo é alinhado à direita)
        lw = rect.get_width()
        ew = int(lw * (1.5 if field == "m" and len(lbl.get_label()) <= 2 else 1.0)) + 8
        ex = int(rect.get_x() + lw + 4 - ew)
        entry.set_size_request(ew, int(rect.get_height()))
        self.fixed.put(entry, max(0, ex), int(rect.get_y()))

        def only_digits(e):
            text = e.get_text()
            clean = "".join(ch for ch in text if ch.isdigit())
            if clean != text:
                e.set_text(clean)
                e.set_position(-1)

        entry.connect("changed", only_digits)

        keys = Gtk.EventControllerKey()
        keys.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        keys.connect("key-pressed", self._on_edit_key)
        entry.add_controller(keys)

        focus = Gtk.EventControllerFocus()
        focus.connect("leave", lambda *_: self._on_edit_focus_lost(entry))
        entry.add_controller(focus)

        self._editor = entry
        self._edit_field = field
        entry.grab_focus()
        entry.select_region(0, -1)

    def _on_edit_key(self, _ctrl, keyval, _code, _state):
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter, Gdk.KEY_ISO_Enter):
            self._commit_edit()
            return True
        if keyval == Gdk.KEY_Escape:
            self.cancel_edit()
            return True
        if keyval in (Gdk.KEY_Tab, Gdk.KEY_ISO_Left_Tab, Gdk.KEY_KP_Tab):
            other = "s" if self._edit_field == "m" else "m"
            self.begin_edit(other)
            return True
        return False

    def _on_edit_focus_lost(self, entry):
        if self._editor is entry:
            self._commit_edit()

    def _take_editor(self):
        entry, self._editor = self._editor, None
        if entry is not None:
            text = entry.get_text()
            GLib.idle_add(self._remove_widget, entry)
            return text
        return None

    def _remove_widget(self, w):
        if w.get_parent() is self.fixed:
            self.fixed.remove(w)
        return False

    def _commit_edit(self, resume=True):
        if self._editor is None:
            return
        field = self._edit_field
        text = self._take_editor()
        m, s = self._remaining // 60, self._remaining % 60
        try:
            v = int(text)
            if field == "m":
                m = min(999, max(0, v))
            else:
                s = min(59, max(0, v))
        except (TypeError, ValueError):
            pass
        total = max(1, m * 60 + s)
        if self._is_break:
            self.cfg.BreakSeconds = total
        else:
            self.cfg.FocusSeconds = total
        self.cfg.save()
        self._remaining = total
        self._refresh_phase()
        self._refresh_time()
        if resume and self._resume_after_edit:
            self._resume_after_edit = False
            self._set_running(True)

    def cancel_edit(self, resume=True):
        if self._editor is None:
            return
        self._take_editor()
        if resume and self._resume_after_edit:
            self._set_running(True)
        self._resume_after_edit = False

    # -------------------------------------------------------------- compacto
    def set_compact(self, compact):
        if compact == self._compact:
            return
        self.cancel_edit()
        self._compact = compact
        self._apply_mode()
        self.reposition(snap=True)

    def toggle_compact(self):
        self.set_compact(not self._compact)

    # ------------------------------------------------------- arrastar/mover
    def _on_drag_begin(self, gesture, x, y):
        self._drag_moved = False
        target = self.pick(x, y, Gtk.PickFlags.DEFAULT)
        w = target
        while w is not None and w is not self:
            if isinstance(w, (Gtk.Button, Gtk.Entry, Gtk.Popover)) or w in (self.mm_lbl, self.ss_lbl):
                gesture.set_state(Gtk.EventSequenceState.DENIED)
                return
            w = w.get_parent()

    def _on_drag_update(self, gesture, dx, dy):
        if self._drag_moved or (abs(dx) <= 3 and abs(dy) <= 3):
            return
        self._drag_moved = True
        surface = self.get_surface()
        device = gesture.get_device()
        ok, sx, sy = gesture.get_start_point()
        if surface is None or device is None or not ok:
            return
        try:
            surface.begin_move(device, 1, sx + dx, sy + dy, gesture.get_current_event_time())
        except Exception as e:
            log(f"begin_move falhou: {e}")
            return
        gesture.set_state(Gtk.EventSequenceState.CLAIMED)
        # O compositor conduz o arrasto e não avisa quando solta: a posição é
        # corrigida quando o ponteiro volta à janela ou quando ela para.
        self._watch_drag()

    def _on_drag_end(self, _gesture, dx, dy):
        if not self._drag_moved and self._compact and abs(dx) <= 3 and abs(dy) <= 3:
            self.set_compact(False)

    def _watch_drag(self):
        if self._drag_watch_id:
            GLib.source_remove(self._drag_watch_id)
        state = {"last": None, "same": 0, "n": 0}

        def poll():
            state["n"] += 1
            c = hypr.client()
            at = tuple(c["at"]) if c else None
            state["same"] = state["same"] + 1 if at == state["last"] else 0
            state["last"] = at
            if state["same"] >= 4 or state["n"] > 150:
                self._drag_watch_id = 0
                self._drag_finished(force=True)
                return False
            return True

        self._drag_watch_id = GLib.timeout_add(200, poll)

    def _drag_finished(self, force=False):
        if not self._drag_moved:
            return
        self._drag_moved = False
        if self._drag_watch_id:
            GLib.source_remove(self._drag_watch_id)
            self._drag_watch_id = 0
        self.reposition(snap=False)

    def reposition(self, snap):
        """snap=True: canto inferior direito da tela escolhida; False: clamp na área útil."""
        for i in self._repos_ids:
            GLib.source_remove(i)
        self._repos_ids = []

        def run(delay):
            def cb():
                self._repos_ids.remove(holder[0])
                self._do_reposition(snap)
                return False
            holder = [GLib.timeout_add(delay, cb)]
            self._repos_ids.append(holder[0])

        # duas passadas: a janela pode ainda estar sendo mapeada/redimensionada
        run(40)
        run(250)

    def _do_reposition(self, snap):
        if not self.get_visible():
            return
        mons = hypr.monitors()
        if not mons:
            return
        c = hypr.client()
        if c is None:
            return
        if snap:
            idx = self.cfg.ScreenIndex if 0 <= self.cfg.ScreenIndex < len(mons) else 0
            mon = mons[idx]
            if c.get("monitor") != mon.get("id"):
                hypr.move_to_monitor(mon["name"])
            left, top, right, bottom = hypr.usable_area(mon)
            w, h = self.win_size
            hypr.move_exact(right - w - 8, bottom - h - 8)
        else:
            mon = next((m for m in mons if m.get("id") == c.get("monitor")), mons[0])
            left, top, right, bottom = hypr.usable_area(mon)
            (x, y), (w, h) = c["at"], c["size"]
            nx = min(max(x, left), max(left, right - w))
            ny = min(max(y, top), max(top, bottom - h))
            if (nx, ny) != (x, y):
                hypr.move_exact(nx, ny)

    # ---------------------------------------------------------- mostrar/esconder
    def show_widget(self):
        self.set_visible(True)
        self.present()
        self.reposition(snap=True)
        self.app.update_awake()

    def hide_widget(self):
        self.cancel_edit()
        if self._popover is not None:
            self._popover.popdown()
        self.set_visible(False)
        self.app.update_awake()

    def toggle_visible(self):
        if self.get_visible():
            self.hide_widget()
        else:
            self.show_widget()

    def _on_close_request(self, *_):
        self.app.quit_app()
        return True

    # --------------------------------------------------------- menu de contexto
    def _on_right_click(self, gesture, _n, x, y):
        gesture.set_state(Gtk.EventSequenceState.CLAIMED)
        self.open_menu(x, y)

    def _screen_items(self):
        mons = hypr.monitors()
        if mons:
            return [(f"{m['width']}x{m['height']}", m.get("id") == 0) for m in mons]
        out = []
        gdk_mons = Gdk.Display.get_default().get_monitors()
        for i in range(gdk_mons.get_n_items()):
            g = gdk_mons.get_item(i).get_geometry()
            out.append((f"{g.width}x{g.height}", i == 0))
        return out

    def open_menu(self, x=None, y=None):
        if self._popover is not None:
            self._popover.unparent()
            self._popover = None
        if not self.get_visible():
            self.show_widget()

        group = Gio.SimpleActionGroup()
        counter = [0]

        def add(menu, label, callback, checked=None):
            counter[0] += 1
            name = f"a{counter[0]}"
            if checked is None:
                action = Gio.SimpleAction.new(name, None)
            else:
                action = Gio.SimpleAction.new_stateful(name, None, GLib.Variant.new_boolean(bool(checked)))
            action.connect("activate", lambda *_: GLib.idle_add(lambda: (callback(), False)[1]))
            group.add_action(action)
            menu.append(label, f"ctx.{name}")

        top = Gio.Menu()
        add(top, "Restaurar" if self._compact else "Minimizar (quadrado no canto)", self.toggle_compact)

        screens = Gio.Menu()
        items = self._screen_items()
        current = self.cfg.ScreenIndex if 0 <= self.cfg.ScreenIndex < len(items) else 0
        for i, (res, primary) in enumerate(items):
            label = f"{i + 1}: {res}" + (" (principal)" if primary else "")
            add(screens, label, lambda i=i: self._set_screen(i), checked=(i == current))
        top.append_submenu("Tela", screens)

        breaks = Gio.Menu()
        for m in BREAK_OPTIONS:
            add(breaks, str(m), lambda m=m: self._set_break(m), checked=(m * 60 == self.cfg.BreakSeconds))
        top.append_submenu("Pausa (min)", breaks)

        sizes = Gio.Menu()
        for label, value in SIZE_OPTIONS:
            add(sizes, label, lambda v=value: self._set_scale(v), checked=abs(self.cfg.Scale - value) < 0.01)
        top.append_submenu("Tamanho", sizes)

        add(top, "Piscar todas as telas", self._toggle_flash_all, checked=self.cfg.FlashAllScreens)
        add(top, "Manter o PC acordado enquanto conta", self._toggle_keep_awake, checked=self.cfg.KeepAwake)
        add(top, "Iniciar com o Omarchy", self._toggle_startup, checked=startup.is_enabled())

        bottom = Gio.Menu()
        add(bottom, "Testar alarme", lambda: self.app.fire_alarm("TESTE"))
        if self.get_visible():
            add(bottom, "Esconder (fica na bandeja)", self.hide_widget)
        else:
            add(bottom, "Mostrar", self.show_widget)
        add(bottom, "Sair", self.app.quit_app)

        model = Gio.Menu()
        model.append_section(None, top)
        model.append_section(None, bottom)

        self.insert_action_group("ctx", group)
        pop = Gtk.PopoverMenu.new_from_model_full(model, Gtk.PopoverMenuFlags.NESTED)
        pop.set_parent(self.fixed)
        pop.set_has_arrow(False)
        rect = Gdk.Rectangle()
        w, h = self.win_size
        rect.x = int(x if x is not None else w / 2)
        rect.y = int(y if y is not None else h / 2)
        rect.width = rect.height = 1
        pop.set_pointing_to(rect)
        self._popover = pop
        pop.popup()

    def _set_screen(self, index):
        self.cfg.ScreenIndex = index
        self.cfg.save()
        self.reposition(snap=True)

    def _set_break(self, minutes):
        self.cfg.BreakSeconds = minutes * 60
        self.cfg.save()
        if self._is_break:
            self.reset()

    def _set_scale(self, value):
        self.cfg.Scale = value
        self.cfg.save()
        self.apply_scale()

    def apply_scale(self):
        self.cancel_edit()
        if self._popover is not None:
            self._popover.unparent()
            self._popover = None
        self._build()
        self.play_btn.set_label(GLYPH_PAUSE if self._running else GLYPH_PLAY)
        self.reposition(snap=True)

    def _toggle_flash_all(self):
        self.cfg.FlashAllScreens = not self.cfg.FlashAllScreens
        self.cfg.save()

    def _toggle_keep_awake(self):
        self.cfg.KeepAwake = not self.cfg.KeepAwake
        self.cfg.save()
        self.app.update_awake()

    def _toggle_startup(self):
        err = startup.set_enabled(not startup.is_enabled())
        if err:
            try:
                dlg = Gtk.AlertDialog()
                dlg.set_message(TITLE)
                dlg.set_detail(f"Não foi possível alterar o atalho de inicialização:\n{err}")
                dlg.show(self if self.get_visible() else None)
            except Exception as e:
                log(f"falha ao mostrar dialogo: {e}")

    def shutdown(self):
        self._stop_tick()
        for i in self._repos_ids:
            GLib.source_remove(i)
        self._repos_ids = []
        if self._drag_watch_id:
            GLib.source_remove(self._drag_watch_id)
            self._drag_watch_id = 0
