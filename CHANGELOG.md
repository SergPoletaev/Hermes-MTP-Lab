# Changelog

## 0.3.3 — Companion picker and backend synchronization

- Model-independent MTP OFF/ON benchmark, with original Hermes preset restoration.
- Automatic mmproj and MTP-head candidates next to the selected model, without silently linking files.
- Native Hermes folder chooser for mmproj and MTP-head GGUF files stored elsewhere; no manual path entry needed.
- Projector results are included in the existing `/status` API to avoid a `/projectors` 404 after Desktop hot reload.
- Explicit Desktop/Python backend version synchronization warning and restart instruction.
- Embedded MTP verified by GGUF header metadata, native preset evidence shown separately, external MTP-head stated explicitly.
- RU/EN Desktop UI, four-language README, quick/full benchmark, reporting, crash recovery.
- Root-level `plugin.yaml` and `desktop/plugin.js` for direct Install from Git.
- Release archives validated with build tests; no manual SHA manifest.
