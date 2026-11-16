# Changelog

## 0.5.1 — Native GGUF picker and remembered directory

- Replaced both folder-grant dialogs (`ctx.files.requestFolder`) with supported native file-open dialogs (`ctx.os.pickOpenPath`).
- The MTP and mmproj fields each have an adjacent **Browse…** button restricted to GGUF. Picking a file fills its field; saving remains explicit.
- The last successfully used directory persists per plugin via `ctx.storage`; the initial browse location defaults to the selected Hermes model directory. Cancel leaves current entries unchanged.
- Added native picker interaction tests and aligned the installer, API, docs, README and release archives to v0.5.1.

## 0.5.0 — Fixed paired protocol, controllable reasoning and self-contained QA

- Default no-thinking request via llama.cpp chat-template parameters, plus optional native reasoning. Never silently assert that a template obeyed the request.
- Replaced oversized open-ended prompts with bounded, gradeable tasks; identical fixed generation budgets for paired OFF/ON, no adaptive regeneration.
- Separated absent launch flags from actual mismatches in comparability.json.
- Exported protocol.json containing exact prompts/greedy flags and copied reference photograph into vision run reports.
- Updated GUI strings and controls, REST API, multilingual README and test suite; preserved Windows installer and existing Hermes isolation.


## 0.4.0 — Paired quality, reproduction and hardware checks

- Implemented OFF/OFF, ON/ON and OFF/ON parity with separate visible/reasoning fields, output review files and 1-/3-cycle balanced runs.
- Adaptive 512–2048 completion limits, truncation detection, workload-specific reference checks and optional sandboxed code tests without host execution.
- Added median absolute deviation, read-only GPU/process instrumentation, engine/head fingerprints and explicit unknown metrics.
- Updated Desktop bilingual controls, Python regression suite, full documentation and deterministic releases without public publisher scripts.

## 0.3.3 — Companion picker, CI and complete repository publication

- Model-independent MTP OFF/ON benchmark, with original Hermes preset restoration.
- Automatic mmproj and MTP-head candidates next to the selected model, without silently linking files.
- Native Hermes folder chooser for mmproj and MTP-head GGUF files stored elsewhere; no manual path entry needed.
- Projector results are included in the existing `/status` API to avoid a `/projectors` 404 after Desktop hot reload.
- Explicit Desktop/Python backend version synchronization warning and restart instruction.
- Embedded MTP verified by GGUF header metadata, native preset evidence shown separately, external MTP-head stated explicitly.
- RU/EN Desktop UI, four-language README, quick/full benchmark, reporting, crash recovery.
- Root-level `plugin.yaml` and `desktop/plugin.js` for direct Install from Git.
- CI includes missing HTTPX `TestClient` dependency and verifies every approved source file.
- Native relative mmproj/MTP-head paths now resolve next to the selected model, with GGUF signature checks.
- Atomic single-benchmark guard avoids competing preset modifications on parallel start requests.
- Recovery markers now record the original MTP state; unknown legacy states are no longer falsely labelled OFF.
- CI is independent of owner-only Git publishing utilities; they are not shipped in the public repository.
- Release archives validated with build tests; no manual SHA manifest.
