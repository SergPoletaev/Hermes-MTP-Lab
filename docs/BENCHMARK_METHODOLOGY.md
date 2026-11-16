# Benchmark methodology — Hermes MTP Lab v0.4.0

## Controlled run

The benchmark uses **one user-selected MTP-compatible**, Hermes-managed local GGUF model with **four text tasks** or **six tasks** when a valid `mmproj` is linked. It preserves the user's exact preset bytes in a local recovery backup, temporarily changes only the selected preset, and restores the original bytes afterwards. It never modifies installed GPU drivers, Hermes cloud providers, Chat Share, or chat messages.

**Quick = one cycle:** two OFF and two ON requests per task, **16 text-only or 24 vision-capable measurements** (plus warm-ups). **Extended = three cycles:** 48 text-only or 72 vision-capable measurements. Phase order is OFF → ON in cycles 1/3 and ON → OFF in cycle 2. Each phase executes two replicas of each task so that OFF/OFF, ON/ON and OFF/ON reproducibility can be reported. One warm-up is excluded per phase switch. Large offloaded GGUFs may require hours; progress is measured requests, not fabricated per-stage loading percentages.

Greedy decoding uses `temperature=0`, `top_k=1`, `top_p=1`, `min_p=0`, `repeat_penalty=1`, `seed=12345`, `cache_prompt=false`. The requested context is `min(native ctx-size, 32768)`, minimum 2048. `max_tokens` is task-specific: code 1024, network/narrative 768, structured/vision 512. If `finish_reason=length` (or a legacy response consumes the cap with no `finish_reason`), the plugin retries the response once, doubling the limit where possible to at most 2048 and leaving room for the prompt. If it is still truncated, quality is marked **incomplete**, not correct. Only the final attempt is counted toward speed; total elapsed time and number of attempts are also recorded. Runs are bounded by the server's request timeout and can be cancelled after an in-flight request finishes.

## Measurements and parity

Prometheus `/metrics` counters yield decode tokens, decode seconds, prompt counters and MTP drafted/accepted token deltas. `valid` means valid speed and observed expected MTP counters, **not** correct content. Median, median absolute deviation (MAD), minimum and maximum tok/s are reported per workload/phase. CPU, GPU, model quantization, KV, CPU cache, context, token budgets, draft acceptance and system load can strongly affect throughput. Speedup values remain descriptive until effective configurations and repeatability are established.

The plugin stores **separate hashes and original texts for visible `content` and `reasoning_content`**. `comparisons.json` records `visible_equal`, `reasoning_equal` and visible-string similarity for OFF/OFF, ON/ON and OFF/ON. Responses are compared within the same task/cycle/replica index; hash inequality is never automatically labeled poor model quality. A quantized model and speculative batching can have near-tie numerical differences even under greedy decoding. Model answers are saved to `answers.jsonl` for manual inspection; this contains benchmark output and should be reviewed **before sharing**. There is no cloud grader.

## Quality checks

- **Deterministic arithmetic (`structured`)**: expected accepted inventory is red **380**, blue **203**, green **206**, total **789**. The output JSON integer fields must match. The prompt fixes those keys.
- **Reference photograph (`grounding`)**: checks that the tent card is read as **TEST 47** and that the notebook stack is described in top-to-bottom **red, green, yellow** order. This is an explicit, narrow reference-word check, *not* a complete visual-quality grade.
- **Generated Python (`code`)**: the task requests `merge_intervals(intervals)` with timezone-aware UTC output, overlap/touching merges and input validation. The plugin runs seven fixed unit tests **only** inside an already installed, cached `python:3.13-alpine` Docker Linux container with no network, read-only root, non-root UID, no Linux capabilities, memory/CPU/PID limits, and a timeout. No image is pulled automatically. If Docker or this exact image is unavailable, code passes static syntax checks but its quality is **unverified**. No generated model code is executed on the Windows host.
- **Open-ended technical text, story and image description**: flagged `manual_review`; automatic text heuristics do not claim factually reliable scores.
- **Incomplete output**: `incomplete` supersedes all grades when the token limit is hit after retry. Missing visible text is `unverified`, never `pass`.

Quality information is in `results.json`, `summary.md`, and the full response/quality entries in `answers.jsonl`. A **quality regression** is tracked when a reference-verified OFF answer passes and its paired ON answer fails. Otherwise mismatches are reported as diagnostic observations only.

## Hardware and engine diagnostics

The running Hermes child is identified via process ownership, its exact main-model path and port. `/metrics` readings use this child only. Reports capture: configured `--n-gpu-layers` / `-ngl`, `--spec-draft-ngl`, requested context, KV-cache formats, flash attention, batch/ubatch, `mmproj`, draft file identity, enabled MTP flags, engine `--version` when available, process RSS, and NVIDIA driver/GPU VRAM/utilization through **read-only** `nvidia-smi` calls when installed. GPU-wide used memory is labeled **global**; `process_vram_mib` is reported only when `nvidia-smi` exposes per-process values (often unavailable under Windows WDDM). The actual loaded count of GPU layers is not reliably exposed by this interface; **launcher GPU-layer flags are not mislabeled as actual offload**. Missing fields are null/unknown, never invented. No GPU settings are altered.

`hardware.json` contains local GGUF basenames, file sizes and **first-64-KiB** fingerprints of the main model, MTP head and optional projector. These are *not* full-file checksums and do *not* mathematically prove model/head compatibility; runtime MTP flag and accepted draft tokens are separately checked. Sensitive full model paths, auth tokens and local process ports are excluded from shareable configuration summaries.

## Scope and output

This is a **direct managed llama.cpp** benchmark, not an end-to-end Hermes Auto/Native/Text UI test. Generation is non-streaming; first-token/UI latency is not measured. Every run produces `results.json`, `results.csv`, `answers.jsonl`, `comparisons.json`, `hardware.json`, `task_summary.json`, `summary.md`. A stopped or failed run still produces partial results when possible; the original selected-model preset is restored after all outcomes and the recovery marker remains if restoration fails. MTP-head compatibility must be independently verified for each model/head/engine. Do not assume all GGUFs support MTP merely because they share a file extension.

This public repository contains no owner-side GitHub publisher files. GitHub Actions checks Python code, Desktop JS, Windows installer syntax, release contents and source file allowlisting; it cannot reproduce a live Hermes/NVIDIA workload on GitHub runners.
