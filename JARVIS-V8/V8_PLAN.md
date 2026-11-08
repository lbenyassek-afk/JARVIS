# JARVIS V8 — plan and status

Last updated: 8 November 2026. Status is based on code and tests in this repository,
not on intentions.

## Where V8 came from

| Source | What happened |
|---|---|
| `lbenyassek-afk/JARVIS-V6` @ `68a552d` | Contains the tested V7 code ("Center V7 around five product pillars"). Imported verbatim as the first commit here. |
| `lbenyassek-afk/JARVIS-V7` | **Not reachable** from the build session (no GitHub App access). Not inspected. |
| `lbenyassek-afk/JARVIS-V8` | **Not reachable** from the build session. V8 lives in `lbenyassek-afk/JARVIS` instead, by owner decision. |

V7 baseline before any change (Linux, offscreen Qt): **68/68 tests, 6/6 benchmarks, `pip check` clean.**

## Status by priority

Legend: **Done** = implemented, wired into the UI and tested. **Partial** = some parts
work, gaps listed. **Inherited** = V7 behaviour kept unchanged. **Not started** = nothing
new yet.

| # | Priority | Status | Notes |
|---|---|---|---|
| 0 | Independent V8 identity | **Done** | Profile, Credential Manager, exe, installer AppId, install dir, shortcuts, backups, update repo, companion port. See `core/identity.py`. |
| 1 | Screen Guide | **Done (accessibility tier)** | Read-only UIA inspection, support assessment, grounded local or Gemini guidance, per-request consent. Screenshot/OCR/vision **not implemented**. |
| 2 | Assistant Studio | Not started | V7 has one tone/length setting plus a single custom-instructions box and manager prompt. |
| 3 | Files, data, deliverables | Not started | `pypdf`/`python-docx` are not dependencies yet. |
| 4 | Intelligence and research | Inherited / Partial | Gemini multi-turn, Google Search grounding with source list, encrypted memory with view/edit/delete/pin dialog, Personal/School/Business contexts. Inference vs. sourced separation is not enforced. |
| 5 | Provider choice | Not started | Gemini only. Catalogue lists OpenAI/Anthropic as not installed; no xAI entry. |
| 6 | Daily use | Inherited / Partial | Today/focus dialog and workspaces exist. No durable scheduler, reminders or Windows notifications. |
| 7 | Voice and reliability | Inherited | V7 adaptive capture, Edge neural voices, background threads. Not re-verified on Windows hardware. |
| 8 | Reviewed desktop actions | Inherited | 18 allowlisted actions, backend permissions, preflight, emergency stop, verification. Unchanged. |

## What V8 changed

### Independent identity

| Item | V6/V7 | V8 |
|---|---|---|
| Profile | `%APPDATA%\JARVIS-V6` | `%APPDATA%\JARVIS-V8` |
| Credential Manager service | `JARVIS-V6` | `JARVIS-V8` (so V8 makes its own encryption key) |
| Executable | `JARVIS V6.exe` | `JARVIS V8.exe` |
| Install dir | `…\Programs\JARVIS V6` | `…\Programs\JARVIS V8` |
| Installer | AppId `B6403D91…`, `JARVIS-V6-Setup.exe` | AppId `8E5A1C47…8008`, `JARVIS-V8-Setup.exe` |
| Backups | `JARVIS6-BACKUP`, `.j6backup` | `JARVIS8-BACKUP`, `.j8backup` |
| Updates | `lbenyassek-afk/JARVIS-V6` | `lbenyassek-afk/JARVIS` |
| Companion port | 8765 | 8768 |

Migration: **none, by design.** V8 never opens V6/V7 files or credentials. A future
import tool must preview what it copies, decrypt with the old key, and re-encrypt
with the V8 key only after the user confirms.

### Screen Guide

How to use it: **GUIDE** in the left rail → describe the goal → **REFRESH WINDOWS** →
pick a window → **INSPECT WINDOW** → optionally tick the sharing box → **GET GUIDANCE**.

| Property | How it is guaranteed |
|---|---|
| Read-only | The backend reads only element name, type, enabled, automation id and class. A token-level test fails if the module references click/invoke/focus/type/value/screenshot/file-write APIs or the action executor. |
| Observation separate from action | The page has no action buttons (tested). Desktop Control remains the only path to actions. |
| Grounded guidance | Each AI step's control name is matched against the observation and shown as **✓ observed** or **⚠ not observed — may be wrong**. |
| Honest support levels | *Supported*, *Limited* (few named controls; Chromium/Electron and terminal notes) and *Unsupported* (no named controls: no guessing, nothing sent to the cloud). |
| Explicit cloud consent | Unchecked by default and reset after every request. **PREVIEW SHARED DATA** shows the exact payload. Settings can turn sharing off. |
| Privacy | Observations stay in memory and are cleared by **CLEAR**. Credential-like names are redacted. Field values are never read. Nothing goes into chat history or memory. |
| No invented sight | Footer and prompt both say only accessibility text is seen. Vision is listed as *future* in Capabilities. |
| Responsiveness | All UIA and network work runs on worker threads. Cancel discards late results. Shutdown waits for workers. |

Settings → **Screen Guide**: enable/disable, cloud sharing (*Ask every request* /
*Never share*), control limit (50–400), **RESET SCREEN GUIDE SETTINGS**.

Not implemented in this tier:
- Screenshot, OCR or vision analysis.
- Live re-observation (each inspection is a single snapshot; guidance warns when it is over two minutes old).
- Hand-off from a guidance step to a reviewed Desktop Control plan.
- Providers other than Gemini for AI guidance.

## Validation evidence (this revision)

| Check | Result | Where |
|---|---|---|
| Unit + integration tests | **101/101 pass** (68 inherited + 33 new) | Linux, Python 3.13, PyQt6 6.12, `QT_QPA_PLATFORM=offscreen` |
| Reliability benchmark | **8/8 pass**, incl. Screen Guide bounded observation (~2 ms for a 6,000-node tree capped at 400) and grounding | `python benchmark.py` |
| Dependency check | `pip check`: no broken requirements | same host |
| UI smoke | Main window builds, GUIDE page opens and reports UIA unavailability on Linux. Offscreen screenshot reviewed. | `tests/test_v8_ui_smoke.py` |
| Gemini Screen Guide request | **Mocked HTTP only**: payload shape, JSON schema, no tools, no memory writes, 429/network/empty-response messages. **No live API call made.** | `tests/test_screen_guide.py` |
| Real Windows UIA | **Not run.** No Windows host was available. The UIA backend is exercised only through a fake tree. | — |
| Windows CI (first push) | Run #1 failed: 7 inherited tests could not delete temp profiles because SQLite connections were never closed (`with sqlite3.connect()` does not close). Fixed in `core/db.py`; unclosed-connection warnings went from 35 to 0; regression test `tests/test_storage_handles.py`. | GitHub Actions |
| Windows CI (after fix) | Run #3 **passed** on `windows-latest`: full test suite, benchmark, `pip check`, PyInstaller build, Inno Setup installer, prerelease `v8.0.0-alpha.1` published with `JARVIS-V8-Setup.exe`. | GitHub Actions |
| Install/uninstall on a real PC | **Not run.** CI builds the installer but does not install it, run Screen Guide against real apps, or test V7+V8 side by side. | — |

Known platform limits:
- `pyautogui` needs `--no-build-isolation` on some Linux pip setups. Qt needs `libegl1`, `libgl1`, `libxkbcommon0`, `libfontconfig1` and `libdbus-1-3` on headless Linux.
- UIA exposure varies by app: Win32/WinUI apps are usually rich; browsers/Electron are partial; games, video and remote desktop are usually unsupported.
- Elevated (admin) windows cannot be read by a non-elevated JARVIS.

## Next increments (in order)

1. **Capability comparison:** ChatGPT, Claude, Gemini and Grok from official sources, separating model, consumer app, API and local-tool capabilities. Not done this session.
2. **Assistant Studio:** built-in specialists plus named custom profiles (tone, language, detail). Protected app rules stay separate from user instructions. Encrypted save/load/edit/delete.
3. **Files and deliverables:** text/Markdown/code/CSV/PDF/DOCX input with size limits, per-file cloud consent, local CSV analysis, and encrypted drafts with export.
4. **Provider adapters:** OpenAI, Anthropic and xAI behind the existing provider catalogue, with Credential Manager keys, configurable models and output limits, no silent fallback, and unsupported tools marked.
5. **Daily use:** durable scheduler, reminders, briefings, Windows notifications and missed-run handling.
6. **Windows acceptance:** run the suite and Screen Guide against Notepad, Explorer, Settings, Edge and VS Code on Windows 11; record support levels.
