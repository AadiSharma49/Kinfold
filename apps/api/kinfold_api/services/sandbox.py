from __future__ import annotations

import base64
from dataclasses import dataclass, field

import docker
from docker.errors import DockerException, NotFound

from kinfold_api.config import get_settings

SANDBOX_IMAGE = "python:3.12-slim"


class SandboxUnavailableError(RuntimeError):
    """Raised when the Docker daemon can't be reached."""


@dataclass
class TestCaseResult:
    passed: bool
    stdout: str
    error: str | None = None


@dataclass
class SandboxRunResult:
    passed_tests: int
    total_tests: int
    results: list[TestCaseResult] = field(default_factory=list)


def _get_client() -> docker.DockerClient:
    try:
        client = docker.from_env()
        client.ping()
    except DockerException as exc:
        raise SandboxUnavailableError(str(exc)) from exc
    return client


def _b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def _build_command(code: str, test_input: str) -> list[str]:
    # The container's root filesystem is read-only, so there's no writable
    # mount to `put_archive` files into before start. Instead, the code and
    # input are embedded in the container's own command, base64-encoded to
    # dodge shell-quoting entirely, and written into the tmpfs /sandbox mount
    # by the container's own shell at runtime.
    script = (
        f"echo {_b64(code)} | base64 -d > /sandbox/solution.py && "
        f"echo {_b64(test_input)} | base64 -d | python /sandbox/solution.py"
    )
    return ["sh", "-c", script]


def _run_one(client: docker.DockerClient, code: str, test_input: str, expected_output: str) -> TestCaseResult:
    settings = get_settings()
    container = None
    try:
        container = client.containers.create(
            SANDBOX_IMAGE,
            command=_build_command(code, test_input),
            network_disabled=True,
            mem_limit=settings.KINFOLD_SANDBOX_MEMORY_LIMIT,
            nano_cpus=1_000_000_000,  # 1 CPU
            pids_limit=64,
            read_only=True,
            tmpfs={"/sandbox": "size=16m,mode=1777"},
            working_dir="/sandbox",
            user="nobody",
            detach=True,
        )
        container.start()

        try:
            exit_status = container.wait(timeout=settings.KINFOLD_SANDBOX_TIMEOUT_SECONDS)
            stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
            stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")
            actual = stdout.strip()
            passed = exit_status.get("StatusCode") == 0 and actual == expected_output.strip()
            return TestCaseResult(passed=passed, stdout=actual, error=stderr or None)
        except Exception as exc:  # noqa: BLE001 - timeout/transport error: treat as a failed test
            try:
                container.kill()
            except (DockerException, NotFound):
                pass
            return TestCaseResult(passed=False, stdout="", error=str(exc))
    finally:
        if container is not None:
            try:
                container.remove(force=True)
            except (DockerException, NotFound):
                pass


def run_python_tests(code: str, tests: list[tuple[str, str]]) -> SandboxRunResult:
    """Run `code` against each (input, expected_output) pair.

    One fresh, network-disabled, resource-limited container per test case,
    auto-removed afterward. Raises SandboxUnavailableError if Docker can't
    be reached at all.
    """
    client = _get_client()
    results = [_run_one(client, code, test_input, expected_output) for test_input, expected_output in tests]
    passed_count = sum(1 for r in results if r.passed)
    return SandboxRunResult(passed_tests=passed_count, total_tests=len(tests), results=results)
