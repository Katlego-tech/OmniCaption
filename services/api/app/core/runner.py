"""Single-slot subprocess runner for the captioner pipeline.

The pipeline owns the GPU and the ``/output`` contract, so at most one run may
be in flight; a second trigger is rejected until the first finishes.
"""

from __future__ import annotations

import logging
import os
import shlex
import subprocess
import threading
from collections.abc import Callable

logger = logging.getLogger(__name__)


class PipelineRunner:
    """Launches the pipeline command in a background thread and tracks its state."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state: str = "idle"
        self._returncode: int | None = None
        self._stdout: str = ""
        self._stderr: str = ""
        self._index: str | None = None

    def start(
        self,
        command: list[str] | str,
        post_run: Callable[[], None] | None = None,
    ) -> bool:
        """Start a run; returns False (without starting) if one is already running.

        Args:
            command: Argument list, or a single command-line string. Strings are
                passed verbatim on Windows (CreateProcess parses them) and
                shell-split on POSIX — never run through an actual shell.
            post_run: Optional best-effort hook invoked after the command exits 0
                (e.g. build the oracle index). A failure is logged and recorded as
                ``index="failed"`` but never fails the run.
        """
        with self._lock:
            if self._state == "running":
                return False
            self._state = "running"
            self._returncode = None
            self._stdout = ""
            self._stderr = ""
            self._index = None

        args: list[str] | str = command
        if isinstance(command, str) and os.name != "nt":
            args = shlex.split(command)

        thread = threading.Thread(target=self._run, args=(args, post_run), daemon=True)
        thread.start()
        return True

    def _run(self, args: list[str] | str, post_run: Callable[[], None] | None = None) -> None:
        try:
            completed = subprocess.run(args, capture_output=True)
            returncode = completed.returncode
            stdout = completed.stdout.decode("utf-8", errors="replace")[-4000:]
            stderr = completed.stderr.decode("utf-8", errors="replace")[-4000:]
        except OSError:
            returncode = -1
            stdout = ""
            stderr = "OSError: command not found or not executable"

        # Best-effort post-run hook (e.g. build the oracle index). Runs while the
        # state is still "running" so a poll only sees "succeeded" once it's done.
        index: str | None = None
        if returncode == 0 and post_run is not None:
            try:
                post_run()
                index = "built"
            except Exception as exc:  # noqa: BLE001 - index build must never fail the run
                logger.warning("post-run hook failed: %s", exc)
                index = "failed"

        with self._lock:
            self._returncode = returncode
            self._state = "succeeded" if returncode == 0 else "failed"
            self._stdout = stdout
            self._stderr = stderr
            self._index = index

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
            if self._index is not None:
                res["index"] = self._index
            return res
