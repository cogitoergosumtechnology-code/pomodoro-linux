"""Socket Unix $XDG_RUNTIME_DIR/pomodoro.sock: uma linha de comando, resposta ok/err."""

import os
import socket

COMMANDS = (
    "show", "hide", "toggle", "start-pause", "reset", "skip",
    "compact", "menu", "alarm", "status", "quit",
)


def socket_path():
    base = os.environ.get("XDG_RUNTIME_DIR") or "/tmp"
    return os.path.join(base, "pomodoro.sock")


def send(cmd, timeout=2.0):
    """Envia um comando à instância ativa. Devolve a resposta ou None se não há instância."""
    path = socket_path()
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect(path)
            s.sendall((cmd + "\n").encode())
            s.shutdown(socket.SHUT_WR)
            data = b""
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                data += chunk
            return data.decode(errors="replace").strip()
    except (FileNotFoundError, ConnectionRefusedError):
        return None
    except OSError:
        return None


class Server:
    def __init__(self, handler):
        """handler(cmd) -> texto de resposta ('ok', 'ok ...' ou 'err ...')."""
        from gi.repository import GLib

        self._GLib = GLib
        self._handler = handler
        self._path = socket_path()
        try:
            os.unlink(self._path)  # socket órfão
        except OSError:
            pass
        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._sock.bind(self._path)
        os.chmod(self._path, 0o600)
        self._sock.listen(8)
        self._sock.setblocking(False)
        self._watch = GLib.io_add_watch(self._sock.fileno(), GLib.IO_IN, self._on_ready)

    def _on_ready(self, *_):
        try:
            conn, _addr = self._sock.accept()
        except OSError:
            return True
        with conn:
            try:
                conn.settimeout(0.5)
                data = b""
                while b"\n" not in data and len(data) < 256:
                    chunk = conn.recv(256)
                    if not chunk:
                        break
                    data += chunk
                cmd = data.decode(errors="replace").strip().split("\n")[0].strip()
                try:
                    reply = self._handler(cmd)
                except Exception as e:
                    reply = f"err {e}"
                conn.sendall((reply + "\n").encode())
            except OSError:
                pass
        return True

    def close(self):
        try:
            self._GLib.source_remove(self._watch)
        except Exception:
            pass
        try:
            self._sock.close()
        except OSError:
            pass
        try:
            os.unlink(self._path)
        except OSError:
            pass
