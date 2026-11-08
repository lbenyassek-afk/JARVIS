"""Screen Guide desktop page: inspect a window read-only, then get grounded guidance."""
from __future__ import annotations

import html
import json
import time
from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFrame, QHBoxLayout, QLabel, QPlainTextEdit,
    QPushButton, QSplitter, QTextBrowser, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from core import screen_guide as sg
from core.config import load_config
from ui.background import BackgroundRunner

STALE_SECONDS = 120


class SharedDataPreview(QDialog):
    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Screen Guide // Data that would be shared")
        self.resize(640, 520)
        layout = QVBoxLayout(self)
        note = QLabel("This is the complete request content. Nothing else from the screen is sent.")
        note.setWordWrap(True)
        layout.addWidget(note)
        body = QPlainTextEdit(text); body.setReadOnly(True)
        layout.addWidget(body, 1)
        close = QPushButton("CLOSE"); close.clicked.connect(self.accept)
        layout.addWidget(close)


class ScreenGuidePage(QWidget):
    """Observation-only page. It contains no control that performs desktop actions."""

    def __init__(self, parent=None, backend_factory=None, guide_function=None, clock=time.time):
        super().__init__(parent)
        self.setObjectName("screenGuidePage")
        self._backend_factory = backend_factory or sg.default_backend
        self._guide = guide_function or sg.guide
        self._clock = clock
        self.runner = BackgroundRunner(self)
        self.runner.changed.connect(self._update_buttons)
        self.observation: sg.Observation | None = None
        self.last_guidance: sg.Guidance | None = None
        self._windows: list[sg.WindowInfo] = []
        self._build()
        self.apply_settings()

    # ------------------------------------------------------------------ layout
    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 22); layout.setSpacing(10)
        title = QHBoxLayout()
        label = QLabel("SCREEN GUIDE"); label.setObjectName("section")
        self.mode_label = QLabel("READ-ONLY  ·  NO ACTIONS"); self.mode_label.setObjectName("engine")
        title.addWidget(label); title.addStretch(); title.addWidget(self.mode_label)
        layout.addLayout(title)

        self.goal = QPlainTextEdit(); self.goal.setObjectName("guideGoal")
        self.goal.setPlaceholderText("Describe your goal, e.g. “export this document as PDF” "
                                     "or “turn on dark mode”.")
        self.goal.setMaximumHeight(64)
        layout.addWidget(self.goal)

        target = QHBoxLayout()
        self.window_selector = QComboBox(); self.window_selector.setMinimumWidth(320)
        self.window_selector.setPlaceholderText("Refresh to list open windows")
        self.refresh_button = QPushButton("REFRESH WINDOWS"); self.refresh_button.clicked.connect(self.refresh_windows)
        self.inspect_button = QPushButton("INSPECT WINDOW"); self.inspect_button.clicked.connect(self.inspect_selected)
        target.addWidget(self.window_selector, 1); target.addWidget(self.refresh_button)
        target.addWidget(self.inspect_button)
        layout.addLayout(target)

        card = QFrame(); card.setObjectName("dataCard"); card_layout = QVBoxLayout(card)
        self.support_label = QLabel("NOTHING OBSERVED YET"); self.support_label.setObjectName("dataValue")
        self.support_reason = QLabel("Choose a window and press Inspect. JARVIS reads its "
                                     "accessibility controls once; it does not watch continuously.")
        self.support_reason.setWordWrap(True); self.support_reason.setObjectName("hint")
        self.meta_label = QLabel(""); self.meta_label.setObjectName("hint"); self.meta_label.setWordWrap(True)
        card_layout.addWidget(self.support_label); card_layout.addWidget(self.support_reason)
        card_layout.addWidget(self.meta_label)
        self.controls_tree = QTreeWidget(); self.controls_tree.setHeaderLabels(["Control", "Type", "Enabled"])
        self.controls_tree.setRootIsDecorated(False); self.controls_tree.setMinimumHeight(110)
        card_layout.addWidget(self.controls_tree, 1)
        self.splitter = QSplitter(Qt.Orientation.Vertical); self.splitter.setChildrenCollapsible(False)
        self.splitter.addWidget(card)

        share_row = QHBoxLayout()
        self.share_checkbox = QCheckBox("Share this window's control names and my goal with Gemini for this request")
        self.preview_button = QPushButton("PREVIEW SHARED DATA"); self.preview_button.clicked.connect(self.preview_shared)
        share_row.addWidget(self.share_checkbox, 1); share_row.addWidget(self.preview_button)
        layout.addLayout(share_row)
        self.share_note = QLabel(""); self.share_note.setObjectName("hint"); self.share_note.setWordWrap(True)
        layout.addWidget(self.share_note)

        actions = QHBoxLayout()
        self.guide_button = QPushButton("GET GUIDANCE"); self.guide_button.setObjectName("primary")
        self.guide_button.clicked.connect(self.request_guidance)
        self.cancel_button = QPushButton("CANCEL"); self.cancel_button.clicked.connect(self.cancel)
        self.clear_button = QPushButton("CLEAR"); self.clear_button.clicked.connect(self.clear)
        actions.addWidget(self.guide_button); actions.addWidget(self.cancel_button)
        actions.addWidget(self.clear_button); actions.addStretch()
        self.status = QLabel(""); self.status.setObjectName("hint"); actions.addWidget(self.status)
        layout.addLayout(actions)

        self.output = QTextBrowser(); self.output.setObjectName("chat"); self.output.setOpenExternalLinks(False)
        self.output.setMinimumHeight(120)
        self.splitter.addWidget(self.output)
        self.splitter.setStretchFactor(0, 1); self.splitter.setStretchFactor(1, 1)
        layout.addWidget(self.splitter, 1)
        footer = QLabel("Screen Guide reads accessibility names and control types only. It captures no "
                        "screenshots, OCR or field contents, keeps observations in memory only, and "
                        "never clicks or types. Use Desktop Control for reviewed actions.")
        footer.setObjectName("hint"); footer.setWordWrap(True)
        layout.addWidget(footer)
        self._update_buttons()

    # ---------------------------------------------------------------- settings
    def settings(self) -> dict:
        return load_config().get("screen_guide", {})

    def apply_settings(self):
        cfg = self.settings()
        enabled = bool(cfg.get("enabled", True))
        sharing = str(cfg.get("cloud_sharing", "ask"))
        self.share_checkbox.setChecked(False)
        self.share_checkbox.setEnabled(enabled and sharing == "ask")
        if not enabled:
            self.share_note.setText("Screen Guide is turned off in Settings → Screen Guide.")
        elif sharing == "never":
            self.share_note.setText("Cloud sharing is disabled in Settings. Guidance is local keyword "
                                    "matching only.")
        else:
            self.share_note.setText("Unchecked: guidance stays on this PC (keyword match). Checked: only the "
                                    "window title, process name and named controls are sent, once.")
        self._update_buttons()

    def _enabled(self) -> bool:
        return bool(self.settings().get("enabled", True))

    def _update_buttons(self):
        busy = self.runner.busy
        enabled = self._enabled()
        self.refresh_button.setEnabled(enabled and not busy)
        self.inspect_button.setEnabled(enabled and not busy and self.window_selector.count() > 0)
        self.guide_button.setEnabled(enabled and not busy and self.observation is not None)
        self.preview_button.setEnabled(self.observation is not None)
        self.cancel_button.setEnabled(busy)

    def _set_status(self, text: str):
        self.status.setText(text)

    # ------------------------------------------------------------- observation
    def refresh_windows(self):
        if not self._enabled():
            return
        self._set_status("Listing windows…")
        self.runner.start(lambda: sg.list_target_windows(self._backend_factory()), (),
                          self._windows_ready, self._observation_failed)
        self._update_buttons()

    def _windows_ready(self, windows):
        self._windows = list(windows)
        self.window_selector.clear()
        for item in self._windows:
            label = item.title + (f"  —  {item.process}" if item.process else "")
            self.window_selector.addItem(label[:120], item.handle)
        if self._windows:
            # A placeholder text leaves the combo unselected; pick the first window.
            self.window_selector.setCurrentIndex(0)
        self._set_status(f"{len(self._windows)} windows found." if self._windows else
                         "No other application windows with titles were found.")
        self._update_buttons()

    def inspect_selected(self):
        if not self._enabled() or self.window_selector.currentIndex() < 0:
            return
        handle = int(self.window_selector.currentData())
        limit = int(self.settings().get("max_controls", sg.DEFAULT_LIMIT))
        self._set_status("Reading accessibility controls…")
        self.runner.start(lambda: sg.observe(handle, self._backend_factory(), limit, self._clock), (),
                          self.show_observation, self._observation_failed)
        self._update_buttons()

    def show_observation(self, observation: sg.Observation):
        self.observation = observation
        self.last_guidance = None
        self.output.clear()
        title = {sg.SUPPORT_RICH: "SUPPORTED", sg.SUPPORT_LIMITED: "LIMITED SUPPORT",
                 sg.SUPPORT_UNSUPPORTED: "UNSUPPORTED"}[observation.support]
        self.support_label.setText(f"{title}  /  {observation.window.title or 'Untitled window'}")
        self.support_reason.setText(observation.support_reason)
        captured = datetime.fromtimestamp(observation.captured_at).strftime("%H:%M:%S")
        meta = [f"Captured {captured}", f"{len(observation.controls)} named controls",
                f"{observation.unnamed} unnamed skipped", observation.source]
        if observation.truncated:
            meta.append("list truncated at limit")
        if observation.redacted:
            meta.append(f"{observation.redacted} credential-like names redacted")
        self.meta_label.setText("  ·  ".join(meta))
        self.controls_tree.clear()
        for control in observation.controls:
            QTreeWidgetItem(self.controls_tree, [("  " * min(control.depth - 1, 6)) + control.name,
                                                 control.control_type, "yes" if control.enabled else "no"])
        self.controls_tree.resizeColumnToContents(1)
        self._set_status("Observation ready.")
        self._update_buttons()

    def _observation_failed(self, message: str):
        self._set_status("")
        self.support_label.setText("OBSERVATION UNAVAILABLE")
        self.support_reason.setText(message)
        self._update_buttons()

    # ---------------------------------------------------------------- guidance
    def shared_request_text(self) -> str:
        if self.observation is None:
            return ""
        return sg.build_request_text(self.goal.toPlainText(), self.observation)

    def preview_shared(self):
        if self.observation is None:
            return
        SharedDataPreview(preview_text(self.goal.toPlainText(), self.observation), self).exec()

    def request_guidance(self):
        goal = self.goal.toPlainText().strip()
        if not goal:
            self._set_status("Describe your goal first.")
            return
        if self.observation is None:
            self._set_status("Inspect a window first.")
            return
        share = bool(self.share_checkbox.isChecked() and self.share_checkbox.isEnabled())
        age = self._clock() - self.observation.captured_at
        self._stale = age > STALE_SECONDS
        self._set_status("Asking Gemini…" if share else "Matching locally…")
        observation = self.observation
        self.runner.start(lambda: self._guide(goal, observation, share), (),
                          self.show_guidance, self._guidance_failed)
        self.share_checkbox.setChecked(False)   # consent is per request
        self._update_buttons()

    def show_guidance(self, result: sg.Guidance):
        self.last_guidance = result
        self.output.setHtml(render_guidance(result, getattr(self, "_stale", False)))
        self._set_status("Guidance ready.")
        self._update_buttons()

    def _guidance_failed(self, message: str):
        self._set_status("")
        self.output.setHtml("<p><b>Guidance failed.</b> " + html.escape(message) +
                            "</p><p>Nothing was changed on your computer. You can retry, or leave "
                            "sharing unchecked for local guidance.</p>")
        self._update_buttons()

    # ----------------------------------------------------------------- control
    def cancel(self):
        self.runner.cancel()
        self._set_status("Cancelled. Any late result will be ignored.")
        # Workers finish on their own; buttons re-enable when they exit.
        self.cancel_button.setEnabled(False)

    def clear(self):
        self.runner.cancel()
        self.observation = None
        self.last_guidance = None
        self.controls_tree.clear(); self.output.clear(); self.meta_label.clear()
        self.support_label.setText("NOTHING OBSERVED YET")
        self.support_reason.setText("Observation cleared from memory.")
        self.share_checkbox.setChecked(False)
        self._set_status("")
        self._update_buttons()

    def shutdown(self):
        self.runner.shutdown()


def preview_text(goal: str, observation: sg.Observation) -> str:
    """Human-readable form of exactly what ``build_request_text`` sends."""
    return ("OBSERVED WINDOW\n" + json.dumps(observation.to_payload(), indent=2, ensure_ascii=False) +
            "\n\nUSER GOAL\n" + " ".join(str(goal).split())[:sg.MAX_GOAL] +
            "\n\nAlso sent: the fixed Screen Guide instruction and response format. "
            "Not sent: screenshots, field contents, unnamed controls, memory or chat history.")


def render_guidance(result: sg.Guidance, stale: bool = False) -> str:
    esc = html.escape
    if result.source == "local":
        source = "Local keyword match on this PC — nothing was sent to the cloud."
    else:
        source = (f"AI guidance from {esc(result.source)}, checked against "
                  f"{result.observed_controls} observed controls.")
    parts = [f"<p><b>Goal:</b> {esc(result.goal)}</p>", f"<p><i>{source}</i></p>"]
    if stale:
        parts.append("<p><b>Warning:</b> this observation is more than two minutes old. "
                     "The window may have changed — inspect again for current controls.</p>")
    if result.unsupported_reason:
        parts.append(f"<p><b>Not supported here:</b> {esc(result.unsupported_reason)}</p>")
    if result.steps:
        parts.append("<ol>")
        for step in result.steps:
            if step.grounded:
                mark = f"✓ observed: “{esc(step.matched_control)}”"
            elif step.control:
                mark = f"⚠ not observed: “{esc(step.control)}” — may be wrong"
            else:
                mark = "• general step (no specific control)"
            parts.append(f"<li>{esc(step.instruction)}<br><small>{mark}</small></li>")
        parts.append("</ol>")
    elif not result.unsupported_reason:
        parts.append("<p>No steps could be grounded in this window.</p>")
    if result.uncertainty:
        parts.append(f"<p><b>Uncertainty:</b> {esc(result.uncertainty)}</p>")
    parts.append("<p><small>Screen Guide only explains. It did not click, type or change anything.</small></p>")
    return "".join(parts)
