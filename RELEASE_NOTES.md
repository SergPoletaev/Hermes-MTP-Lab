# Hermes MTP Lab v0.5.1 — Native GGUF file picker and persistent browsing

This is a **complete** root-level Hermes plugin repository, not a patch. Desktop, Python backend, Windows installer, CI and 4-language README share version **0.5.1**.

## Fixes and behavior

- **Native file chooser.** MTP-head and mmproj now open a Windows file picker showing `.gguf` files, remember the last directory and fill the selected path; no folder-grant dialogs.
- **Benchmark fixes retained from v0.5.0.** The v0.4.0 benchmark repeatedly exhausted 2,048 tokens of unbounded reasoning and returned 24 incomplete outputs. The current version uses an early no-thinking probe, short prompts, fixed 768–1,536-token budgets, and records incomplete responses without running a second full generation.
- **Reasoning selector:** default `off` sends `chat_template_kwargs.enable_thinking=false` and `reasoning_effort=none` to llama.cpp. `native` keeps default model behavior for throughput tests. Actual reasoning is still reported since model templates may ignore the request.
- **Paired comparability:** no more mislabeling missing `batch`, `ubatch`, or `gpu_layers` launch flags as an observed mismatch. `comparability.json` distinguishes unknown settings from unequal known settings and unequal paired token caps.
- **Self-contained reports:** add `protocol.json` (task prompts, caps, request flags), `comparability.json`, and exact reference image `assets/benchmark_scene.jpg` when vision tasks run. Existing report files remain.
- Fixed OFF/OFF, ON/ON and OFF/ON repeats, safe restore/recovery, model/head/mmproj selection, 4-language documentation, and no public publishing scripts.

## Packages

- `Hermes_MTP_Lab_v0.5.1_PORTABLE_INSTALL.zip` — installable plugin and Windows installer.
- `Hermes_MTP_Lab_v0.5.1_FULL_SOURCE.zip` — public GitHub root with tests, CI and release build tools.

## Verification scope

54 offline Python tests, Desktop registration and file-dialog interaction tests, source allowlist verification, both ZIP archives and their byte-for-byte contents. Real llama.cpp Gemma 4 MTP execution on the user's Windows RTX 4060 Ti cannot be performed in this test environment. The project never automatically replaces llama.cpp or Python/CUDA DLLs. Running the fixed protocol with the user's model is required to validate real runtime compatibility.
