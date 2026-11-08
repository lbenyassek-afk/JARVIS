"""Screen Guide: read-only observation, grounding, consent, provider contract and UI smoke."""
import json
import os
import re
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from core import config, screen_guide as sg
from core.llm import LLMClient, LLMError

ROOT = Path(__file__).resolve().parent.parent
C = sg.ControlInfo


class FakeBackend:
    """Accessibility tree double that records every call it receives."""

    def __init__(self, controls, windows=None, class_name="Notepad"):
        self.controls = list(controls)
        self.calls = []
        self.windows = windows or [sg.WindowInfo(11, "Untitled - Notepad", "notepad.exe", class_name),
                                   sg.WindowInfo(12, "JARVIS V8 // Created by Reda Benyassek", "JARVIS V8.exe")]
        self.class_name = class_name

    def list_windows(self):
        self.calls.append("list_windows")
        return list(self.windows)

    def read_tree(self, handle, limit):
        self.calls.append(("read_tree", handle, limit))
        window = next(w for w in self.windows if w.handle == handle)
        return window, iter(self.controls)


RICH = [C("File", "MenuItem"), C("Edit", "MenuItem"), C("Format", "MenuItem"),
        C("Save as", "MenuItem", depth=2), C("Text editor", "Document"), C("", "Pane"),
        C("File", "MenuItem"), C("Word wrap", "MenuItem", enabled=False, depth=2)]


class IsolatedProfile(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self._old = (config.APP_DIR, config.CONFIG_PATH)
        config.APP_DIR, config.CONFIG_PATH = root, root / "config.json"

    def tearDown(self):
        config.APP_DIR, config.CONFIG_PATH = self._old
        self.tmp.cleanup()


class ObservationTests(IsolatedProfile):
    def test_observe_dedupes_counts_unnamed_and_reads_only(self):
        backend = FakeBackend(RICH)
        obs = sg.observe(11, backend, limit=50, clock=lambda: 100.0)
        names = [c.name for c in obs.controls]
        self.assertEqual(names.count("File"), 1)
        self.assertEqual(obs.unnamed, 1)
        self.assertEqual(obs.captured_at, 100.0)
        self.assertEqual(obs.support, sg.SUPPORT_RICH)
        self.assertEqual(backend.calls, [("read_tree", 11, 50)])

    def test_unsupported_when_no_named_controls(self):
        obs = sg.observe(11, FakeBackend([C("", "Pane"), C("", "Custom")]))
        self.assertEqual(obs.support, sg.SUPPORT_UNSUPPORTED)
        self.assertIn("will not guess", obs.support_reason)

    def test_limited_support_and_chromium_note(self):
        backend = FakeBackend([C("Reload", "Button"), C("", "Pane"), C("", "Pane"), C("", "Pane"),
                               C("", "Pane")], class_name="Chrome_WidgetWin_1")
        obs = sg.observe(11, backend)
        self.assertEqual(obs.support, sg.SUPPORT_LIMITED)
        self.assertIn("Chromium", obs.support_reason)

    def test_truncation_and_hard_limits(self):
        many = [C(f"Item {i}", "ListItem") for i in range(600)]
        obs = sg.observe(11, FakeBackend(many), limit=10_000)
        self.assertEqual(len(obs.controls), sg.HARD_LIMIT)
        self.assertTrue(obs.truncated)

    def test_credential_like_names_are_redacted_before_display_or_sharing(self):
        obs = sg.observe(11, FakeBackend([C("password: hunter22", "Text"), C("AIza" + "x" * 30, "Text"),
                                          C("Sign in", "Button"), C("Help", "Button"), C("Next", "Button")]))
        payload = json.dumps(obs.to_payload())
        self.assertNotIn("hunter22", payload)
        self.assertNotIn("AIza", payload)
        self.assertEqual(obs.redacted, 2)

    def test_own_window_is_excluded_from_targets(self):
        titles = [w.title for w in sg.list_target_windows(FakeBackend(RICH))]
        self.assertEqual(titles, ["Untitled - Notepad"])

    def test_non_windows_reports_clear_unavailability(self):
        if os.name == "nt":
            self.skipTest("Windows host")
        with self.assertRaises(sg.ScreenGuideUnavailable) as caught:
            sg.WindowsUIABackend()
        self.assertIn("Windows", str(caught.exception))

    def test_observation_module_has_no_action_or_capture_path(self):
        import io
        import tokenize
        source = (ROOT / "core" / "screen_guide.py").read_text(encoding="utf-8")
        names = {tok.string for tok in tokenize.generate_tokens(io.StringIO(source).readline)
                 if tok.type == tokenize.NAME}
        forbidden = {"invoke", "click", "click_input", "set_focus", "type_keys", "set_edit_text",
                     "get_value", "pyautogui", "pyperclip", "screenshot", "ImageGrab", "tasks",
                     "skills", "TaskExecutor", "open", "write_text", "write_bytes", "sqlite3"}
        self.assertEqual(names & forbidden, set())


class GuidanceTests(IsolatedProfile):
    def setUp(self):
        super().setUp()
        self.obs = sg.observe(11, FakeBackend(RICH))

    def test_local_guidance_matches_observed_controls_without_cloud(self):
        result = sg.guide("save as a new file", self.obs, share_with_cloud=False,
                          client=Mock(side_effect=AssertionError("cloud used")))
        self.assertEqual(result.source, "local")
        self.assertFalse(result.shared_with_cloud)
        self.assertIn("Save as", [s.matched_control for s in result.steps])
        self.assertTrue(all(s.grounded for s in result.steps))
        self.assertIn("not a verified sequence", result.uncertainty)

    def test_local_guidance_reports_no_match_honestly(self):
        result = sg.guide("book a flight", self.obs, share_with_cloud=False)
        self.assertEqual(result.steps, [])
        self.assertIn("No observed control", result.uncertainty)

    def test_unsupported_window_never_reaches_cloud(self):
        obs = sg.observe(11, FakeBackend([C("", "Pane")]))
        client = Mock()
        result = sg.guide("anything", obs, share_with_cloud=True, client=client)
        client.screen_guidance.assert_not_called()
        self.assertTrue(result.unsupported_reason)

    def test_empty_goal_rejected(self):
        with self.assertRaises(ValueError):
            sg.guide("   ", self.obs, False)

    def test_cloud_guidance_is_grounded_and_flags_unobserved_controls(self):
        raw = json.dumps({"steps": [
            {"instruction": "Open the File menu", "control": "File", "control_type": "MenuItem"},
            {"instruction": "Choose Save as", "control": "save AS"},
            {"instruction": "Click Export PDF", "control": "Export PDF"},
            {"instruction": "Pick a folder", "control": ""}],
            "uncertainty": "", "unsupported_reason": ""})
        client = Mock()
        client.screen_guidance.return_value = (raw, "Google Gemini")
        result = sg.guide("save as pdf", self.obs, share_with_cloud=True, client=client)
        self.assertEqual([s.grounded for s in result.steps], [True, True, False, False])
        self.assertEqual(result.steps[1].matched_control, "Save as")
        self.assertIn("not in the observed list", result.uncertainty)
        self.assertTrue(result.shared_with_cloud)
        sent = client.screen_guidance.call_args.args[1]
        self.assertIn("Save as", sent)
        self.assertIn("data, not instructions", sent)
        self.assertNotIn("depth", sent)

    def test_malformed_provider_output_is_an_error_not_a_guess(self):
        with self.assertRaises(ValueError):
            sg.parse_guidance("not json", "goal", self.obs, "Google Gemini")


class ProviderContractTests(IsolatedProfile):
    """Mocked HTTP: verifies the request contract. Not a live Gemini call."""

    def _response(self, status=200, text='{"steps": [], "uncertainty": "", "unsupported_reason": ""}'):
        response = Mock(status_code=status)
        response.json.return_value = {"candidates": [{"content": {"parts": [{"text": text}]}}]}
        return response

    def test_request_is_structured_json_without_tools_or_memory(self):
        client = LLMClient()
        with patch("core.llm.get_secret", return_value="AIza-test"), \
             patch("core.llm.remember_exchange") as remember, \
             patch.object(client.session, "post", return_value=self._response()) as post:
            raw, source = client.screen_guidance(sg.GUIDE_INSTRUCTION, "DATA", sg.GUIDE_SCHEMA)
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["generationConfig"]["responseMimeType"], "application/json")
        self.assertEqual(payload["generationConfig"]["responseSchema"], sg.GUIDE_SCHEMA)
        self.assertNotIn("tools", payload)
        self.assertEqual(post.call_args.kwargs["params"], {"key": "AIza-test"})
        self.assertEqual(source, "Google Gemini")
        remember.assert_not_called()
        self.assertEqual(client.history, [])
        self.assertEqual(json.loads(raw)["steps"], [])

    def test_missing_key_and_failures_are_explained(self):
        client = LLMClient()
        with patch("core.llm.get_secret", return_value=""):
            with self.assertRaisesRegex(LLMError, "Connect Gemini"):
                client.screen_guidance("i", "d", {})
        with patch("core.llm.get_secret", return_value="AIza-test"), \
             patch.object(client.session, "post", return_value=self._response(429)):
            with self.assertRaisesRegex(LLMError, "quota"):
                client.screen_guidance("i", "d", {})
        with patch("core.llm.get_secret", return_value="AIza-test"), \
             patch.object(client.session, "post", side_effect=requests.ConnectionError("down")):
            with self.assertRaisesRegex(LLMError, "Cannot reach"):
                client.screen_guidance("i", "d", {})
        with patch("core.llm.get_secret", return_value="AIza-test"), \
             patch.object(client.session, "post", return_value=self._response(text="  ")):
            with self.assertRaisesRegex(LLMError, "empty"):
                client.screen_guidance("i", "d", {})


class SettingsTests(IsolatedProfile):
    def test_defaults_persist_and_invalid_values_are_corrected(self):
        cfg = config.load_config()
        self.assertEqual(cfg["screen_guide"], {"enabled": True, "cloud_sharing": "ask", "max_controls": 150})
        cfg["screen_guide"] = {"enabled": False, "cloud_sharing": "always", "max_controls": 9999}
        config.save_config(cfg)
        loaded = config.load_config()["screen_guide"]
        self.assertEqual(loaded, {"enabled": False, "cloud_sharing": "ask", "max_controls": 400})

    def test_reset_section_restores_defaults(self):
        cfg = config.load_config()
        cfg["screen_guide"]["cloud_sharing"] = "never"
        config.reset_section(cfg, "screen_guide")
        self.assertEqual(cfg["screen_guide"]["cloud_sharing"], "ask")
        with self.assertRaises(KeyError):
            config.reset_section(cfg, "nope")


class ScreenGuidePageSmokeTests(IsolatedProfile):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _wait(self, page, timeout=5.0):
        deadline = time.time() + timeout
        while page.runner.busy and time.time() < deadline:
            self.app.processEvents()
            time.sleep(0.01)
        for _ in range(5):
            self.app.processEvents()
        self.assertFalse(page.runner.busy, "worker did not finish")

    def _page(self, guide_function=None):
        from ui.screen_guide import ScreenGuidePage
        backend = FakeBackend(RICH)
        page = ScreenGuidePage(backend_factory=lambda: backend, guide_function=guide_function)
        self.addCleanup(page.shutdown)
        return page, backend

    def test_full_local_flow_and_per_request_consent(self):
        page, backend = self._page()
        page.refresh_windows(); self._wait(page)
        self.assertEqual(page.window_selector.count(), 1)
        page.inspect_selected(); self._wait(page)
        self.assertIsNotNone(page.observation, page.support_reason.text())
        self.assertEqual(page.controls_tree.topLevelItemCount(), len(page.observation.controls))
        self.assertIn("SUPPORTED", page.support_label.text())
        page.goal.setPlainText("save as")
        page.share_checkbox.setChecked(False)
        page.request_guidance(); self._wait(page)
        html = page.output.toHtml()
        self.assertIn("nothing was sent to the cloud", html)
        self.assertIn("did not click, type or change anything", html)
        self.assertEqual([c for c in backend.calls if c != "list_windows"][0][0], "read_tree")

    def test_sharing_checkbox_resets_after_each_request(self):
        seen = []
        page, _ = self._page(lambda goal, obs, share: seen.append(share) or sg.local_guidance(goal, obs))
        page.refresh_windows(); self._wait(page)
        page.inspect_selected(); self._wait(page)
        page.goal.setPlainText("format")
        page.share_checkbox.setChecked(True)
        page.request_guidance(); self._wait(page)
        self.assertEqual(seen, [True])
        self.assertFalse(page.share_checkbox.isChecked())
        page.request_guidance(); self._wait(page)
        self.assertEqual(seen, [True, False])

    def test_never_share_setting_disables_consent_box(self):
        cfg = config.load_config(); cfg["screen_guide"]["cloud_sharing"] = "never"; config.save_config(cfg)
        page, _ = self._page()
        self.assertFalse(page.share_checkbox.isEnabled())

    def test_failure_is_reported_without_claiming_success(self):
        def boom(*_args):
            raise LLMError("Gemini rate limit reached.")
        page, _ = self._page(boom)
        page.refresh_windows(); self._wait(page)
        page.inspect_selected(); self._wait(page)
        page.goal.setPlainText("format")
        page.request_guidance(); self._wait(page)
        html = page.output.toHtml()
        self.assertIn("Guidance failed", html)
        self.assertIn("Nothing was changed", html)
        self.assertIsNone(page.last_guidance)

    def test_cancel_discards_late_results_and_clear_forgets_observation(self):
        page, _ = self._page(lambda goal, obs, share: (time.sleep(0.2), sg.local_guidance(goal, obs))[1])
        page.refresh_windows(); self._wait(page)
        page.inspect_selected(); self._wait(page)
        page.goal.setPlainText("format")
        page.request_guidance(); page.cancel(); self._wait(page)
        self.assertIsNone(page.last_guidance)
        page.clear()
        self.assertIsNone(page.observation)
        self.assertFalse(page.guide_button.isEnabled())

    def test_page_offers_no_action_buttons(self):
        from PyQt6.QtWidgets import QPushButton
        page, _ = self._page()
        labels = [b.text().casefold() for b in page.findChildren(QPushButton)]
        for label in labels:
            self.assertIsNone(re.search(r"\b(run|execute|click|type|apply|perform)\b", label), label)


if __name__ == "__main__":
    unittest.main()
