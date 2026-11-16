# Architecture

```text
Hermes Desktop sidebar /mtp-lab
  ↕ Plugin SDK bridge (desktop/plugin.js)
Hermes Python plugin dashboard/plugin_api.py
  ↕ benchmark engine dashboard/bench_core.py
Hermes local runtime supervisor (must be owned by this backend)
  ↕ managed llama.cpp router and model child
Local /chat/completions and /metrics
```

The Git repository root is the self-contained Hermes hybrid plugin (`plugin.yaml`, `__init__.py`, `desktop/`, `dashboard/`). Hermes loads `desktop/plugin.js` for the sidebar route, and the Python API exposes `/status`, `/select`, `/configure`, `/start`, `/cancel`, `/toggle`, `/recover` within the Hermes plugin framework.

## Model-agnostic selection, pairing and recovery

`dashboard/model_support.py` reads **Hermes managed model presets** and the optional `model-companions.json` mapping. The user selects an exact model ID and can select a compatible separate MTP-head GGUF and optional vision projector using discovered choices or the native GGUF file picker; the last-used chooser directory is persisted via `ctx.storage` and defaults to the model folder. Nearby candidate files are ranked by filename but never automatically paired. Models with embedded MTP are eligible when the native preset or supported GGUF metadata confirms it. A missing projector simply removes image workloads; missing MTP support blocks the benchmark.

The benchmark copies the original `presets.ini` bytes to a unique backup, writes an interrupt-recovery marker, modifies **only the selected model section** for an OFF or ON phase, calls the existing `sup.reload_presets()` on the owned idle router, and verifies the child process flags plus speculative token acceptance. On completion it restores the exact original preset bytes and reloads the router. It does not alter unrelated model sections or reconfigure cloud providers. Manual toggles are temporary and may be reset by the native Hermes planner.

`model-companions.json` is only changed by an explicit user action saving a head/projector mapping; a backup of that file is created first. Declaring an MTP head does not prove architectural compatibility: actual llama.cpp loading and token acceptance remain mandatory.


## Limits

- The UI displays a stage timer and overall progress. It does not fabricate percentages for a model load, non-streaming response generation or separate model reasoning.
- Backend metrics are cumulative per-server counters; concurrent inference can make deltas unreliable. Run no other chat requests during the benchmark.
- The test context is the lesser of 32768 and the selected model native context. The report records discovered runtime parameters and warns when equality cannot be verified.
- Complete user-interface Auto/Native/Text performance testing requires separate tests against Hermes orchestration; this plugin only checks the local inference route.

## Repository validation and CI

The public repository contains the Hermes plugin, installers, documentation, tests and CI workflows only. Owner-side publishing credentials and publishing scripts are not part of the repository and are not CI dependencies. `requirements-ci.txt` supplies FastAPI and HTTPX for clean GitHub runners. The source builder uses the verifier’s explicit file allowlist; every release entry is compared byte-for-byte against the audited source. Deleting or excluding private publishing scripts must not make any CI job fail.

## v0.5.1 controlled evaluation

`dashboard/quality_eval.py` grades deterministic reference tasks, distinguishes open-ended manual reviews, and permits generated-code execution only in a cached restricted Docker container. `dashboard/hardware_diag.py` reads launcher/process state and optional NVIDIA telemetry without changing the engine. `dashboard/bench_core.py` runs two replicas in each OFF/ON phase with cycle-order reversal, captures separate visible and reasoning output, does not retry truncated outputs, restores selected preset bytes and writes nine report files plus the vision reference image when applicable. Missing system metrics are explicitly unknown.
