# JARVIS V8

**Created by Reda Benyassek**  
Copyright © 2026 Reda Benyassek.

JARVIS V8 is a native PyQt6 Windows personal assistant built on the tested V7
foundation. It has its own application profile, encrypted memory, credentials,
executable, installer, update channel and companion port, so it installs and
runs beside V6/V7 without reading or overwriting their data.

## V8 identity

| Item | V8 value |
|---|---|
| Application / version | JARVIS V8 8.0.0 |
| Executable | `JARVIS V8.exe` |
| Install directory | `%LOCALAPPDATA%\Programs\JARVIS V8` |
| Shortcuts | Desktop, Start menu and Startup `JARVIS V8.lnk` |
| Installer | `JARVIS-V8-Setup.exe`, AppId `{8E5A1C47-3D2B-4F60-9A8E-0C8D2F7B8008}` |
| Profile / config | `%APPDATA%\JARVIS-V8\config.json` |
| Credential Manager | service `JARVIS-V8` |
| Encryption key | new key in `JARVIS-V8` Credential Manager (fallback `%APPDATA%\JARVIS-V8\.memory.key`) |
| Backups | `*.j8backup`, header `JARVIS8-BACKUP` |
| Updates | `lbenyassek-afk/JARVIS` releases |
| Companion port | `127.0.0.1:8768` (V6/V7 use 8765) |

All values live in `core/identity.py`; `tests/test_v8_identity.py` fails if
the installer, version resource, workflow or code drift from it or collide
with an earlier generation.

**Migration:** V8 never reads V6/V7 profiles automatically. No import tool
exists yet. A future import must be explicit, show what it will copy, and
re-encrypt with the V8 key.

## Inherited V7 foundation

### V6/V7 target

- Minimal cinematic HUD with responsive natural voice.
- Gemini intelligence with a useful local core and provider-ready architecture.
- Organized, editable memory for identity, preferences, relationships, projects,
  businesses, goals, decisions, routines and notes.
- Plan-then-execute desktop control with allowlisted actions, permission tiers,
  emergency stop and sensitive-action audit.
- Verified research and unified School, Personal and Business workspaces.
- Secure plugin manifests and an authenticated companion transport for iPhone.

### V7 foundation features

- Original V6 satin-titanium J-reactor icon with arctic-blue energy, transparent
  edges and ten Windows sizes from 16 to 256 pixels.
- Five persistent presence designs: Energy Orb, Reactor Core, HUD Face, Hybrid
  and Minimal Assistant, selectable directly from the main window or Settings.
- Six coordinated minimal colour themes plus an optional custom accent. Theme
  changes recolour the HUD, panels, controls, waveform and presence visual together.
- Voice customization for multilingual neural voices, preview, speed, pitch,
  volume, capture engine, activation behaviour and microphone selection.
- Four one-click voice styles—Cinematic, Fast Operator, Deep British and Natural
  British—plus fully custom voice, speed, pitch and volume controls.
- Multilingual intelligence for English, French, Arabic, Spanish, German, Italian
  and Portuguese, with automatic reply-language detection, language-specific free
  speech recognition and matching Edge neural voices.
- Fast, Adaptive and Thorough intelligence profiles with configurable tone and
  response length, multilingual research routing and resilient Gemini requests.
- Unicode-aware encrypted memory and conversation retrieval, including older
  relevant exchanges in any supported language without copying the full history.
- Desktop Mission Control for goal-based allowlisted plans, mouse-position capture,
  step reordering, live progress, emergency cancellation and encrypted action history.
- Windows app-aware control using accessibility names for windows, buttons, menu items
  and text fields, with an active-app scanner and coordinate fallback.
- Encrypted reusable Desktop Routines that remain locally validated when loaded again.
- Fast typed or spoken desktop commands for approved apps, window switching, desktop,
  volume, media, scrolling and screenshots, routed through the same permission system.
- `/desktop control` starts a session-only natural command mode. Multi-step spoken or
  typed goals are compiled by Gemini into structured steps and validated against the
  local action/value allowlist before approval or execution. `/desktop off` exits.
- Guided Gemini registration with live key-format feedback, stored-key retesting,
  explicit test/save states and Windows Credential Manager storage.
- Five-stage Gemini registration diagnostics for key format, Google connectivity,
  compatible model discovery, live generation and Windows Credential Manager storage.
  Successful setup stays visible until the user presses Done and explains why the
  key field was cleared.
- Structured Gemini voice understanding with transcript confidence, language metadata,
  background-audio rejection, adaptive end-of-speech timing and model fallback when a
  specific Flash model reaches its quota.
- Smarter answer continuity and self-checking for names, dates, quantities, assumptions
  and next actions, plus transparent recovery from temporary Gemini server failures.
- A full Capabilities screen reports ready, setup-required, disabled and future
  components without presenting unfinished integrations as working features.
- Eighteen bounded desktop actions including approved applications, Unicode text,
  named Windows controls, window focus and layout, clipboard, fixed shortcuts,
  pointer actions, scrolling, media, screenshots and waits. Sensitive actions
  still require explicit approval.
- Local offline core for time, date, status, local memory search and capability help.
- Structured execution-plan validation against the desktop action allowlist.
- Complete mission preflight before the first side effect, dependency-aware
  execution graphs, encrypted crash checkpoints and blocked-step propagation.
- Postcondition verification for supported desktop actions, with bounded retries
  only where repeating the operation is safe.
- Reviewed desktop and no-execution simulation profiles selectable in Settings.
- Typed plugin operation and adapter contracts with exact domain allowlists and
  optional SHA-256 payload integrity checks.
- Hybrid encrypted memory retrieval that combines exact multilingual relevance
  with a lightweight local related-memory signal.
- A repeatable offline reliability benchmark available from Performance Monitor
  or with `python benchmark.py`.
- V6 memory metadata for importance, pinning, source and update history.
- Authenticated local companion command inbox. It queues commands for the main
  permission system and never executes desktop actions by itself.

Alpha builds are development previews. A stable release will ship only after Windows
hardware, clean-install, migration, voice, Gemini, recovery, performance and
desktop-control acceptance tests pass.

## Development

Run `python -m unittest discover -s tests -v`, `python benchmark.py`, then
`python main.py`.
Windows packaging is handled by `.github/workflows/build-jarvis-v8.yml`.

See [V7_PRODUCT_MAP.md](V7_PRODUCT_MAP.md) for the visual architecture, current
evidence, release gates and the recommended V7 sequence.
