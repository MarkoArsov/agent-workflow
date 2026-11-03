"""Container isolation tests: policy, argv, environment guards, cancellation.

All tests requiring the isolation module use guarded imports (FAIL/AssertionError
rather than ImportError). No real container engine is used by default.
PLOVI_TEST_DOCKER=1 opts into a smoke test against a locally built image.
"""
from __future__ import annotations
import json
import os
import platform
import subprocess
import sys
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch
from tests.helpers import PACKAGE, WorkspaceTest, install_script


class ContainerTests(WorkspaceTest):

    # ---- helpers -----------------------------------------------------------

    def _require_isolation(self):
        try:
            from plovi import isolation
            return isolation
        except ImportError:
            self.fail("plovi.isolation module not yet implemented")

    def _require_factory(self):
        import importlib.util
        self.assertIsNotNone(importlib.util.find_spec("plovi.factory"), "plovi.factory module not yet implemented")
        from plovi import factory
        return factory

    def _factory_owned_project(self, task, repo_id="app"):
        """Build a project with a real remote and obtain a factory-owned checkout for it.

        C2 requires factory-owned checkout metadata for container execution; a plain
        local/legacy project must not be mistaken for an owned allocation.
        """
        factory = self._require_factory()
        bare = self.bare_remote(f"container-{task}")
        self.seed_remote(bare)
        # Clone directory's basename is the repo_id so repository auto-detection
        # assigns the same id as the patched repository below, instead of
        # registering it twice under two ids with the same "." path.
        (self.root / task).mkdir(parents=True, exist_ok=True)
        working = self.clone_repo(bare, f"{task}/{repo_id}")
        project = self.setup_project(working, patch={
            "repositories": [{"id": repo_id, "path": ".", "checkout_strategy": "worktree", "base_branch": "main"}],
        })
        result = factory.allocate(project, task, unattended=True)
        checkout = result[repo_id] if isinstance(result, dict) else result
        return project, task, Path(checkout)

    def _install_fake_runtime(self, name="docker"):
        """Install fake docker/podman binary in a test bin dir and return record path."""
        # Exercise the fake engine protocol on every host; the separate Windows
        # diagnostic still exercises the actual unsupported-platform guard.
        isolation = self._require_isolation()
        preflight = isolation.preflight
        def simulated_preflight(*args, **kwargs):
            kwargs.setdefault("platform_override", "Darwin")
            return preflight(*args, **kwargs)
        simulator = patch.object(isolation, "preflight", side_effect=simulated_preflight)
        simulator.start()
        self.addCleanup(simulator.stop)
        bin_dir = self.root / "fake-bin"
        install_script(bin_dir, name, PACKAGE / "tests/fixtures/fake_docker.py")
        record = self.root / "container-calls.json"
        self.env["PLOVI_TEST_CONTAINER_RECORD"] = str(record)
        self.env["PATH"] = str(bin_dir) + os.pathsep + self.env.get("PATH", "")
        os.environ["PLOVI_TEST_CONTAINER_RECORD"] = str(record)
        os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")
        return record

    def _read_calls(self, record):
        if not record.exists():
            return []
        return json.loads(record.read_text())

    # ---- red check ---------------------------------------------------------

    def test_isolation_policy_is_accepted(self):
        """plovi.toml with [isolation] section must be accepted by policy.validate()."""
        import tomllib
        from plovi import policy
        from plovi.util import WorkflowError

        toml_text = textwrap.dedent("""\
            [isolation]
            mode = 'container'
            checkout = 'factory'
            runtime = 'auto'
            image = 'plovi/runner:latest'
            network = 'off'
            mount_harness_config = []
            api_key_env = []
        """)
        data = tomllib.loads(toml_text)
        # Currently raises WorkflowError because isolation is an unknown section.
        # After implementation, validate() must accept it and return it in the result.
        try:
            result = policy.validate(data)
        except WorkflowError as exc:
            self.fail(f"policy.validate() must accept [isolation] section; got: {exc}")
        self.assertIn("isolation", result, "Isolation section must be present in validated policy")
        isolation_cfg = result["isolation"]
        self.assertEqual(isolation_cfg.get("mode"), "container")
        self.assertEqual(isolation_cfg.get("image"), "plovi/runner:latest")

    # ---- green checks ------------------------------------------------------

    def test_docker_and_podman_argv(self):
        """isolation module must build correct argv for both docker and podman runtimes."""
        isolation = self._require_isolation()
        self.assertTrue(hasattr(isolation, "build_container_argv"),
                        "isolation.build_container_argv must be implemented")
        for runtime in ("docker", "podman"):
            argv = isolation.build_container_argv(
                runtime=runtime,
                image="plovi/runner:test",
                workdir="/workspace",
                env_names=["MY_API_KEY"],
                mounts=["/workspace:/workspace:rw"],
                network="off",
                stdin=True,
            )
            self.assertEqual(argv[0], runtime, f"First element must be {runtime!r}")
            self.assertIn("run", argv, "argv must include 'run' subcommand")
            self.assertIn("--rm", argv, "argv must include --rm for cleanup")
            self.assertIn("--pull=never", argv, "argv must include --pull=never")
            self.assertNotIn("-t", argv, "argv must not allocate a TTY (-t)")
            self.assertIn("--network=none", argv, "network=off must map to --network=none")
            # Image must be present
            self.assertIn("plovi/runner:test", argv, "Image must appear in argv")

    def test_fake_runtime_runs_stages_and_checks(self):
        """With a fake runtime, stage commands must be executed via the container wrapper."""
        isolation = self._require_isolation()
        record = self._install_fake_runtime("docker")

        project, task, checkout = self._factory_owned_project("run-stage")
        policy_cfg = {
            "isolation": {
                "mode": "container", "checkout": "factory",
                "runtime": "docker",
                "image": "plovi/runner:test",
                "network": "off",
                "mount_harness_config": [],
                "api_key_env": [],
            }
        }
        self.assertTrue(hasattr(isolation, "build_execution_context"),
                        "isolation.build_execution_context must be implemented")
        ctx = isolation.build_execution_context(project, policy_cfg, task=task)
        self.assertIsNotNone(ctx, "Execution context must not be None for container mode")

        # Run a simple command through the container wrapper
        self.assertTrue(hasattr(isolation, "run_contained"),
                        "isolation.run_contained must be implemented")
        result = isolation.run_contained(ctx, ["echo", "hello"])
        self.assertEqual(result.returncode, 0, "Contained command must succeed with fake runtime")

        calls = self._read_calls(record)
        self.assertTrue(calls, "Fake runtime must record at least one invocation")
        # Preflight/image-inspect probing may precede execution (C4); find the actual
        # execution call rather than assuming it is the first recorded invocation.
        run_calls = [c for c in calls if "run" in c.get("argv", [])]
        self.assertTrue(run_calls, "Fake runtime must record the execution 'run' invocation")
        execution_call = run_calls[-1]
        self.assertIn("--pull=never", execution_call["argv"], "Execution call must use --pull=never")

    def test_missing_runtime_refuses_trusted_unattended(self):
        """Trusted unattended execution must refuse before any stage when runtime is unavailable."""
        isolation = self._require_isolation()
        # Factory-owned checkout first (git must stay available long enough to
        # construct it), so the refusal below is attributable to the missing
        # runtime and not to absent ownership metadata (C2).
        project, task, checkout = self._factory_owned_project("missing-runtime-trusted")
        # Ensure docker/podman are not in PATH for this test.
        empty_bin = self.root / "empty-bin"
        empty_bin.mkdir(exist_ok=True)
        self.env["PATH"] = str(empty_bin)
        os.environ["PATH"] = str(empty_bin)

        policy_cfg = {
            "isolation": {
                "mode": "container", "checkout": "factory",
                "runtime": "auto",
                "image": "plovi/runner:test",
            }
        }
        from plovi.util import WorkflowError
        with self.assertRaises(WorkflowError,
                               msg="Missing runtime must refuse trusted unattended execution"):
            isolation.preflight(project, policy_cfg, trusted=True, unattended=True, task=task)

    def test_missing_runtime_reports_restricted_fallback(self):
        """Restricted execution with missing runtime must report a degraded boundary, not fail."""
        isolation = self._require_isolation()
        # Factory-owned checkout first, so the result below is attributable to the
        # missing runtime and not to absent ownership metadata (C2).
        project, task, checkout = self._factory_owned_project("missing-runtime-restricted")
        # Ensure docker/podman are not in PATH for this test.
        empty_bin = self.root / "empty-bin"
        empty_bin.mkdir(exist_ok=True)
        self.env["PATH"] = str(empty_bin)
        os.environ["PATH"] = str(empty_bin)

        policy_cfg = {
            "isolation": {
                "mode": "container", "checkout": "factory",
                "runtime": "auto",
                "image": "plovi/runner:test",
            }
        }
        self.assertTrue(hasattr(isolation, "preflight"),
                        "isolation.preflight must be implemented")
        result = isolation.preflight(project, policy_cfg, trusted=False, unattended=True, task=task)
        self.assertIsNotNone(result, "Preflight must return a result even for degraded boundary")
        self.assertTrue(
            result.get("degraded") or result.get("fallback"),
            "Preflight result must indicate degraded/fallback mode when runtime is missing",
        )

    def test_no_implicit_pull(self):
        """A missing container image must never trigger an implicit pull."""
        isolation = self._require_isolation()
        record = self._install_fake_runtime("docker")
        # The fake engine records inspection of this missing-image tag and fails it.
        project, task, checkout = self._factory_owned_project("missing-image")
        policy_cfg = {
            "isolation": {
                "mode": "container", "checkout": "factory",
                "runtime": "docker",
                "image": "plovi/runner:missing",
                "network": "off",
            }
        }
        from plovi.util import WorkflowError
        with self.assertRaises(WorkflowError,
                               msg="Missing image must fail without implicit pull"):
            isolation.preflight(project, policy_cfg, trusted=True, unattended=True, task=task)

        calls = self._read_calls(record)
        pull_calls = [c for c in calls if "pull" in c.get("argv", [])]
        self.assertFalse(pull_calls, "No implicit pull must happen for missing image")

    def test_explicit_pull_consent(self):
        """With explicit pull consent, the runtime must pull the named image."""
        isolation = self._require_isolation()
        record = self._install_fake_runtime("docker")
        project = self.setup_project(self.repo("proj"))
        policy_cfg = {
            "isolation": {
                "mode": "container", "checkout": "factory",
                "runtime": "docker",
                "image": "plovi/runner:test",
            }
        }
        self.assertTrue(hasattr(isolation, "pull_image"),
                        "isolation.pull_image must be implemented")
        isolation.pull_image(project, policy_cfg, runtime="docker")
        calls = self._read_calls(record)
        pull_calls = [c for c in calls if "pull" in c.get("argv", [])]
        self.assertTrue(pull_calls, "Explicit pull consent must invoke runtime pull")
        self.assertIn("plovi/runner:test", pull_calls[0]["argv"],
                      "Pull must target the configured image")

    def test_container_environment_does_not_leak_keys(self):
        """API keys must not appear in the container environment via non-allowlisted names."""
        isolation = self._require_isolation()
        record = self._install_fake_runtime("docker")

        # Set a fake API key in the host environment
        os.environ["CANARY_SECRET_KEY"] = "very-secret-value"
        os.environ["MY_EXPLICIT_API_KEY"] = "allowed-value"
        self.addCleanup(lambda: os.environ.pop("CANARY_SECRET_KEY", None))
        self.addCleanup(lambda: os.environ.pop("MY_EXPLICIT_API_KEY", None))

        project, task, checkout = self._factory_owned_project("env-leak-check")
        policy_cfg = {
            "isolation": {
                "mode": "container", "checkout": "factory",
                "runtime": "docker",
                "image": "plovi/runner:test",
                "network": "off",
                "api_key_env": ["MY_EXPLICIT_API_KEY"],
                "mount_harness_config": [],
            }
        }
        ctx = isolation.build_execution_context(project, policy_cfg, task=task)
        isolation.run_contained(ctx, ["echo", "test"])

        calls = self._read_calls(record)
        self.assertTrue(calls, "Must have at least one container call")
        last = calls[-1]
        passed_env = last.get("env_keys", [])

        # Canary key must not be forwarded
        self.assertNotIn("CANARY_SECRET_KEY", passed_env,
                         "Non-allowlisted env keys must not leak into container")
        # Explicitly allowlisted key must be forwarded
        self.assertIn("MY_EXPLICIT_API_KEY", passed_env,
                      "Allowlisted API key must be forwarded to container")

    def test_check_services_stay_contained(self):
        """Check environment services must run inside the container boundary, not on the host."""
        isolation = self._require_isolation()
        self.assertTrue(hasattr(isolation, "build_service_context"),
                        "isolation.build_service_context must be implemented")
        project, task, checkout = self._factory_owned_project("task-svc")
        policy_cfg = {
            "isolation": {
                "mode": "container", "checkout": "factory",
                "runtime": "docker",
                "image": "plovi/runner:test",
                "network": "on",
            }
        }
        # A service context with network=on must provide a task-scoped runtime network
        ctx = isolation.build_service_context(project, task, policy_cfg)
        self.assertIsNotNone(ctx, "Service context must not be None in container mode")
        # Host execution flag must not be set
        self.assertFalse(
            ctx.get("host_execution", False),
            "Container service context must not allow host execution of services",
        )

    def test_cancel_removes_only_owned_container(self):
        """Cancellation must stop and remove the task's container without touching others."""
        isolation = self._require_isolation()
        record = self._install_fake_runtime("docker")
        project, task, checkout = self._factory_owned_project("cancel-check")
        policy_cfg = {
            "isolation": {
                "mode": "container", "checkout": "factory",
                "runtime": "docker",
                "image": "plovi/runner:test",
                "network": "off",
            }
        }
        ctx = isolation.build_execution_context(project, policy_cfg, task=task)
        # Simulate a tracked container name
        container_name = ctx.get("container_name") if ctx else None
        self.assertTrue(hasattr(isolation, "cancel_containers"),
                        "isolation.cancel_containers must be implemented")
        # Should not raise even if no container is actually running
        isolation.cancel_containers(ctx)

        if record.exists():
            calls = self._read_calls(record)
            stop_rm_calls = [
                c for c in calls
                if any(a in c.get("argv", []) for a in ("stop", "rm"))
            ]
            for call in stop_rm_calls:
                if container_name:
                    # Only owned container name should appear in stop/rm calls
                    non_owned = [
                        a for a in call["argv"]
                        if a != container_name and not a.startswith("-") and
                        a not in ("docker", "podman", "stop", "rm")
                    ]
                    self.assertFalse(
                        non_owned,
                        f"Cancel must only reference owned container; got: {call['argv']}",
                    )

    def test_windows_container_diagnostic(self):
        """Container mode on Windows must report unsupported with a clear diagnostic."""
        isolation = self._require_isolation()
        project, task, checkout = self._factory_owned_project("windows-diagnostic")
        policy_cfg = {
            "isolation": {
                "mode": "container", "checkout": "factory",
                "runtime": "auto",
                "image": "plovi/runner:test",
            }
        }
        from plovi.util import WorkflowError
        with self.assertRaises((WorkflowError, NotImplementedError),
                               msg="Windows container mode must report unsupported"):
            isolation.preflight(project, policy_cfg, trusted=True, unattended=True,
                                platform_override="Windows", task=task)

    @unittest.skipUnless(os.environ.get("PLOVI_TEST_DOCKER") == "1",
                         "Set PLOVI_TEST_DOCKER=1 to run real-engine smoke test")
    def test_real_engine_smoke(self):
        """Real-engine smoke: container mounts, git reads, UID and cancellation (opt-in only)."""
        isolation = self._require_isolation()
        project, task, checkout = self._factory_owned_project("real-engine-smoke")
        policy_cfg = {
            "isolation": {
                "mode": "container", "checkout": "factory",
                "runtime": "docker",
                "image": os.environ.get("PLOVI_TEST_IMAGE", "plovi/runner:test"),
                "network": "off",
                "mount_harness_config": [],
                "api_key_env": [],
            }
        }
        ctx = isolation.build_execution_context(project, policy_cfg, task=task)
        result = isolation.run_contained(ctx, ["git", "rev-parse", "--git-dir"])
        self.assertEqual(result.returncode, 0, "git must work inside the container")
        marker = checkout / "container-smoke.txt"
        marker.write_text("owned workspace\n")
        for command in (["git", "status", "--porcelain"], ["git", "diff"],
                        ["python3", "-c", "from pathlib import Path; print(Path('container-smoke.txt').read_text())"]):
            result = isolation.run_contained(ctx, command)
            self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("owned workspace", result.stdout)
        if platform.system() == "Linux":
            result = isolation.run_contained(ctx, ["python3", "-c", "import os; print(os.getuid())"])
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertEqual(int(result.stdout.strip()), os.getuid())
        readonly = next(m['target'] for m in ctx['mounts'] if m['readonly'])
        result = isolation.run_contained(ctx, ["python3", "-c",
            "from pathlib import Path; import sys; (Path(sys.argv[1])/'forbidden-smoke').write_text('x')", readonly])
        self.assertNotEqual(result.returncode, 0, "Mirror metadata must remain read-only")
        isolation.cancel_containers(ctx)
        # A timed-out client must also remove the engine's running container.
        cancellation = isolation.build_execution_context(project, policy_cfg, task=task)
        self.addCleanup(isolation.cancel_containers, cancellation)
        result = isolation.run_contained(cancellation, ["python3", "-c", "import time; time.sleep(60)"], timeout=1)
        self.assertNotEqual(result.returncode, 0)
        probe = subprocess.run([cancellation['binary'], "inspect", cancellation['container_name']],
                               capture_output=True, env=isolation.runtime_environment({}))
        self.assertNotEqual(probe.returncode, 0, "Cancelled container must no longer exist")

    # ---- negative coverage (C2 ownership, C4 image identity) ---------------

    def test_container_mode_requires_factory_ownership(self):
        """Container execution must refuse a project/task with no factory allocation."""
        isolation = self._require_isolation()
        project = self.setup_project(self.repo("proj"))
        policy_cfg = {
            "isolation": {
                "mode": "container", "checkout": "factory",
                "runtime": "docker",
                "image": "plovi/runner:test",
                "network": "off",
            }
        }
        from plovi.util import WorkflowError
        with self.assertRaises(WorkflowError,
                               msg="Container mode must refuse a non-factory-owned (legacy/local) checkout"):
            isolation.build_execution_context(project, policy_cfg, task="unowned-task")

    def test_invalid_image_metadata_refused(self):
        """Preflight must refuse to pin an image ID from malformed inspect metadata."""
        isolation = self._require_isolation()
        self._install_fake_runtime("docker")
        os.environ["PLOVI_TEST_CONTAINER_INSPECT_INVALID"] = "1"
        self.env["PLOVI_TEST_CONTAINER_INSPECT_INVALID"] = "1"
        self.addCleanup(lambda: os.environ.pop("PLOVI_TEST_CONTAINER_INSPECT_INVALID", None))

        project, task, checkout = self._factory_owned_project("invalid-image-metadata")
        policy_cfg = {
            "isolation": {
                "mode": "container", "checkout": "factory",
                "runtime": "docker",
                "image": "plovi/runner:test",
                "network": "off",
            }
        }
        from plovi.util import WorkflowError
        with self.assertRaises(WorkflowError,
                               msg="Malformed image inspect metadata must refuse, not pin a fabricated ID"):
            isolation.preflight(project, policy_cfg, trusted=True, unattended=True, task=task)

    def test_config_mount_cannot_expose_home_or_project(self):
        """Provider opt-in must never turn into a broad host data mount."""
        isolation = self._require_isolation()
        from plovi.util import WorkflowError
        project = self.setup_project(self.repo("mount-guard"))
        config = {"mount_harness_config": ["codex"]}
        for source in (self.home, project.root, PACKAGE, project.config / "local"):
            source.mkdir(parents=True, exist_ok=True)
            with self.subTest(source=source.name), patch.dict(os.environ, {"CODEX_HOME": str(source)}):
                with self.assertRaises(WorkflowError):
                    isolation._config_mounts(project, config)

    def test_service_lease_uses_owned_network_and_contained_commands(self):
        """Exercise the actual service/check wrapper and engine cleanup protocol."""
        isolation = self._require_isolation()
        from plovi.environments import lease
        record = self._install_fake_runtime()
        project, task, checkout = self._factory_owned_project("service-protocol")
        project.profile["environments"] = {"fixture": {"services": [{
            "id": "fixture-service", "repository": "app",
            "command": {"argv": [sys.executable, "-u", "-c",
                "import time; print('READY'); time.sleep(60)"], "cwd": "."},
            "ready_pattern": "READY", "startup_timeout_seconds": 5,
            "exports": {"SERVICE_URL": "http://fixture-service:1234"},
        }]}}
        ctx = isolation.build_execution_context(project, {"isolation": {
            "mode": "container", "checkout": "factory", "runtime": "docker", "image": "plovi/runner:test", "network": "on",
        }}, task=task)
        self.addCleanup(isolation.cancel_containers, ctx)
        token = isolation.active.set(ctx)
        try:
            with lease(project, "fixture", ctx['checkouts']) as (exported, cancelled):
                result = isolation.run_contained(ctx, [sys.executable, "-c",
                    "import os; print(os.environ['SERVICE_URL'])"], env=dict(os.environ, **exported))
                self.assertEqual(result.returncode, 0, result.stdout)
                self.assertIn("http://fixture-service:1234", result.stdout)
                self.assertFalse(cancelled())
            isolation.cancel_containers(ctx)
        finally:
            isolation.active.reset(token)
        calls = self._read_calls(record)
        service = next(c for c in calls if '--network-alias' in c['argv'])
        name = service['argv'][service['argv'].index('--name') + 1]
        self.assertTrue(any(c['argv'] == ['rm', '-f', name] for c in calls))
        self.assertTrue(any(c['argv'][:2] == ['network', 'create'] for c in calls))
        self.assertTrue(any(c['argv'][:2] == ['network', 'rm'] for c in calls))
