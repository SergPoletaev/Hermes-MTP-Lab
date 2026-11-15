# Hermes MTP Lab v0.3.2 — Companion Discovery Pre-release
**Packaging patch:** Hermes can now discover this hybrid plugin from the normal Git repository URL (`https://github.com/SergPoletaev/Hermes-MTP-Lab.git`) without a `#subdirectory` fragment. Its `plugin.yaml`, `__init__.py`, `desktop/plugin.js`, and `dashboard/manifest.json` are in the repository root. The full source ZIP and the portable installer have been rebuilt accordingly.

**Existing v0.3.0 release remains unchanged.** This update does not alter MTP benchmarking algorithms or require manual source SHA-256 files.


Hermes Desktop plugin for automatic OFF/ON Multi-Token Prediction A/B comparisons across **user-selected, compatible** locally managed GGUF models, without locking to Gemma or one quantization. Supported models with external MTP GGUF heads and models with confirmed embedded MTP metadata/native presets may be tested. Optional mmproj enables image tasks; text-only models use four tasks. A compatible llama.cpp engine and model/head combination are required; the plugin cannot add MTP to models that do not support it.

**New in v0.3.2:** Automatic adjacent-folder mmproj discovery with a confirm-before-link picker, native folder browse for projectors in another folder, and explicit GGUF-metadata-verified green embedded MTP status (native preset-only evidence is marked unverified). The automatic suggestions do not prove vision compatibility.

**Previously:** model picker, explicit per-model companion links, supported/unsupported indicators, controlled selected-model preset overrides, byte-exact restoration and recovery marker. RU/EN UI preserved. The original four-language README and real v0.2.1 benchmark screenshot are retained.

The last real Windows benchmarks were performed on v0.2.1 and one Gemma setup; **v0.3.2 remains experimental and has not yet been validated on other models or Windows Hermes**. Offline CI checks cannot prove engine compatibility. Existing user chats, cloud provider configuration and Lifecycle Fix are not modified.

**Packaging update:** Source SHA manifest and mandatory SHA256SUMS are removed. Editing files no longer requires rebuilding checksum lists. CI validates executable tests, file structure and ZIP contents directly.

## Release files

- `Hermes_MTP_Lab_v0.3.2_PORTABLE_INSTALL.zip` — complete plugin and Windows installer.
- `Hermes_MTP_Lab_v0.3.2_FULL_SOURCE.zip` — complete source project, CI, tests and documentation.

**Do not publish as a stable release until real Hermes Desktop model selection, A/B restore and compatible MTP trials succeed.**
