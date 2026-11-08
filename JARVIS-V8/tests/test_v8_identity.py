"""V8 must coexist with V6/V7: no shared profile, credentials, installer or port."""
import re
import unittest
from pathlib import Path

from core import backup, companion, config, identity, secrets, updates

ROOT = Path(__file__).resolve().parent.parent


class V8IdentityTests(unittest.TestCase):
    def test_runtime_identity_is_v8(self):
        self.assertEqual(config.APP_DIR.name, "JARVIS-V8")
        self.assertEqual(secrets.SERVICE, "JARVIS-V8")
        self.assertEqual(updates.CURRENT_VERSION, "8.0.0")
        self.assertEqual(config.DEFAULTS["updates"]["repository"], identity.UPDATE_REPOSITORY)
        self.assertEqual(config.DEFAULTS["companion"]["port"], identity.COMPANION_PORT)
        self.assertTrue(backup.MAGIC.startswith(b"JARVIS8"))

    def test_no_collision_with_previous_generations(self):
        mine = {
            "profile_dir": identity.PROFILE_DIR_NAME,
            "credential_service": identity.CREDENTIAL_SERVICE,
            "exe": identity.EXE_NAME,
            "installer_app_id": identity.INSTALLER_APP_ID,
            "companion_port": identity.COMPANION_PORT,
            "update_repository": identity.UPDATE_REPOSITORY,
        }
        for generation, theirs in identity.PREVIOUS_GENERATIONS.items():
            for key, value in theirs.items():
                self.assertNotEqual(mine[key], value, f"{key} collides with {generation}")

    def test_companion_defaults_to_v8_port(self):
        server = companion.CompanionServer(token="t")
        self.assertEqual(server.port, identity.COMPANION_PORT)

    def test_installer_matches_identity(self):
        iss = (ROOT / "installer.iss").read_text(encoding="utf-8")
        self.assertIn(f'#define MyAppName "{identity.APP_NAME}"', iss)
        self.assertIn(f'#define MyAppVersion "{identity.VERSION}"', iss)
        self.assertIn(f'#define MyAppExeName "{identity.EXE_NAME}"', iss)
        self.assertIn("AppId={" + identity.INSTALLER_APP_ID + "\n", iss)
        self.assertIn(f"OutputBaseFilename={identity.INSTALLER_OUTPUT}", iss)
        self.assertNotIn("V6", iss)

    def test_version_resource_matches_identity(self):
        text = (ROOT / "version_info.txt").read_text(encoding="utf-8")
        self.assertIn(f"filevers={identity.VERSION_TUPLE}", text)
        self.assertIn(f"'OriginalFilename', '{identity.EXE_NAME}'", text)
        self.assertNotIn("V6", text)

    def test_workflow_builds_v8_artifacts(self):
        workflow = (ROOT.parent / ".github" / "workflows" / "build-jarvis-v8.yml")
        if not workflow.exists():
            self.skipTest("workflow is outside this checkout")
        text = workflow.read_text(encoding="utf-8")
        self.assertIn(identity.INSTALLER_OUTPUT + ".exe", text)
        self.assertNotRegex(text, re.compile(r"JARVIS[- ]V6"))

    def test_no_hardcoded_previous_identity_in_application_code(self):
        offenders = []
        for path in list((ROOT / "core").glob("*.py")) + list((ROOT / "ui").glob("*.py")) + \
                [ROOT / "main.py", ROOT / "install.py"]:
            if path.name == "identity.py":
                continue
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if re.search(r"JARVIS[- ]V6|j6backup|\b8765\b", line):
                    offenders.append(f"{path.name}:{number}")
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
