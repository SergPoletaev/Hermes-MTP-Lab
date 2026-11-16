# Hermes MTP Lab v0.4.0 — Controlled MTP Quality & Performance Benchmark

A complete, model-agnostic local Hermes MTP Lab update built from the clean public repository. No owner-side publishing scripts are included.

## Changes since v0.3.3

- Paired OFF/OFF, ON/ON, OFF/ON comparisons per task and trial, with reversed phase order in the middle of the three-cycle mode. Visible text and `reasoning_content` are tracked and compared separately.
- Task-specific 512–1024-token budgets, `finish_reason` capture, one bounded adaptive retry (maximum 2048) and explicit `incomplete` results instead of silently grading truncated answers.
- Exact JSON arithmetic reference checks, visual label/stack reference checks, and optional seven generated-code unit tests in an **already cached, restricted Docker** environment. Without Docker, generated code is not executed on the host and remains `unverified`.
- Median, MAD, min/max and per-pair parity information; response mismatch does not automatically mean poor output quality.
- Read-only GPU telemetry, requested GPU-layer and KV launch settings, engine version where available, process RSS and model/head identity. No fake actual GPU-layer or per-process VRAM figures.
- Added `quality_eval.py`, `hardware_diag.py`, regression tests, updated Desktop RU/EN interface and four-language README.
- Exact original preset byte restoration remains unchanged. Other Hermes plugins, Chat Share, cloud providers and CUDA settings are untouched.

## Release artifacts

- `Hermes_MTP_Lab_v0.4.0_PORTABLE_INSTALL.zip` — plugin with Windows installer and docs.
- `Hermes_MTP_Lab_v0.4.0_FULL_SOURCE.zip` — complete audited GitHub source with tests and CI.

The benchmark does **not** automatically install Docker, download images or alter local inference engines. Use the Hermes-managed local model and verify the selected model/head pairing independently. Runtime testing requires the user's own Windows/Hermes environment.
