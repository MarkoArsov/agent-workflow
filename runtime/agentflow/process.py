"""Bounded process groups; only terminate children created by this process."""
from __future__ import annotations
import os
import queue
import selectors
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from .util import redact

WINDOWS = os.name == "nt"

if WINDOWS:
    import ctypes
    from ctypes import wintypes
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    _kernel32.CreateJobObjectW.argtypes = (wintypes.LPVOID, wintypes.LPCWSTR)
    _kernel32.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
    _kernel32.TerminateJobObject.argtypes = (wintypes.HANDLE, wintypes.UINT)
    _kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    _ntdll = ctypes.WinDLL("ntdll")
    _ntdll.NtResumeProcess.argtypes = (wintypes.HANDLE,)

def detached():
    """Popen options for a background child that outlives this process and its console."""
    if WINDOWS:
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS}
    return {"start_new_session": True}

def spawn(argv, **options):
    """Start a child that stop() can end with all of its descendants.

    POSIX uses a new session. Windows has no process groups that outlive their
    leader, so the child starts suspended, joins a job object, then resumes;
    anything it starts later joins the same job.
    """
    if not WINDOWS:
        return subprocess.Popen(executable(argv), start_new_session=True, **options)
    process = subprocess.Popen(executable(argv), **options,
                               creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | 0x4)  # CREATE_SUSPENDED
    job = _kernel32.CreateJobObjectW(None, None)
    if not job or not _kernel32.AssignProcessToJobObject(job, int(process._handle)):
        error = ctypes.get_last_error()
        process.kill(); process.wait()
        raise OSError(error, "Cannot place the child process in a job object")
    process._workflow_job = job
    _ntdll.NtResumeProcess(int(process._handle))
    return process

def executable(argv):
    """Windows finds only .exe files by bare name; agent CLIs are often .cmd shims."""
    argv = [str(x) for x in argv]
    if WINDOWS and argv and not Path(argv[0]).suffix:
        argv[0] = shutil.which(argv[0]) or argv[0]
    return argv

class Reader:
    """Read a child's output with a bounded wait. Windows pipes are not selectable, so use a thread there."""
    def __init__(self, stream):
        self.open = True
        self.stream = stream
        self.dropping = False
        if WINDOWS:
            self.chunks = queue.Queue()
            threading.Thread(target=self._pump, args=(stream.fileno(),), daemon=True).start()
        else:
            self.selector = selectors.DefaultSelector()
            self.selector.register(stream, selectors.EVENT_READ)

    def _pump(self, fd):
        try:
            while chunk := os.read(fd, 65536):
                if not self.dropping:
                    self.chunks.put(chunk)
        except OSError:
            pass
        self.chunks.put(b"")

    def read(self, wait):
        """Return the output available within wait seconds. Sets open to False at end of output."""
        if WINDOWS:
            chunks = []
            try:
                chunks.append(self.chunks.get(timeout=wait))
                while chunks[-1]:
                    chunks.append(self.chunks.get_nowait())
            except queue.Empty:
                pass
        else:
            chunks = [os.read(key.fileobj.fileno(), 65536) for key, _ in self.selector.select(wait)]
        if b"" in chunks:
            self.open = False
            chunks = chunks[:chunks.index(b"")]
        return chunks

    def discard(self):
        """Keep reading but drop the output, so a busy child cannot fill its pipe."""
        self.close()
        if WINDOWS:
            self.dropping = True
            return
        def drain():
            try:
                while os.read(self.stream.fileno(), 65536):
                    pass
            except (OSError, ValueError):
                pass
        threading.Thread(target=drain, daemon=True).start()

    def close(self):
        if not WINDOWS and self.selector:
            self.selector.close()
            self.selector = None

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
    if WINDOWS:
        # Ends the child and every descendant, even after the child itself exited.
        job = getattr(process, "_workflow_job", None)
        if job:
            _kernel32.TerminateJobObject(job, 1)
            _kernel32.CloseHandle(job)
            process._workflow_job = None
        elif process.poll() is None:
            process.kill()
        process.wait()
        return
    # The session leader can exit while descendants still hold stdout or ignore TERM.
    # Every caller created this process with spawn().
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
    process = spawn(argv, cwd=cwd, env=env,
                    stdin=subprocess.PIPE if input_text is not None else subprocess.DEVNULL,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if input_text is not None:
        def feed():
            try:
                process.stdin.write(input_text.encode()); process.stdin.close()
            except (BrokenPipeError, OSError):
                pass
        threading.Thread(target=feed, daemon=True).start()
    if on_start:
        on_start(process.pid)
    reader = Reader(process.stdout)
    buffer = b""
    output, reason, tool_started, output_size = [], None, None, 0
    try:
        while reader.open:
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
            for chunk in reader.read(0.1):
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
        reader.close()
        process.stdout.close()
