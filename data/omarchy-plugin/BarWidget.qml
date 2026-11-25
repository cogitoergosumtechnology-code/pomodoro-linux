import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui

// "Bandeja" do Pomodoro: mostra o tempo lido de $XDG_RUNTIME_DIR/pomodoro.json
// (escrito pelo app a cada segundo) e some quando o app não está rodando.
// Clique esquerdo: mostrar/esconder; direito: menu; meio: iniciar/pausar.
BarWidget {
  id: root
  moduleName: "aurelio.pomodoro"

  readonly property string statePath: Quickshell.env("XDG_RUNTIME_DIR") + "/pomodoro.json"
  readonly property string cli: Quickshell.env("HOME") + "/.local/bin/pomodoro"
  property string timeText: ""
  property string tooltip: ""
  property bool isBreak: false
  property bool isRunning: false

  visible: timeText !== ""
  implicitWidth: visible ? button.implicitWidth : 0
  implicitHeight: visible ? button.implicitHeight : 0

  function clear() {
    root.timeText = ""
    root.tooltip = ""
  }

  function parse(content) {
    try {
      var data = JSON.parse(String(content || ""))
      var text = String(data.text || "")
      // Só aceita o formato MM:SS; o arquivo é dado externo.
      root.timeText = /^[0-9]{1,4}:[0-9]{2}$/.test(text) ? text : ""
      root.isBreak = data["class"] === "break"
      root.isRunning = data.alt === "running"
      root.tooltip = root.timeText === "" ? ""
        : "Pomodoro " + (root.isBreak ? "PAUSA" : "FOCO") + " " + root.timeText
    } catch (e) {
      root.clear()
    }
  }

  FileView {
    id: stateFile
    path: root.statePath
    watchChanges: true
    printErrors: false
    onFileChanged: reload()
    onLoaded: root.parse(text())
    onLoadFailed: root.clear()
  }

  // O app troca o arquivo com rename atômico (novo inode); o timer cobre o
  // caso de o inotify não rearmar e detecta o arquivo removido ao sair.
  Timer {
    interval: 1000
    running: true
    repeat: true
    onTriggered: stateFile.reload()
  }

  WidgetButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: "🍅 " + root.timeText
    active: root.isRunning && !root.isBreak
    tooltipText: root.tooltip
    onPressed: function(mouseButton) {
      var cmd = mouseButton === Qt.RightButton ? "menu"
        : mouseButton === Qt.MiddleButton ? "start-pause" : "toggle"
      Quickshell.execDetached([root.cli, cmd])
    }
  }
}
