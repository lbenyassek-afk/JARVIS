"""Single source of truth for the JARVIS V8 application identity.

V8 must coexist with V6/V7 on the same Windows account without sharing or
overwriting private data. Every name that touches the operating system
(profile folder, Credential Manager service, executable, installer AppId,
shortcuts, update repository, companion port) is defined here and nowhere else.
"""
from __future__ import annotations

APP_NAME = "JARVIS V8"
APP_SLUG = "JARVIS-V8"
VERSION = "8.0.0"
VERSION_TUPLE = (8, 0, 0, 0)
CREATOR = "Reda Benyassek"
DESCRIPTION = "JARVIS V8 Personal Intelligence"

# Windows identities. Never reuse a value from an earlier generation.
PROFILE_DIR_NAME = "JARVIS-V8"            # %APPDATA%\JARVIS-V8
CREDENTIAL_SERVICE = "JARVIS-V8"          # Windows Credential Manager target
EXE_NAME = "JARVIS V8.exe"
INSTALL_DIR_NAME = "JARVIS V8"            # %LOCALAPPDATA%\Programs\JARVIS V8
SHORTCUT_NAME = "JARVIS V8.lnk"
BUILD_DIR_NAME = "JARVIS-V8-Build"
INSTALLER_APP_ID = "{8E5A1C47-3D2B-4F60-9A8E-0C8D2F7B8008}"
INSTALLER_OUTPUT = "JARVIS-V8-Setup"
BACKUP_SUFFIX = ".j8backup"
USER_AGENT = "JARVIS-V8/8.0"

UPDATE_REPOSITORY = "lbenyassek-afk/JARVIS"
COMPANION_PORT = 8768

# Identities used by earlier generations. Kept only so tests and the explicit
# migration preview can prove V8 never collides with them. The "V7" entry is
# reserved defensively: the separate JARVIS-V7 repository could not be
# inspected, so V8 avoids the names it would most plausibly use.
PREVIOUS_GENERATIONS = {
    "V6/V7": {
        "profile_dir": "JARVIS-V6",
        "credential_service": "JARVIS-V6",
        "exe": "JARVIS V6.exe",
        "installer_app_id": "{B6403D91-890E-46B6-A210-6F0A0B6E6001}",
        "companion_port": 8765,
        "update_repository": "lbenyassek-afk/JARVIS-V6",
    },
    "V7": {
        "profile_dir": "JARVIS-V7",
        "credential_service": "JARVIS-V7",
        "exe": "JARVIS V7.exe",
        "companion_port": 8766,
        "update_repository": "lbenyassek-afk/JARVIS-V7",
    },
}
