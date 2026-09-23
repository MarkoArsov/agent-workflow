"""Disposable test services with named leases, observed readiness, and owned cleanup."""
from __future__ import annotations
import os
import re
import selectors
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path
from .process import stop
from .profile import validate_command
from .state import lock
from .util import WorkflowError, contained, identifier, read_json, user_data, write_json, redact

def definition(project, name):
    identifier(name)
    value = project.profile.get("environments", {}).get(name)
    if not value or not value.get("services"):
        raise WorkflowError(f"Configure test environment {name} with owned services and readiness patterns")
    identifier(value.get("lock_id", project.profile["project"]["id"] + "-" + name))
    for service in value["services"]:
        identifier(service.get("id", ""))
        project.repository(service.get("repository"))
        validate_command(service.get("command"))
        if not service.get("ready_pattern"):
            raise WorkflowError("An environment service requires an observed ready_pattern")
        re.compile(service["ready_pattern"])
        if not 1 <= service.get("startup_timeout_seconds", 30) <= 300:
            raise WorkflowError("Environment startup timeout must be between 1 and 300 seconds")
    return value

def status(project, name):
    return read_json(project.config / "local/environments" / identifier(name) / "status.json",
                     {"status": "not_started", "environment": name})

def release(project, name):
    value = status(project, name)
    if value["status"] != "active":
        return value
    write_json(project.config / "local/environments" / identifier(name) / "release.json", {"requested_at": time.time()})
    return {"environment": name, "release_requested": True,
            "detail": "The owning process stops its own services; no PID is killed by this request."}

@contextmanager
def lease(project, name, checkouts, cancel=None):
    from .verification import command_environment
    config = definition(project, name)
    root = project.config / "local/environments" / name
    root.mkdir(parents=True, exist_ok=True)
    lock_id = config.get("lock_id", project.profile["project"]["id"] + "-" + name)
    services, exported = [], {}
    with lock(user_data() / "environment-locks" / (lock_id + ".lock")):
        (root / "release.json").unlink(missing_ok=True)
        cancelled = lambda: (root / "release.json").exists() or bool(cancel and cancel())
        record = {"environment": name, "status": "starting", "owner_pid": os.getpid(), "services": [], "lock_id": lock_id}
        write_json(root / "status.json", record)
        try:
            for service in config["services"]:
                if service["repository"] not in checkouts:
                    raise WorkflowError("Environment services must use a participating repository")
                command = service["command"]
                cwd = contained(Path(checkouts[service["repository"]]), command.get("cwd", "."))
                process = subprocess.Popen(command["argv"], cwd=cwd, env=command_environment(command, exported),
                                           stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                           start_new_session=True)
                services.append(process)
                selector = selectors.DefaultSelector()
                selector.register(process.stdout, selectors.EVENT_READ)
                deadline = time.monotonic() + service.get("startup_timeout_seconds", 30)
                buffer = b""; observed = []
                ready = None
                try:
                    while time.monotonic() < deadline and not cancelled():
                        for key, _ in selector.select(0.1):
                            chunk = os.read(key.fileobj.fileno(), 65536)
                            if not chunk:
                                raise WorkflowError(f"Environment service {service['id']} exited before readiness")
                            buffer += chunk
                            while b"\n" in buffer:
                                line, buffer = buffer.split(b"\n", 1)
                                text = line.decode(errors="replace")
                                observed.append(text)
                                ready = re.search(service["ready_pattern"], text)
                                if ready:
                                    break
                        if ready:
                            break
                    if not ready:
                        raise WorkflowError(f"Environment service {service['id']} did not become ready within its bound")
                    for key, template in service.get("exports", {}).items():
                        exported[key] = template.format(**ready.groupdict())
                    record["services"].append({"id": service["id"], "pid": process.pid, "ready": True})
                    # Drain stdout after readiness so a busy service cannot fill its pipe.
                    import threading
                    def drain(stream):
                        try:
                            for line in iter(stream.readline, b""):
                                pass
                        except (OSError, ValueError):
                            pass
                    threading.Thread(target=drain, args=(process.stdout,), daemon=True).start()
                finally:
                    selector.close()
                    (root / (service["id"] + ".log")).write_text(redact("\n".join(observed)))
            record["status"] = "active"; write_json(root / "status.json", record)
            yield exported, cancelled
        finally:
            for process in reversed(services):
                stop(process)
                process.stdout.close()
            record["status"] = "released"; record["released_at"] = time.time()
            write_json(root / "status.json", record)
