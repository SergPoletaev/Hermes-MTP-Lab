# Hermes MTP Lab v0.3.3 — Universal MTP Benchmark

Hermes Desktop plugin for model-independent local MTP OFF/ON benchmarking.

## Features

- Choose any compatible, locally managed GGUF model from Hermes.
- Auto-discover nearby `mmproj` and MTP-head GGUF files; select another folder through Hermes Desktop's native folder picker, without typing file paths.
- Explicit **embedded MTP confirmed** status when GGUF metadata declares MTP layers; separate status for Hermes preset configuration and separately linked MTP heads.
- RU/EN Desktop interface; quick and full text/vision benchmarking with preconfigured workloads, live stages, accepted/drafted token metrics, CSV/JSON/Markdown reports.
- Restore original selected-model presets after each test and support recovery after interruption.
- Install directly from GitHub repository root or from the portable Windows installer.
- No mandatory per-source SHA-256 manifest or manual checksum regeneration.

## Files

- `Hermes_MTP_Lab_v0.3.3_PORTABLE_INSTALL.zip` — installable plugin, Windows installer and documentation.
- `Hermes_MTP_Lab_v0.3.3_FULL_SOURCE.zip` — project sources, tests and CI.

MTP must be supported by the chosen model and llama.cpp runtime. Filename matching proposes candidate files but does not silently associate them; actual speculative-token acceptance and acceleration are measured by the benchmark.
