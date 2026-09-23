"""Bounded process groups; only terminate children created by this process."""
from __future__ import annotations
import os
import selectors
import signal
import subprocess
import sys
import time
from .util import redact

def signal_group(process, sig):
    process.poll()  # Reap our leader before probing a group containing only zombies.
    try:
        os.killpg(process.pid, sig)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        if sys.platform != "darwin":
            raise
        # Darwin returns EPERM for a group whose remaining members are zombies.
        # Confirm that fact; never hide denied signals to a live process.
        listing = subprocess.run(["ps", "-A", "-o", "pgid=,stat="], text=True, capture_output=True, check=True)
        members = [line.split()[1] for line in listing.stdout.splitlines()
                   if len(line.split()) == 2 and line.split()[0] == str(process.pid)]
        if any(not status.startswith("Z") for status in members):
            raise
        return False

def stop(process):
    if getattr(process, "_workflow_stopped", False):
        return
    process._workflow_stopped = True
    # The session leader can exit while descendants still hold stdout or ignore TERM.
    # Every caller created this process with start_new_session=True.
    if not signal_group(process, signal.SIGTERM):
        process.wait()
        return
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        if not signal_group(process, 0):
            break
        time.sleep(0.05)
    else:
        signal_group(process, signal.SIGKILL)
    process.wait()

def execute(argv, cwd, *, input_text=None, env=None, timeout=1800, inactivity=300,
            tool_timeout=600, cancel=None, on_line=None, on_start=None):
    started = last_output = time.monotonic()
    process = subprocess.Popen([str(x) for x in argv], cwd=cwd, env=env, start_new_session=True,
                               stdin=subprocess.PIPE if input_text is not None else subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if input_text is not None:
        import threading
        def feed():
            try:
                process.stdin.write(input_text.encode()); process.stdin.close()
            except (BrokenPipeError, OSError):
                pass
        threading.Thread(target=feed, daemon=True).start()
    if on_start:
        on_start(process.pid)
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    buffer = b""
    output, reason, tool_started, output_size = [], None, None, 0
    try:
        while selector.get_map():
            now = time.monotonic()
            if cancel and cancel():
                reason = "cancelled"
            elif now - started > timeout:
                reason = "timeout"
            elif now - last_output > inactivity:
                reason = "inactive"
            elif tool_started is not None and now - tool_started > tool_timeout:
                reason = "tool-stalled"
            if reason:
                stop(process)
                break
            for key, _ in selector.select(0.1):
                chunk = os.read(key.fileobj.fileno(), 65536)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                last_output = time.monotonic()
                buffer += chunk
                output_size += len(chunk)
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    line = line.decode(errors="replace")
                    output.append(line)
                    if on_line:
                        event = on_line(line)
                        if event == "tool-start" and tool_started is None:
                            tool_started = time.monotonic()
                        elif event == "tool-end":
                            tool_started = None
            if output_size > 16_000_000:
                reason = "output-limit"
                stop(process)
                break
        if buffer:
            line = buffer.decode(errors="replace"); output.append(line)
            if on_line:
                on_line(line)
        try:
            code = process.wait(timeout=max(0.1, timeout - (time.monotonic() - started)))
        except subprocess.TimeoutExpired:
            reason = "timeout"; stop(process); code = process.returncode
        return {"exit_code": code, "reason": reason, "output": redact("\n".join(output)),
                "duration_seconds": round(time.monotonic() - started, 3)}
    finally:
        stop(process)
        selector.close()
        process.stdout.close()
