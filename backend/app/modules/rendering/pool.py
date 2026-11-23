"""Render worker processes (docs/04 §11; docs/12 §9; ADR-09).

At most ``RENDER_WORKERS`` renders run at once, each in a separate process started with the
``spawn`` method. A render that takes longer than ``RENDER_TIMEOUT_S`` is killed and its
worker replaced. Workers receive plain payloads and return PDF bytes; they never touch the
database or storage.
"""

from __future__ import annotations

import logging
import multiprocessing
import queue
import threading
from dataclasses import dataclass
from multiprocessing.connection import Connection
from typing import Any

logger = logging.getLogger("app.rendering")

WAIT_FOR_WORKER_EXTRA_S = 5


class RenderError(RuntimeError):
    """A render failed; ``code`` is a ``document_artifacts.last_error_code`` value."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class RenderJob:
    template_id: str
    payload: dict[str, Any]
    preview: bool
    expected_sha256: str | None = None  # final renders: the snapshot's canonical hash


def worker_main(connection: Connection) -> None:
    """Worker loop: receive a job, render it, send ("ok", bytes) or ("error", code)."""
    from app.modules.rendering.renderer import TemplateIntegrityError, render_pdf

    while True:
        try:
            job = connection.recv()
        except (EOFError, OSError):
            return
        if job is None:
            return
        try:
            if job.expected_sha256 is not None:
                from app.modules.documents.snapshot import canonical_sha256

                if canonical_sha256(job.payload) != job.expected_sha256:
                    connection.send(("error", "snapshot_integrity"))
                    continue
            connection.send(("ok", render_pdf(job.template_id, job.payload, preview=job.preview)))
        except TemplateIntegrityError:
            logger.error("template files do not match the registry: %s", job.template_id)
            connection.send(("error", "render_error"))
        except Exception:
            logger.exception("render failed")
            connection.send(("error", "render_error"))


class _Worker:
    def __init__(self, context: Any) -> None:
        parent, child = context.Pipe()
        self.process = context.Process(target=worker_main, args=(child,), daemon=True)
        self.process.start()
        child.close()
        self.connection: Connection = parent

    def stop(self, *, kill: bool) -> None:
        if not kill:
            try:
                self.connection.send(None)
            except (OSError, ValueError):
                pass
            self.process.join(timeout=2)
        if self.process.is_alive():
            self.process.kill()
            self.process.join(timeout=2)
        self.connection.close()


class RenderPool:
    def __init__(self, workers: int, timeout_s: float) -> None:
        self.timeout_s = timeout_s
        self._context = multiprocessing.get_context("spawn")
        self._slots: queue.Queue[_Worker | None] = queue.Queue()
        for _ in range(workers):
            self._slots.put(None)  # started lazily, on first use
        self._started: set[_Worker] = set()
        self._lock = threading.Lock()
        self._closed = False

    def render(self, job: RenderJob) -> bytes:
        """PDF bytes, or RenderError (render_timeout, render_error, snapshot_integrity,
        or ``unavailable`` when no worker becomes free in time)."""
        if self._closed:
            raise RenderError("unavailable")
        try:
            worker = self._slots.get(timeout=self.timeout_s + WAIT_FOR_WORKER_EXTRA_S)
        except queue.Empty:
            raise RenderError("unavailable") from None
        try:
            if worker is None:
                worker = self._start()
            worker.connection.send(job)
            if not worker.connection.poll(self.timeout_s):
                logger.error("render exceeded %ss; worker killed", self.timeout_s)
                self._discard(worker)
                worker = None
                raise RenderError("render_timeout")
            status, data = worker.connection.recv()
        except (EOFError, OSError, BrokenPipeError):
            logger.error("render worker stopped unexpectedly")
            if worker is not None:
                self._discard(worker)
            worker = None
            raise RenderError("render_error") from None
        finally:
            self._slots.put(worker)
        if status == "ok":
            return bytes(data)
        raise RenderError(str(data))

    def _start(self) -> _Worker:
        worker = _Worker(self._context)
        with self._lock:
            self._started.add(worker)
        return worker

    def _discard(self, worker: _Worker) -> None:
        with self._lock:
            self._started.discard(worker)
        worker.stop(kill=True)

    def close(self) -> None:
        self._closed = True
        with self._lock:
            workers = list(self._started)
            self._started.clear()
        for worker in workers:
            worker.stop(kill=False)
