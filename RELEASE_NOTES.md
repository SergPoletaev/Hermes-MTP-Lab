# Hermes MTP Lab v0.5.2 — Robustness hardening

This is a **complete** root-level Hermes plugin repository, not a patch. Desktop, Python backend, Windows installer, CI and 4-language README share version **0.5.2**. All v0.5.1 behavior (native GGUF picker, remembered directories, paired OFF/ON protocol) is retained.

## Fixes and behavior in 0.5.2

- **Atomic backups everywhere.** Preset phase backups, companion-config backups and manual-toggle backups are written through the same atomic (temp-file + `os.replace`) path as presets themselves. A crash mid-write can no longer produce a truncated backup that would fail SHA-256 verification and block the recovery flow.
- **Adaptive per-request timeouts.** The HTTP timeout for each benchmark request is derived from the warm-up probe's measured per-token latency, bounded to **480–7200 seconds**. Previously a fixed `max(480, 0.9·max_tokens)` ceiling could abort an entire multi-hour CPU-offloaded run mid-request. The policy is recorded in `protocol.json` as `request_timeout_policy`.
- **BOM-preserving phase presets.** If the native Hermes preset starts with a UTF-8 BOM, temporary OFF/ON phase presets keep it byte-for-byte.
- **Missing reference image handled honestly.** A vision run now fails fast with a clear reinstall instruction before any request is sent; report writing degrades gracefully with an explicit warning in `summary.md` and `protocol.json` instead of destroying an otherwise complete report.
- **Status-poll discovery caching.** `mmproj` and MTP-head candidate scans are cached per folder fingerprint (directory mtime + per-GGUF mtime/size), so the 1.5-second status poll no longer re-stats every GGUF on slow or network drives. The cache invalidates automatically when folder contents change.
- **Backup housekeeping.** Only the newest five automatic backups per pattern are kept (preset, companion-config, manual-toggle); older ones are pruned after successful operations. Pruned counts are noted in the run notes.
- **Sandbox payload fix.** The Docker code-sandbox harness reads the entire stdin payload with an explicit 100 000-character cap instead of silently truncating at 25 000 characters, so long JSON-escaped sources no longer fail with a misleading `runtime_error`.
- **Internal cleanup.** Removed the duplicated `reasoning_modes` status field and inline `__import__` calls in the plugin API; new regression tests cover every fix.

## Retained from v0.5.0/v0.5.1

- Fixed paired protocol: two OFF and two ON requests per task per cycle, phase order alternated between cycles, identical fixed 768–1536-token budgets, no adaptive retries on truncation, `incomplete` marking.
- Reasoning selector: default `off` sends `chat_template_kwargs.enable_thinking=false` plus `reasoning_effort=none`; `native` keeps model defaults; actual `reasoning_content` is always recorded separately.
- Paired comparability: missing `batch`/`ubatch`/`gpu_layers` launch flags are reported as unknown, never as an observed mismatch; unequal paired token caps are counted separately.
- Self-contained reports: `protocol.json`, `comparability.json`, `answers.jsonl`, `hardware.json`, `task_summary.json`, `comparisons.json`, `results.csv/json`, `summary.md` and the exact reference image for vision runs.
- Native GGUF file pickers with remembered last directory; byte-for-byte preset restoration with SHA-256-verified recovery markers.

## Packages

- `Hermes_MTP_Lab_v0.5.2_PORTABLE_INSTALL.zip` — installable plugin and Windows installer.
- `Hermes_MTP_Lab_v0.5.2_FULL_SOURCE.zip` — public GitHub root with tests, CI and release build tools.

## Verification scope

Offline Python test suite (including new v0.5.2 regression tests), Desktop registration and file-dialog interaction tests, source allowlist verification, both ZIP archives and their byte-for-byte contents. Real llama.cpp MTP execution on the user's hardware cannot be performed in this test environment. The project never automatically replaces llama.cpp or Python/CUDA DLLs. Running the fixed protocol with the user's model is required to validate real runtime compatibility.
