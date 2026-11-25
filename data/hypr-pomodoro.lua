-- Pomodoro widget (Hyprland 0.55+, config em Lua)
hl.window_rule({
  name = "pomodoro",
  match = { class = "^(pomodoro)$" },
  float = true,
  pin = true,
  border_size = 0,
  rounding = 0,
  no_shadow = true,
  no_blur = true,
  no_anim = true,
  no_initial_focus = true,
  no_dim = true,
  no_max_size = true,
})

-- Pomodoro alarme (só usado no fallback sem layer-shell)
hl.window_rule({
  name = "pomodoro-alarm",
  match = { class = "^(pomodoro-alarm)$" },
  fullscreen = true,
  pin = true,
  stay_focused = true,
  no_anim = true,
})

-- Alarme layer-shell: aparece e some sem animação
hl.layer_rule({ match = { namespace = "^(pomodoro-alarm)$" }, no_anim = true, animation = "none" })
