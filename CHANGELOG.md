# Changelog

All notable changes to Hermes MTP Lab are documented here. Version numbers identify the **plugin**, not Hermes Desktop or llama.cpp.

## [0.3.0] — 2026-11-15 (experimental, model-agnostic)

- Remove BUILD-MANIFEST per-file SHA-256 requirements and release SHA256SUMS generation; CI now verifies source structure and tests and compares release ZIP entries directly to current sources. No manual checksum updates after edits.

- Remove all hardcoded Gemma model IDs, quantization names and MTP-head filenames from the runtime.
- Discover selectable models from native Hermes managed presets, with explicit separate MTP-head and optional mmproj links per model.
- Support text-only workloads without vision projector; use image tasks only when a projector is present.
- Support embedded MTP when the native preset or readable GGUF metadata advertises it; reject unconfirmed MTP combinations.
- Run controlled OFF/ON tests by temporarily editing **only the selected model preset**, restore its original bytes and retain a crash-recovery backup.
- Add RU/EN model selector, explicit companion-link fields and supported/unsupported indicators.
- Generic support is conditional on actual llama.cpp model/head compatibility; this release has not been validated on every architecture.

## [0.2.3] — 2026-11-15 (experimental)

- Consolidate project documentation into **one four-language README**: Russian, English, Simplified Chinese and Hindi.
- Add an actual Hermes MTP Lab dashboard screenshot, clearly identified as the v0.2.1 tested UI.
- Add a persistent **Auto (Hermes) / Russian / English** language switch on the MTP Lab page and settings page, using the same plugin SDK i18n mechanism as ChatVault.
- Localize controls, benchmark stages, timers, warnings, progress, status, and result table labels; keep original low-level engine errors available for diagnosis.
- Include the documentation image in both source and portable archives, and add checks for translations, language order and screenshot packaging.
- Release-source verification now checks SHA-256 for every distributed repository file (except its own manifest); CI installs the FastAPI unit-test dependency explicitly.
- MTP algorithm and runtime ownership safeguards unchanged. Integration testing of v0.2.3 in Hermes Desktop: **pending**.

## [0.2.2] — 2026-11-15 (experimental)

- Add visible stages for model loading, warm-up, inference and configuration restore.
- Add run and stage timers and progress indicators that distinguish measured progress from unspecified waits.
- Fix the false "previous test interrupted" banner during a healthy running benchmark.
- Rename workload labels to avoid suggesting nonexistent Vision chat mode; document real Hermes modes Auto, Native, Text.
- Keep existing auto OFF/ON benchmark logic and safety/restore handling unchanged.
- Correct stale version text in Windows `.cmd` installer; add repository metadata, CI and release packaging.
- Real-world Hermes Desktop test of v0.2.2: **pending**.

## [0.2.1] — 2026-11-15

- Switch to official Hermes `plugins enable` command for Python backend consent, avoiding fragile YAML text edits.
- MTP Lab page is available in Hermes Desktop through the plugin's sidebar route.
- Real-world A/B performance measurements obtained on a model-specific Windows installation; they do not guarantee other hardware speeds.

## [0.2.0] — 2026-11-15

- Register Desktop route and sidebar navigation.
- Add backend presence and ownership checks.

## [0.1.0] — 2026-11-15

- Initial local MTP ON/OFF and automatic benchmark prototype.
