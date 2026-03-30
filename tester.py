#!/usr/bin/env python3
"""
Watch src/ for .c/.h changes, rebuild, restart server, run client.
Usage: tester.py [--re] [--polling] [--clear] "message"

  --re       use 'make re' (full rebuild); default is 'make'
  --polling  use polling instead of inotify (useful in WSL)
  --clear    clear console before each run
"""

import os
import re
import subprocess
import sys
import threading
import time

# Load mywatcher as a module to reuse CommandWatcher (no .py extension, needs explicit loader)
from importlib.machinery import SourceFileLoader
_mywatcher = SourceFileLoader("mywatcher", "/home/Dan/.local/bin/mywatcher").load_module()
CommandWatcher = _mywatcher.CommandWatcher

SRC_DIR = "src"


def start_server():
    """Start ./server with line-buffered stdout, parse PID, relay all output."""
    proc = subprocess.Popen(
        ["stdbuf", "-oL", "./server"],
        stdout=subprocess.PIPE,
        stderr=None,
    )

    pid_found = threading.Event()
    pid_holder = [None]

    def reader():
        buf = b""
        pid_line_done = False
        while True:
            byte = proc.stdout.read(1)
            if not byte:
                break
            if not pid_line_done:
                buf += byte
                if byte == b"\n":
                    line = buf.decode("utf-8", errors="replace")
                    sys.stdout.write(line)
                    sys.stdout.flush()
                    buf = b""
                    m = re.match(r"^(\d+)$", line.strip())
                    if m:
                        pid_holder[0] = int(m.group(1))
                        pid_found.set()
                        pid_line_done = True
            else:
                sys.stdout.buffer.write(byte)
                sys.stdout.buffer.flush()

    threading.Thread(target=reader, daemon=True).start()

    if not pid_found.wait(timeout=5):
        print("[tester] ERROR: timed out waiting for server PID")
        proc.kill()
        return None, None

    return proc, pid_holder[0]


class MinitalkWatcher(CommandWatcher):
    def __init__(self, message, make_cmd, clear_console=False):
        super().__init__("", ["*.c", "*.h"], clear_console=clear_console)
        self.message = message
        self.make_cmd = make_cmd
        self._server_proc = None
        self._server_pid = None
        self._client_proc = None

    def _kill_proc(self, proc):
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()

    def _kill_server(self):
        self._kill_proc(self._client_proc)
        self._client_proc = None
        self._kill_proc(self._server_proc)
        self._server_proc = None
        self._server_pid = None

    def run_command(self):
        # Block debounce events for the duration of the build
        self._last_run = time.time() + 9999

        self._kill_server()

        self._clear_console()

        print(f"[tester] Building... ({' '.join(self.make_cmd)})")
        print("-" * 50)

        result = subprocess.run(self.make_cmd)
        if result.returncode != 0:
            print("[tester] Build failed. Waiting for next change...")
            self._last_run = time.time()
            return

        print("[SERVER] -------------------------------")
        self._server_proc, self._server_pid = start_server()
        if not self._server_pid:
            print("[tester] Failed to start server.")
            self._last_run = time.time()
            return

        time.sleep(0.05)
        print(f"\n[tester] Sending: {self.message!r}")
        self._client_proc = subprocess.Popen(["./client", str(self._server_pid), self.message])
        print("\n[CLIENT] -------------------------------")
        print("\n[-- DONE --]")

        # Re-enable debounce from this point forward
        self._last_run = time.time()

    def stop(self):
        self._kill_server()


def main():
    args = sys.argv[1:]

    full_rebuild = "--re" in args
    use_polling  = "--polling" in args
    clear_console = "--clear" in args
    args = [a for a in args if a not in {"--re", "--polling", "--clear"}]

    if not args:
        print('Usage: tester.py [--re] [--polling] [--clear] "message"')
        sys.exit(1)

    message = args[0]
    make_cmd = ["make", "re"] if full_rebuild else ["make"]

    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    watcher = MinitalkWatcher(message, make_cmd, clear_console=clear_console)

    if use_polling:
        from watchdog.observers.polling import PollingObserver
        observer = PollingObserver(timeout=0.1)
    else:
        from watchdog.observers import Observer
        observer = Observer()

    observer.schedule(watcher, path=SRC_DIR, recursive=True)

    try:
        observer.start()
        watcher.run_command()
        print(f"\n[tester] Watching {SRC_DIR}/ for .c/.h changes... (Ctrl+C to stop)")

        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[tester] Stopping.")
        observer.stop()
        watcher.stop()
    finally:
        observer.join()


if __name__ == "__main__":
    main()
