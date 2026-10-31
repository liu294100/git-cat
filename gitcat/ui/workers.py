"""Thread-pool jobs and the signal bridge that brings their results back to the GUI thread."""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QObject, QRunnable, Signal


class Bridge(QObject):
    """Worker thread -> GUI thread signal bridge."""
    log = Signal(str, int, str, str)
    progress = Signal(int, str, int)
    finished = Signal(int, bool, object)


class Job(QRunnable):
    def __init__(self, jid: int, fn: Callable, bridge: Bridge, with_progress: bool = False):
        super().__init__()
        self.jid, self.fn, self.bridge, self.with_progress = jid, fn, bridge, with_progress

    def _emit(self, signal_name: str, *args) -> None:
        try:
            getattr(self.bridge, signal_name).emit(*args)
        except RuntimeError:  # window already destroyed (app shutting down)
            pass

    def run(self):
        try:
            if self.with_progress:
                res = self.fn(lambda phase, pct: self._emit("progress", self.jid, phase, pct))
            else:
                res = self.fn()
        except Exception as e:  # noqa: BLE001
            self._emit("finished", self.jid, False, e)
            return
        self._emit("finished", self.jid, True, res)
