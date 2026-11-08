"""Small helper that keeps slow work off the Qt UI thread and shuts down safely."""
from __future__ import annotations

import itertools

from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot


class _Job(QObject):
    done = pyqtSignal(int, object)
    failed = pyqtSignal(int, str)

    def __init__(self, job_id: int, function, args):
        super().__init__()
        self.job_id, self.function, self.args = job_id, function, tuple(args)

    @pyqtSlot()
    def run(self):
        try:
            self.done.emit(self.job_id, self.function(*self.args))
        except Exception as exc:  # surfaced to the UI as a readable message
            self.failed.emit(self.job_id, str(exc) or exc.__class__.__name__)


class BackgroundRunner(QObject):
    """Runs callables on worker threads; callbacks always run on the runner's (UI) thread.

    Results are routed through slots on this QObject, so Qt queues them to the
    UI thread. ``cancel`` discards results of jobs that are still running.
    """

    changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ids = itertools.count(1)
        self._jobs: dict[int, tuple[QThread, _Job, object, object, int]] = {}
        self.generation = 0
        self.closing = False

    @property
    def busy(self) -> bool:
        return bool(self._jobs)

    def cancel(self) -> None:
        """Late results are ignored. Python work cannot be interrupted mid-call."""
        self.generation += 1

    def start(self, function, args, done, failed):
        if self.closing:
            return
        job_id = next(self._ids)
        thread = QThread(self)
        job = _Job(job_id, function, args)
        job.moveToThread(thread)
        thread.started.connect(job.run)
        job.done.connect(self._on_done)
        job.failed.connect(self._on_failed)
        job.done.connect(thread.quit)
        job.failed.connect(thread.quit)
        thread.finished.connect(job.deleteLater)
        thread.finished.connect(self._on_finished)
        self._jobs[job_id] = (thread, job, done, failed, self.generation)
        thread.start()
        self.changed.emit()

    def _callback(self, job_id: int, index: int):
        entry = self._jobs.get(job_id)
        if not entry or self.closing or entry[4] != self.generation:
            return None
        return entry[index]

    @pyqtSlot(int, object)
    def _on_done(self, job_id, value):
        callback = self._callback(job_id, 2)
        if callback:
            callback(value)

    @pyqtSlot(int, str)
    def _on_failed(self, job_id, message):
        callback = self._callback(job_id, 3)
        if callback:
            callback(message)

    @pyqtSlot()
    def _on_finished(self):
        for job_id, entry in list(self._jobs.items()):
            if entry[0].isFinished():
                del self._jobs[job_id]
        if not self.closing:
            self.changed.emit()

    def shutdown(self, timeout_ms: int = 3000) -> bool:
        """Stop delivering results and wait for workers. Returns True if all finished."""
        self.closing = True
        self.generation += 1
        clean = True
        for thread, *_rest in list(self._jobs.values()):
            thread.quit()
            clean = thread.wait(timeout_ms) and clean
        self._jobs.clear()
        return clean
