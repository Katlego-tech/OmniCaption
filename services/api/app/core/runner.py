"""Single-slot subprocess runner for the captioner pipeline.

The pipeline owns the GPU and the ``/output`` contract, so at most one run may
be in flight; a second trigger is rejected until the first finishes.
"""

from __future__ import annotations

import os
import shlex
import subprocess
import threading


class PipelineRunner:
    """Launches the pipeline command in a background thread and tracks its state."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state: str = "idle"
        self._returncode: int | None = None
        self._stdout: str = ""
        self._stderr: str = ""

    def start(self, command: list[str] | str) -> bool:
        """Start a run; returns False (without starting) if one is already running.

        Args:
            command: Argument list, or a single command-line string. Strings are
                passed verbatim on Windows (CreateProcess parses them) and
                shell-split on POSIX — never run through an actual shell.
        """
        with self._lock:
            if self._state == "running":
                return False
            self._state = "running"
            self._returncode = None
            self._stdout = ""
            self._stderr = ""

        args: list[str] | str = command
        if isinstance(command, str) and os.name != "nt":
            args = shlex.split(command)

        thread = threading.Thread(target=self._run, args=(args,), daemon=True)
        thread.start()
        return True

    def _run(self, args: list[str] | str) -> None:
        try:
            completed = subprocess.run(args, capture_output=True)
            returncode = completed.returncode
            stdout = completed.stdout.decode("utf-8", errors="replace")[-4000:]
            stderr = completed.stderr.decode("utf-8", errors="replace")[-4000:]
        except OSError:
            returncode = -1
            stdout = ""
            stderr = "OSError: command not found or not executable"
        with self._lock:
            self._returncode = returncode
            self._state = "succeeded" if returncode == 0 else "failed"
            self._stdout = stdout
            self._stderr = stderr

    def status(self) -> dict[str, str | int | None]:
        """Current run state and, once finished, the pipeline's exit code."""
        with self._lock:
            res: dict[str, str | int | None] = {
                "state": self._state,
                "returncode": self._returncode,
            }
            if self._state in ("succeeded", "failed"):
                res["stdout"] = self._stdout
                res["stderr"] = self._stderr
            return res
