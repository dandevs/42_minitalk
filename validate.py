#!/usr/bin/env python3
"""
validate.py — Automated evaluation script for the 42 minitalk project.

Covers all criteria from CLAUDE.md (Evaluation section):
  Prerequisites, General Instructions, Mandatory Part, Bonus Part
"""

import os
import re
import signal
import subprocess
import sys
import threading
import time

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_BIN = os.path.join(PROJECT_DIR, "server")
CLIENT_BIN = os.path.join(PROJECT_DIR, "client")
SRC_DIR = os.path.join(PROJECT_DIR, "src")

# ─── ANSI colours ────────────────────────────────────────────────────────────
GREEN  = "\033[32m"
RED    = "\033[31m"
YELLOW = "\033[33m"
CYAN   = "\033[36m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def ok(msg):   print(f"  {GREEN}✔{RESET}  {msg}")
def fail(msg): print(f"  {RED}✘{RESET}  {msg}")
def warn(msg): print(f"  {YELLOW}⚠{RESET}  {msg}")
def info(msg): print(f"  {CYAN}i{RESET}  {msg}")
def section(title):
    print(f"\n{BOLD}{CYAN}{'─'*55}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'─'*55}{RESET}")


# ─── Score accumulator ───────────────────────────────────────────────────────
class Score:
    def __init__(self):
        self.points = 0
        self.max    = 0
        self.failures = []

    def add(self, earned, maximum, label):
        self.points += earned
        self.max    += maximum
        if earned < maximum:
            self.failures.append(f"{label} ({earned}/{maximum})")

    def passed(self, label, pts=1):
        self.add(pts, pts, label)

    def failed(self, label, pts=1):
        self.add(0, pts, label)
        self.failures.append(label)

    def summary(self):
        return self.points, self.max


# ─── Helpers ─────────────────────────────────────────────────────────────────
def kill_proc(proc):
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()


class ServerSession:
    """
    Manages a running server process with a single reader thread that
    captures all output after the PID line into a shared buffer.
    """
    def __init__(self):
        self.proc   = None
        self.pid    = None
        self._buf   = []
        self._lock  = threading.Lock()
        self._ready = threading.Event()

    def start(self):
        self.proc = subprocess.Popen(
            ["stdbuf", "-oL", SERVER_BIN],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        threading.Thread(target=self._reader, daemon=True).start()
        if not self._ready.wait(timeout=5):
            self.kill()
            return False
        return True

    def _reader(self):
        buf      = b""
        pid_done = False
        while True:
            byte = self.proc.stdout.read(1)
            if not byte:
                break
            if not pid_done:
                buf += byte
                if byte == b"\n":
                    line = buf.decode("utf-8", errors="replace").strip()
                    buf  = b""
                    if re.fullmatch(r"\d+", line):
                        self.pid = int(line)
                        pid_done = True
                        self._ready.set()
            else:
                with self._lock:
                    self._buf.append(byte)

    def captured(self):
        with self._lock:
            return b"".join(self._buf).decode("utf-8", errors="replace")

    def clear(self):
        with self._lock:
            self._buf.clear()

    def kill(self):
        kill_proc(self.proc)


def start_server():
    """
    Launch ./server, wait for PID.
    Returns (proc, pid) or (None, None) on timeout.
    Output is NOT captured after the PID line — use ServerSession instead.
    """
    proc = subprocess.Popen(
        ["stdbuf", "-oL", SERVER_BIN],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    pid_found  = threading.Event()
    pid_holder = [None]

    def _reader():
        buf = b""
        while True:
            byte = proc.stdout.read(1)
            if not byte:
                break
            buf += byte
            if byte == b"\n":
                line = buf.decode("utf-8", errors="replace").strip()
                buf  = b""
                if re.fullmatch(r"\d+", line):
                    pid_holder[0] = int(line)
                    pid_found.set()
                    return   # stop consuming stdout; caller can use it

    threading.Thread(target=_reader, daemon=True).start()
    if not pid_found.wait(timeout=5):
        kill_proc(proc)
        return None, None
    return proc, pid_holder[0]


def run_client(pid, message, timeout=10):
    """
    Run ./client <pid> <message>.
    Returns (returncode, elapsed_seconds).
    """
    t0  = time.monotonic()
    ret = subprocess.run(
        [CLIENT_BIN, str(pid), message],
        timeout=timeout,
        capture_output=True,
    )
    return ret.returncode, time.monotonic() - t0


def send_and_capture(message, wait_after=2.0):
    """
    Start server, send one message, capture server output.
    Returns (server_output, elapsed_client_seconds, ServerSession).
    """
    sess = ServerSession()
    if not sess.start():
        return None, None, None

    _, elapsed = run_client(sess.pid, message)
    time.sleep(wait_after)

    return sess.captured(), elapsed, sess


# ─── Individual checks ───────────────────────────────────────────────────────

def check_files(score: Score):
    section("PREREQUISITES — Required files")

    # Source directory
    if os.path.isdir(SRC_DIR):
        ok("src/ directory exists")
        score.passed("src/ directory")
    else:
        fail("src/ directory missing")
        score.failed("src/ directory")

    # Makefile
    mf = os.path.join(PROJECT_DIR, "Makefile")
    if os.path.isfile(mf):
        ok("Makefile present")
        score.passed("Makefile present")
    else:
        fail("Makefile missing")
        score.failed("Makefile present")

    # C source files
    c_files = []
    for root, _, files in os.walk(SRC_DIR):
        for f in files:
            if f.endswith(".c"):
                c_files.append(os.path.join(root, f))
    if c_files:
        ok(f"{len(c_files)} .c source file(s) found")
        score.passed(".c files present")
    else:
        fail("No .c source files found")
        score.failed(".c files present")


def check_norminette(score: Score):
    section("PREREQUISITES — Norm check")

    result = subprocess.run(
        ["norminette", SRC_DIR],
        capture_output=True, text=True
    )
    errors = [l for l in result.stdout.splitlines() if "Error" in l]
    if result.returncode == 0 and not errors:
        ok("No Norm errors")
        score.passed("Norm clean")
    else:
        fail(f"{len(errors)} Norm error(s) found")
        for e in errors[:10]:
            info(e)
        if len(errors) > 10:
            info(f"  ... and {len(errors) - 10} more")
        score.failed("Norm clean")


def check_compilation(score: Score):
    section("GENERAL — Compilation")

    # Full rebuild
    result = subprocess.run(
        ["make", "re"],
        cwd=PROJECT_DIR,
        capture_output=True, text=True
    )
    if result.returncode != 0:
        fail("make re failed")
        info(result.stderr[-500:] if result.stderr else "(no stderr)")
        score.failed("Compiles without errors", 1)
        return False

    # Both binaries must exist
    both = os.path.isfile(SERVER_BIN) and os.path.isfile(CLIENT_BIN)
    if both:
        ok("Both 'server' and 'client' binaries produced")
        score.passed("Makefile compiles both executables", 1)
    else:
        missing = []
        if not os.path.isfile(SERVER_BIN): missing.append("server")
        if not os.path.isfile(CLIENT_BIN): missing.append("client")
        fail(f"Missing binaries: {', '.join(missing)}")
        score.failed("Makefile compiles both executables", 1)
        return False

    # Re-linking check: run plain `make` again — should do nothing
    result2 = subprocess.run(
        ["make"],
        cwd=PROJECT_DIR,
        capture_output=True, text=True
    )
    relink = any(
        line.strip() and not line.startswith("make") and "Nothing to be done" not in line
        for line in result2.stdout.splitlines()
    )
    if relink:
        warn("Makefile may re-link unnecessarily (make ran commands on second invocation)")
        warn(result2.stdout[:300])
    else:
        ok("No unnecessary re-linking")

    return True


def check_server_pid(score: Score):
    section("GENERAL — Server prints its PID")

    proc, pid = start_server()
    if pid is not None:
        ok(f"Server prints its PID on launch: {pid}")
        score.passed("Server displays PID", 2)
    else:
        fail("Server did not print its PID within 5 seconds")
        score.failed("Server displays PID", 2)
    kill_proc(proc)
    return pid is not None


def check_client_usage(score: Score):
    section("GENERAL — Client usage: ./client PID MESSAGE")

    # Start a server to get a real PID
    srv, pid = start_server()
    if pid is None:
        kill_proc(srv)
        fail("Cannot test client: server failed to start")
        score.failed("Client usage", 2)
        return

    ret, _ = run_client(pid, "hello", timeout=5)
    kill_proc(srv)

    if ret == 0:
        ok(f"Client exits cleanly when called as ./client {pid} hello")
        score.passed("Client usage", 2)
    else:
        fail(f"Client exited with code {ret}")
        score.failed("Client usage", 2)


def check_global_variables(score: Score):
    section("MANDATORY — At most one global variable per program")

    # Collect source files per program
    client_src = []
    server_src = []
    shared_src = []
    for root, _, files in os.walk(SRC_DIR):
        for f in files:
            if not f.endswith(".c"):
                continue
            path = os.path.join(root, f)
            rel  = os.path.relpath(path, SRC_DIR)
            if rel.startswith("client"):
                client_src.append(path)
            elif rel.startswith("server"):
                server_src.append(path)
            else:
                shared_src.append(path)

    # Regex: a line at file scope (not inside a function) that looks like a variable declaration.
    # Heuristic: non-indented line that is NOT a preprocessor directive, typedef, struct/enum def,
    # function prototype, or function definition body.
    global_var_re = re.compile(
        r'^(?![\s#])'                          # must start at column 0, not #
        r'(?!.*\()'                            # not a function definition/prototype
        r'(?!(?:typedef|struct|enum|union)\b)' # not a type definition
        r'(?!\/[\/\*])'                        # not a comment
        r'\b(?:int|char|long|size_t|pid_t|volatile|sig_atomic_t|unsigned|static|extern)'
        r'.*[^;{]$|'                           # ends without ; or { (tricky)
        r'^(?:int|char|long|size_t|pid_t|volatile|sig_atomic_t|unsigned)\s+\w',
        re.MULTILINE,
    )

    # Simpler and more reliable approach: look for global variable patterns
    global_decl_re = re.compile(
        r'^(?:volatile\s+)?(?:static\s+)?'
        r'(?:int|char|long|unsigned\s+\w+|size_t|pid_t|sig_atomic_t|t_\w+)\s+'
        r'\w+\s*(?:=\s*[^;]+)?;',
        re.MULTILINE,
    )

    def count_globals(files):
        count  = 0
        found  = []
        for path in files:
            with open(path, encoding="utf-8", errors="replace") as fh:
                content = fh.read()
            # Remove block comments
            content_no_comments = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
            # Remove line comments
            content_no_comments = re.sub(r'//[^\n]*', '', content_no_comments)
            # Find all lines that look like global variable declarations
            # (at column 0, not inside a function)
            for m in global_decl_re.finditer(content_no_comments):
                # Make sure it's at line start (column 0)
                start = m.start()
                if start == 0 or content_no_comments[start - 1] == '\n':
                    count += 1
                    found.append((os.path.basename(path), m.group().strip()))
        return count, found

    all_ok = True
    for prog, srcs in [("client", client_src + shared_src), ("server", server_src + shared_src)]:
        n, found = count_globals(srcs)
        if n <= 1:
            ok(f"{prog}: {n} global variable(s) (allowed ≤ 1)")
        else:
            fail(f"{prog}: {n} global variable(s) found — only 1 allowed")
            for fname, decl in found:
                info(f"    {fname}: {decl[:80]}")
            all_ok = False

    if all_ok:
        score.passed("At most one global variable per program", 1)
    else:
        score.failed("At most one global variable per program", 1)


def check_signal_usage(score: Score):
    section("MANDATORY — Only SIGUSR1 and SIGUSR2 used for communication")

    forbidden_signals = {
        "SIGINT", "SIGTERM", "SIGHUP", "SIGQUIT", "SIGPIPE",
        "SIGALRM", "SIGCHLD", "SIGCONT", "SIGSTOP", "SIGIO",
        "SIGRTMIN", "SIGRTMAX",
    }
    allowed = {"SIGUSR1", "SIGUSR2"}

    used_forbidden = set()
    c_files = []
    for root, _, files in os.walk(SRC_DIR):
        for f in files:
            if f.endswith(".c"):
                c_files.append(os.path.join(root, f))

    for path in c_files:
        with open(path, encoding="utf-8", errors="replace") as fh:
            content = fh.read()
        for sig in forbidden_signals:
            if re.search(r'\b' + sig + r'\b', content):
                used_forbidden.add(sig)

    # Check that SIGUSR1 and SIGUSR2 are actually used
    uses_usr1 = any(
        re.search(r'\bSIGUSR1\b', open(p, errors="replace").read())
        for p in c_files
    )
    uses_usr2 = any(
        re.search(r'\bSIGUSR2\b', open(p, errors="replace").read())
        for p in c_files
    )

    if not uses_usr1 or not uses_usr2:
        fail("SIGUSR1 and/or SIGUSR2 not found in source code")
        score.failed("Uses only SIGUSR1/SIGUSR2", 3)
    elif used_forbidden:
        fail(f"Forbidden signals found in source: {', '.join(sorted(used_forbidden))}")
        score.failed("Uses only SIGUSR1/SIGUSR2", 3)
    else:
        ok("Only SIGUSR1 and SIGUSR2 used for communication")
        score.passed("Uses only SIGUSR1/SIGUSR2", 3)


def check_message_transmission(score: Score):
    section("MANDATORY — Message transmission")

    test_cases = [
        ("Hello, World!", "short ASCII"),
        ("A" * 100,        "100-char string"),
        ("A" * 500,        "500-char string"),
        ("The quick brown fox jumps over the lazy dog", "sentence"),
        ("12345 !@#$%", "digits and special chars"),
    ]

    passed_count = 0
    for msg, label in test_cases:
        output, elapsed, sess = send_and_capture(msg, wait_after=max(1.5, len(msg) / 50))
        if sess:
            sess.kill()

        if output is None:
            fail(f"[{label}] Server failed to start")
            continue

        received = output.strip()
        expected = msg.strip()

        if expected in received:
            ok(f"[{label}] Received correctly ({elapsed:.2f}s)")
            passed_count += 1
        else:
            fail(f"[{label}] Mismatch")
            info(f"    Expected : {expected[:60]!r}")
            info(f"    Got      : {received[:60]!r}")

    if passed_count == len(test_cases):
        score.passed("Messages transmitted correctly", 5)
    elif passed_count >= 3:
        score.add(3, 5, "Messages transmitted correctly")
        warn(f"Partial: {passed_count}/{len(test_cases)} test cases passed")
    elif passed_count >= 1:
        score.add(1, 5, "Messages transmitted correctly")
        warn(f"Partial: {passed_count}/{len(test_cases)} test cases passed")
    else:
        score.failed("Messages transmitted correctly", 5)


def check_multiple_clients(score: Score):
    section("MANDATORY — Server handles multiple clients without restart")

    messages = ["First message", "Second message", "Third message"]

    sess = ServerSession()
    if not sess.start():
        fail("Server failed to start")
        score.failed("Multiple clients without restart", 1)
        return

    all_ok = True
    for msg in messages:
        ret, _ = run_client(sess.pid, msg, timeout=10)
        time.sleep(1.0)
        if ret != 0:
            fail(f"Client failed for message: {msg!r}")
            all_ok = False

    time.sleep(1.0)
    output = sess.captured()
    sess.kill()

    for msg in messages:
        if msg not in output:
            fail(f"Message not received: {msg!r}")
            info(f"Server output: {output[:200]!r}")
            all_ok = False

    if all_ok:
        ok(f"Server received {len(messages)} sequential messages without restart")
        score.passed("Multiple clients without restart", 1)
    else:
        score.failed("Multiple clients without restart", 1)


def check_performance(score: Score):
    section("MANDATORY — Performance (100 chars in < 1 second)")

    message = "A" * 100

    srv, pid = start_server()
    if pid is None:
        kill_proc(srv)
        fail("Server failed to start")
        score.failed("Performance: 100 chars < 1s", 0)  # informational only
        return

    _, elapsed = run_client(pid, message, timeout=15)
    kill_proc(srv)

    if elapsed < 1.0:
        ok(f"100 chars transmitted in {elapsed:.3f}s (< 1s) ✓")
    else:
        fail(f"100 chars took {elapsed:.3f}s (> 1s) — performance requirement not met")

    info(f"Elapsed: {elapsed:.3f}s")


def check_bonus_acknowledgment(score: Score):
    section("BONUS — Server acknowledges each message")

    # The client should exit cleanly only after receiving the ACK.
    # We detect this by measuring that the client waits for a signal
    # and exits 0 even for longer messages.
    message = "Hello bonus"
    srv, pid = start_server()
    if pid is None:
        kill_proc(srv)
        fail("Server failed to start")
        score.failed("Bonus: acknowledgment", 1)
        return

    ret, elapsed = run_client(pid, message, timeout=10)
    kill_proc(srv)

    # If the client does ACK-based flow, it will only exit after server signals back.
    # We can't directly detect the signal, but a clean exit is a good proxy.
    if ret == 0:
        ok(f"Client exited cleanly (possible ACK support, elapsed={elapsed:.2f}s)")
        info("Note: cannot guarantee ACK without inspecting source — manual review recommended")
        # Check source for send-back signal
        ack_in_source = False
        for root, _, files in os.walk(SRC_DIR):
            for f in files:
                if not f.endswith(".c"):
                    continue
                with open(os.path.join(root, f), errors="replace") as fh:
                    content = fh.read()
                if re.search(r'kill\s*\(', content) and re.search(r'SIGUSR[12]', content):
                    # Check if server sends signal to client (kill call in server code)
                    if "server" in root.lower() or "shared" in root.lower():
                        ack_in_source = True
        if ack_in_source:
            ok("Server source contains kill() — likely sends ACK signals")
            score.passed("Bonus: acknowledgment", 1)
        else:
            warn("No ACK kill() found in server source — acknowledgment may not be implemented")
            score.failed("Bonus: acknowledgment", 1)
    else:
        fail(f"Client exited with code {ret}")
        score.failed("Bonus: acknowledgment", 1)


def check_bonus_unicode(score: Score):
    section("BONUS — Unicode character support")

    unicode_messages = [
        ("héllo", "accented chars"),
        ("日本語", "Japanese"),
        ("→ ← ↑ ↓", "arrows"),
        ("€ £ ¥", "currency symbols"),
    ]

    passed = 0
    for msg, label in unicode_messages:
        output, elapsed, sess = send_and_capture(msg, wait_after=2.0)
        if sess:
            sess.kill()

        if output is None:
            fail(f"[{label}] Server failed to start")
            continue

        received = output.strip()
        if msg in received:
            ok(f"[{label}] Unicode received correctly")
            passed += 1
        else:
            fail(f"[{label}] Unicode mismatch")
            info(f"    Expected : {msg!r}")
            info(f"    Got      : {received[:80]!r}")

    if passed == len(unicode_messages):
        score.passed("Bonus: Unicode", 1)
    elif passed > 0:
        score.add(0, 1, "Bonus: Unicode (partial)")
        warn(f"Partial Unicode support: {passed}/{len(unicode_messages)}")
    else:
        score.failed("Bonus: Unicode", 1)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    os.chdir(PROJECT_DIR)

    print(f"\n{BOLD}{'═'*55}")
    print(f"  minitalk — Automated Validator")
    print(f"{'═'*55}{RESET}")
    print(f"  Project dir : {PROJECT_DIR}")
    print(f"  Date        : {time.strftime('%Y-%m-%d %H:%M:%S')}")

    args  = set(sys.argv[1:])
    bonus = "--bonus" in args or "-b" in args
    skip_norm = "--no-norm" in args

    score = Score()

    # ── Prerequisites ──────────────────────────────────────────────────────
    check_files(score)
    if not skip_norm:
        result = subprocess.run(["which", "norminette"], capture_output=True)
        if result.returncode == 0:
            check_norminette(score)
        else:
            warn("norminette not found — skipping norm check")
    else:
        warn("Norm check skipped (--no-norm)")

    # ── General Instructions ───────────────────────────────────────────────
    compiled = check_compilation(score)
    if not compiled:
        section("ABORTED")
        fail("Cannot continue — compilation failed")
        _print_summary(score)
        sys.exit(1)

    server_ok = check_server_pid(score)
    check_client_usage(score)

    # ── Mandatory Part ─────────────────────────────────────────────────────
    check_global_variables(score)
    check_signal_usage(score)

    if server_ok:
        check_message_transmission(score)
        check_multiple_clients(score)
        check_performance(score)
    else:
        warn("Skipping runtime tests — server did not print PID")

    # ── Bonus Part ─────────────────────────────────────────────────────────
    if bonus:
        check_bonus_acknowledgment(score)
        check_bonus_unicode(score)
    else:
        info("Bonus checks skipped (run with --bonus / -b to enable)")

    _print_summary(score)


def _print_summary(score: Score):
    pts, mx = score.summary()
    pct = (pts / mx * 100) if mx else 0

    section("SUMMARY")
    print(f"  Score: {BOLD}{pts}/{mx}{RESET}  ({pct:.0f}%)")

    if score.failures:
        print(f"\n  {RED}Failed checks:{RESET}")
        for f in score.failures:
            print(f"    {RED}•{RESET} {f}")
    else:
        print(f"\n  {GREEN}{BOLD}All checks passed!{RESET}")

    print()


if __name__ == "__main__":
    main()
